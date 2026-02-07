"""Puzzle export functionality for BusyBrainPaint generators."""

import json
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


def assign_region_colors(
    puzzle: GeneratedPuzzle,
    num_colors: int,
    region_ids: np.ndarray,
) -> list[int]:
    """Assign colors to regions using graph coloring.

    Ensures adjacent regions have different colors when possible.

    Args:
        puzzle: Generated puzzle data.
        num_colors: Number of colors available.
        region_ids: Region ID array.

    Returns:
        List mapping region_id -> color_index.
    """
    num_regions = puzzle.num_regions
    height, width = region_ids.shape

    # Build adjacency graph
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

    # Greedy graph coloring
    import random
    rng = random.Random(puzzle.params.get("seed"))

    colors = [-1] * num_regions
    for region in range(num_regions):
        used = {colors[n] for n in adj[region] if colors[n] >= 0}
        available = [c for c in range(num_colors) if c not in used]
        if available:
            colors[region] = rng.choice(available)
        else:
            colors[region] = rng.randint(0, num_colors - 1)

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

    # Create puzzle.json
    puzzle_json = {
        "version": 1,
        "width": puzzle.width,
        "height": puzzle.height,
        "palette": palette_data,
        "region_color": region_colors,
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
