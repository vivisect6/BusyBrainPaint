#!/usr/bin/env python3
"""Convert an image into a paint-by-numbers puzzle for BusyBrainPaint.

Produces the same puzzle.json + region_ids.png format that the game loads.

Usage:
    python image_to_puzzle.py photo.jpg
    python image_to_puzzle.py photo.jpg puzzles/current --colors 16 --size 1024
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import label
from scipy.spatial import cKDTree

from generators.cleanup import cleanup_regions


def load_and_resize(path: str, max_edge: int) -> Image.Image:
    """Load an image and resize so the longest edge equals max_edge.

    Args:
        path: Path to the input image.
        max_edge: Target size for the longest edge in pixels.

    Returns:
        Resized RGB PIL Image.
    """
    img = Image.open(path).convert("RGB")
    w, h = img.size
    scale = max_edge / max(w, h)
    new_w = max(1, round(w * scale))
    new_h = max(1, round(h * scale))
    return img.resize((new_w, new_h), Image.LANCZOS)


def quantize_image(
    img: Image.Image, num_colors: int, blur_radius: float
) -> tuple[Image.Image, list[tuple[int, int, int]]]:
    """Quantize an image to a fixed number of colors.

    Args:
        img: Input RGB image.
        num_colors: Number of palette colors.
        blur_radius: Gaussian blur radius applied before quantization (0 to skip).

    Returns:
        Tuple of (quantized RGB image, list of palette RGB tuples).
    """
    if blur_radius > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # Quantize to palette
    quantized = img.quantize(colors=num_colors, method=Image.Quantize.MEDIANCUT)

    # Extract the palette colors
    raw_palette = quantized.getpalette()  # flat [r,g,b, r,g,b, ...]
    palette: list[tuple[int, int, int]] = []
    for i in range(num_colors):
        r, g, b = raw_palette[i * 3 : i * 3 + 3]
        palette.append((r, g, b))

    # Convert back to RGB for pixel access
    quantized_rgb = quantized.convert("RGB")
    return quantized_rgb, palette


def build_region_ids(
    quantized_rgb: Image.Image,
    palette: list[tuple[int, int, int]],
) -> np.ndarray:
    """Label connected components of same-color pixels.

    Args:
        quantized_rgb: Quantized RGB image.
        palette: List of palette colors.

    Returns:
        2D int array where each pixel has a unique region ID.
    """
    arr = np.array(quantized_rgb, dtype=np.uint8)
    h, w = arr.shape[:2]

    # Map each pixel to its palette index
    palette_arr = np.array(palette, dtype=np.uint8)  # (num_colors, 3)
    # Compute color index per pixel by matching against palette
    pixel_colors = arr.reshape(-1, 3)  # (h*w, 3)
    # Broadcast comparison: (h*w, 1, 3) == (1, num_colors, 3) -> all match
    matches = np.all(
        pixel_colors[:, np.newaxis, :] == palette_arr[np.newaxis, :, :],
        axis=2,
    )  # (h*w, num_colors)
    color_index_map = np.argmax(matches, axis=1).reshape(h, w)

    # Label connected components per color
    region_ids = np.zeros((h, w), dtype=np.int32)
    next_id = 0
    structure = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])  # 4-connected

    for color_idx in range(len(palette)):
        mask = color_index_map == color_idx
        if not np.any(mask):
            continue
        labels, num_features = label(mask, structure=structure)
        # Assign globally unique IDs (skip label 0 which is background)
        for lbl in range(1, num_features + 1):
            region_ids[labels == lbl] = next_id
            next_id += 1

    return region_ids


def build_region_color_map(
    region_ids: np.ndarray,
    quantized_rgb: Image.Image,
    palette: list[tuple[int, int, int]],
) -> list[int]:
    """Map each region to its dominant palette color index.

    Args:
        region_ids: Region ID map after cleanup.
        quantized_rgb: Quantized RGB image.
        palette: List of palette colors.

    Returns:
        List where region_color[region_id] = palette_index.
    """
    arr = np.array(quantized_rgb, dtype=np.uint8)
    num_regions = int(np.max(region_ids)) + 1
    palette_arr = np.array(palette, dtype=np.uint8)

    region_color = [0] * num_regions
    for rid in range(num_regions):
        mask = region_ids == rid
        if not np.any(mask):
            continue
        # Sample the dominant color from region pixels
        pixels = arr[mask]  # (N, 3)
        # Find mean color, then match to nearest palette entry
        mean_color = pixels.mean(axis=0)
        dists = np.sum((palette_arr.astype(float) - mean_color) ** 2, axis=1)
        region_color[rid] = int(np.argmin(dists))

    return region_color


def subdivide_regions(
    region_ids: np.ndarray,
    target_regions: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Subdivide large regions using Voronoi seeds to reach a target count.

    Regions whose area exceeds (total_pixels / target_regions) are split by
    scattering random seed points inside them and assigning each pixel to
    the nearest seed via a KD-tree query.

    Args:
        region_ids: Cleaned region ID map (contiguous 0..N-1).
        target_regions: Desired approximate total region count.
        rng: NumPy random generator for reproducibility.

    Returns:
        Region ID map with large regions subdivided (IDs not yet contiguous).
    """
    num_regions = int(np.max(region_ids)) + 1
    h, w = region_ids.shape
    total_pixels = h * w
    target_area = total_pixels / target_regions

    # Compute area per region
    areas = np.bincount(region_ids.ravel(), minlength=num_regions)

    result = region_ids.copy()
    next_id = num_regions

    for rid in range(num_regions):
        area = int(areas[rid])
        if area <= target_area * 1.5:
            continue

        # How many sub-regions to create
        num_splits = max(2, round(area / target_area))

        # Get all pixel coordinates for this region
        ys, xs = np.nonzero(region_ids == rid)
        coords = np.column_stack([xs, ys])  # (N, 2) as (x, y)

        # Pick random seed points from within the region
        seed_indices = rng.choice(len(coords), size=num_splits, replace=False)
        seeds = coords[seed_indices].astype(np.float64)

        # Assign each pixel to nearest seed
        tree = cKDTree(seeds)
        _, labels = tree.query(coords)

        # Write new IDs (first sub-region keeps original ID, rest get new ones)
        for sub_idx in range(num_splits):
            sub_mask = labels == sub_idx
            if sub_idx == 0:
                # Keep original rid
                pass
            else:
                sub_pixels = coords[sub_mask]
                result[sub_pixels[:, 1], sub_pixels[:, 0]] = next_id
                next_id += 1

    return result


