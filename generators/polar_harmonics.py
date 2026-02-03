"""Polar Harmonics generator (Preset B) for BusyBrainPaint.

Generates classic mandala patterns with petals, rings, and spokes
using polar coordinate harmonics.
"""

import math
from dataclasses import dataclass

import numpy as np

from .base import BaseGenerator, GeneratorParams, GeneratedPuzzle


@dataclass
class PolarHarmonicsParams(GeneratorParams):
    """Parameters for Polar Harmonics generation."""

    ring_count: int = 5  # Number of concentric rings
    petal_freq: int = 0  # Petal frequency (0 = no petals, use symmetry_slices)
    petal_depth: float = 0.3  # How deep petals cut into rings (0-1)
    spoke_count: int = 0  # Number of spokes (0 = none, use symmetry_slices)
    spoke_width: float = 0.02  # Spoke width as fraction of radius
    jitter: float = 0.0  # Small random variation (0-0.1)


class PolarHarmonicsGenerator(BaseGenerator):
    """Generates polar harmonics mandala puzzles.

    Method:
    1. Work in polar coordinates (r, theta)
    2. Fold theta by symmetry_slices for radial symmetry
    3. Create rings by thresholding radius
    4. Add petals using sine/cos modulation of ring boundaries
    5. Add spokes as angular segments
    6. Combine layers to create regions
    """

    name = "polar_harmonics"

    def __init__(self, params: PolarHarmonicsParams) -> None:
        """Initialize generator.

        Args:
            params: Polar harmonics parameters.
        """
        super().__init__(params)
        self.ph_params = params

    def generate(self) -> GeneratedPuzzle:
        """Generate a polar harmonics mandala puzzle.

        Returns:
            GeneratedPuzzle with region_ids and metadata.
        """
        width = self.params.width
        height = self.params.height
        cx, cy = width / 2, height / 2
        radius = min(width, height) / 2 - 2

        # Create coordinate arrays
        y_coords, x_coords = np.ogrid[:height, :width]
        dx = x_coords - cx
        dy = y_coords - cy

        # Convert to polar
        r = np.sqrt(dx * dx + dy * dy)
        theta = np.arctan2(dy, dx)

        # Normalize radius to 0-1
        r_norm = r / radius

        # Fold theta for symmetry
        slices = self.params.symmetry_slices
        theta_folded = np.abs(np.mod(theta + math.pi, 2 * math.pi / slices) - math.pi / slices)
        theta_folded = theta_folded / (math.pi / slices)  # Normalize to 0-1

        # Generate ring boundaries with petal modulation
        ring_ids = self._compute_rings(r_norm, theta, radius)

        # Add spokes if specified
        if self.ph_params.spoke_count > 0 or self.params.symmetry_slices > 0:
            spoke_mask = self._compute_spokes(theta, r_norm)
            ring_ids = self._combine_with_spokes(ring_ids, spoke_mask)

        # Create unique region IDs
        region_ids = self._create_region_ids(ring_ids, theta, r_norm)

        # Clip to circle
        region_ids = self._clip_to_circle(region_ids)

        # Clean up tiny regions
        region_ids = self._cleanup_regions(region_ids, min_area=25)

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
                "ring_count": self.ph_params.ring_count,
                "petal_freq": self.ph_params.petal_freq,
                "petal_depth": self.ph_params.petal_depth,
                "spoke_count": self.ph_params.spoke_count,
                "spoke_width": self.ph_params.spoke_width,
            },
        )

    def _compute_rings(
        self, r_norm: np.ndarray, theta: np.ndarray, radius: float
    ) -> np.ndarray:
        """Compute ring layer for each pixel.

        Args:
            r_norm: Normalized radius (0-1).
            theta: Angle in radians.
            radius: Maximum radius.

        Returns:
            Array with ring index for each pixel.
        """
        ring_count = self.ph_params.ring_count
        petal_freq = self.ph_params.petal_freq or self.params.symmetry_slices
        petal_depth = self.ph_params.petal_depth
        jitter = self.ph_params.jitter

        # Base ring boundaries
        ring_ids = np.zeros_like(r_norm, dtype=np.int32)

        for ring in range(ring_count):
            # Ring boundary radius (inner to outer)
            base_r = (ring + 1) / ring_count

            # Add petal modulation
            if petal_freq > 0 and petal_depth > 0:
                # Alternate petal phase for adjacent rings
                phase = math.pi if ring % 2 else 0
                modulation = petal_depth * (1 / ring_count) * np.sin(petal_freq * theta + phase)
                boundary = base_r + modulation
            else:
                boundary = base_r

            # Add jitter
            if jitter > 0:
                boundary = boundary + self.np_rng.uniform(-jitter, jitter, boundary.shape) / ring_count

            # Assign ring
            ring_ids[r_norm <= boundary] = ring

        return ring_ids

    def _compute_spokes(self, theta: np.ndarray, r_norm: np.ndarray) -> np.ndarray:
        """Compute spoke mask.

        Args:
            theta: Angle in radians.
            r_norm: Normalized radius.

        Returns:
            Boolean mask where True indicates spoke pixels.
        """
        spoke_count = self.ph_params.spoke_count or self.params.symmetry_slices
        spoke_width = self.ph_params.spoke_width

        if spoke_count <= 0:
            return np.zeros_like(theta, dtype=bool)

        # Angular width of spokes
        spoke_angle = 2 * math.pi / spoke_count
        half_width = spoke_width * math.pi

        # Check if pixel is within a spoke
        theta_mod = np.mod(theta + math.pi, spoke_angle)
        spoke_mask = (theta_mod < half_width) | (theta_mod > spoke_angle - half_width)

        # Don't apply spokes to center
        spoke_mask = spoke_mask & (r_norm > 0.1)

        return spoke_mask

    def _combine_with_spokes(
        self, ring_ids: np.ndarray, spoke_mask: np.ndarray
    ) -> np.ndarray:
        """Combine ring regions with spoke divisions.

        Args:
            ring_ids: Ring index array.
            spoke_mask: Boolean spoke mask.

        Returns:
            Combined region array.
        """
        # Spokes split rings, so add offset for spoke regions
        max_ring = int(np.max(ring_ids))
        result = ring_ids.copy()
        result[spoke_mask] = result[spoke_mask] + max_ring + 1
        return result

    def _create_region_ids(
        self, base_ids: np.ndarray, theta: np.ndarray, r_norm: np.ndarray
    ) -> np.ndarray:
        """Create unique region IDs by subdividing by angle.

        Args:
            base_ids: Base region IDs (from rings/spokes).
            theta: Angle in radians.
            r_norm: Normalized radius.

        Returns:
            Region ID array with angular subdivisions.
        """
        slices = self.params.symmetry_slices
        if slices <= 1:
            return base_ids

        # Compute angular slice index
        slice_angle = 2 * math.pi / slices
        slice_ids = np.floor((theta + math.pi) / slice_angle).astype(np.int32)
        slice_ids = np.clip(slice_ids, 0, slices - 1)

        # Combine base ID with slice ID
        max_base = int(np.max(base_ids)) + 1
        region_ids = base_ids + slice_ids * max_base

        return region_ids
