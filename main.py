"""BusyBrainPaint - Paint-by-numbers mandala game."""

import sys
from datetime import datetime
from pathlib import Path

import pygame

from camera import Camera
from fill_controller import FillController
from input_handler import InputHandler, BUTTON_A, BUTTON_B, BUTTON_LB, BUTTON_RB, BUTTON_L3
from puzzle_loader import Puzzle, load_puzzle
from save_manager import SaveManager, create_save_data
from selection import SelectionController
from main_menu import run_main_menu
from settings import run_settings_menu, PuzzleSettings


class GameRenderer:
    """Handles rendering of the puzzle and UI."""

    # Colors
    BACKGROUND = (40, 40, 40)
    OUTLINE_COLOR = (60, 60, 60)
    HIGHLIGHT_COLOR = (255, 255, 255)
    UNFILLED_COLOR = (220, 220, 220)
    NUMBER_COLOR = (80, 80, 80)
    NUMBER_COLOR_SELECTED = (0, 0, 0)

    # Region number visibility thresholds
    MIN_AREA_FOR_NUMBER = 150  # Minimum region area to show number (always)
    MIN_ZOOM_FOR_SMALL = 4.0  # Minimum zoom to show numbers on small regions
    MIN_SCREEN_SIZE_FOR_NUMBER = 20  # Minimum screen pixels for number to fit

    def __init__(self, puzzle: Puzzle, screen: pygame.Surface) -> None:
        """Initialize renderer.

        Args:
            puzzle: The puzzle to render.
            screen: The pygame display surface.
        """
        self.puzzle = puzzle
        self.screen = screen
        self.screen_w, self.screen_h = screen.get_size()

        # Create surfaces
        self._create_surfaces()

    def _create_surfaces(self) -> None:
        """Create the rendering surfaces."""
        w, h = self.puzzle.width, self.puzzle.height

        # Base surface with outlines and unfilled regions
        self.base_surface = pygame.Surface((w, h))
        self.base_surface.fill(self.UNFILLED_COLOR)
        self._draw_outlines(self.base_surface)

        # Filled surface (starts empty/transparent)
        self.filled_surface = pygame.Surface((w, h), pygame.SRCALPHA)

        # Temp fill surface for preview during hold (cleared after commit/reject)
        self.temp_fill_surface = pygame.Surface((w, h), pygame.SRCALPHA)

        # Highlight surface (redrawn each frame)
        self.highlight_surface = pygame.Surface((w, h), pygame.SRCALPHA)

    def _draw_outlines(self, surface: pygame.Surface) -> None:
        """Draw region outlines on a surface.

        Args:
            surface: Surface to draw on.
        """
        region_ids = self.puzzle.region_ids
        height, width = region_ids.shape

        # Draw horizontal boundaries
        for y in range(height):
            for x in range(width - 1):
                if region_ids[y, x] != region_ids[y, x + 1]:
                    surface.set_at((x, y), self.OUTLINE_COLOR)
                    surface.set_at((x + 1, y), self.OUTLINE_COLOR)

        # Draw vertical boundaries
        for y in range(height - 1):
            for x in range(width):
                if region_ids[y, x] != region_ids[y + 1, x]:
                    surface.set_at((x, y), self.OUTLINE_COLOR)
                    surface.set_at((x, y + 1), self.OUTLINE_COLOR)

    def draw_region_highlight(self, region_id: int) -> None:
        """Draw highlight for the selected region.

        Args:
            region_id: Region to highlight.
        """
        self.highlight_surface.fill((0, 0, 0, 0))

        if region_id < 0 or region_id >= self.puzzle.num_regions:
            return

        # Draw pulsing highlight border
        runs = self.puzzle.region_runs[region_id]
        highlight_color = (*self.HIGHLIGHT_COLOR, 200)

        for y, x_start, x_end in runs:
            # Draw top and bottom edges of each run
            for x in range(x_start, x_end):
                # Check if this pixel is on the edge of the region
                is_edge = False
                if y == 0 or self.puzzle.region_ids[y - 1, x] != region_id:
                    is_edge = True
                if y == self.puzzle.height - 1 or self.puzzle.region_ids[y + 1, x] != region_id:
                    is_edge = True
                if x == x_start:
                    is_edge = True
                if x == x_end - 1:
                    is_edge = True

                if is_edge:
                    self.highlight_surface.set_at((x, y), highlight_color)

    def draw_filled_region(self, region_id: int) -> None:
        """Draw a filled region on the filled surface.

        Args:
            region_id: Region to fill.
        """
        if region_id < 0 or region_id >= self.puzzle.num_regions:
            return

        color_idx = self.puzzle.region_color[region_id]
        color = self.puzzle.palette[color_idx]

        for y, x_start, x_end in self.puzzle.region_runs[region_id]:
            pygame.draw.line(self.filled_surface, color, (x_start, y), (x_end - 1, y))

    def draw_temp_fill(self, region_id: int, color_idx: int) -> None:
        """Draw a preview fill on the temp surface.

        Args:
            region_id: Region to preview.
            color_idx: Palette index to use for fill color.
        """
        if region_id < 0 or region_id >= self.puzzle.num_regions:
            return
        if color_idx < 0 or color_idx >= len(self.puzzle.palette):
            return

        color = self.puzzle.palette[color_idx]

        for y, x_start, x_end in self.puzzle.region_runs[region_id]:
            pygame.draw.line(self.temp_fill_surface, color, (x_start, y), (x_end - 1, y))

    def clear_temp_fill(self) -> None:
        """Clear the temp fill surface."""
        self.temp_fill_surface.fill((0, 0, 0, 0))

    def render(
        self,
        selected_region: int,
        selected_palette: int,
        camera: Camera,
        fill_controller: FillController | None = None,
    ) -> None:
        """Render the full game view.

        Args:
            selected_region: Currently selected region ID.
            selected_palette: Currently selected palette index.
            camera: Camera for view transform.
            fill_controller: Optional fill controller for preview rendering.
        """
        self.screen.fill(self.BACKGROUND)

        # Update highlight (don't show during fill)
        if fill_controller is None or not fill_controller.is_active():
            self.draw_region_highlight(selected_region)
        else:
            self.highlight_surface.fill((0, 0, 0, 0))

        # Composite puzzle layers
        composite = self.base_surface.copy()
        composite.blit(self.filled_surface, (0, 0))

        # Add temp fill surface with shake/fade if active
        if fill_controller is not None and fill_controller.is_active():
            shake_x, shake_y = fill_controller.get_reject_offset()
            alpha = fill_controller.get_reject_alpha()

            if alpha < 255:
                # Create faded copy of temp surface
                faded_temp = self.temp_fill_surface.copy()
                faded_temp.set_alpha(alpha)
                composite.blit(faded_temp, (shake_x, shake_y))
            else:
                composite.blit(self.temp_fill_surface, (shake_x, shake_y))

        composite.blit(self.highlight_surface, (0, 0))

        # Get camera transform
        origin_x, origin_y, zoom = camera.get_view_transform()

        # Scale composite by zoom
        scaled_w = int(self.puzzle.width * zoom)
        scaled_h = int(self.puzzle.height * zoom)

        if scaled_w > 0 and scaled_h > 0:
            scaled = pygame.transform.smoothscale(composite, (scaled_w, scaled_h))
            # Blit at camera-determined position
            self.screen.blit(scaled, (int(origin_x), int(origin_y)))

        # Draw numbers inside unfilled regions
        self._draw_region_numbers(camera, selected_region)

        # Draw palette indicator
        self._draw_palette_ui(selected_palette)

        # Draw selection info
        self._draw_selection_info(selected_region, camera)

        # Draw fill progress if filling
        if fill_controller is not None and fill_controller.is_filling():
            self._draw_fill_progress(fill_controller.progress, camera, selected_region)

        pygame.display.flip()

    def _draw_fill_progress(
        self, progress: float, camera: Camera, region_id: int
    ) -> None:
        """Draw fill progress indicator.

        Args:
            progress: Fill progress (0 to 1).
            camera: Camera for positioning.
            region_id: Region being filled.
        """
        # Get region centroid in screen coordinates
        cx, cy = self.puzzle.region_centroid[region_id]
        screen_x, screen_y = camera.world_to_screen(cx, cy)

        # Draw progress ring
        radius = 30
        thickness = 6

        # Background ring (dark)
        pygame.draw.circle(
            self.screen, (60, 60, 60), (int(screen_x), int(screen_y)), radius, thickness
        )

        # Progress arc
        if progress > 0:
            import math

            start_angle = -math.pi / 2  # Start at top
            end_angle = start_angle + progress * 2 * math.pi
            rect = pygame.Rect(
                int(screen_x) - radius,
                int(screen_y) - radius,
                radius * 2,
                radius * 2,
            )
            pygame.draw.arc(
                self.screen,
                (100, 255, 100),
                rect,
                start_angle,
                end_angle,
                thickness,
            )

    def _draw_region_numbers(
        self, camera: Camera, selected_region: int
    ) -> None:
        """Draw numbers inside unfilled regions.

        Numbers are shown based on thresholds:
        - Large regions (area >= MIN_AREA_FOR_NUMBER): always show
        - Small regions: show if zoom >= MIN_ZOOM_FOR_SMALL or if selected
        - Filled regions: never show

        Args:
            camera: Camera for coordinate transforms.
            selected_region: Currently selected region ID.
        """
        # Get visible area bounds for culling
        vis_x, vis_y, vis_w, vis_h = camera.get_visible_world_rect()
        vis_right = vis_x + vis_w
        vis_bottom = vis_y + vis_h

        # Calculate font size based on zoom (with limits)
        base_font_size = 14
        font_size = int(base_font_size * min(camera.zoom, 4.0))
        font_size = max(12, min(font_size, 36))
        font = pygame.font.Font(None, font_size)

        for region_id in range(self.puzzle.num_regions):
            # Skip filled regions
            if self.puzzle.filled[region_id]:
                continue

            area = self.puzzle.region_area[region_id]
            if area == 0:
                continue

            # Determine if number should be shown
            is_selected = region_id == selected_region
            is_large = area >= self.MIN_AREA_FOR_NUMBER
            is_zoomed_enough = camera.zoom >= self.MIN_ZOOM_FOR_SMALL

            if not (is_selected or is_large or is_zoomed_enough):
                continue

            # Get centroid and check if in view
            cx, cy = self.puzzle.region_centroid[region_id]
            if cx < vis_x or cx > vis_right or cy < vis_y or cy > vis_bottom:
                continue

            # Convert to screen coordinates
            screen_x, screen_y = camera.world_to_screen(cx, cy)

            # Check if on screen
            if (
                screen_x < 0
                or screen_x > self.screen_w
                or screen_y < 0
                or screen_y > self.screen_h
            ):
                continue

            # Check if region is large enough on screen to fit a number
            bbox = self.puzzle.region_bbox[region_id]
            bbox_w = (bbox[2] - bbox[0]) * camera.zoom
            bbox_h = (bbox[3] - bbox[1]) * camera.zoom
            min_dim = min(bbox_w, bbox_h)

            if min_dim < self.MIN_SCREEN_SIZE_FOR_NUMBER and not is_selected:
                continue

            # Get the number to display
            color_idx = self.puzzle.region_color[region_id]
            number = self.puzzle.palette_numbers[color_idx]

            # Choose color based on selection
            text_color = self.NUMBER_COLOR_SELECTED if is_selected else self.NUMBER_COLOR

            # Render the number
            text = font.render(str(number), True, text_color)
            text_rect = text.get_rect(center=(int(screen_x), int(screen_y)))
            self.screen.blit(text, text_rect)

    def _draw_palette_ui(self, selected_index: int) -> None:
        """Draw the palette selection UI.

        Args:
            selected_index: Currently selected palette index.
        """
        palette = self.puzzle.palette
        num_colors = len(palette)

        # Draw palette at bottom of screen
        swatch_size = 40
        spacing = 10
        total_width = num_colors * swatch_size + (num_colors - 1) * spacing
        start_x = (self.screen_w - total_width) // 2
        y = self.screen_h - 80

        for i, color in enumerate(palette):
            x = start_x + i * (swatch_size + spacing)
            rect = pygame.Rect(x, y, swatch_size, swatch_size)

            # Draw swatch
            pygame.draw.rect(self.screen, color, rect)

            # Draw selection border
            if i == selected_index:
                pygame.draw.rect(self.screen, self.HIGHLIGHT_COLOR, rect, 3)
            else:
                pygame.draw.rect(self.screen, self.OUTLINE_COLOR, rect, 1)

            # Draw number
            font = pygame.font.Font(None, 24)
            number = self.puzzle.palette_numbers[i]
            text = font.render(str(number), True, (0, 0, 0))
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)

    def _draw_selection_info(self, selected_region: int, camera: Camera) -> None:
        """Draw info about the selected region.

        Args:
            selected_region: Currently selected region ID.
            camera: Camera for zoom display.
        """
        if selected_region < 0 or selected_region >= self.puzzle.num_regions:
            return

        font = pygame.font.Font(None, 28)

        # Region info
        area = self.puzzle.region_area[selected_region]
        color_idx = self.puzzle.region_color[selected_region]
        target_num = self.puzzle.palette_numbers[color_idx]
        filled = self.puzzle.filled[selected_region]
        status = "Filled" if filled else "Empty"

        text = f"Region {selected_region} | Target: {target_num} | Area: {area}px | {status} | Zoom: {camera.zoom:.1f}x"
        rendered = font.render(text, True, (200, 200, 200))
        self.screen.blit(rendered, (20, 20))

        # Controls hint
        hint = "A: Fill | RStick: Navigate | DPad: Jump | LStick: Pan | Triggers: Zoom | LB/RB: Palette"
        hint_rendered = font.render(hint, True, (150, 150, 150))
        self.screen.blit(hint_rendered, (20, self.screen_h - 30))