def export_image_puzzle(
    region_ids: np.ndarray,
    palette: list[tuple[int, int, int]],
    region_color: list[int],
    output_dir: Path,
    source_path: str,
) -> None:
    """Write puzzle.json and region_ids.png for an image puzzle.

    Args:
        region_ids: Cleaned region ID map (contiguous 0..N-1).
        palette: List of RGB palette colors.
        region_color: Mapping region_id -> palette_index.
        output_dir: Directory to write output files.
        source_path: Original image path (stored in metadata).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    h, w = region_ids.shape
    num_regions = int(np.max(region_ids)) + 1

    palette_data = []
    for i, color in enumerate(palette):
        palette_data.append({
            "color": list(color),
            "number": i + 1,
        })

    puzzle_json = {
        "version": 1,
        "width": w,
        "height": h,
        "palette": palette_data,
        "region_color": region_color,
        "non_playable": [],
        "generator": {
            "name": "image",
            "params": {
                "source": os.path.basename(source_path),
            },
        },
    }

    with open(output_dir / "puzzle.json", "w", encoding="utf-8") as f:
        json.dump(puzzle_json, f, indent=2)

    # Encode region_ids.png: id = r + (g << 8) + (b << 16)
    ids = region_ids.astype(np.uint32)
    r = (ids & 0xFF).astype(np.uint8)
    g = ((ids >> 8) & 0xFF).astype(np.uint8)
    b = ((ids >> 16) & 0xFF).astype(np.uint8)
    rgb = np.stack([r, g, b], axis=-1)
    img = Image.fromarray(rgb)
    img.save(output_dir / "region_ids.png")

    print(f"Exported image puzzle to {output_dir}")
    print(f"  Source: {os.path.basename(source_path)}")
    print(f"  Size: {w}x{h}")
    print(f"  Regions: {num_regions}")
    print(f"  Colors: {len(palette)}")


def main() -> None:
    """Main entry point for the image-to-puzzle CLI."""
    parser = argparse.ArgumentParser(
        description="Convert an image into a paint-by-numbers puzzle for BusyBrainPaint",
    )
    parser.add_argument(
        "image_path",
        help="Input image (PNG, JPG, etc.)",
    )
    parser.add_argument(
        "output_dir",
        nargs="?",
        type=Path,
        default=Path("puzzles/current"),
        help="Output directory (default: puzzles/current)",
    )
    parser.add_argument(
        "--colors",
        type=int,
        default=12,
        choices=[6, 8, 12, 16, 24],
        help="Palette size (default: 12)",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=768,
        help="Target size for longest edge in pixels (default: 768)",
    )
    parser.add_argument(
        "--min-area",
        type=int,
        default=20,
        help="Min region area before merging (default: 20)",
    )
    parser.add_argument(
        "--blur",
        type=float,
        default=1.0,
        help="Pre-quantization blur radius, 0 to disable (default: 1.0)",
    )
    parser.add_argument(
        "--target-regions",
        type=int,
        default=300,
        help="Target region count; large regions are subdivided to reach this (default: 300)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible subdivision (default: random)",
    )

    args = parser.parse_args()

    print(f"Loading {args.image_path}...")
    img = load_and_resize(args.image_path, args.size)
    print(f"  Resized to {img.size[0]}x{img.size[1]}")

    print(f"Quantizing to {args.colors} colors...")
    quantized_rgb, palette = quantize_image(img, args.colors, args.blur)

    print("Labeling connected regions...")
    region_ids = build_region_ids(quantized_rgb, palette)
    raw_regions = int(np.max(region_ids)) + 1
    print(f"  Found {raw_regions} raw regions")

    print("Cleaning up regions...")
    region_ids = cleanup_regions(region_ids, min_area=args.min_area)
    clean_regions = int(np.max(region_ids)) + 1
    print(f"  {clean_regions} regions after cleanup")

    if args.target_regions > clean_regions:
        rng = np.random.default_rng(args.seed)
        print(f"Subdividing to ~{args.target_regions} regions...")
        region_ids = subdivide_regions(region_ids, args.target_regions, rng)
        region_ids = cleanup_regions(region_ids, min_area=args.min_area)
        final_regions = int(np.max(region_ids)) + 1
        print(f"  {final_regions} regions after subdivision")
    else:
        final_regions = clean_regions

    print("Assigning colors...")
    region_color = build_region_color_map(region_ids, quantized_rgb, palette)

    export_image_puzzle(
        region_ids, palette, region_color, args.output_dir, args.image_path
    )

    # Clear stale save file
    save_path = Path("saves/save.json")
    if save_path.exists():
        save_path.unlink()
        print("Cleared old save file")

    print("\nDone! Run 'python main.py' and hit Continue to play.")


if __name__ == "__main__":
    main()
