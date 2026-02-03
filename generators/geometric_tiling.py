"""Geometric Tiling generator (Preset C) for BusyBrainPaint.

Generates crisp mosaic / Islamic tile style mandalas using
regular tilings clipped to a circle.
"""

import math
from dataclasses import dataclass
from enum import Enum

import numpy as np

from .base import BaseGenerator, GeneratorParams, GeneratedPuzzle


class TilingType(Enum):
    """Types of regular tilings."""

    SQUARE = "square"
    HEXAGON = "hexagon"
    TRIANGLE = "triangle"


@dataclass
class GeometricTilingParams(GeneratorParams):
    """Parameters for Geometric Tiling generation."""

    tiling_type: TilingType = TilingType.HEXAGON
    cell_size: int = 32  # Size of each tile in pixels
    warp_strength: float = 0.0  # Polar warp (0-0.5)
    layer_count: int = 1  # Number of overlaid tiling layers


class GeometricTilingGenerator(BaseGenerator):
    """Generates geometric tiling mandala puzzles.

    Method:
    1. Build base tiling (hex/tri/square) in world coordinates
    2. Apply optional radial symmetry via polar warp
    3. Clip to circle
    4. Optionally overlay multiple tiling layers
    """

    name = "geometric_tiling"

    def __init__(self, params: GeometricTilingParams) -> None:
        """Initialize generator.

        Args:
            params: Geometric tiling parameters.
        """
        super().__init__(params)
        self.gt_params = params

    def generate(self) -> GeneratedPuzzle:
        """Generate a geometric tiling mandala puzzle.

        Returns:
            GeneratedPuzzle with region_ids and metadata.
        """
        width = self.params.width
        height = self.params.height

        # Generate base tiling
        if self.gt_params.tiling_type == TilingType.HEXAGON:
            region_ids = self._generate_hexagon_tiling(width, height)
        elif self.gt_params.tiling_type == TilingType.TRIANGLE:
            region_ids = self._generate_triangle_tiling(width, height)
        else:
            region_ids = self._generate_square_tiling(width, height)

        # Apply polar warp if specified
        if self.gt_params.warp_strength > 0:
            region_ids = self._apply_polar_warp(region_ids)

        # Handle multiple layers
        if self.gt_params.layer_count > 1:
            region_ids = self._add_layers(region_ids)

        # Clip to circle
        region_ids = self._clip_to_circle(region_ids)

        # Clean up tiny regions
        region_ids = self._cleanup_regions(region_ids, min_area=20)

        num_regions = int(np.max(region_ids)) + 1

        return GeneratedPuzzle(
            region_ids=region_ids,
            num_regions=num_regions,
            width=width,
            height=height,
            generator_name=self.name,
            params={
                "seed": self.params.seed,
                "symmetry_slices": self.params.symmetry_slices,
                "tiling_type": self.gt_params.tiling_type.value,
                "cell_size": self.gt_params.cell_size,
                "warp_strength": self.gt_params.warp_strength,
                "layer_count": self.gt_params.layer_count,
            },
        )

    def _generate_square_tiling(self, width: int, height: int) -> np.ndarray:
        """Generate a square tiling pattern.

        Args:
            width: Image width.
            height: Image height.

        Returns:
            Region ID array.
        """
        cell_size = self.gt_params.cell_size

        y_coords, x_coords = np.ogrid[:height, :width]

        # Compute cell indices
        cell_x = x_coords // cell_size
        cell_y = y_coords // cell_size

        # Compute unique cell ID
        cells_per_row = (width + cell_size - 1) // cell_size
        region_ids = cell_y * cells_per_row + cell_x

        return region_ids.astype(np.int32)

    def _generate_hexagon_tiling(self, width: int, height: int) -> np.ndarray:
        """Generate a hexagonal tiling pattern.

        Args:
            width: Image width.
            height: Image height.

        Returns:
            Region ID array.
        """
        cell_size = self.gt_params.cell_size

        # Hexagon geometry
        hex_width = cell_size
        hex_height = int(cell_size * math.sqrt(3) / 2)
        row_offset = hex_width * 0.5

        y_coords, x_coords = np.ogrid[:height, :width]
        y_grid = np.broadcast_to(y_coords, (height, width)).astype(np.float32)
        x_grid = np.broadcast_to(x_coords, (height, width)).astype(np.float32)

        # Compute row and apply offset for odd rows
        row = (y_grid / hex_height).astype(np.int32)
        x_offset = np.where(row % 2 == 1, row_offset, 0)

        # Compute column with offset
        col = ((x_grid - x_offset) / hex_width).astype(np.int32)

        # Compute unique hex ID
        cols_per_row = (width + hex_width) // hex_width + 1
        region_ids = row * cols_per_row + col

        return region_ids.astype(np.int32)

    def _generate_triangle_tiling(self, width: int, height: int) -> np.ndarray:
        """Generate a triangular tiling pattern.

        Args:
            width: Image width.
            height: Image height.

        Returns:
            Region ID array.
        """
        cell_size = self.gt_params.cell_size

        # Triangle geometry
        tri_width = cell_size
        tri_height = int(cell_size * math.sqrt(3) / 2)

        y_coords, x_coords = np.ogrid[:height, :width]
        y_grid = np.broadcast_to(y_coords, (height, width)).astype(np.float32)
        x_grid = np.broadcast_to(x_coords, (height, width)).astype(np.float32)

        # Compute row
        row = (y_grid / tri_height).astype(np.int32)

        # Compute base column
        col = (x_grid / (tri_width / 2)).astype(np.int32)

        # Determine if upward or downward triangle
        # Based on position within the parallelogram cell
        local_x = x_grid - col * (tri_width / 2)
        local_y = y_grid - row * tri_height

        # Diagonal check to determine triangle orientation
        is_upper = (local_x / (tri_width / 2) + local_y / tri_height) < 1

        # Encode row, col, and orientation into unique ID
        cols_per_row = (width * 2) // tri_width + 2
        base_id = row * cols_per_row * 2 + col * 2
        region_ids = np.where(is_upper, base_id, base_id + 1)

        return region_ids.astype(np.int32)

    def _apply_polar_warp(self, region_ids: np.ndarray) -> np.ndarray:
        """Apply polar coordinate warp for radial effect.

        Args:
            region_ids: Input region ID array.

        Returns:
            Warped region ID array.
        """
        height, width = region_ids.shape
        cx, cy = width / 2, height / 2
        strength = self.gt_params.warp_strength

        y_coords, x_coords = np.ogrid[:height, :width]
        y_grid = np.broadcast_to(y_coords, (height, width)).astype(np.float32)
        x_grid = np.broadcast_to(x_coords, (height, width)).astype(np.float32)

        # Convert to polar
        dx = x_grid - cx
        dy = y_grid - cy
        r = np.sqrt(dx * dx + dy * dy)
        theta = np.arctan2(dy, dx)

        # Apply warp: compress radially
        max_r = math.sqrt(cx * cx + cy * cy)
        r_warped = r * (1 + strength * np.sin(theta * self.params.symmetry_slices))

        # Convert back to cartesian
        src_x = (r_warped * np.cos(theta) + cx).astype(np.int32)
        src_y = (r_warped * np.sin(theta) + cy).astype(np.int32)

        # Clamp to bounds
        src_x = np.clip(src_x, 0, width - 1)
        src_y = np.clip(src_y, 0, height - 1)

        # Sample from warped coordinates
        return region_ids[src_y, src_x]

    def _add_layers(self, region_ids: np.ndarray) -> np.ndarray:
        """Add additional tiling layers with offset.

        Args:
            region_ids: Base layer region IDs.

        Returns:
            Combined region IDs from multiple layers.
        """
        height, width = region_ids.shape
        cell_size = self.gt_params.cell_size
        max_id = int(np.max(region_ids)) + 1

        result = region_ids.copy()

        for layer in range(1, self.gt_params.layer_count):
            # Offset for this layer
            offset_x = (cell_size // 2) * layer
            offset_y = (cell_size // 3) * layer

            # Generate offset tiling
            if self.gt_params.tiling_type == TilingType.HEXAGON:
                layer_ids = self._generate_hexagon_tiling(width + offset_x, height + offset_y)
            elif self.gt_params.tiling_type == TilingType.TRIANGLE:
                layer_ids = self._generate_triangle_tiling(width + offset_x, height + offset_y)
            else:
                layer_ids = self._generate_square_tiling(width + offset_x, height + offset_y)

            # Crop to original size
            layer_ids = layer_ids[offset_y:offset_y + height, offset_x:offset_x + width]

            # Combine: use layer to subdivide existing regions
            layer_ids = layer_ids + max_id
            max_id = int(np.max(layer_ids)) + 1

            # Create new regions where layers differ
            combined = result * max_id + layer_ids
            result = combined

        return self._remap_to_contiguous(result)
