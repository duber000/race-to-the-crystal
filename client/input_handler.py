"""Input handling for keyboard and mouse events."""

import pygame
from typing import Optional, Tuple, Callable
from enum import Enum, auto


class InputAction(Enum):
    """Enumeration of input actions."""
    # Camera controls
    ZOOM_IN = auto()
    ZOOM_OUT = auto()
    PAN_UP = auto()
    PAN_DOWN = auto()
    PAN_LEFT = auto()
    PAN_RIGHT = auto()

    # Game actions
    SELECT = auto()
    CANCEL = auto()
    END_TURN = auto()

    # System
    QUIT = auto()


class InputHandler:
    """
    Handles keyboard and mouse input for the game.

    Processes events and translates them into game actions.
    """

    def __init__(self):
        """Initialize the input handler."""
        # Mouse state
        self.mouse_pos = (0, 0)
        self.mouse_down = False
        self.mouse_drag_start: Optional[Tuple[int, int]] = None

        # Keyboard state
        self.keys_pressed = set()

        # Pan speed for keyboard panning
        self.pan_speed = 5.0

    def process_events(self) -> list:
        """
        Process all pending input events.

        Returns:
            List of (InputAction, data) tuples
        """
        actions = []

        for event in pygame.event.get():
            # Quit event
            if event.type == pygame.QUIT:
                actions.append((InputAction.QUIT, None))

            # Keyboard events
            elif event.type == pygame.KEYDOWN:
                actions.extend(self._handle_keydown(event))

            elif event.type == pygame.KEYUP:
                self._handle_keyup(event)

            # Mouse events
            elif event.type == pygame.MOUSEMOTION:
                actions.extend(self._handle_mouse_motion(event))

            elif event.type == pygame.MOUSEBUTTONDOWN:
                actions.extend(self._handle_mouse_button_down(event))

            elif event.type == pygame.MOUSEBUTTONUP:
                actions.extend(self._handle_mouse_button_up(event))

        # Handle continuous keyboard input (held keys)
        actions.extend(self._handle_continuous_input())

        return actions

    def _handle_keydown(self, event) -> list:
        """
        Handle key press events.

        Args:
            event: Pygame key event

        Returns:
            List of actions
        """
        actions = []
        self.keys_pressed.add(event.key)

        # Zoom controls
        if event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
            actions.append((InputAction.ZOOM_IN, None))
        elif event.key == pygame.K_MINUS:
            actions.append((InputAction.ZOOM_OUT, None))

        # Cancel/Escape
        elif event.key == pygame.K_ESCAPE:
            actions.append((InputAction.CANCEL, None))

        # End turn
        elif event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
            actions.append((InputAction.END_TURN, None))

        # Quit
        elif event.key == pygame.K_q and pygame.key.get_mods() & pygame.KMOD_CTRL:
            actions.append((InputAction.QUIT, None))

        return actions

    def _handle_keyup(self, event):
        """
        Handle key release events.

        Args:
            event: Pygame key event
        """
        if event.key in self.keys_pressed:
            self.keys_pressed.remove(event.key)

    def _handle_continuous_input(self) -> list:
        """
        Handle continuous keyboard input (held keys).

        Returns:
            List of actions
        """
        actions = []

        # Arrow key panning
        if pygame.K_UP in self.keys_pressed or pygame.K_w in self.keys_pressed:
            actions.append((InputAction.PAN_UP, self.pan_speed))
        if pygame.K_DOWN in self.keys_pressed or pygame.K_s in self.keys_pressed:
            actions.append((InputAction.PAN_DOWN, self.pan_speed))
        if pygame.K_LEFT in self.keys_pressed or pygame.K_a in self.keys_pressed:
            actions.append((InputAction.PAN_LEFT, self.pan_speed))
        if pygame.K_RIGHT in self.keys_pressed or pygame.K_d in self.keys_pressed:
            actions.append((InputAction.PAN_RIGHT, self.pan_speed))

        return actions

    def _handle_mouse_motion(self, event) -> list:
        """
        Handle mouse motion events.

        Args:
            event: Pygame mouse motion event

        Returns:
            List of actions
        """
        actions = []
        self.mouse_pos = event.pos

        # Handle dragging for panning
        if self.mouse_down and self.mouse_drag_start and event.buttons[2]:  # Right mouse button
            dx = event.pos[0] - self.mouse_drag_start[0]
            dy = event.pos[1] - self.mouse_drag_start[1]
            self.mouse_drag_start = event.pos

            # Return pan action with delta
            actions.append(('pan', (dx, dy)))

        return actions

    def _handle_mouse_button_down(self, event) -> list:
        """
        Handle mouse button press events.

        Args:
            event: Pygame mouse button event

        Returns:
            List of actions
        """
        actions = []
        self.mouse_down = True

        # Left click - select
        if event.button == 1:
            actions.append((InputAction.SELECT, event.pos))

        # Right click - start drag for panning
        elif event.button == 3:
            self.mouse_drag_start = event.pos

        # Mouse wheel - zoom
        elif event.button == 4:  # Scroll up
            actions.append((InputAction.ZOOM_IN, None))
        elif event.button == 5:  # Scroll down
            actions.append((InputAction.ZOOM_OUT, None))

        return actions

    def _handle_mouse_button_up(self, event) -> list:
        """
        Handle mouse button release events.

        Args:
            event: Pygame mouse button event

        Returns:
            List of actions
        """
        actions = []

        if event.button == 3:  # Right click
            self.mouse_drag_start = None

        self.mouse_down = False

        return actions

    def get_mouse_pos(self) -> Tuple[int, int]:
        """
        Get the current mouse position.

        Returns:
            (x, y) mouse position
        """
        return self.mouse_pos


class InputMapper:
    """
    Maps input actions to game actions using callbacks.

    This allows the game logic to register handlers for specific input actions.
    """

    def __init__(self):
        """Initialize the input mapper."""
        self.handlers = {}

    def register_handler(self, action: InputAction, handler: Callable):
        """
        Register a handler for an input action.

        Args:
            action: Input action to handle
            handler: Callback function to execute
        """
        self.handlers[action] = handler

    def handle_action(self, action: InputAction, data=None):
        """
        Handle an input action by calling its registered handler.

        Args:
            action: Input action
            data: Optional data associated with the action
        """
        if action in self.handlers:
            self.handlers[action](data)

    def handle_actions(self, actions: list):
        """
        Handle multiple input actions.

        Args:
            actions: List of (InputAction, data) tuples
        """
        for action, data in actions:
            # Handle special string actions (like 'pan')
            if isinstance(action, str):
                if action == 'pan' and 'pan' in self.handlers:
                    self.handlers['pan'](data)
            else:
                self.handle_action(action, data)
