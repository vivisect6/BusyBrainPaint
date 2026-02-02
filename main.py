"""BusyBrainPaint - Paint-by-numbers mandala game."""

from pathlib import Path

import pygame

from input_handler import InputHandler, BUTTON_B, BUTTON_LB, BUTTON_RB
from puzzle_loader import Puzzle, load_puzzle
from selection import SelectionController


class GameRenderer:
    """Handles rendering of the puzzle and UI."""

    # Colors
    BACKGROUND = (40, 40, 40)
    OUTLINE_COLOR = (60, 60, 60)
    HIGHLIGHT_COLOR = (255, 255, 255)
    UNFILLED_COLOR = (220, 220, 220)

    def __init__(self, puzzle: Puzzle, screen: pygame.Surface) -> None:
        """Initialize renderer.

        Args:
            puzzle: The puzzle to render.
            screen: The pygame display surface.
        """
        self.puzzle = puzzle
        self.screen = screen
        self.screen_w, self.screen_h = screen.get_size()

        # Calculate scale to fit puzzle on screen with padding
        padding = 100
        available_w = self.screen_w - padding * 2
        available_h = self.screen_h - padding * 2
        scale_x = available_w / puzzle.width
        scale_y = available_h / puzzle.height
        self.scale = min(scale_x, scale_y, 6.0)  # Cap at 6x

        # Puzzle position (centered)
        self.puzzle_w = int(puzzle.width * self.scale)
        self.puzzle_h = int(puzzle.height * self.scale)
        self.puzzle_x = (self.screen_w - self.puzzle_w) // 2
        self.puzzle_y = (self.screen_h - self.puzzle_h) // 2

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

    def render(self, selected_region: int, selected_palette: int) -> None:
        """Render the full game view.

        Args:
            selected_region: Currently selected region ID.
            selected_palette: Currently selected palette index.
        """
        self.screen.fill(self.BACKGROUND)

        # Update highlight
        self.draw_region_highlight(selected_region)

        # Composite puzzle layers
        composite = self.base_surface.copy()
        composite.blit(self.filled_surface, (0, 0))
        composite.blit(self.highlight_surface, (0, 0))

        # Scale and blit to screen
        scaled = pygame.transform.scale(composite, (self.puzzle_w, self.puzzle_h))
        self.screen.blit(scaled, (self.puzzle_x, self.puzzle_y))

        # Draw palette indicator
        self._draw_palette_ui(selected_palette)

        # Draw selection info
        self._draw_selection_info(selected_region)

        pygame.display.flip()

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

    def _draw_selection_info(self, selected_region: int) -> None:
        """Draw info about the selected region.

        Args:
            selected_region: Currently selected region ID.
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

        text = f"Region {selected_region} | Target: {target_num} | Area: {area}px | {status}"
        rendered = font.render(text, True, (200, 200, 200))
        self.screen.blit(rendered, (20, 20))

        # Controls hint
        hint = "Right Stick: Navigate | D-Pad: Jump | LB/RB: Palette | B: Exit"
        hint_rendered = font.render(hint, True, (150, 150, 150))
        self.screen.blit(hint_rendered, (20, self.screen_h - 30))


def main() -> None:
    """Main entry point."""
    pygame.init()

    # Load stub puzzle
    puzzle_dir = Path(__file__).parent / "puzzles" / "stub"

    if not puzzle_dir.exists():
        print(f"Puzzle not found at {puzzle_dir}")
        print("Run 'python create_stub_puzzle.py' first to generate test assets.")
        return

    print("Loading puzzle...")
    puzzle = load_puzzle(puzzle_dir)
    print(f"Loaded: {puzzle.width}x{puzzle.height}, {puzzle.num_regions} regions")

    # Initialize display (fullscreen)
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("BusyBrainPaint")

    # Initialize subsystems
    input_handler = InputHandler()
    selection = SelectionController(puzzle)
    renderer = GameRenderer(puzzle, screen)

    # Game state
    selected_palette = 0
    running = True
    clock = pygame.time.Clock()

    # Mark some regions as filled for testing
    puzzle.filled[0] = True
    puzzle.filled[3] = True
    renderer.draw_filled_region(0)
    renderer.draw_filled_region(3)

    while running:
        dt_ms = clock.tick(60)

        # Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        # Update input
        input_handler.update()

        # Check exit
        if input_handler.is_button_pressed(BUTTON_B):
            running = False

        # Palette selection
        if input_handler.is_button_pressed(BUTTON_LB):
            selected_palette = (selected_palette - 1) % len(puzzle.palette)
        if input_handler.is_button_pressed(BUTTON_RB):
            selected_palette = (selected_palette + 1) % len(puzzle.palette)

        # Right stick navigation
        rx, ry = input_handler.state.right_stick
        if selection.update_stick_selection(rx, ry, dt_ms):
            print(f"Selected region {selection.selected_region}")

        # D-pad navigation
        if input_handler.state.dpad_pressed:
            dx, dy = input_handler.state.dpad_pressed
            if selection.handle_dpad(dx, dy):
                print(f"Jumped to region {selection.selected_region}")

        # Render
        renderer.render(selection.selected_region, selected_palette)

    pygame.quit()
    print("Done.")


if __name__ == "__main__":
    main()
