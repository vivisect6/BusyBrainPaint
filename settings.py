"""Settings management for BusyBrainPaint.

Handles puzzle generation settings and the settings menu.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import random

import pygame

from generators import (
    get_generator,
    create_puzzle,
    PRESETS,
    TilingType,
)
from menu import Menu, MenuItem, MenuItemType, MenuRenderer, MenuController
from input_handler import InputHandler, BUTTON_A, BUTTON_B, BUTTON_LB, BUTTON_RB


# Scale presets: name -> (width, height, detail_multiplier)
SCALE_PRESETS = {
    "Small": (256, 256, 0.5),
    "Medium": (384, 384, 0.75),
    "Large": (512, 512, 1.0),
    "Extra Large": (640, 640, 1.25),
}

# Color count options
COLOR_OPTIONS = [6, 8, 12, 16, 24]

# Symmetry options
SYMMETRY_OPTIONS = [4, 6, 8, 10, 12, 16]

# Preset display names
PRESET_NAMES = {
    "voronoi_mandala": "Voronoi Mandala",
    "polar_harmonics": "Polar Harmonics",
    "geometric_tiling": "Geometric Tiling",
    "stained_glass": "Stained Glass",
}


@dataclass
class PuzzleSettings:
    """Settings for puzzle generation."""

    preset: str = "voronoi_mandala"
    scale: str = "Medium"
    num_colors: int = 6
    symmetry: int = 8
    seed: int | None = None  # None = random

    def get_size(self) -> tuple[int, int]:
        """Get puzzle dimensions based on scale."""
        return SCALE_PRESETS[self.scale][:2]

    def get_detail_multiplier(self) -> float:
        """Get detail multiplier based on scale."""
        return SCALE_PRESETS[self.scale][2]

    def to_generator_kwargs(self) -> dict[str, Any]:
        """Convert settings to generator kwargs."""
        width, height = self.get_size()
        detail = self.get_detail_multiplier()

        kwargs = {
            "width": width,
            "height": height,
            "num_colors": self.num_colors,
            "symmetry_slices": self.symmetry,
            "seed": self.seed if self.seed is not None else random.randint(0, 2**31),
        }

        # Preset-specific params scaled by detail
        if self.preset == "voronoi_mandala":
            kwargs["point_count"] = int(25 * detail)
            kwargs["relax_iters"] = 1
        elif self.preset == "polar_harmonics":
            kwargs["ring_count"] = int(4 + 2 * detail)
            kwargs["petal_depth"] = 0.3
        elif self.preset == "geometric_tiling":
            kwargs["tiling_type"] = TilingType.HEXAGON
            kwargs["cell_size"] = int(32 / detail) if detail > 0 else 32
        elif self.preset == "stained_glass":
            kwargs["point_count"] = int(20 * detail)
            kwargs["outline_thickness"] = max(2, int(4 * detail))

        return kwargs


class SettingsMenu:
    """Settings menu for configuring puzzle generation."""

    def __init__(self, screen: pygame.Surface) -> None:
        """Initialize settings menu.

        Args:
            screen: Pygame surface for rendering.
        """
        self.screen = screen
        self.settings = PuzzleSettings()
        self.renderer = MenuRenderer(screen)
        self.controller = MenuController()

        self._result: str | None = None  # "generate" or "cancel"
        self._build_menu()

    def _build_menu(self) -> None:
        """Build the settings menu."""
        preset_options = list(PRESET_NAMES.values())
        preset_keys = list(PRESET_NAMES.keys())

        scale_options = list(SCALE_PRESETS.keys())
        color_options = [str(c) for c in COLOR_OPTIONS]
        symmetry_options = [str(s) for s in SYMMETRY_OPTIONS]

        # Find current indices
        preset_idx = preset_keys.index(self.settings.preset) if self.settings.preset in preset_keys else 0
        scale_idx = scale_options.index(self.settings.scale) if self.settings.scale in scale_options else 1
        color_idx = COLOR_OPTIONS.index(self.settings.num_colors) if self.settings.num_colors in COLOR_OPTIONS else 0
        symmetry_idx = SYMMETRY_OPTIONS.index(self.settings.symmetry) if self.settings.symmetry in SYMMETRY_OPTIONS else 2

        self.menu = Menu("New Puzzle Settings", [
            MenuItem(
                label="Preset",
                item_type=MenuItemType.SELECTOR,
                options=preset_options,
                selected_index=preset_idx,
            ),
            MenuItem(
                label="Size",
                item_type=MenuItemType.SELECTOR,
                options=scale_options,
                selected_index=scale_idx,
            ),
            MenuItem(
                label="Colors",
                item_type=MenuItemType.SELECTOR,
                options=color_options,
                selected_index=color_idx,
            ),
            MenuItem(
                label="Symmetry",
                item_type=MenuItemType.SELECTOR,
                options=symmetry_options,
                selected_index=symmetry_idx,
            ),
            MenuItem(
                label="Generate Puzzle",
                item_type=MenuItemType.ACTION,
                action=self._on_generate,
            ),
            MenuItem(
                label="Cancel",
                item_type=MenuItemType.ACTION,
                action=self._on_cancel,
            ),
        ])

        # Store references for easy access
        self._preset_item = self.menu.items[0]
        self._scale_item = self.menu.items[1]
        self._colors_item = self.menu.items[2]
        self._symmetry_item = self.menu.items[3]

    def _on_generate(self) -> None:
        """Handle generate button press."""
        self._apply_settings()
        self._result = "generate"

    def _on_cancel(self) -> None:
        """Handle cancel button press."""
        self._result = "cancel"

    def _apply_settings(self) -> None:
        """Apply menu selections to settings."""
        preset_keys = list(PRESET_NAMES.keys())
        self.settings.preset = preset_keys[self._preset_item.selected_index]
        self.settings.scale = list(SCALE_PRESETS.keys())[self._scale_item.selected_index]
        self.settings.num_colors = COLOR_OPTIONS[self._colors_item.selected_index]
        self.settings.symmetry = SYMMETRY_OPTIONS[self._symmetry_item.selected_index]

    def run(self, input_handler: InputHandler) -> str | None:
        """Run the settings menu.

        Args:
            input_handler: Input handler for controller input.

        Returns:
            "generate" if user wants to generate puzzle,
            "cancel" if user cancelled,
            None if menu is still active.
        """
        self._result = None
        clock = pygame.time.Clock()

        while self._result is None:
            dt_ms = clock.tick(60)

            # Process events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "cancel"
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "cancel"

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
            _, back = self.controller.update(
                self.menu,
                dpad,
                left_stick,
                dt_ms,
                a_pressed,
                b_pressed,
                lb_pressed,
                rb_pressed,
            )

            if back:
                return "cancel"

            # Render
            self.renderer.render(self.menu)

        return self._result

    def generate_puzzle(self, output_dir: Path) -> bool:
        """Generate a puzzle with current settings.

        Args:
            output_dir: Directory to save puzzle files.

        Returns:
            True if generation succeeded.
        """
        try:
            kwargs = self.settings.to_generator_kwargs()
            generator = get_generator(self.settings.preset, **kwargs)
            create_puzzle(generator, output_dir, num_colors=self.settings.num_colors)
            return True
        except Exception as e:
            print(f"Failed to generate puzzle: {e}")
            return False


def run_settings_menu(
    screen: pygame.Surface,
    input_handler: InputHandler,
) -> tuple[str | None, PuzzleSettings | None]:
    """Run the settings menu and return result.

    Args:
        screen: Pygame surface for rendering.
        input_handler: Input handler for controller input.

    Returns:
        Tuple of (result, settings) where result is "generate" or "cancel",
        and settings is the configured PuzzleSettings if result is "generate".
    """
    menu = SettingsMenu(screen)
    result = menu.run(input_handler)

    if result == "generate":
        return (result, menu.settings)
    return (result, None)
