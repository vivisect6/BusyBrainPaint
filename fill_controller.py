"""Fill controller for BusyBrainPaint.

Manages the hold-to-fill mechanic including timing, preview, and reject animations.
"""

from enum import Enum, auto


class FillState(Enum):
    """State of the fill action."""

    IDLE = auto()
    FILLING = auto()
    REJECTING = auto()


class FillController:
    """Manages hold-to-fill mechanics.

    Tracks fill progress, handles correct/wrong fills, and manages
    the reject animation timing.
    """

    # Fill timing parameters (from CLAUDE.md)
    PIXELS_PER_SECOND = 12000
    MIN_FILL_TIME = 0.15
    MAX_FILL_TIME = 2.0

    # Reject animation timing
    REJECT_DURATION = 0.3  # Total shake+fade duration in seconds
    SHAKE_AMPLITUDE = 3  # Pixels to shake

    def __init__(self) -> None:
        """Initialize fill controller."""
        self.state = FillState.IDLE
        self.target_region: int = -1
        self.fill_color_idx: int = -1
        self.progress: float = 0.0
        self.fill_time: float = 0.0
        self.reject_timer: float = 0.0
        self._is_correct: bool = False

    def start_fill(
        self, region_id: int, region_area: int, palette_idx: int, correct_idx: int
    ) -> None:
        """Begin filling a region.

        Args:
            region_id: Region being filled.
            region_area: Area of the region in pixels.
            palette_idx: Currently selected palette index.
            correct_idx: Correct palette index for this region.
        """
        if self.state != FillState.IDLE:
            return

        self.state = FillState.FILLING
        self.target_region = region_id
        self.fill_color_idx = palette_idx
        self.progress = 0.0
        self._is_correct = palette_idx == correct_idx

        # Calculate fill time based on area
        raw_time = region_area / self.PIXELS_PER_SECOND
        self.fill_time = max(self.MIN_FILL_TIME, min(raw_time, self.MAX_FILL_TIME))

    def update(self, dt_sec: float, a_held: bool) -> tuple[bool, bool, int]:
        """Update fill state.

        Args:
            dt_sec: Delta time in seconds.
            a_held: Whether the A button is currently held.

        Returns:
            Tuple of (fill_completed, was_correct, region_id).
            fill_completed is True when a fill finishes (correct or wrong).
            was_correct indicates if the completed fill was correct.
            region_id is the region that was filled (-1 if not applicable).
        """
        if self.state == FillState.IDLE:
            return (False, False, -1)

        if self.state == FillState.FILLING:
            if not a_held:
                # Released early - cancel
                self.cancel()
                return (False, False, -1)

            # Update progress
            self.progress += dt_sec / self.fill_time
            if self.progress >= 1.0:
                self.progress = 1.0
                if self._is_correct:
                    # Correct fill - complete immediately
                    completed_region = self.target_region
                    self._reset()
                    return (True, True, completed_region)
                else:
                    # Wrong fill - start reject animation
                    self.state = FillState.REJECTING
                    self.reject_timer = 0.0
                    return (False, False, -1)

        elif self.state == FillState.REJECTING:
            self.reject_timer += dt_sec
            if self.reject_timer >= self.REJECT_DURATION:
                # Reject animation complete
                completed_region = self.target_region
                self._reset()
                return (True, False, completed_region)

        return (False, False, -1)

    def cancel(self) -> None:
        """Cancel the current fill action."""
        if self.state == FillState.FILLING:
            self._reset()

    def _reset(self) -> None:
        """Reset to idle state."""
        self.state = FillState.IDLE
        self.target_region = -1
        self.fill_color_idx = -1
        self.progress = 0.0
        self.fill_time = 0.0
        self.reject_timer = 0.0
        self._is_correct = False

    def is_filling(self) -> bool:
        """Check if currently in filling state."""
        return self.state == FillState.FILLING

    def is_rejecting(self) -> bool:
        """Check if currently playing reject animation."""
        return self.state == FillState.REJECTING

    def is_active(self) -> bool:
        """Check if fill action is active (filling or rejecting)."""
        return self.state != FillState.IDLE

    def get_reject_offset(self) -> tuple[int, int]:
        """Get shake offset for reject animation.

        Returns:
            (x_offset, y_offset) in pixels for shake effect.
        """
        if self.state != FillState.REJECTING:
            return (0, 0)

        # Shake back and forth, decaying over time
        t = self.reject_timer / self.REJECT_DURATION
        decay = 1.0 - t
        # Oscillate at ~20Hz
        import math

        phase = self.reject_timer * 20 * 2 * math.pi
        offset = int(math.sin(phase) * self.SHAKE_AMPLITUDE * decay)
        return (offset, 0)

    def get_reject_alpha(self) -> int:
        """Get alpha value for reject animation fade.

        Returns:
            Alpha value (0-255) for the fading preview.
        """
        if self.state != FillState.REJECTING:
            return 255

        t = self.reject_timer / self.REJECT_DURATION
        return int(255 * (1.0 - t))
