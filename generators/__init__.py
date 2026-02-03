"""Puzzle generators for BusyBrainPaint.

This module provides procedural puzzle generators for creating
mandala-style paint-by-numbers puzzles.

Available generators:
- VoronoiMandalaGenerator (Preset A): Stained-glass organic cells
- PolarHarmonicsGenerator (Preset B): Classic petals, rings, spokes
- GeometricTilingGenerator (Preset C): Crisp mosaic patterns
- StainedGlassGenerator (Preset D): Bold outlines, big fills
"""

from .base import BaseGenerator, GeneratorParams, GeneratedPuzzle
from .voronoi_mandala import VoronoiMandalaGenerator, VoronoiMandalaParams
from .polar_harmonics import PolarHarmonicsGenerator, PolarHarmonicsParams
from .geometric_tiling import GeometricTilingGenerator, GeometricTilingParams, TilingType
from .stained_glass import StainedGlassGenerator, StainedGlassParams
from .export import export_puzzle, create_puzzle, generate_palette

__all__ = [
    # Base classes
    "BaseGenerator",
    "GeneratorParams",
    "GeneratedPuzzle",
    # Generators
    "VoronoiMandalaGenerator",
    "VoronoiMandalaParams",
    "PolarHarmonicsGenerator",
    "PolarHarmonicsParams",
    "GeometricTilingGenerator",
    "GeometricTilingParams",
    "TilingType",
    "StainedGlassGenerator",
    "StainedGlassParams",
    # Export functions
    "export_puzzle",
    "create_puzzle",
    "generate_palette",
]


# Preset configurations for easy access
PRESETS = {
    "voronoi_mandala": {
        "generator": VoronoiMandalaGenerator,
        "params": VoronoiMandalaParams,
        "description": "Stained-glass / organic cell mandalas",
    },
    "polar_harmonics": {
        "generator": PolarHarmonicsGenerator,
        "params": PolarHarmonicsParams,
        "description": "Classic mandala petals, rosettes, rings",
    },
    "geometric_tiling": {
        "generator": GeometricTilingGenerator,
        "params": GeometricTilingParams,
        "description": "Crisp mosaic / Islamic tile patterns",
    },
    "stained_glass": {
        "generator": StainedGlassGenerator,
        "params": StainedGlassParams,
        "description": "Bold outlines, big satisfying fills",
    },
}


def get_generator(preset_name: str, **kwargs) -> BaseGenerator:
    """Create a generator instance by preset name.

    Args:
        preset_name: Name of the preset (e.g., "voronoi_mandala").
        **kwargs: Parameters to pass to the generator.

    Returns:
        Initialized generator instance.

    Raises:
        ValueError: If preset_name is not recognized.
    """
    if preset_name not in PRESETS:
        available = ", ".join(PRESETS.keys())
        raise ValueError(f"Unknown preset: {preset_name}. Available: {available}")

    preset = PRESETS[preset_name]
    params = preset["params"](**kwargs)
    return preset["generator"](params)
