"""Puzzle export functionality for BusyBrainPaint generators."""

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image

from .base import GeneratedPuzzle, BaseGenerator


# Default palette colors (vibrant, distinguishable)
DEFAULT_PALETTE = [
    (231, 76, 60),    # Red
    (46, 204, 113),   # Green
    (52, 152, 219),   # Blue
    (241, 196, 15),   # Yellow
    (155, 89, 182),   # Purple
    (230, 126, 34),   # Orange
    (26, 188, 156),   # Teal
    (236, 240, 241),  # Light gray
    (52, 73, 94),     # Dark blue-gray
    (231, 130, 132),  # Light red
    (125, 206, 160),  # Light green
    (133, 193, 233),  # Light blue
]


def generate_palette(num_colors: int) -> list[tuple[int, int, int]]:
    """Generate a color palette.

    Args:
        num_colors: Number of colors needed.

    Returns:
        List of RGB tuples.
    """
    if num_colors <= len(DEFAULT_PALETTE):
        return DEFAULT_PALETTE[:num_colors]

    # Generate additional colors by interpolation
    palette = list(DEFAULT_PALETTE)
    while len(palette) < num_colors:
        # Add variations of existing colors
        base_idx = len(palette) % len(DEFAULT_PALETTE)
        base = DEFAULT_PALETTE[base_idx]
        # Lighten or darken
        factor = 0.7 if (len(palette) // len(DEFAULT_PALETTE)) % 2 == 0 else 1.3
        new_color = tuple(max(0, min(255, int(c * factor))) for c in base)
        palette.append(new_color)

    return palette[:num_colors]


def _compute_centroids(
    region_ids: np.ndarray,
    num_regions: int,
) -> np.ndarray:
    """Compute region centroids using vectorized bincount.

    Args:
        region_ids: HxW int array of region IDs.
        num_regions: Total number of regions.

    Returns:
        Array of shape (num_regions, 2) with (cx, cy) per region.
    """
    height, width = region_ids.shape
    flat = region_ids.ravel()
    y_coords, x_coords = np.mgrid[:height, :width]

    counts = np.bincount(flat, minlength=num_regions).astype(np.float64)
    counts = np.maximum(counts, 1.0)  # avoid division by zero
    sum_x = np.bincount(flat, weights=x_coords.ravel(), minlength=num_regions)
    sum_y = np.bincount(flat, weights=y_coords.ravel(), minlength=num_regions)

    centroids = np.stack([sum_x / counts, sum_y / counts], axis=-1)
    return centroids


def _build_adjacency(
    region_ids: np.ndarray,
    num_regions: int,
) -> list[set[int]]:
    """Build region adjacency graph from region ID map.

    Args:
        region_ids: HxW int array of region IDs.
        num_regions: Total number of regions.

    Returns:
        List where adj[i] is the set of region IDs adjacent to region i.
    """
    height, width = region_ids.shape
    adj: list[set[int]] = [set() for _ in range(num_regions)]

    for y in range(height):
        for x in range(width - 1):
            r1, r2 = int(region_ids[y, x]), int(region_ids[y, x + 1])
            if r1 != r2 and r1 < num_regions and r2 < num_regions:
                adj[r1].add(r2)
                adj[r2].add(r1)

    for y in range(height - 1):
        for x in range(width):
            r1, r2 = int(region_ids[y, x]), int(region_ids[y + 1, x])
            if r1 != r2 and r1 < num_regions and r2 < num_regions:
                adj[r1].add(r2)
                adj[r2].add(r1)

    return adj


def assign_region_colors(
    puzzle: GeneratedPuzzle,
    num_colors: int,
    region_ids: np.ndarray,
) -> list[int]:
    """Assign colors to regions using structure-aware grouping.

    Groups symmetric counterparts together so they share the same color,
    then assigns colors cycling by radial distance with adjacency constraints.

    Args:
        puzzle: Generated puzzle data.
        num_colors: Number of colors available.
        region_ids: Region ID array.

    Returns:
        List mapping region_id -> color_index.
    """
    num_regions = puzzle.num_regions
    height, width = region_ids.shape
    symmetry_slices = puzzle.params.get("symmetry_slices", 1)

    # Compute centroids and adjacency
    centroids = _compute_centroids(region_ids, num_regions)
    adj = _build_adjacency(region_ids, num_regions)

    # Puzzle center
    cx, cy = width / 2.0, height / 2.0

    # Convert centroids to polar coordinates
    dx = centroids[:, 0] - cx
    dy = centroids[:, 1] - cy
    r = np.sqrt(dx * dx + dy * dy)
    theta = np.arctan2(dy, dx)  # -pi to pi

    # Normalize radius
    max_r = max(width, height) / 2.0
    r_norm = r / max_r  # 0 to ~1

    # Fold theta by symmetry to group symmetric counterparts
    if symmetry_slices > 1:
        wedge = 2.0 * math.pi / symmetry_slices
        # Shift theta to [0, 2*pi) then fold into [0, wedge)
        theta_folded = (theta + math.pi) % wedge
        theta_folded_norm = theta_folded / wedge  # 0 to 1
    else:
        theta_folded_norm = (theta + math.pi) / (2.0 * math.pi)

    # Quantize into bins to form equivalence groups
    r_bins = 20
    t_bins = max(5, symmetry_slices)
    r_bin = np.round(r_norm * r_bins).astype(int)
    t_bin = np.round(theta_folded_norm * t_bins).astype(int)

    # Identify special regions
    border_region = int(region_ids[0, 0])

    # Lead region: adjacent to >50% of all regions (stained glass lead lines)
    lead_region = -1
    half_regions = num_regions / 2.0
    for rid in range(num_regions):
        if len(adj[rid]) > half_regions:
            lead_region = rid
            break

    # Center region: closest centroid to puzzle center (excluding border/lead)
    center_region = -1
    min_center_dist = float("inf")
    for rid in range(num_regions):
        if rid == border_region or rid == lead_region:
            continue
        dist = r[rid]
        if dist < min_center_dist:
            min_center_dist = dist
            center_region = rid

    # Assign regions to groups
    region_to_group: dict[int, int] = {}
    group_members: dict[int, list[int]] = defaultdict(list)
    next_group = 0

    # Special regions get their own groups
    special_group_ids: dict[int, int] = {}
    for rid in (border_region, lead_region, center_region):
        if rid >= 0:
            gid = next_group
            next_group += 1
            region_to_group[rid] = gid
            group_members[gid].append(rid)
            special_group_ids[rid] = gid

    # Group remaining regions by (r_bin, t_bin)
    bin_to_group: dict[tuple[int, int], int] = {}
    for rid in range(num_regions):
        if rid in region_to_group:
            continue
        key = (int(r_bin[rid]), int(t_bin[rid]))
        if key not in bin_to_group:
            bin_to_group[key] = next_group
            next_group += 1
        gid = bin_to_group[key]
        region_to_group[rid] = gid
        group_members[gid].append(rid)

    num_groups = next_group

    # Compute group centroids (average r and theta of members)
    group_r = np.zeros(num_groups)
    group_t = np.zeros(num_groups)
    for gid, members in group_members.items():
        group_r[gid] = np.mean([r_norm[m] for m in members])
        group_t[gid] = np.mean([theta_folded_norm[m] for m in members])

    # Build group adjacency
    group_adj: list[set[int]] = [set() for _ in range(num_groups)]
    for rid in range(num_regions):
        gid = region_to_group[rid]
        for neighbor in adj[rid]:
            ngid = region_to_group[neighbor]
            if ngid != gid:
                group_adj[gid].add(ngid)

    # Sort groups by (radius, angle) for radial color cycling
    group_order = sorted(
        range(num_groups),
        key=lambda g: (round(group_r[g] * 5), group_t[g]),
    )

    # Assign colors to groups, cycling through palette by radius
    group_colors = [-1] * num_groups
    color_cursor = 0

    for gid in group_order:
        used = {group_colors[ng] for ng in group_adj[gid] if group_colors[ng] >= 0}

        # Try the next cursor color first (for visual cycling pattern)
        if color_cursor % num_colors not in used:
            group_colors[gid] = color_cursor % num_colors
        else:
            # Find nearest available color to cursor position
            for offset in range(num_colors):
                candidate = (color_cursor + offset) % num_colors
                if candidate not in used:
                    group_colors[gid] = candidate
                    break
            else:
                # All colors conflict; pick the cursor color anyway
                group_colors[gid] = color_cursor % num_colors

        color_cursor += 1

    # Map group colors back to individual regions
    colors = [0] * num_regions
    for rid in range(num_regions):
        gid = region_to_group[rid]
        colors[rid] = group_colors[gid]

    return colors


def export_puzzle(
    puzzle: GeneratedPuzzle,
    output_dir: Path,
    num_colors: int = 6,
    palette: Sequence[tuple[int, int, int]] | None = None,
) -> None:
    """Export a generated puzzle to the standard format.

    Creates:
    - puzzle.json: Metadata and color assignments
    - region_ids.png: Region ID map encoded as RGB

    Args:
        puzzle: Generated puzzle to export.
        output_dir: Directory to write files to.
        num_colors: Number of colors in palette.
        palette: Optional custom palette (RGB tuples).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate or use provided palette
    if palette is None:
        palette = generate_palette(num_colors)
    else:
        palette = list(palette)

    # Assign colors to regions
    region_colors = assign_region_colors(puzzle, num_colors, puzzle.region_ids)

    # Create palette with numbers
    palette_data = []
    for i, color in enumerate(palette):
        palette_data.append({
            "color": list(color),
            "number": i + 1,
        })

    # Identify non-playable regions (border + structural framework)
    num_regions = puzzle.num_regions
    region_ids = puzzle.region_ids
    non_playable: list[int] = []

    # Border region (outside the circle for mandalas)
    border_region = int(region_ids[0, 0])
    non_playable.append(border_region)

    # Structural "framework" regions (e.g. stained glass lead lines)
    adj = _build_adjacency(region_ids, num_regions)
    half = num_regions / 2.0
    for rid in range(num_regions):
        if rid != border_region and len(adj[rid]) > half:
            non_playable.append(rid)

    # Create puzzle.json
    puzzle_json = {
        "version": 1,
        "width": puzzle.width,
        "height": puzzle.height,
        "palette": palette_data,
        "region_color": region_colors,
        "non_playable": non_playable,
        "generator": {
            "name": puzzle.generator_name,
            "params": puzzle.params,
        },
    }

    with open(output_dir / "puzzle.json", "w", encoding="utf-8") as f:
        json.dump(puzzle_json, f, indent=2)

    # Create region_ids.png
    # Encoding: id = r + (g << 8) + (b << 16)
    region_ids = puzzle.region_ids.astype(np.uint32)
    r = (region_ids & 0xFF).astype(np.uint8)
    g = ((region_ids >> 8) & 0xFF).astype(np.uint8)
    b = ((region_ids >> 16) & 0xFF).astype(np.uint8)

    rgb = np.stack([r, g, b], axis=-1)
    img = Image.fromarray(rgb, mode="RGB")
    img.save(output_dir / "region_ids.png")

    print(f"Exported puzzle to {output_dir}")
    print(f"  Size: {puzzle.width}x{puzzle.height}")
    print(f"  Regions: {puzzle.num_regions}")
    print(f"  Colors: {num_colors}")


def create_puzzle(
    generator: BaseGenerator,
    output_dir: Path,
    num_colors: int = 6,
    palette: Sequence[tuple[int, int, int]] | None = None,
) -> GeneratedPuzzle:
    """Generate and export a puzzle in one step.

    Args:
        generator: Initialized generator to use.
        output_dir: Directory to write files to.
        num_colors: Number of colors in palette.
        palette: Optional custom palette (RGB tuples).

    Returns:
        The generated puzzle data.
    """
    puzzle = generator.generate()
    export_puzzle(puzzle, output_dir, num_colors, palette=palette)
    return puzzle
