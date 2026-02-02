"""Gamepad input handling for BusyBrainPaint."""

import pygame


# Button mappings (Xbox-style)
BUTTON_A = 0
BUTTON_B = 1
BUTTON_X = 2
BUTTON_Y = 3
BUTTON_LB = 4
BUTTON_RB = 5
BUTTON_BACK = 6
BUTTON_START = 7
BUTTON_L3 = 8
BUTTON_R3 = 9

# Axis mappings
AXIS_LEFT_X = 0
AXIS_LEFT_Y = 1
AXIS_RIGHT_X = 2
AXIS_RIGHT_Y = 3
AXIS_LT = 4
AXIS_RT = 5

# Hat (D-pad) mappings
HAT_INDEX = 0


class InputState:
    """Current state of gamepad inputs."""

    def __init__(self) -> None:
        """Initialize input state."""
        # Sticks (normalized -1 to 1)
        self.left_stick: tuple[float, float] = (0.0, 0.0)
        self.right_stick: tuple[float, float] = (0.0, 0.0)

        # Triggers (0 to 1)
        self.lt: float = 0.0
        self.rt: float = 0.0

        # D-pad (raw hat values)
        self.dpad: tuple[int, int] = (0, 0)

        # Buttons (current frame)
        self.buttons: dict[int, bool] = {}

        # Button events (just pressed this frame)
        self.buttons_pressed: set[int] = set()
        self.buttons_released: set[int] = set()

        # D-pad events (just pressed this frame)
        self.dpad_pressed: tuple[int, int] | None = None


class InputHandler:
    """Handles gamepad input with deadzone and event detection."""

    def __init__(self, stick_deadzone: float = 0.2, trigger_deadzone: float = 0.1) -> None:
        """Initialize input handler.

        Args:
            stick_deadzone: Deadzone for analog sticks.
            trigger_deadzone: Deadzone for triggers.
        """
        self.stick_deadzone = stick_deadzone
        self.trigger_deadzone = trigger_deadzone

        self.joystick: pygame.joystick.JoystickType | None = None
        self.state = InputState()
        self._prev_buttons: dict[int, bool] = {}
        self._prev_dpad: tuple[int, int] = (0, 0)

        self._init_joystick()

    def _init_joystick(self) -> None:
        """Initialize the first available joystick."""
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"Gamepad connected: {self.joystick.get_name()}")
        else:
            print("No gamepad detected")

    def _apply_deadzone(self, value: float, deadzone: float) -> float:
        """Apply deadzone to an axis value.

        Args:
            value: Raw axis value (-1 to 1).
            deadzone: Deadzone threshold.

        Returns:
            Processed value with deadzone applied.
        """
        if abs(value) < deadzone:
            return 0.0
        # Remap to full range outside deadzone
        sign = 1.0 if value > 0 else -1.0
        return sign * (abs(value) - deadzone) / (1.0 - deadzone)

    def _apply_stick_deadzone(self, x: float, y: float) -> tuple[float, float]:
        """Apply circular deadzone to stick input.

        Args:
            x: Raw X axis value.
            y: Raw Y axis value.

        Returns:
            Processed (x, y) with circular deadzone applied.
        """
        magnitude = (x * x + y * y) ** 0.5
        if magnitude < self.stick_deadzone:
            return (0.0, 0.0)

        # Normalize and remap
        scale = (magnitude - self.stick_deadzone) / (1.0 - self.stick_deadzone)
        scale = min(scale, 1.0)  # Clamp to 1.0
        return (x / magnitude * scale, y / magnitude * scale)

    def update(self) -> None:
        """Update input state. Call once per frame."""
        self.state.buttons_pressed.clear()
        self.state.buttons_released.clear()
        self.state.dpad_pressed = None

        if self.joystick is None:
            # Try to reconnect
            pygame.joystick.quit()
            self._init_joystick()
            if self.joystick is None:
                return

        # Read sticks
        try:
            raw_lx = self.joystick.get_axis(AXIS_LEFT_X)
            raw_ly = self.joystick.get_axis(AXIS_LEFT_Y)
            self.state.left_stick = self._apply_stick_deadzone(raw_lx, raw_ly)

            raw_rx = self.joystick.get_axis(AXIS_RIGHT_X)
            raw_ry = self.joystick.get_axis(AXIS_RIGHT_Y)
            self.state.right_stick = self._apply_stick_deadzone(raw_rx, raw_ry)

            # Read triggers (some controllers report -1 to 1, normalize to 0 to 1)
            raw_lt = self.joystick.get_axis(AXIS_LT)
            raw_rt = self.joystick.get_axis(AXIS_RT)
            self.state.lt = max(0.0, self._apply_deadzone((raw_lt + 1) / 2, self.trigger_deadzone))
            self.state.rt = max(0.0, self._apply_deadzone((raw_rt + 1) / 2, self.trigger_deadzone))

            # Read D-pad
            if self.joystick.get_numhats() > 0:
                self.state.dpad = self.joystick.get_hat(HAT_INDEX)

                # Detect D-pad press event
                if self.state.dpad != (0, 0) and self._prev_dpad == (0, 0):
                    self.state.dpad_pressed = self.state.dpad
                self._prev_dpad = self.state.dpad

            # Read buttons
            for btn in range(self.joystick.get_numbuttons()):
                pressed = self.joystick.get_button(btn)
                self.state.buttons[btn] = pressed

                was_pressed = self._prev_buttons.get(btn, False)
                if pressed and not was_pressed:
                    self.state.buttons_pressed.add(btn)
                elif not pressed and was_pressed:
                    self.state.buttons_released.add(btn)

                self._prev_buttons[btn] = pressed

        except pygame.error:
            # Controller disconnected
            self.joystick = None
            print("Gamepad disconnected")

    def is_button_pressed(self, button: int) -> bool:
        """Check if button was just pressed this frame.

        Args:
            button: Button index to check.

        Returns:
            True if button was just pressed.
        """
        return button in self.state.buttons_pressed

    def is_button_held(self, button: int) -> bool:
        """Check if button is currently held.

        Args:
            button: Button index to check.

        Returns:
            True if button is held.
        """
        return self.state.buttons.get(button, False)

    def is_button_released(self, button: int) -> bool:
        """Check if button was just released this frame.

        Args:
            button: Button index to check.

        Returns:
            True if button was just released.
        """
        return button in self.state.buttons_released
