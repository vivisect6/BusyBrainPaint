"""Standalone region cleanup utilities for BusyBrainPaint.

These functions are used by both the procedural generators (via BaseGenerator)
and the image-to-puzzle converter.
"""

import numpy as np


def merge_tiny_regions(
    region_ids: np.ndarray, min_area: int = 20
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


def smooth_boundaries(
    region_ids: np.ndarray, iterations: int = 2
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


def remap_to_contiguous(region_ids: np.ndarray) -> np.ndarray:
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


def cleanup_regions(
    region_ids: np.ndarray, min_area: int = 20
) -> np.ndarray:
    """Clean up regions by merging tiny ones and smoothing boundaries.

    Orchestrates: merge -> smooth -> re-merge -> remap.

    Args:
        region_ids: Raw region ID map.
        min_area: Minimum region area to keep.

    Returns:
        Cleaned region ID map with contiguous IDs 0..N-1.
    """
    region_ids = merge_tiny_regions(region_ids, min_area)
    region_ids = smooth_boundaries(region_ids, iterations=2)
    region_ids = merge_tiny_regions(region_ids, min_area)
    return remap_to_contiguous(region_ids)
