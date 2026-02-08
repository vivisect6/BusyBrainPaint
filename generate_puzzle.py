#!/usr/bin/env python3
"""CLI script to generate puzzles for BusyBrainPaint.

Usage:
    python generate_puzzle.py [preset] [output_dir] [options]

Examples:
    python generate_puzzle.py voronoi_mandala puzzles/my_puzzle
    python generate_puzzle.py stained_glass puzzles/stained --size 512 --colors 8
"""

import argparse
from pathlib import Path

from generators import (
    get_generator,
    create_puzzle,
    PRESETS,
)


def main() -> None:
    """Main entry point for puzzle generation CLI."""
    parser = argparse.ArgumentParser(
        description="Generate mandala puzzles for BusyBrainPaint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available presets:
  voronoi_mandala  - Stained-glass / organic cell mandalas
  stained_glass    - Bold outlines, big satisfying fills
""",
    )

    parser.add_argument(
        "preset",
        choices=list(PRESETS.keys()),
        help="Generator preset to use",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Output directory for puzzle files",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=768,
        help="Puzzle size in pixels (default: 768)",
    )
    parser.add_argument(
        "--colors",
        type=int,
        default=6,
        help="Number of palette colors (default: 6)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--symmetry",
        type=int,
        default=8,
        help="Number of symmetry slices (default: 8)",
    )

    # Voronoi-specific options
    parser.add_argument(
        "--points",
        type=int,
        default=30,
        help="Point count for Voronoi generators (default: 30)",
    )
    parser.add_argument(
        "--relax",
        type=int,
        default=1,
        help="Lloyd relaxation iterations for Voronoi (default: 1)",
    )

    # Stained glass options
    parser.add_argument(
        "--outline",
        type=int,
        default=4,
        help="Outline thickness for stained glass (default: 4)",
    )

    args = parser.parse_args()

    # Build generator kwargs based on preset
    kwargs = {
        "width": args.size,
        "height": args.size,
        "seed": args.seed,
        "symmetry_slices": args.symmetry,
        "num_colors": args.colors,
    }

    if args.preset == "voronoi_mandala":
        kwargs["point_count"] = args.points
        kwargs["relax_iters"] = args.relax
    elif args.preset == "stained_glass":
        kwargs["point_count"] = args.points
        kwargs["outline_thickness"] = args.outline

    # Generate and export
    print(f"Generating {args.preset} puzzle...")
    generator = get_generator(args.preset, **kwargs)
    puzzle = create_puzzle(generator, args.output_dir, num_colors=args.colors)

    print(f"\nPuzzle generated successfully!")
    print(f"  Preset: {args.preset}")
    print(f"  Size: {puzzle.width}x{puzzle.height}")
    print(f"  Regions: {puzzle.num_regions}")
    print(f"  Colors: {args.colors}")
    print(f"  Output: {args.output_dir}")


if __name__ == "__main__":
    main()
