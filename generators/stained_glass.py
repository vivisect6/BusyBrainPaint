"""Stained Glass generator (Preset D) for BusyBrainPaint.

Generates bold stained glass style patterns with thick "lead" outlines
using Voronoi cells.
"""

import math
from dataclasses import dataclass

import numpy as np

from .base import BaseGenerator, GeneratorParams, GeneratedPuzzle


@dataclass
class StainedGlassParams(GeneratorParams):
    """Parameters for Stained Glass generation."""

    point_count: int = 25  # Number of glass cells
    outline_thickness: int = 4  # Thickness of "lead" lines
    edge_detail_boost: float = 0.5  # Extra points near edge (0-1)
    use_symmetry: bool = True  # Whether to use radial symmetry


class StainedGlassGenerator(BaseGenerator):
    """Generates stained glass style puzzles.

    Method:
    1. Generate Voronoi cells (optionally with symmetry)
    2. Render thick "lead" outlines between cells
    3. Each glass pane becomes a fillable region
    4. Lead lines form the background/border
    """

    name = "stained_glass"

    def __init__(self, params: StainedGlassParams) -> None:
        """Initialize generator.

        Args:
            params: Stained glass parameters.
        """
        super().__init__(params)
        self.sg_params = params

    def generate(self) -> GeneratedPuzzle:
        """Generate a stained glass puzzle.

        Returns:
            GeneratedPuzzle with region_ids and metadata.
        """
        width = self.params.width
        height = self.params.height
        cx, cy = width / 2, height / 2
        radius = min(width, height) / 2 - 2

        # Generate seed points
        if self.sg_params.use_symmetry:
            points = self._generate_symmetric_points(cx, cy, radius)
        else:
            points = self._generate_random_points(cx, cy, radius)

        # Compute Voronoi
        region_ids = self._compute_voronoi(points, width, height)

        # Add thick outlines (lead)
        region_ids = self._add_lead_outlines(region_ids)

        # Clip to circle
        region_ids = self._clip_to_circle(region_ids)

        # Clean up tiny regions (but keep lead as separate region)
        region_ids = self._cleanup_regions(region_ids, min_area=15)

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
                "point_count": self.sg_params.point_count,
                "outline_thickness": self.sg_params.outline_thickness,
                "edge_detail_boost": self.sg_params.edge_detail_boost,
                "use_symmetry": self.sg_params.use_symmetry,
            },
        )

    def _generate_symmetric_points(
        self, cx: float, cy: float, radius: float
    ) -> list[tuple[float, float]]:
        """Generate points with radial symmetry.

        Args:
            cx: Center X coordinate.
            cy: Center Y coordinate.
            radius: Mandala radius.

        Returns:
            List of (x, y) point coordinates.
        """
        points = []
        slices = self.params.symmetry_slices
        wedge_angle = 2 * math.pi / slices
        point_count = self.sg_params.point_count
        edge_boost = self.sg_params.edge_detail_boost

        # Generate points in the first wedge
        wedge_points = []
        points_per_wedge = max(1, point_count // slices)

        for _ in range(points_per_wedge):
            angle = self.rng.uniform(0, wedge_angle)

            # Random radius with edge bias
            r = self.rng.random()
            if edge_boost > 0:
                # Bias toward edge
                r = r ** (1 - edge_boost * 0.7)
            r = r * radius * 0.9

            px = r * math.cos(angle)
            py = r * math.sin(angle)
            wedge_points.append((px, py))

        # Rotate-copy to all slices
        for i in range(slices):
            rot_angle = i * wedge_angle
            cos_a = math.cos(rot_angle)
            sin_a = math.sin(rot_angle)

            for px, py in wedge_points:
                rx = px * cos_a - py * sin_a + cx
                ry = px * sin_a + py * cos_a + cy
                points.append((rx, ry))

        # Add center point
        points.append((cx, cy))

        return points

    def _generate_random_points(
        self, cx: float, cy: float, radius: float
    ) -> list[tuple[float, float]]:
        """Generate random points without symmetry.

        Args:
            cx: Center X coordinate.
            cy: Center Y coordinate.
            radius: Mandala radius.

        Returns:
            List of (x, y) point coordinates.
        """
        points = []
        point_count = self.sg_params.point_count
        edge_boost = self.sg_params.edge_detail_boost

        for _ in range(point_count):
            # Random angle
            angle = self.rng.uniform(0, 2 * math.pi)

            # Random radius with edge bias
            r = self.rng.random()
            if edge_boost > 0:
                r = r ** (1 - edge_boost * 0.7)
            r = r * radius * 0.9

            px = r * math.cos(angle) + cx
            py = r * math.sin(angle) + cy
            points.append((px, py))

        # Add center point
        points.append((cx, cy))

        return points

    def _compute_voronoi(
        self, points: list[tuple[float, float]], width: int, height: int
    ) -> np.ndarray:
        """Compute Voronoi diagram.

        Args:
            points: List of seed points.
            width: Image width.
            height: Image height.

        Returns:
            Region ID array.
        """
        y_coords, x_coords = np.ogrid[:height, :width]
        y_grid = y_coords.astype(np.float32)
        x_grid = x_coords.astype(np.float32)

        min_dist = np.full((height, width), np.inf, dtype=np.float32)
        region_ids = np.zeros((height, width), dtype=np.int32)

        for i, (px, py) in enumerate(points):
            dist = (x_grid - px) ** 2 + (y_grid - py) ** 2
            closer = dist < min_dist
            min_dist[closer] = dist[closer]
            region_ids[closer] = i

        return region_ids

    def _add_lead_outlines(self, region_ids: np.ndarray) -> np.ndarray:
        """Add thick "lead" outlines between regions.

        Args:
            region_ids: Voronoi region IDs.

        Returns:
            Region IDs with outline pixels marked as a separate region.
        """
        thickness = self.sg_params.outline_thickness
        height, width = region_ids.shape

        # Find boundary pixels
        boundary = np.zeros((height, width), dtype=bool)

        # Check horizontal neighbors
        boundary[:, :-1] |= region_ids[:, :-1] != region_ids[:, 1:]
        boundary[:, 1:] |= region_ids[:, :-1] != region_ids[:, 1:]

        # Check vertical neighbors
        boundary[:-1, :] |= region_ids[:-1, :] != region_ids[1:, :]
        boundary[1:, :] |= region_ids[:-1, :] != region_ids[1:, :]

        # Dilate boundary to create thick outlines
        if thickness > 1:
            dilated = boundary.copy()
            for _ in range(thickness - 1):
                new_dilated = dilated.copy()
                new_dilated[:-1, :] |= dilated[1:, :]
                new_dilated[1:, :] |= dilated[:-1, :]
                new_dilated[:, :-1] |= dilated[:, 1:]
                new_dilated[:, 1:] |= dilated[:, :-1]
                dilated = new_dilated
            boundary = dilated

        # Mark lead as the highest region ID
        lead_id = int(np.max(region_ids)) + 1
        result = region_ids.copy()
        result[boundary] = lead_id

        return result