def create_puzzle_snapshot(
    puzzle: Puzzle,
    renderer: "GameRenderer",
) -> pygame.Surface:
    """Create a snapshot image of the completed puzzle.

    Args:
        puzzle: The completed puzzle.
        renderer: The game renderer with filled surfaces.

    Returns:
        A pygame Surface containing the completed puzzle image.
    """
    # Create a surface matching the puzzle size
    snapshot = pygame.Surface((puzzle.width, puzzle.height))

    # Draw the base (unfilled background with outlines)
    snapshot.blit(renderer.base_surface, (0, 0))

    # Draw all filled regions
    snapshot.blit(renderer.filled_surface, (0, 0))

    return snapshot


def save_snapshot_to_gallery(
    snapshot: pygame.Surface,
    gallery_dir: Path,
) -> Path | None:
    """Save a puzzle snapshot to the gallery.

    Args:
        snapshot: The puzzle snapshot surface.
        gallery_dir: Path to gallery directory.

    Returns:
        Path to saved image, or None if save failed.
    """
    # Ensure gallery directory exists
    gallery_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"puzzle_{timestamp}.png"
    filepath = gallery_dir / filename

    try:
        pygame.image.save(snapshot, str(filepath))
        return filepath
    except pygame.error as e:
        print(f"Failed to save snapshot: {e}")
        return None


