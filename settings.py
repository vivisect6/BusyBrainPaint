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
)
from menu import Menu, MenuItem, MenuItemType, MenuRenderer, MenuController
from input_handler import InputHandler, BUTTON_A, BUTTON_B, BUTTON_LB, BUTTON_RB
from palettes import PALETTE_NAMES, get_palette


# Scale presets: name -> (width, height, detail_multiplier)
SCALE_PRESETS = {
    "Small": (512, 512, 1.0),
    "Medium": (768, 768, 1.5),
    "Large": (1024, 1024, 2.0),
    "Extra Large": (1280, 1280, 2.5),
}

# Color count options
COLOR_OPTIONS = [6, 8, 12, 16, 24]

# Symmetry presets: label -> number of slices
SYMMETRY_PRESETS = {
    "Minimal": 4,
    "Low": 6,
    "Medium": 8,
    "High": 10,
    "Very High": 12,
    "Ultra": 16,
}

# Preset display names
PRESET_NAMES = {
    "voronoi_mandala": "Voronoi Mandala",
    "stained_glass": "Stained Glass",
}

# Per-generator option values
OUTLINE_WEIGHT_PRESETS = {"Thin": 2, "Medium": 4, "Thick": 6}
OUTLINE_WEIGHT_OPTIONS = list(OUTLINE_WEIGHT_PRESETS.keys())


