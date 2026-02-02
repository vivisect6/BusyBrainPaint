"""Generate stub puzzle assets for testing the loader."""

import json
from pathlib import Path

import numpy as np
from PIL import Image


def create_stub_puzzle(output_dir: Path, size: int = 128) -> None:
    """Create a simple stub puzzle with a grid pattern.

    Args:
        output_dir: Directory to write puzzle.json and region_ids.png.
        size: Puzzle dimensions (size x size pixels).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create a simple 4x4 grid of regions (16 regions total)
    # Plus a border region (region 0) and center circle (region 17)
    grid_cells = 4
    cell_size = size // grid_cells

    region_ids = np.zeros((size, size), dtype=np.uint32)

    # Fill grid cells (regions 1-16)
    for gy in range(grid_cells):
        for gx in range(grid_cells):
            region_id = gy * grid_cells + gx + 1
            y_start = gy * cell_size
            y_end = (gy + 1) * cell_size
            x_start = gx * cell_size
            x_end = (gx + 1) * cell_size
            region_ids[y_start:y_end, x_start:x_end] = region_id

    # Add a center circle (region 17)
    center = size // 2
    radius = size // 6
    for y in range(size):
        for x in range(size):
            if (x - center) ** 2 + (y - center) ** 2 < radius ** 2:
                region_ids[y, x] = 17

    # Count unique regions
    unique_regions = np.unique(region_ids)
    num_regions = len(unique_regions)

    # Create palette (6 colors for variety)
    palette = [
        {"color": [231, 76, 60], "number": 1},    # Red
        {"color": [46, 204, 113], "number": 2},   # Green
        {"color": [52, 152, 219], "number": 3},   # Blue
        {"color": [241, 196, 15], "number": 4},   # Yellow
        {"color": [155, 89, 182], "number": 5},   # Purple
        {"color": [230, 126, 34], "number": 6},   # Orange
    ]

    # Assign colors to regions (cycling through palette)
    region_color = [i % len(palette) for i in range(num_regions)]

    # Create puzzle.json
    puzzle_data = {
        "version": 1,
        "width": size,
        "height": size,
        "palette": palette,
        "region_color": region_color,
        "generator": {
            "preset": "stub",
            "params": {"grid_cells": grid_cells},
            "seed": 12345,
        },
    }

    with open(output_dir / "puzzle.json", "w", encoding="utf-8") as f:
        json.dump(puzzle_data, f, indent=2)

    # Encode region IDs as RGB PNG
    # id = r + (g << 8) + (b << 16)
    r = (region_ids & 0xFF).astype(np.uint8)
    g = ((region_ids >> 8) & 0xFF).astype(np.uint8)
    b = ((region_ids >> 16) & 0xFF).astype(np.uint8)

    rgb = np.stack([r, g, b], axis=-1)
    img = Image.fromarray(rgb, mode="RGB")
    img.save(output_dir / "region_ids.png")

    print(f"Created stub puzzle in {output_dir}")
    print(f"  Size: {size}x{size}")
    print(f"  Regions: {num_regions}")
    print(f"  Palette colors: {len(palette)}")


if __name__ == "__main__":
    output_dir = Path(__file__).parent / "puzzles" / "stub"
    create_stub_puzzle(output_dir)