def show_completion_screen(
    screen: pygame.Surface,
    input_handler: InputHandler,
    snapshot: pygame.Surface,
) -> None:
    """Show the puzzle completion screen.

    Args:
        screen: Pygame display surface.
        input_handler: Input handler instance.
        snapshot: The completed puzzle snapshot.
    """
    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()

    # Fonts
    title_font = pygame.font.Font(None, 72)
    hint_font = pygame.font.Font(None, 32)

    # Scale snapshot to fit screen nicely
    img_w, img_h = snapshot.get_size()
    max_w, max_h = screen_w - 100, screen_h - 200
    scale = min(max_w / img_w, max_h / img_h, 2.0)  # Allow up to 2x scaling
    new_w, new_h = int(img_w * scale), int(img_h * scale)
    scaled_snapshot = pygame.transform.smoothscale(snapshot, (new_w, new_h))

    # Animation state
    fade_in = 0.0
    celebration_time = 0.0

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        fade_in = min(fade_in + dt * 2.0, 1.0)  # Fade in over 0.5 seconds
        celebration_time += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    running = False

        input_handler.update()

        # Any button press after fade-in completes
        if fade_in >= 1.0:
            if input_handler.is_button_pressed(BUTTON_A) or input_handler.is_button_pressed(BUTTON_B):
                running = False

        # Render
        screen.fill((20, 25, 30))

        # Draw title with gentle pulse
        pulse = 1.0 + 0.05 * abs((celebration_time * 2) % 2 - 1)
        title_text = "Puzzle Complete!"
        title_color = (100, 220, 150)
        title_surf = title_font.render(title_text, True, title_color)
        title_rect = title_surf.get_rect(centerx=screen_w // 2, top=40)

        # Scale title with pulse
        if pulse != 1.0:
            pw, ph = title_surf.get_size()
            scaled_title = pygame.transform.smoothscale(
                title_surf, (int(pw * pulse), int(ph * pulse))
            )
            title_rect = scaled_title.get_rect(centerx=screen_w // 2, top=40)
            screen.blit(scaled_title, title_rect)
        else:
            screen.blit(title_surf, title_rect)

        # Draw snapshot with fade-in
        snapshot_rect = scaled_snapshot.get_rect(center=(screen_w // 2, screen_h // 2 + 20))
        if fade_in < 1.0:
            temp = scaled_snapshot.copy()
            temp.set_alpha(int(255 * fade_in))
            screen.blit(temp, snapshot_rect)
        else:
            screen.blit(scaled_snapshot, snapshot_rect)

        # Draw border around snapshot
        border_rect = snapshot_rect.inflate(8, 8)
        pygame.draw.rect(screen, (80, 80, 90), border_rect, 3, border_radius=4)

        # Draw hint
        hint_text = "Press A or B to continue"
        hint_surf = hint_font.render(hint_text, True, (120, 120, 120))
        hint_rect = hint_surf.get_rect(centerx=screen_w // 2, bottom=screen_h - 40)
        screen.blit(hint_surf, hint_rect)

        pygame.display.flip()


def run_game(
    screen: pygame.Surface,
    input_handler: InputHandler,
    puzzle_dir: Path,
    puzzle_path_str: str,
    gallery_dir: Path | None = None,
) -> bool:
    """Run the main game loop.

    Args:
        screen: Pygame display surface.
        input_handler: Input handler instance.
        puzzle_dir: Path to puzzle directory.
        puzzle_path_str: Puzzle path string for save file.
        gallery_dir: Path to gallery directory for saving completed puzzles.

    Returns:
        True if puzzle was completed, False if exited early.
    """
    screen_w, screen_h = screen.get_size()

    # Load puzzle
    print("Loading puzzle...")
    puzzle = load_puzzle(puzzle_dir)
    print(f"Loaded: {puzzle.width}x{puzzle.height}, {puzzle.num_regions} regions")

    # Initialize subsystems
    selection = SelectionController(puzzle)
    renderer = GameRenderer(puzzle, screen)
    camera = Camera(puzzle.width, puzzle.height, screen_w, screen_h)
    fill_controller = FillController()
    save_manager = SaveManager()

    # Draw any pre-filled regions (e.g. border region outside the circle)
    for i in range(puzzle.num_regions):
        if puzzle.filled[i]:
            renderer.draw_filled_region(i)

    # Game state
    selected_palette = 0
    running = True
    clock = pygame.time.Clock()

    # Try to load saved state
    saved_data = save_manager.load()
    if saved_data is not None and saved_data.puzzle_path == puzzle_path_str:
        print("Loading saved progress...")

        # Restore filled regions
        for i, is_filled in enumerate(saved_data.filled_regions):
            if i < puzzle.num_regions and is_filled:
                puzzle.filled[i] = True
                renderer.draw_filled_region(i)

        # Restore UI state
        selected_palette = saved_data.selected_palette % len(puzzle.palette)
        if 0 <= saved_data.selected_region < puzzle.num_regions:
            selection.select_region(saved_data.selected_region)

        # Restore camera state
        camera.cam_x = saved_data.camera_x
        camera.cam_y = saved_data.camera_y
        camera.zoom = max(Camera.MIN_ZOOM, min(saved_data.camera_zoom, Camera.MAX_ZOOM))

        filled_count = sum(1 for f in puzzle.filled if f)
        print(f"Restored: {filled_count}/{puzzle.num_regions} regions filled")
    else:
        if saved_data is not None:
            print("Save file is for a different puzzle, starting fresh")
        else:
            print("No save file found, starting fresh")

    # Track previous state for movement detection
    prev_selected_region = selection.selected_region
    prev_cam_x, prev_cam_y = camera.cam_x, camera.cam_y
    prev_zoom = camera.zoom

    # Movement thresholds for fill cancellation
    PAN_CANCEL_THRESHOLD = 5.0  # World pixels
    ZOOM_CANCEL_THRESHOLD = 0.1  # Zoom units

    while running:
        dt_ms = clock.tick(60)
        dt_sec = dt_ms / 1000.0

        # Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        # Update input
        input_handler.update()

        # Check exit (only when not filling)
        if input_handler.is_button_pressed(BUTTON_B) and not fill_controller.is_active():
            running = False

        # Track if any cancel-worthy movement happened
        selection_changed = False
        camera_moved = False
        zoom_changed = False

        # Palette selection (only when not filling)
        if not fill_controller.is_active():
            if input_handler.is_button_pressed(BUTTON_LB):
                selected_palette = (selected_palette - 1) % len(puzzle.palette)
            if input_handler.is_button_pressed(BUTTON_RB):
                selected_palette = (selected_palette + 1) % len(puzzle.palette)

        # Right stick navigation (only when not filling)
        rx, ry = input_handler.state.right_stick
        if not fill_controller.is_active():
            if selection.update_stick_selection(rx, ry, dt_ms):
                selection_changed = True
                print(f"Selected region {selection.selected_region}")
        elif abs(rx) > 0.5 or abs(ry) > 0.5:
            # Cancel fill on right stick movement
            selection_changed = True

        # D-pad navigation (only when not filling)
        if input_handler.state.dpad_pressed:
            if not fill_controller.is_active():
                dx, dy = input_handler.state.dpad_pressed
                if selection.handle_dpad(dx, dy):
                    selection_changed = True
                    print(f"Jumped to region {selection.selected_region}")
            else:
                # Cancel fill on D-pad
                selection_changed = True

        # Camera controls: trigger zoom
        if camera.update_zoom(input_handler.state.rt, input_handler.state.lt, dt_sec):
            if abs(camera.zoom - prev_zoom) > ZOOM_CANCEL_THRESHOLD:
                zoom_changed = True

        # Camera controls: left stick pan
        lx, ly = input_handler.state.left_stick
        if camera.update_pan(lx, ly, dt_sec):
            dx = abs(camera.cam_x - prev_cam_x)
            dy = abs(camera.cam_y - prev_cam_y)
            if dx > PAN_CANCEL_THRESHOLD or dy > PAN_CANCEL_THRESHOLD:
                camera_moved = True

        # Camera controls: L3 snap to selected region (only when not filling)
        if input_handler.is_button_pressed(BUTTON_L3) and not fill_controller.is_active():
            centroid = puzzle.region_centroid[selection.selected_region]
            camera.snap_to(centroid[0], centroid[1])
            print(f"Snapped camera to region {selection.selected_region}")

        # Camera nudge: keep selected region visible when selection changes
        if selection.selected_region != prev_selected_region:
            prev_selected_region = selection.selected_region
            centroid = puzzle.region_centroid[selection.selected_region]
            camera.nudge_to_keep_visible(centroid[0], centroid[1], dt_sec)
        else:
            centroid = puzzle.region_centroid[selection.selected_region]
            camera.nudge_to_keep_visible(centroid[0], centroid[1], dt_sec)

        # Fill action: cancel on movement
        if fill_controller.is_filling():
            if selection_changed or camera_moved or zoom_changed:
                fill_controller.cancel()
                renderer.clear_temp_fill()
                print("Fill cancelled due to movement")

        # Fill action: start on A press
        if input_handler.is_button_pressed(BUTTON_A) and not fill_controller.is_active():
            region_id = selection.selected_region
            # Don't allow filling already-filled regions
            if not puzzle.filled[region_id]:
                region_area = puzzle.region_area[region_id]
                correct_idx = puzzle.region_color[region_id]
                fill_controller.start_fill(
                    region_id, region_area, selected_palette, correct_idx
                )
                # Draw preview
                renderer.draw_temp_fill(region_id, selected_palette)
                print(f"Started filling region {region_id}")

        # Update fill controller
        a_held = input_handler.is_button_held(BUTTON_A)
        fill_completed, was_correct, completed_region = fill_controller.update(dt_sec, a_held)

        # Handle fill completion
        if fill_completed:
            if was_correct:
                # Commit the fill to permanent surface
                puzzle.filled[completed_region] = True
                renderer.draw_filled_region(completed_region)
                renderer.clear_temp_fill()

                # Autosave after successful fill
                save_data = create_save_data(
                    puzzle_path=puzzle_path_str,
                    filled=puzzle.filled,
                    selected_palette=selected_palette,
                    selected_region=selection.selected_region,
                    camera_x=camera.cam_x,
                    camera_y=camera.cam_y,
                    camera_zoom=camera.zoom,
                )
                if save_manager.save(save_data):
                    filled_count = sum(1 for f in puzzle.filled if f)
                    print(f"Fill completed! Region {completed_region} filled. Progress: {filled_count}/{puzzle.num_regions}")
                else:
                    print(f"Fill completed! Region {completed_region} filled. (Save failed)")

                # Check for puzzle completion
                if all(puzzle.filled):
                    print("Puzzle complete!")

                    # Create snapshot of completed puzzle
                    snapshot = create_puzzle_snapshot(puzzle, renderer)

                    # Save to gallery
                    if gallery_dir is not None:
                        saved_path = save_snapshot_to_gallery(snapshot, gallery_dir)
                        if saved_path:
                            print(f"Saved to gallery: {saved_path}")

                    # Show completion screen
                    show_completion_screen(screen, input_handler, snapshot)

                    # Delete save file (puzzle is complete)
                    save_manager.delete_save()

                    return True
            else:
                # Wrong fill - just clear the temp surface
                renderer.clear_temp_fill()
                print("Wrong color! Fill rejected.")

        # Update tracking for next frame
        prev_cam_x, prev_cam_y = camera.cam_x, camera.cam_y
        prev_zoom = camera.zoom

        # Render
        renderer.render(selection.selected_region, selected_palette, camera, fill_controller)

    # Exited without completing
    return False


def generate_new_puzzle(
    screen: pygame.Surface,
    input_handler: InputHandler,
    settings: PuzzleSettings,
) -> tuple[Path, str] | None:
    """Generate a new puzzle from settings.

    Args:
        screen: Pygame display surface.
        input_handler: Input handler instance.
        settings: Puzzle generation settings.

    Returns:
        Tuple of (puzzle_dir, puzzle_path_str) if successful, None if failed.
    """
    from settings import SettingsMenu

    # Create output directory
    base_dir = Path(__file__).parent / "puzzles" / "current"
    puzzle_path_str = "puzzles/current"

    # Show generating message
    screen.fill((30, 30, 35))
    font = pygame.font.Font(None, 48)
    text = font.render("Generating puzzle...", True, (200, 200, 200))
    text_rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
    screen.blit(text, text_rect)
    pygame.display.flip()

    # Generate puzzle
    menu = SettingsMenu(screen)
    menu.settings = settings
    if menu.generate_puzzle(base_dir):
        return (base_dir, puzzle_path_str)
    return None


def show_gallery(screen: pygame.Surface, input_handler: InputHandler, gallery_dir: Path) -> None:
    """Show the gallery of completed puzzles.

    Args:
        screen: Pygame display surface.
        input_handler: Input handler instance.
        gallery_dir: Path to gallery directory.
    """
    from menu import MenuRenderer

    # Placeholder - will be fully implemented in milestone 11
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 48)
    hint_font = pygame.font.Font(None, 32)

    # Get list of gallery images
    images: list[Path] = []
    if gallery_dir.exists():
        for ext in ("*.png", "*.jpg", "*.jpeg"):
            images.extend(gallery_dir.glob(ext))
    images.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    current_index = 0
    current_image: pygame.Surface | None = None

    if images:
        try:
            current_image = pygame.image.load(str(images[0]))
        except pygame.error:
            pass

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        input_handler.update()

        # B to go back
        if input_handler.is_button_pressed(BUTTON_B):
            running = False

        # LB/RB to navigate images
        if images:
            if input_handler.is_button_pressed(BUTTON_LB):
                current_index = (current_index - 1) % len(images)
                try:
                    current_image = pygame.image.load(str(images[current_index]))
                except pygame.error:
                    current_image = None
            if input_handler.is_button_pressed(BUTTON_RB):
                current_index = (current_index + 1) % len(images)
                try:
                    current_image = pygame.image.load(str(images[current_index]))
                except pygame.error:
                    current_image = None

        # Render
        screen.fill((30, 30, 35))

        if not images:
            text = font.render("Gallery is empty", True, (150, 150, 150))
            text_rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
            screen.blit(text, text_rect)
        elif current_image:
            # Scale image to fit screen while maintaining aspect ratio
            img_w, img_h = current_image.get_size()
            screen_w, screen_h = screen.get_size()
            max_w, max_h = screen_w - 100, screen_h - 150

            scale = min(max_w / img_w, max_h / img_h, 1.0)
            new_w, new_h = int(img_w * scale), int(img_h * scale)

            scaled = pygame.transform.smoothscale(current_image, (new_w, new_h))
            img_rect = scaled.get_rect(center=(screen_w // 2, screen_h // 2 - 30))
            screen.blit(scaled, img_rect)

            # Show image counter
            counter = font.render(f"{current_index + 1} / {len(images)}", True, (200, 200, 200))
            counter_rect = counter.get_rect(centerx=screen_w // 2, top=30)
            screen.blit(counter, counter_rect)

        # Show controls hint
        hint = hint_font.render("LB/RB: Navigate | B: Back", True, (120, 120, 120))
        hint_rect = hint.get_rect(centerx=screen.get_width() // 2, bottom=screen.get_height() - 30)
        screen.blit(hint, hint_rect)

        pygame.display.flip()
        clock.tick(60)


def main() -> None:
    """Main entry point."""
    pygame.init()

    # Initialize display (fullscreen)
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("BusyBrainPaint")

    # Initialize input handler
    input_handler = InputHandler()

    # Set up paths
    base_path = Path(__file__).parent
    gallery_dir = base_path / "gallery"
    save_manager = SaveManager()

    # Main application loop - returns to menu after each game
    running = True
    while running:
        # Show main menu
        result = run_main_menu(screen, input_handler, save_manager, gallery_dir)

        if result == "quit":
            running = False

        elif result == "new_game":
            # Show settings menu
            settings_result, settings = run_settings_menu(screen, input_handler)

            if settings_result == "generate" and settings is not None:
                # Generate new puzzle
                gen_result = generate_new_puzzle(screen, input_handler, settings)
                if gen_result:
                    puzzle_dir, puzzle_path_str = gen_result
                    # Clear old save since we have a new puzzle
                    save_manager.delete_save()
                    # Run the game
                    run_game(screen, input_handler, puzzle_dir, puzzle_path_str, gallery_dir)
                else:
                    # Generation failed, return to menu
                    print("Failed to generate puzzle")
            # If cancelled, loop back to main menu

        elif result == "continue":
            # Load existing puzzle
            puzzle_dir = base_path / "puzzles" / "current"
            puzzle_path_str = "puzzles/current"

            # Fallback to stub puzzle if current doesn't exist
            if not puzzle_dir.exists():
                stub_dir = base_path / "puzzles" / "stub"
                if stub_dir.exists():
                    puzzle_dir = stub_dir
                    puzzle_path_str = "puzzles/stub"

            if puzzle_dir.exists():
                run_game(screen, input_handler, puzzle_dir, puzzle_path_str, gallery_dir)
            else:
                print(f"No puzzle found at {puzzle_dir}")

        elif result == "gallery":
            show_gallery(screen, input_handler, gallery_dir)

    pygame.quit()
    print("Done.")


if __name__ == "__main__":
    main()
