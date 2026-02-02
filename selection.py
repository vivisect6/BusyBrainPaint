"""Region selection logic for BusyBrainPaint."""

import math

from puzzle_loader import Puzzle


def normalize(x: float, y: float) -> tuple[float, float]:
    """Normalize a 2D vector.

    Args:
        x: X component.
        y: Y component.

    Returns:
        Normalized (x, y) tuple, or (0, 0) if magnitude is zero.
    """
    mag = math.sqrt(x * x + y * y)
    if mag < 1e-6:
        return (0.0, 0.0)
    return (x / mag, y / mag)


def dot(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Compute dot product of two 2D vectors.

    Args:
        a: First vector.
        b: Second vector.

    Returns:
        Dot product.
    """
    return a[0] * b[0] + a[1] * b[1]


class SelectionController:
    """Handles region selection via right stick and D-pad."""

    # Right-stick selection parameters
    SCORE_THRESHOLD = 0.3
    DEBOUNCE_INITIAL_MS = 180
    DEBOUNCE_REPEAT_MS = 90

    # D-pad quadrant jump parameters
    AXIS_PENALTY_K = 2.0  # Higher = stronger preference to stay on axis

    def __init__(self, puzzle: Puzzle) -> None:
        """Initialize selection controller.

        Args:
            puzzle: The puzzle to navigate.
        """
        self.puzzle = puzzle
        self.selected_region: int = self._find_initial_region()

        # Debounce state for right stick
        self._stick_active = False
        self._stick_timer_ms = 0.0

    def _find_initial_region(self) -> int:
        """Find a good initial region to select.

        Returns:
            Region ID of an unfilled region near the center, or 0.
        """
        if self.puzzle.num_regions == 0:
            return 0

        center_x = self.puzzle.width / 2
        center_y = self.puzzle.height / 2

        best_region = 0
        best_dist = float("inf")

        for region_id in range(self.puzzle.num_regions):
            if self.puzzle.region_area[region_id] == 0:
                continue

            cx, cy = self.puzzle.region_centroid[region_id]
            dist = (cx - center_x) ** 2 + (cy - center_y) ** 2

            # Prefer unfilled regions
            if not self.puzzle.filled[region_id]:
                dist -= 1e9  # Strong preference for unfilled

            if dist < best_dist:
                best_dist = dist
                best_region = region_id

        return best_region

    def update_stick_selection(
        self, stick_x: float, stick_y: float, dt_ms: float
    ) -> bool:
        """Update selection based on right stick input.

        Args:
            stick_x: Right stick X axis (-1 to 1).
            stick_y: Right stick Y axis (-1 to 1).
            dt_ms: Delta time in milliseconds.

        Returns:
            True if selection changed.
        """
        magnitude = math.sqrt(stick_x * stick_x + stick_y * stick_y)

        # Check if stick is active (past deadzone - already applied by input handler)
        if magnitude < 0.1:
            self._stick_active = False
            self._stick_timer_ms = 0.0
            return False

        # Debounce logic
        if self._stick_active:
            self._stick_timer_ms += dt_ms
            if self._stick_timer_ms < self.DEBOUNCE_REPEAT_MS:
                return False
            self._stick_timer_ms = 0.0
        else:
            self._stick_active = True
            self._stick_timer_ms = -self.DEBOUNCE_INITIAL_MS + self.DEBOUNCE_REPEAT_MS

        # Find best neighbor in stick direction
        new_region = self._find_neighbor_in_direction(stick_x, stick_y)
        if new_region is not None and new_region != self.selected_region:
            self.selected_region = new_region
            return True

        return False

    def _find_neighbor_in_direction(
        self, stick_x: float, stick_y: float
    ) -> int | None:
        """Find the best neighboring region in the given direction.

        Uses the algorithm from CLAUDE.md:
        - d = normalize((rx, ry))
        - For each neighbor: score = dot(direction_to_neighbor, d)
        - Choose highest score > threshold
        - Tiebreakers: prefer unfilled, then nearer centroid

        Args:
            stick_x: Stick X direction.
            stick_y: Stick Y direction.

        Returns:
            Best neighbor region ID, or None if no valid neighbor.
        """
        d = normalize(stick_x, stick_y)
        if d == (0.0, 0.0):
            return None

        current_centroid = self.puzzle.region_centroid[self.selected_region]
        neighbors = self.puzzle.adj[self.selected_region]

        candidates: list[tuple[float, bool, float, int]] = []

        for neighbor_id in neighbors:
            neighbor_id_int = int(neighbor_id)
            if self.puzzle.region_area[neighbor_id_int] == 0:
                continue

            neighbor_centroid = self.puzzle.region_centroid[neighbor_id_int]
            dx = neighbor_centroid[0] - current_centroid[0]
            dy = neighbor_centroid[1] - current_centroid[1]

            v = normalize(dx, dy)
            if v == (0.0, 0.0):
                continue

            score = dot(v, d)
            if score < self.SCORE_THRESHOLD:
                continue

            is_filled = self.puzzle.filled[neighbor_id_int]
            distance = math.sqrt(dx * dx + dy * dy)

            # Sort key: higher score first, unfilled first, nearer first
            candidates.append((-score, is_filled, distance, neighbor_id_int))

        if not candidates:
            return None

        candidates.sort()
        return candidates[0][3]

    def handle_dpad(self, dpad_x: int, dpad_y: int) -> bool:
        """Handle D-pad input for quadrant jumping.

        Args:
            dpad_x: D-pad X (-1, 0, or 1).
            dpad_y: D-pad Y (-1, 0, or 1). Note: typically -1 is down, 1 is up.

        Returns:
            True if selection changed.
        """
        if dpad_x == 0 and dpad_y == 0:
            return False

        # Pygame hat: (1, 0) = right, (-1, 0) = left, (0, 1) = up, (0, -1) = down
        # In world coords, +Y is down, so we invert dpad_y
        new_region = self._find_quadrant_jump(dpad_x, -dpad_y)
        if new_region is not None and new_region != self.selected_region:
            self.selected_region = new_region
            return True

        return False

    def _find_quadrant_jump(self, dir_x: int, dir_y: int) -> int | None:
        """Find the nearest region in the given quadrant direction.

        Uses the algorithm from CLAUDE.md:
        - Filter by direction sign (dx > 0 for right, etc.)
        - Score = abs(primary_axis) + k * abs(secondary_axis)
        - Choose minimum score
        - Prefer unfilled; fallback to filled

        Args:
            dir_x: X direction (-1, 0, or 1).
            dir_y: Y direction (-1, 0, or 1).

        Returns:
            Best region ID in that direction, or None.
        """
        current_centroid = self.puzzle.region_centroid[self.selected_region]
        k = self.AXIS_PENALTY_K

        unfilled_candidates: list[tuple[float, float, int]] = []
        filled_candidates: list[tuple[float, float, int]] = []

        for region_id in range(self.puzzle.num_regions):
            if region_id == self.selected_region:
                continue
            if self.puzzle.region_area[region_id] == 0:
                continue

            centroid = self.puzzle.region_centroid[region_id]
            dx = centroid[0] - current_centroid[0]
            dy = centroid[1] - current_centroid[1]

            # Filter by direction
            if dir_x > 0 and dx <= 0:
                continue
            if dir_x < 0 and dx >= 0:
                continue
            if dir_y > 0 and dy <= 0:
                continue
            if dir_y < 0 and dy >= 0:
                continue

            # Compute score based on primary direction
            if dir_x != 0:
                # Horizontal movement: primary = dx, secondary = dy
                score = abs(dx) + k * abs(dy)
            else:
                # Vertical movement: primary = dy, secondary = dx
                score = abs(dy) + k * abs(dx)

            distance = math.sqrt(dx * dx + dy * dy)

            if self.puzzle.filled[region_id]:
                filled_candidates.append((score, distance, region_id))
            else:
                unfilled_candidates.append((score, distance, region_id))

        # Prefer unfilled, then use score (lower is better), then distance
        if unfilled_candidates:
            unfilled_candidates.sort()
            return unfilled_candidates[0][2]
        elif filled_candidates:
            filled_candidates.sort()
            return filled_candidates[0][2]

        return None

    def select_region(self, region_id: int) -> None:
        """Directly select a specific region.

        Args:
            region_id: Region to select.
        """
        if 0 <= region_id < self.puzzle.num_regions:
            self.selected_region = region_id
