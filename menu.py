"""Menu system for BusyBrainPaint.

Provides controller-friendly menu navigation for settings and main menu.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable

import pygame


class MenuItemType(Enum):
    """Types of menu items."""

    ACTION = auto()  # Triggers a callback when selected
    SELECTOR = auto()  # Cycles through options
    SUBMENU = auto()  # Opens a submenu


@dataclass
class MenuItem:
    """A single menu item."""

    label: str
    item_type: MenuItemType
    options: list[str] | None = None  # For SELECTOR type
    selected_index: int = 0  # Current selection for SELECTOR
    action: Callable[[], None] | None = None  # For ACTION type
    submenu: "Menu | None" = None  # For SUBMENU type
    enabled: bool = True
    swatches: list[list[tuple[int, int, int]]] | None = None  # Per-option color swatches

    def get_display_value(self) -> str:
        """Get the current display value for selector items."""
        if self.item_type == MenuItemType.SELECTOR and self.options:
            return self.options[self.selected_index]
        return ""

    def cycle_next(self) -> None:
        """Cycle to next option (for SELECTOR)."""
        if self.item_type == MenuItemType.SELECTOR and self.options:
            self.selected_index = (self.selected_index + 1) % len(self.options)

    def cycle_prev(self) -> None:
        """Cycle to previous option (for SELECTOR)."""
        if self.item_type == MenuItemType.SELECTOR and self.options:
            self.selected_index = (self.selected_index - 1) % len(self.options)


class Menu:
    """A menu with navigable items."""

    def __init__(self, title: str, items: list[MenuItem]) -> None:
        """Initialize menu.

        Args:
            title: Menu title displayed at top.
            items: List of menu items.
        """
        self.title = title
        self.items = items
        self.selected_index = 0
        self._find_first_enabled()

    def _find_first_enabled(self) -> None:
        """Find and select first enabled item."""
        for i, item in enumerate(self.items):
            if item.enabled:
                self.selected_index = i
                return

    def move_up(self) -> None:
        """Move selection up to previous enabled item."""
        start = self.selected_index
        while True:
            self.selected_index = (self.selected_index - 1) % len(self.items)
            if self.items[self.selected_index].enabled:
                break
            if self.selected_index == start:
                break

    def move_down(self) -> None:
        """Move selection down to next enabled item."""
        start = self.selected_index
        while True:
            self.selected_index = (self.selected_index + 1) % len(self.items)
            if self.items[self.selected_index].enabled:
                break
            if self.selected_index == start:
                break

    def get_selected(self) -> MenuItem:
        """Get currently selected item."""
        return self.items[self.selected_index]


class MenuRenderer:
    """Renders menus to the screen."""

    # Colors
    BACKGROUND = (30, 30, 35)
    TITLE_COLOR = (255, 255, 255)
    ITEM_COLOR = (200, 200, 200)
    SELECTED_COLOR = (100, 200, 255)
    DISABLED_COLOR = (100, 100, 100)
    VALUE_COLOR = (150, 220, 150)
    HIGHLIGHT_BG = (50, 50, 60)

    def __init__(self, screen: pygame.Surface) -> None:
        """Initialize renderer.

        Args:
            screen: Pygame surface to render to.
        """
        self.screen = screen
        self.screen_w, self.screen_h = screen.get_size()
        self.title_font = pygame.font.Font(None, 64)
        self.item_font = pygame.font.Font(None, 42)
        self.hint_font = pygame.font.Font(None, 28)

    def render(self, menu: Menu) -> None:
        """Render a menu to the screen.

        Args:
            menu: Menu to render.
        """
        self.screen.fill(self.BACKGROUND)

        # Draw title
        title_surf = self.title_font.render(menu.title, True, self.TITLE_COLOR)
        title_rect = title_surf.get_rect(centerx=self.screen_w // 2, top=80)
        self.screen.blit(title_surf, title_rect)

        # Calculate menu item positions
        item_height = 60
        total_height = len(menu.items) * item_height
        start_y = (self.screen_h - total_height) // 2

        # Draw items
        for i, item in enumerate(menu.items):
            y = start_y + i * item_height
            self._draw_item(item, y, i == menu.selected_index)

        # Draw control hints
        self._draw_hints()

        pygame.display.flip()

    def _draw_item(self, item: MenuItem, y: int, selected: bool) -> None:
        """Draw a single menu item.

        Args:
            item: Menu item to draw.
            y: Y position.
            selected: Whether this item is selected.
        """
        # Determine colors
        if not item.enabled:
            text_color = self.DISABLED_COLOR
        elif selected:
            text_color = self.SELECTED_COLOR
        else:
            text_color = self.ITEM_COLOR

        # Draw selection highlight
        if selected and item.enabled:
            highlight_rect = pygame.Rect(
                self.screen_w // 4,
                y - 5,
                self.screen_w // 2,
                50,
            )
            pygame.draw.rect(self.screen, self.HIGHLIGHT_BG, highlight_rect, border_radius=8)

        # Draw label
        if item.item_type == MenuItemType.SELECTOR:
            # Label on left, value on right
            label_surf = self.item_font.render(item.label, True, text_color)
            label_rect = label_surf.get_rect(
                right=self.screen_w // 2 - 20,
                centery=y + 20,
            )
            self.screen.blit(label_surf, label_rect)

            # Draw value with arrows if selected
            value = item.get_display_value()
            if selected and item.enabled:
                value_text = f"< {value} >"
            else:
                value_text = value
            value_surf = self.item_font.render(value_text, True, self.VALUE_COLOR if item.enabled else self.DISABLED_COLOR)
            value_rect = value_surf.get_rect(
                left=self.screen_w // 2 + 20,
                centery=y + 20,
            )
            self.screen.blit(value_surf, value_rect)

            # Draw color swatches if available
            if item.swatches and item.selected_index < len(item.swatches):
                colors = item.swatches[item.selected_index]
                if colors:
                    swatch_size = 12
                    swatch_gap = 2
                    sx = value_rect.right + 12
                    sy = value_rect.centery - swatch_size // 2
                    for color in colors:
                        rect = pygame.Rect(sx, sy, swatch_size, swatch_size)
                        pygame.draw.rect(self.screen, color, rect)
                        pygame.draw.rect(self.screen, (40, 40, 45), rect, 1)
                        sx += swatch_size + swatch_gap
        else:
            # Centered label
            label_surf = self.item_font.render(item.label, True, text_color)
            label_rect = label_surf.get_rect(
                centerx=self.screen_w // 2,
                centery=y + 20,
            )
            self.screen.blit(label_surf, label_rect)

    def _draw_hints(self) -> None:
        """Draw control hints at bottom of screen."""
        hints = "D-Pad/Stick: Navigate | A: Select | LB/RB or Left/Right: Change Value | B: Back"
        hint_surf = self.hint_font.render(hints, True, (120, 120, 120))
        hint_rect = hint_surf.get_rect(
            centerx=self.screen_w // 2,
            bottom=self.screen_h - 30,
        )
        self.screen.blit(hint_surf, hint_rect)


class MenuController:
    """Handles input for menu navigation."""

    # Debounce timing
    DEBOUNCE_INITIAL_MS = 300
    DEBOUNCE_REPEAT_MS = 150

    def __init__(self) -> None:
        """Initialize menu controller."""
        self._vertical_timer = 0.0
        self._horizontal_timer = 0.0
        self._vertical_active = False
        self._horizontal_active = False

    def update(
        self,
        menu: Menu,
        dpad: tuple[int, int],
        left_stick: tuple[float, float],
        dt_ms: float,
        a_pressed: bool,
        b_pressed: bool,
        lb_pressed: bool,
        rb_pressed: bool,
    ) -> tuple[bool, bool]:
        """Update menu based on input.

        Args:
            menu: Menu to update.
            dpad: D-pad state (x, y).
            left_stick: Left stick state (x, y).
            dt_ms: Delta time in milliseconds.
            a_pressed: Whether A was just pressed.
            b_pressed: Whether B was just pressed.
            lb_pressed: Whether LB was just pressed.
            rb_pressed: Whether RB was just pressed.

        Returns:
            Tuple of (item_activated, back_pressed).
        """
        # Combine D-pad and stick for navigation
        # D-pad: hat returns (0, 1) for UP, (0, -1) for DOWN
        nav_x = dpad[0]
        nav_y = dpad[1]

        # Left stick: Y axis is inverted (negative = up, positive = down)
        if abs(left_stick[0]) > 0.5:
            nav_x = 1 if left_stick[0] > 0 else -1
        if abs(left_stick[1]) > 0.5:
            nav_y = -1 if left_stick[1] > 0 else 1

        # Vertical navigation with debounce
        if nav_y != 0:
            if not self._vertical_active:
                self._vertical_active = True
                self._vertical_timer = -self.DEBOUNCE_INITIAL_MS + self.DEBOUNCE_REPEAT_MS
                if nav_y > 0:
                    menu.move_up()
                else:
                    menu.move_down()
            else:
                self._vertical_timer += dt_ms
                if self._vertical_timer >= self.DEBOUNCE_REPEAT_MS:
                    self._vertical_timer = 0
                    if nav_y > 0:
                        menu.move_up()
                    else:
                        menu.move_down()
        else:
            self._vertical_active = False
            self._vertical_timer = 0

        # Horizontal navigation for selectors
        selected = menu.get_selected()
        if selected.item_type == MenuItemType.SELECTOR and selected.enabled:
            # LB/RB for quick change
            if lb_pressed:
                selected.cycle_prev()
            if rb_pressed:
                selected.cycle_next()

            # D-pad/stick horizontal
            if nav_x != 0:
                if not self._horizontal_active:
                    self._horizontal_active = True
                    self._horizontal_timer = -self.DEBOUNCE_INITIAL_MS + self.DEBOUNCE_REPEAT_MS
                    if nav_x > 0:
                        selected.cycle_next()
                    else:
                        selected.cycle_prev()
                else:
                    self._horizontal_timer += dt_ms
                    if self._horizontal_timer >= self.DEBOUNCE_REPEAT_MS:
                        self._horizontal_timer = 0
                        if nav_x > 0:
                            selected.cycle_next()
                        else:
                            selected.cycle_prev()
            else:
                self._horizontal_active = False
                self._horizontal_timer = 0

        # A button activates selected item
        item_activated = False
        if a_pressed and selected.enabled:
            if selected.item_type == MenuItemType.ACTION and selected.action:
                selected.action()
                item_activated = True
            elif selected.item_type == MenuItemType.SELECTOR:
                selected.cycle_next()

        return (item_activated, b_pressed)
