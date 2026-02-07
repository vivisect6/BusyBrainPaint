"""Puzzle loader for BusyBrainPaint.

Loads puzzle assets (region_ids.png + puzzle.json) and builds runtime data structures.
"""

import json
from pathlib import Path

import numpy as np
from PIL import Image


def load_region_ids(path: Path) -> np.ndarray:
    """Load region ID map from PNG image.

    Args:
        path: Path to region_ids.png file.

    Returns:
        2D numpy array of integer region IDs (HxW).
        Encoding: id = r + (g << 8) + (b << 16)
    """
    img = Image.open(path).convert("RGB")
    arr = np.array(img, dtype=np.uint32)
    region_ids = arr[:, :, 0] + (arr[:, :, 1] << 8) + (arr[:, :, 2] << 16)
    return region_ids


def load_puzzle_json(path: Path) -> dict:
    """Load puzzle metadata from JSON file.

    Args:
        path: Path to puzzle.json file.

    Returns:
        Dictionary containing:
        - version: format version
        - width, height: puzzle dimensions
        - palette: list of {"color": [r,g,b], "number": int}
        - region_color: list mapping region_id -> palette_index
        - generator: optional dict with preset/params/seed
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def remap_region_ids(region_ids: np.ndarray) -> tuple[np.ndarray, dict[int, int]]:
    """Remap region IDs to contiguous range 0..N-1.

    Args:
        region_ids: Original region ID map.

    Returns:
        Tuple of (remapped array, mapping from old_id -> new_id).
    """
    unique_ids = np.unique(region_ids)
    old_to_new = {old_id: new_id for new_id, old_id in enumerate(unique_ids)}

    remapped = np.zeros_like(region_ids)
    for old_id, new_id in old_to_new.items():
        remapped[region_ids == old_id] = new_id

    return remapped, old_to_new


def build_region_runs(region_ids: np.ndarray, num_regions: int) -> list[list[tuple[int, int, int]]]:
    """Build run-length spans for each region.

    Args:
        region_ids: 2D array of region IDs.
        num_regions: Total number of regions.

    Returns:
        List where region_runs[region_id] = [(y, x_start, x_end), ...]
    """
    height, width = region_ids.shape
    region_runs: list[list[tuple[int, int, int]]] = [[] for _ in range(num_regions)]

    for y in range(height):
        row = region_ids[y]
        x = 0
        while x < width:
            region_id = row[x]
            x_start = x
            while x < width and row[x] == region_id:
                x += 1
            x_end = x
            region_runs[region_id].append((y, x_start, x_end))

    return region_runs


def compute_region_stats(
    region_runs: list[list[tuple[int, int, int]]]
) -> tuple[list[int], list[tuple[int, int, int, int]], list[tuple[float, float]]]:
    """Compute area, bounding box, and centroid for each region.

    Args:
        region_runs: Run-length spans per region.

    Returns:
        Tuple of (areas, bboxes, centroids) where:
        - areas[region_id] = pixel count
        - bboxes[region_id] = (min_x, min_y, max_x, max_y)
        - centroids[region_id] = (cx, cy)
    """
    num_regions = len(region_runs)
    areas: list[int] = []
    bboxes: list[tuple[int, int, int, int]] = []
    centroids: list[tuple[float, float]] = []

    for region_id in range(num_regions):
        runs = region_runs[region_id]
        if not runs:
            areas.append(0)
            bboxes.append((0, 0, 0, 0))
            centroids.append((0.0, 0.0))
            continue

        area = 0
        sum_x = 0.0
        sum_y = 0.0
        min_x = float("inf")
        min_y = float("inf")
        max_x = float("-inf")
        max_y = float("-inf")

        for y, x_start, x_end in runs:
            run_len = x_end - x_start
            area += run_len

            # Centroid contribution: sum of all x coords in run
            sum_x += (x_start + x_end - 1) / 2.0 * run_len
            sum_y += y * run_len

            min_x = min(min_x, x_start)
            max_x = max(max_x, x_end - 1)
            min_y = min(min_y, y)
            max_y = max(max_y, y)

        areas.append(area)
        bboxes.append((int(min_x), int(min_y), int(max_x), int(max_y)))
        centroids.append((sum_x / area, sum_y / area))

    return areas, bboxes, centroids


def build_adjacency(region_ids: np.ndarray, num_regions: int) -> list[set[int]]:
    """Build adjacency graph for regions.

    Args:
        region_ids: 2D array of region IDs.
        num_regions: Total number of regions.

    Returns:
        List where adj[region_id] = set of neighboring region IDs.
    """
    height, width = region_ids.shape
    adj: list[set[int]] = [set() for _ in range(num_regions)]

    # Check horizontal adjacency
    for y in range(height):
        for x in range(width - 1):
            r1 = region_ids[y, x]
            r2 = region_ids[y, x + 1]
            if r1 != r2:
                adj[r1].add(r2)
                adj[r2].add(r1)

    # Check vertical adjacency
    for y in range(height - 1):
        for x in range(width):
            r1 = region_ids[y, x]
            r2 = region_ids[y + 1, x]
            if r1 != r2:
                adj[r1].add(r2)
                adj[r2].add(r1)

    return adj


class Puzzle:
    """Runtime puzzle data structure."""

    def __init__(
        self,
        region_ids: np.ndarray,
        palette: list[tuple[int, int, int]],
        palette_numbers: list[int],
        region_color: list[int],
        region_runs: list[list[tuple[int, int, int]]],
        region_area: list[int],
        region_bbox: list[tuple[int, int, int, int]],
        region_centroid: list[tuple[float, float]],
        adj: list[set[int]],
        width: int,
        height: int,
    ):
        """Initialize puzzle with precomputed data.

        Args:
            region_ids: 2D array mapping pixels to region IDs.
            palette: List of RGB tuples for each palette entry.
            palette_numbers: Display number for each palette entry.
            region_color: Mapping from region_id to palette_index.
            region_runs: Run-length spans per region.
            region_area: Pixel count per region.
            region_bbox: Bounding box per region (min_x, min_y, max_x, max_y).
            region_centroid: Center point per region (cx, cy).
            adj: Adjacency graph (neighbors per region).
            width: Puzzle width in pixels.
            height: Puzzle height in pixels.
        """
        self.region_ids = region_ids
        self.palette = palette
        self.palette_numbers = palette_numbers
        self.region_color = region_color
        self.region_runs = region_runs
        self.region_area = region_area
        self.region_bbox = region_bbox
        self.region_centroid = region_centroid
        self.adj = adj
        self.width = width
        self.height = height
        self.num_regions = len(region_area)

        # Runtime state
        self.filled: list[bool] = [False] * self.num_regions


def load_puzzle(puzzle_dir: Path) -> Puzzle:
    """Load a complete puzzle from directory.

    Args:
        puzzle_dir: Directory containing puzzle.json and region_ids.png.

    Returns:
        Fully initialized Puzzle object with precomputed data.
    """
    # Load raw data
    region_ids_path = puzzle_dir / "region_ids.png"
    puzzle_json_path = puzzle_dir / "puzzle.json"

    region_ids = load_region_ids(region_ids_path)
    puzzle_data = load_puzzle_json(puzzle_json_path)

    # Remap to contiguous IDs
    region_ids, id_mapping = remap_region_ids(region_ids)
    num_regions = len(id_mapping)

    # Remap region_color if needed
    region_color_raw = puzzle_data["region_color"]
    region_color = [0] * num_regions
    for old_id, new_id in id_mapping.items():
        if old_id < len(region_color_raw):
            region_color[new_id] = region_color_raw[old_id]

    # Extract palette
    palette: list[tuple[int, int, int]] = []
    palette_numbers: list[int] = []
    for entry in puzzle_data["palette"]:
        color = entry["color"]
        palette.append((color[0], color[1], color[2]))
        palette_numbers.append(entry["number"])

    # Precompute region data
    region_runs = build_region_runs(region_ids, num_regions)
    region_area, region_bbox, region_centroid = compute_region_stats(region_runs)
    adj = build_adjacency(region_ids, num_regions)

    puzzle = Puzzle(
        region_ids=region_ids,
        palette=palette,
        palette_numbers=palette_numbers,
        region_color=region_color,
        region_runs=region_runs,
        region_area=region_area,
        region_bbox=region_bbox,
        region_centroid=region_centroid,
        adj=adj,
        width=puzzle_data["width"],
        height=puzzle_data["height"],
    )

    # Pre-fill the border region (pixels outside the circle).
    # Its centroid falls at the image center due to corner symmetry,
    # which would cause a stray number to render in the middle.
    border_region = int(region_ids[0, 0])
    puzzle.filled[border_region] = True

    return puzzle