@dataclass
class PuzzleSettings:
    """Settings for puzzle generation."""

    preset: str = "voronoi_mandala"
    scale: str = "Medium"
    num_colors: int = 6
    palette_name: str = "Classic"
    symmetry: int = 8
    seed: int | None = None  # None = random
    # Stained Glass options
    outline_weight: str = "Medium"

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

        kwargs: dict[str, Any] = {
            "width": width,
            "height": height,
            "num_colors": self.num_colors,
            "seed": self.seed if self.seed is not None else random.randint(0, 2**31),
        }

        if self.preset == "voronoi_mandala":
            kwargs["symmetry_slices"] = self.symmetry
            kwargs["point_count"] = int(30 * detail)
            kwargs["relax_iters"] = 1
        elif self.preset == "stained_glass":
            kwargs["symmetry_slices"] = self.symmetry
            kwargs["point_count"] = max(int(80 * detail), self.symmetry * 3)
            base_thickness = OUTLINE_WEIGHT_PRESETS.get(self.outline_weight, 4)
            kwargs["outline_thickness"] = max(1, int(base_thickness * detail))

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
        self._last_preset_idx: int = 0
        self._build_menu()

    def _build_menu(self) -> None:
        """Build the settings menu with per-generator options."""
        preset_options = list(PRESET_NAMES.values())
        preset_keys = list(PRESET_NAMES.keys())
        scale_options = list(SCALE_PRESETS.keys())
        color_options = [str(c) for c in COLOR_OPTIONS]
        symmetry_options = list(SYMMETRY_PRESETS.keys())
        symmetry_values = list(SYMMETRY_PRESETS.values())

        preset_idx = (
            preset_keys.index(self.settings.preset)
            if self.settings.preset in preset_keys
            else 0
        )
        scale_idx = (
            scale_options.index(self.settings.scale)
            if self.settings.scale in scale_options
            else 1
        )
        color_idx = (
            COLOR_OPTIONS.index(self.settings.num_colors)
            if self.settings.num_colors in COLOR_OPTIONS
            else 0
        )
        symmetry_idx = (
            symmetry_values.index(self.settings.symmetry)
            if self.settings.symmetry in symmetry_values
            else 2
        )

        # Common items always shown first
        items: list[MenuItem] = [
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
        ]

        # Palette selector (shown for all generators)
        palette_options = ["Random"] + PALETTE_NAMES
        palette_idx = (
            palette_options.index(self.settings.palette_name)
            if self.settings.palette_name in palette_options
            else 0
        )
        palette_swatches: list[list[tuple[int, int, int]]] = [[]]  # Empty for "Random"
        for name in PALETTE_NAMES:
            palette_swatches.append(get_palette(name, self.settings.num_colors))
        items.append(
            MenuItem(
                label="Palette",
                item_type=MenuItemType.SELECTOR,
                options=palette_options,
                selected_index=palette_idx,
                swatches=palette_swatches,
            )
        )

        current_preset = self.settings.preset

        # Symmetry: relevant for voronoi mandala and stained glass
        if current_preset in ("voronoi_mandala", "stained_glass"):
            items.append(
                MenuItem(
                    label="Symmetry",
                    item_type=MenuItemType.SELECTOR,
                    options=symmetry_options,
                    selected_index=symmetry_idx,
                )
            )

        # Stained Glass specific: outline weight
        if current_preset == "stained_glass":
            weight_idx = (
                OUTLINE_WEIGHT_OPTIONS.index(self.settings.outline_weight)
                if self.settings.outline_weight in OUTLINE_WEIGHT_OPTIONS
                else 1
            )
            items.append(
                MenuItem(
                    label="Outline",
                    item_type=MenuItemType.SELECTOR,
                    options=OUTLINE_WEIGHT_OPTIONS,
                    selected_index=weight_idx,
                )
            )

        # Action buttons always at the end
        items.append(
            MenuItem(
                label="Generate Puzzle",
                item_type=MenuItemType.ACTION,
                action=self._on_generate,
            )
        )
        items.append(
            MenuItem(
                label="Cancel",
                item_type=MenuItemType.ACTION,
                action=self._on_cancel,
            )
        )

        self.menu = Menu("New Puzzle Settings", items)
        self._last_preset_idx = preset_idx
        self._last_color_idx = color_idx

    def _on_generate(self) -> None:
        """Handle generate button press."""
        self._apply_settings()
        self._result = "generate"

    def _on_cancel(self) -> None:
        """Handle cancel button press."""
        self._result = "cancel"

    def _apply_settings(self) -> None:
        """Apply menu selections to settings."""
        for item in self.menu.items:
            if item.item_type != MenuItemType.SELECTOR:
                continue
            if item.label == "Preset":
                preset_keys = list(PRESET_NAMES.keys())
                self.settings.preset = preset_keys[item.selected_index]
            elif item.label == "Size":
                self.settings.scale = list(SCALE_PRESETS.keys())[
                    item.selected_index
                ]
            elif item.label == "Colors":
                self.settings.num_colors = COLOR_OPTIONS[item.selected_index]
            elif item.label == "Palette":
                palette_options = ["Random"] + PALETTE_NAMES
                self.settings.palette_name = palette_options[item.selected_index]
            elif item.label == "Symmetry":
                self.settings.symmetry = list(SYMMETRY_PRESETS.values())[item.selected_index]
            elif item.label == "Outline":
                self.settings.outline_weight = OUTLINE_WEIGHT_OPTIONS[
                    item.selected_index
                ]

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

            # Rebuild menu when preset changes
            preset_item = self.menu.items[0]
            if preset_item.selected_index != self._last_preset_idx:
                self._apply_settings()
                self._build_menu()

            # Update palette swatches when color count changes
            colors_item = self.menu.items[2]  # "Colors" selector
            if colors_item.selected_index != self._last_color_idx:
                self._last_color_idx = colors_item.selected_index
                num_colors = COLOR_OPTIONS[colors_item.selected_index]
                for item in self.menu.items:
                    if item.label == "Palette" and item.swatches is not None:
                        item.swatches = [[]]  # Empty for "Random"
                        for name in PALETTE_NAMES:
                            item.swatches.append(get_palette(name, num_colors))
                        break

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
            palette = get_palette(self.settings.palette_name, self.settings.num_colors)
            create_puzzle(
                generator, output_dir,
                num_colors=self.settings.num_colors,
                palette=palette,
            )
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
