"""Main menu for BusyBrainPaint.

Provides the initial menu with New Game, Continue, and Gallery options.
"""

from pathlib import Path

import pygame

from input_handler import InputHandler, BUTTON_A, BUTTON_B, BUTTON_LB, BUTTON_RB
from menu import Menu, MenuItem, MenuItemType, MenuRenderer, MenuController
from save_manager import SaveManager


class MainMenu:
    """Main menu for the game."""

    def __init__(
        self,
        screen: pygame.Surface,
        has_save: bool,
        has_gallery: bool = False,
    ) -> None:
        """Initialize main menu.

        Args:
            screen: Pygame surface for rendering.
            has_save: Whether a save file exists (enables Continue).
            has_gallery: Whether gallery has any images (enables Gallery).
        """
        self.screen = screen
        self.has_save = has_save
        self.has_gallery = has_gallery
        self.renderer = MenuRenderer(screen)
        self.controller = MenuController()

        self._result: str | None = None
        self._build_menu()

    def _build_menu(self) -> None:
        """Build the main menu."""
        self.menu = Menu("BusyBrainPaint", [
            MenuItem(
                label="New Game",
                item_type=MenuItemType.ACTION,
                action=self._on_new_game,
            ),
            MenuItem(
                label="Continue",
                item_type=MenuItemType.ACTION,
                action=self._on_continue,
                enabled=self.has_save,
            ),
            MenuItem(
                label="Gallery",
                item_type=MenuItemType.ACTION,
                action=self._on_gallery,
                enabled=self.has_gallery,
            ),
            MenuItem(
                label="Quit",
                item_type=MenuItemType.ACTION,
                action=self._on_quit,
            ),
        ])

    def _on_new_game(self) -> None:
        """Handle New Game selection."""
        self._result = "new_game"

    def _on_continue(self) -> None:
        """Handle Continue selection."""
        self._result = "continue"

    def _on_gallery(self) -> None:
        """Handle Gallery selection."""
        self._result = "gallery"

    def _on_quit(self) -> None:
        """Handle Quit selection."""
        self._result = "quit"

    def run(self, input_handler: InputHandler) -> str:
        """Run the main menu.

        Args:
            input_handler: Input handler for controller input.

        Returns:
            One of: "new_game", "continue", "gallery", "quit"
        """
        self._result = None
        clock = pygame.time.Clock()

        while self._result is None:
            dt_ms = clock.tick(60)

            # Process events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "quit"

            # Update input
            input_handler.update()

            # Get input state
            dpad = input_handler.state.dpad
            left_stick = input_handler.state.left_stick
            a_pressed = input_handler.is_button_pressed(BUTTON_A)
            b_pressed = input_handler.is_button_pressed(BUTTON_B)
            lb_pressed = input_handler.is_button_pressed(BUTTON_LB)
            rb_pressed = input_handler.is_button_pressed(BUTTON_RB)

            # Update menu
            self.controller.update(
                self.menu,
                dpad,
                left_stick,
                dt_ms,
                a_pressed,
                b_pressed,
                lb_pressed,
                rb_pressed,
            )

            # Render
            self.renderer.render(self.menu)

        return self._result


def check_gallery_has_images(gallery_dir: Path) -> bool:
    """Check if gallery directory has any images.

    Args:
        gallery_dir: Path to gallery directory.

    Returns:
        True if gallery has at least one image.
    """
    if not gallery_dir.exists():
        return False

    for ext in ("*.png", "*.jpg", "*.jpeg"):
        if list(gallery_dir.glob(ext)):
            return True
    return False


def run_main_menu(
    screen: pygame.Surface,
    input_handler: InputHandler,
    save_manager: SaveManager,
    gallery_dir: Path,
) -> str:
    """Run the main menu and return the selected action.

    Args:
        screen: Pygame surface for rendering.
        input_handler: Input handler for controller input.
        save_manager: Save manager to check for existing saves.
        gallery_dir: Path to gallery directory.

    Returns:
        One of: "new_game", "continue", "gallery", "quit"
    """
    has_save = save_manager.has_save()
    has_gallery = check_gallery_has_images(gallery_dir)

    menu = MainMenu(screen, has_save, has_gallery)
    return menu.run(input_handler)
