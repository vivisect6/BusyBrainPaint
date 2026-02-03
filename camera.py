"""Camera system for BusyBrainPaint.

Handles world-space camera positioning, zoom, panning, and view transforms.
"""


class Camera:
    """Manages camera state and world-to-screen transforms.

    The camera tracks a position in world space (cam_x, cam_y) representing
    the center of the view, along with a zoom level.

    Attributes:
        cam_x: X position of camera center in world coordinates.
        cam_y: Y position of camera center in world coordinates.
        zoom: Current zoom level (1.0 = 1 world pixel = 1 screen pixel).
    """

    # Zoom limits
    MIN_ZOOM = 1.0
    MAX_ZOOM = 10.0

    # Zoom speed (multiplier per second when holding trigger)
    ZOOM_SPEED = 2.0

    # Pan speed (world pixels per second at zoom=1.0)
    PAN_SPEED = 300.0

    # Nudge margin (screen fraction from edge to start nudging)
    NUDGE_MARGIN = 0.15

    # Nudge speed (fraction of distance to move per second)
    NUDGE_SPEED = 5.0

    def __init__(
        self,
        world_width: int,
        world_height: int,
        screen_width: int,
        screen_height: int,
    ) -> None:
        """Initialize camera centered on the world.

        Args:
            world_width: Width of the world/puzzle in pixels.
            world_height: Height of the world/puzzle in pixels.
            screen_width: Screen width in pixels.
            screen_height: Screen height in pixels.
        """
        self.world_width = world_width
        self.world_height = world_height
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Start centered on the world
        self.cam_x = world_width / 2.0
        self.cam_y = world_height / 2.0

        # Calculate initial zoom to fit world on screen with padding
        padding = 100
        available_w = screen_width - padding * 2
        available_h = screen_height - padding * 2
        fit_zoom = min(available_w / world_width, available_h / world_height)
        self.zoom = max(self.MIN_ZOOM, min(fit_zoom, self.MAX_ZOOM))

    def update_zoom(self, rt: float, lt: float, dt_sec: float) -> bool:
        """Update zoom based on trigger input.

        RT zooms in, LT zooms out (continuous while held).

        Args:
            rt: Right trigger value (0 to 1).
            lt: Left trigger value (0 to 1).
            dt_sec: Delta time in seconds.

        Returns:
            True if zoom changed.
        """
        if rt <= 0 and lt <= 0:
            return False

        old_zoom = self.zoom

        # RT zooms in (multiply), LT zooms out (divide)
        if rt > 0:
            self.zoom *= 1.0 + self.ZOOM_SPEED * rt * dt_sec
        if lt > 0:
            self.zoom /= 1.0 + self.ZOOM_SPEED * lt * dt_sec

        # Clamp zoom
        self.zoom = max(self.MIN_ZOOM, min(self.zoom, self.MAX_ZOOM))

        return abs(self.zoom - old_zoom) > 0.001

    def update_pan(self, stick_x: float, stick_y: float, dt_sec: float) -> bool:
        """Update camera position based on left stick input.

        Pan speed is scaled by zoom (higher zoom = slower pan in world space).

        Args:
            stick_x: Left stick X axis (-1 to 1).
            stick_y: Left stick Y axis (-1 to 1).
            dt_sec: Delta time in seconds.

        Returns:
            True if camera moved.
        """
        if abs(stick_x) < 0.01 and abs(stick_y) < 0.01:
            return False

        # Scale pan speed inversely with zoom (so screen movement feels consistent)
        speed = self.PAN_SPEED / self.zoom

        self.cam_x += stick_x * speed * dt_sec
        self.cam_y += stick_y * speed * dt_sec

        # Clamp to world bounds (with some margin to see edges)
        half_view_w = (self.screen_width / 2) / self.zoom
        half_view_h = (self.screen_height / 2) / self.zoom

        min_x = half_view_w * 0.5
        max_x = self.world_width - half_view_w * 0.5
        min_y = half_view_h * 0.5
        max_y = self.world_height - half_view_h * 0.5

        # Only clamp if world is larger than view
        if max_x > min_x:
            self.cam_x = max(min_x, min(self.cam_x, max_x))
        else:
            self.cam_x = self.world_width / 2

        if max_y > min_y:
            self.cam_y = max(min_y, min(self.cam_y, max_y))
        else:
            self.cam_y = self.world_height / 2

        return True

    def snap_to(self, world_x: float, world_y: float) -> None:
        """Instantly center camera on a world position.

        Args:
            world_x: X coordinate in world space.
            world_y: Y coordinate in world space.
        """
        self.cam_x = world_x
        self.cam_y = world_y

    def nudge_to_keep_visible(
        self, world_x: float, world_y: float, dt_sec: float
    ) -> bool:
        """Smoothly nudge camera to keep a point comfortably visible.

        If the point is near the edge of the screen, gently move the camera
        to bring it more toward the center.

        Args:
            world_x: X coordinate in world space to keep visible.
            world_y: Y coordinate in world space to keep visible.
            dt_sec: Delta time in seconds.

        Returns:
            True if camera moved.
        """
        # Convert world point to screen position
        screen_x, screen_y = self.world_to_screen(world_x, world_y)

        # Calculate comfortable bounds (with margin)
        margin_x = self.screen_width * self.NUDGE_MARGIN
        margin_y = self.screen_height * self.NUDGE_MARGIN

        min_x = margin_x
        max_x = self.screen_width - margin_x
        min_y = margin_y
        max_y = self.screen_height - margin_y

        # Calculate how far outside comfortable bounds
        nudge_x = 0.0
        nudge_y = 0.0

        if screen_x < min_x:
            nudge_x = screen_x - min_x
        elif screen_x > max_x:
            nudge_x = screen_x - max_x

        if screen_y < min_y:
            nudge_y = screen_y - min_y
        elif screen_y > max_y:
            nudge_y = screen_y - max_y

        if abs(nudge_x) < 1 and abs(nudge_y) < 1:
            return False

        # Convert screen offset to world offset and apply smoothly
        world_nudge_x = nudge_x / self.zoom
        world_nudge_y = nudge_y / self.zoom

        # Smooth movement
        factor = min(1.0, self.NUDGE_SPEED * dt_sec)
        self.cam_x += world_nudge_x * factor
        self.cam_y += world_nudge_y * factor

        return True

    def world_to_screen(self, world_x: float, world_y: float) -> tuple[float, float]:
        """Convert world coordinates to screen coordinates.

        Args:
            world_x: X position in world space.
            world_y: Y position in world space.

        Returns:
            (screen_x, screen_y) tuple.
        """
        # Offset from camera center, scaled by zoom, centered on screen
        screen_x = (world_x - self.cam_x) * self.zoom + self.screen_width / 2
        screen_y = (world_y - self.cam_y) * self.zoom + self.screen_height / 2
        return (screen_x, screen_y)

    def screen_to_world(self, screen_x: float, screen_y: float) -> tuple[float, float]:
        """Convert screen coordinates to world coordinates.

        Args:
            screen_x: X position on screen.
            screen_y: Y position on screen.

        Returns:
            (world_x, world_y) tuple.
        """
        world_x = (screen_x - self.screen_width / 2) / self.zoom + self.cam_x
        world_y = (screen_y - self.screen_height / 2) / self.zoom + self.cam_y
        return (world_x, world_y)

    def get_visible_world_rect(self) -> tuple[float, float, float, float]:
        """Get the world-space rectangle visible on screen.

        Returns:
            (x, y, width, height) in world coordinates.
        """
        half_w = (self.screen_width / 2) / self.zoom
        half_h = (self.screen_height / 2) / self.zoom
        return (
            self.cam_x - half_w,
            self.cam_y - half_h,
            half_w * 2,
            half_h * 2,
        )

    def get_view_transform(self) -> tuple[float, float, float]:
        """Get transform parameters for rendering.

        Returns:
            (offset_x, offset_y, zoom) where offset is screen position
            of world origin (0, 0).
        """
        origin_screen_x, origin_screen_y = self.world_to_screen(0, 0)
        return (origin_screen_x, origin_screen_y, self.zoom)
