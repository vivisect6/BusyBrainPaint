"""Base generator class for BusyBrainPaint puzzle generation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import random

import numpy as np


@dataclass
class GeneratorParams:
    """Common parameters for all generators."""

    width: int = 512
    height: int = 512
    num_colors: int = 6
    seed: int | None = None
    symmetry_slices: int = 8


@dataclass
class GeneratedPuzzle:
    """Output from a puzzle generator."""

    region_ids: np.ndarray  # HxW int array
    num_regions: int
    width: int
    height: int
    generator_name: str
    params: dict  # Generator-specific params for reproducibility


class BaseGenerator(ABC):
    """Abstract base class for puzzle generators."""

    name: str = "base"

    def __init__(self, params: GeneratorParams) -> None:
        """Initialize generator with parameters.

        Args:
            params: Common generation parameters.
        """
        self.params = params
        self.rng = random.Random(params.seed)
        self.np_rng = np.random.default_rng(params.seed)

    @abstractmethod
    def generate(self) -> GeneratedPuzzle:
        """Generate a puzzle.

        Returns:
            GeneratedPuzzle with region_ids and metadata.
        """
        pass

    def _cleanup_regions(
        self, region_ids: np.ndarray, min_area: int = 20
    ) -> np.ndarray:
        """Clean up regions by merging tiny ones and smoothing boundaries.

        Args:
            region_ids: Raw region ID map.
            min_area: Minimum region area to keep.

        Returns:
            Cleaned region ID map with contiguous IDs.
        """
        # Merge tiny regions into neighbors
        region_ids = self._merge_tiny_regions(region_ids, min_area)

        # Smooth jagged boundaries with majority-vote filter
        region_ids = self._smooth_boundaries(region_ids, iterations=2)

        # Re-merge any tiny fragments created by smoothing
        region_ids = self._merge_tiny_regions(region_ids, min_area)

        # Remap to contiguous IDs
        return self._remap_to_contiguous(region_ids)

    def _merge_tiny_regions(
        self, region_ids: np.ndarray, min_area: int = 20
    ) -> np.ndarray:
        """Merge regions smaller than min_area into their largest neighbor.

        Args:
            region_ids: Region ID map.
            min_area: Minimum region area to keep.

        Returns:
            Region ID map with tiny regions merged.
        """
        unique_ids = np.unique(region_ids)
        areas = {rid: np.sum(region_ids == rid) for rid in unique_ids}

        tiny_regions = [rid for rid, area in areas.items() if area < min_area]

        for tiny_id in tiny_regions:
            mask = region_ids == tiny_id
            # Dilate mask to find neighbors
            dilated = np.zeros_like(mask)
            dilated[:-1, :] |= mask[1:, :]
            dilated[1:, :] |= mask[:-1, :]
            dilated[:, :-1] |= mask[:, 1:]
            dilated[:, 1:] |= mask[:, :-1]
            neighbor_mask = dilated & ~mask

            if np.any(neighbor_mask):
                neighbor_ids = region_ids[neighbor_mask]
                neighbor_counts: dict[int, int] = {}
                for nid in neighbor_ids:
                    if nid != tiny_id:
                        neighbor_counts[nid] = neighbor_counts.get(nid, 0) + 1
                if neighbor_counts:
                    best_neighbor = max(neighbor_counts, key=neighbor_counts.get)
                    region_ids[mask] = best_neighbor

        return region_ids

    def _smooth_boundaries(
        self, region_ids: np.ndarray, iterations: int = 2
    ) -> np.ndarray:
        """Smooth jagged region boundaries using a majority-vote mode filter.

        Only boundary pixels (those with a 4-neighbor of different ID) are
        modified.  A pixel is reassigned only when a strict majority (>=5 of 9)
        of its 3x3 neighborhood agrees on a single ID, which protects thin
        structures like stained-glass lead lines.

        Args:
            region_ids: Region ID map.
            iterations: Number of smoothing passes.

        Returns:
            Region ID map with smoother boundaries.
        """
        result = region_ids.copy()

        for _ in range(iterations):
            # Pad by 1 on each side (replicate edge values)
            padded = np.pad(result, 1, mode="edge")

            # Build 9 shifted views of the 3x3 neighborhood
            h, w = result.shape
            views = []
            for dy in range(3):
                for dx in range(3):
                    views.append(padded[dy : dy + h, dx : dx + w])

            # Identify boundary pixels: any 4-connected neighbor differs
            center = views[4]  # (1,1) offset = center
            boundary = (
                (center != views[1])   # up
                | (center != views[7]) # down
                | (center != views[3]) # left
                | (center != views[5]) # right
            )

            boundary_indices = np.nonzero(boundary)
            if boundary_indices[0].size == 0:
                break

            # Stack neighbor values at boundary pixels: shape (9, N_boundary)
            neighbor_vals = np.stack(
                [v[boundary_indices] for v in views], axis=0
            )

            # For each neighbor position, count how many of the 9 match it
            # counts[j, i] = number of the 9 neighbors equal to neighbor_vals[j, i]
            counts = np.zeros_like(neighbor_vals, dtype=np.int32)
            for j in range(9):
                for k in range(9):
                    counts[j] += neighbor_vals[k] == neighbor_vals[j]

            # Find the neighbor position with the highest vote count per pixel
            best_pos = np.argmax(counts, axis=0)
            best_count = counts[best_pos, np.arange(counts.shape[1])]
            best_val = neighbor_vals[best_pos, np.arange(neighbor_vals.shape[1])]

            # Apply only where strict majority (>=5 of 9)
            apply_mask = best_count >= 5
            by, bx = boundary_indices
            result[by[apply_mask], bx[apply_mask]] = best_val[apply_mask]

        return result

    def _remap_to_contiguous(self, region_ids: np.ndarray) -> np.ndarray:
        """Remap region IDs to contiguous range 0..N-1.

        Args:
            region_ids: Region ID map with possibly non-contiguous IDs.

        Returns:
            Region ID map with IDs 0..N-1.
        """
        unique_ids = np.unique(region_ids)
        mapping = {old: new for new, old in enumerate(unique_ids)}
        result = np.zeros_like(region_ids)
        for old, new in mapping.items():
            result[region_ids == old] = new
        return result

    def _assign_colors(self, region_ids: np.ndarray, num_colors: int) -> list[int]:
        """Assign colors to regions using graph coloring.

        Tries to ensure adjacent regions have different colors.

        Args:
            region_ids: Region ID map.
            num_colors: Number of colors available.

        Returns:
            List mapping region_id -> color_index.
        """
        num_regions = int(np.max(region_ids)) + 1

        # Build adjacency
        adj: list[set[int]] = [set() for _ in range(num_regions)]
        height, width = region_ids.shape

        for y in range(height):
            for x in range(width - 1):
                r1, r2 = region_ids[y, x], region_ids[y, x + 1]
                if r1 != r2:
                    adj[r1].add(r2)
                    adj[r2].add(r1)

        for y in range(height - 1):
            for x in range(width):
                r1, r2 = region_ids[y, x], region_ids[y + 1, x]
                if r1 != r2:
                    adj[r1].add(r2)
                    adj[r2].add(r1)

        # Greedy graph coloring
        colors = [-1] * num_regions
        for region in range(num_regions):
            used = {colors[n] for n in adj[region] if colors[n] >= 0}
            for c in range(num_colors):
                if c not in used:
                    colors[region] = c
                    break
            if colors[region] < 0:
                # Fallback: use random color if all are used by neighbors
                colors[region] = self.rng.randint(0, num_colors - 1)

        return colors

    def _clip_to_circle(self, region_ids: np.ndarray, border_id: int = -1) -> np.ndarray:
        """Clip regions to a circle, setting outside pixels to border_id.

        Args:
            region_ids: Region ID map.
            border_id: ID to assign to pixels outside the circle.

        Returns:
            Clipped region ID map.
        """
        height, width = region_ids.shape
        cy, cx = height / 2, width / 2
        radius = min(height, width) / 2 - 1

        y_coords, x_coords = np.ogrid[:height, :width]
        dist_sq = (x_coords - cx) ** 2 + (y_coords - cy) ** 2
        outside = dist_sq > radius * radius

        result = region_ids.copy()
        if border_id >= 0:
            result[outside] = border_id
        else:
            # Mark outside as a new region
            max_id = int(np.max(region_ids))
            result[outside] = max_id + 1

        return result
