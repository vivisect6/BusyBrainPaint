"""Voronoi Mandala generator (Preset A) for BusyBrainPaint.

Generates stained-glass / organic cell mandalas using Voronoi diagrams
with radial symmetry.
"""

import math
from dataclasses import dataclass

import numpy as np

from .base import BaseGenerator, GeneratorParams, GeneratedPuzzle


@dataclass
class VoronoiMandalaParams(GeneratorParams):
    """Parameters for Voronoi Mandala generation."""

    point_count: int = 30  # Points per wedge (scaled with difficulty)
    radial_bias: float = 0.5  # 0=uniform, 1=more points near edge
    relax_iters: int = 1  # Lloyd relaxation iterations (0-3)
    outline_thickness: int = 1  # Thickness of cell boundaries


class VoronoiMandalaGenerator(BaseGenerator):
    """Generates Voronoi-based mandala puzzles.

    Method:
    1. Generate points in a wedge (one slice of the mandala)
    2. Rotate-copy points around center for symmetry
    3. Compute Voronoi diagram (assign each pixel to nearest point)
    4. Optionally apply Lloyd relaxation for smoother cells
    5. Clip to circle
    """

    name = "voronoi_mandala"

    def __init__(self, params: VoronoiMandalaParams) -> None:
        """Initialize generator.

        Args:
            params: Voronoi mandala parameters.
        """
        super().__init__(params)
        self.vm_params = params

    def generate(self) -> GeneratedPuzzle:
        """Generate a Voronoi mandala puzzle.

        Returns:
            GeneratedPuzzle with region_ids and metadata.
        """
        width = self.params.width
        height = self.params.height
        cx, cy = width / 2, height / 2
        radius = min(width, height) / 2 - 2

        # Generate seed points with symmetry
        points = self._generate_symmetric_points(cx, cy, radius)

        # Apply Lloyd relaxation
        for _ in range(self.vm_params.relax_iters):
            region_ids = self._compute_voronoi(points, width, height)
            points = self._lloyd_relax(region_ids, points, cx, cy, radius)

        # Final Voronoi computation
        region_ids = self._compute_voronoi(points, width, height)

        # Clip to circle
        region_ids = self._clip_to_circle(region_ids)

        # Clean up tiny regions
        region_ids = self._cleanup_regions(region_ids, min_area=30)

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
                "point_count": self.vm_params.point_count,
                "radial_bias": self.vm_params.radial_bias,
                "relax_iters": self.vm_params.relax_iters,
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
        point_count = self.vm_params.point_count
        bias = self.vm_params.radial_bias

        # Generate points in the first wedge
        wedge_points = []
        for _ in range(point_count):
            # Random angle within wedge
            angle = self.rng.uniform(0, wedge_angle)

            # Random radius with bias toward edge
            r = self.rng.random()
            if bias > 0:
                r = r ** (1 - bias * 0.8)  # Power transform for edge bias
            r = r * radius * 0.95  # Keep points slightly inside edge

            # Convert to cartesian (relative to center)
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

    def _compute_voronoi(
        self, points: list[tuple[float, float]], width: int, height: int
    ) -> np.ndarray:
        """Compute Voronoi diagram by assigning each pixel to nearest point.

        Args:
            points: List of seed points.
            width: Image width.
            height: Image height.

        Returns:
            Region ID array where each pixel is assigned to nearest point.
        """
        # Create coordinate grids
        y_coords, x_coords = np.ogrid[:height, :width]
        y_grid = y_coords.astype(np.float32)
        x_grid = x_coords.astype(np.float32)

        # Initialize with large distances
        min_dist = np.full((height, width), np.inf, dtype=np.float32)
        region_ids = np.zeros((height, width), dtype=np.int32)

        # Assign each pixel to nearest point
        for i, (px, py) in enumerate(points):
            dist = (x_grid - px) ** 2 + (y_grid - py) ** 2
            closer = dist < min_dist
            min_dist[closer] = dist[closer]
            region_ids[closer] = i

        return region_ids

    def _lloyd_relax(
        self,
        region_ids: np.ndarray,
        points: list[tuple[float, float]],
        cx: float,
        cy: float,
        radius: float,
    ) -> list[tuple[float, float]]:
        """Apply one iteration of Lloyd relaxation.

        Moves each point to the centroid of its Voronoi cell.

        Args:
            region_ids: Current Voronoi diagram.
            points: Current point positions.
            cx: Center X for boundary clamping.
            cy: Center Y for boundary clamping.
            radius: Radius for boundary clamping.

        Returns:
            Updated point positions.
        """
        height, width = region_ids.shape
        new_points = []

        for i in range(len(points)):
            mask = region_ids == i
            if not np.any(mask):
                new_points.append(points[i])
                continue

            # Compute centroid
            y_coords, x_coords = np.where(mask)
            new_x = float(np.mean(x_coords))
            new_y = float(np.mean(y_coords))

            # Clamp to circle
            dx, dy = new_x - cx, new_y - cy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > radius * 0.95:
                scale = radius * 0.95 / dist
                new_x = cx + dx * scale
                new_y = cy + dy * scale

            new_points.append((new_x, new_y))

        return new_points
