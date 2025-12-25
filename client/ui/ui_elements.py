"""HUD elements and UI components for the game."""

import pygame
from typing import Optional, List, Tuple

from game.player import Player
from game.game_state import GameState
from shared.enums import TurnPhase, GamePhase
from shared.constants import (
    PLAYER_COLORS,
    BACKGROUND_COLOR,
)
from client.ui.vector_graphics import (
    draw_glow_rect,
    draw_text_with_glow,
    COLORS,
)


class Button:
    """A clickable button UI element."""

    def __init__(self, rect: pygame.Rect, text: str, color: Tuple[int, int, int]):
        """
        Initialize a button.

        Args:
            rect: Rectangle defining button position and size
            text: Button text
            color: Button color
        """
        self.rect = rect
        self.text = text
        self.color = color
        self.hover = False
        self.enabled = True

        pygame.font.init()
        self.font = pygame.font.Font(None, 24)

    def render(self, surface: pygame.Surface):
        """
        Render the button.

        Args:
            surface: Surface to draw on
        """
        if not self.enabled:
            color = COLORS['gray']
        elif self.hover:
            color = COLORS['white']
        else:
            color = self.color

        # Draw button background
        draw_glow_rect(surface, color, self.rect, width=2, glow_size=2 if self.hover else 1)

        # Draw text
        text_surface = self.font.render(self.text, True, color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def handle_mouse_motion(self, pos: Tuple[int, int]):
        """
        Handle mouse motion to update hover state.

        Args:
            pos: Mouse position
        """
        self.hover = self.rect.collidepoint(pos)

    def handle_click(self, pos: Tuple[int, int]) -> bool:
        """
        Handle mouse click.

        Args:
            pos: Mouse position

        Returns:
            True if button was clicked, False otherwise
        """
        if self.enabled and self.rect.collidepoint(pos):
            return True
        return False


class PlayerInfoPanel:
    """Panel showing information about players."""

    def __init__(self, x: int, y: int, width: int):
        """
        Initialize the player info panel.

        Args:
            x: X position of panel
            y: Y position of panel
            width: Width of panel
        """
        self.x = x
        self.y = y
        self.width = width
        self.height_per_player = 60

        pygame.font.init()
        self.name_font = pygame.font.Font(None, 24)
        self.info_font = pygame.font.Font(None, 18)

    def render(self, surface: pygame.Surface, players: List[Player], current_player_id: str, tokens_alive: dict):
        """
        Render the player info panel.

        Args:
            surface: Surface to draw on
            players: List of players
            current_player_id: ID of the current player
            tokens_alive: Dictionary mapping player_id to alive token count
        """
        for i, player in enumerate(players):
            if not player.is_active:
                continue

            y_offset = self.y + i * self.height_per_player
            player_index = i
            color = PLAYER_COLORS[player_index % len(PLAYER_COLORS)]

            # Draw panel background
            panel_rect = pygame.Rect(self.x, y_offset, self.width, self.height_per_player - 5)

            # Highlight current player
            if player.id == current_player_id:
                draw_glow_rect(surface, color, panel_rect, width=3, glow_size=3)
            else:
                pygame.draw.rect(surface, color, panel_rect, 1)

            # Draw player name
            name_surface = self.name_font.render(player.name, True, color)
            surface.blit(name_surface, (self.x + 10, y_offset + 10))

            # Draw token count
            alive_count = tokens_alive.get(player.id, 0)
            info_text = f"Tokens: {alive_count}"
            info_surface = self.info_font.render(info_text, True, COLORS['white'])
            surface.blit(info_surface, (self.x + 10, y_offset + 35))


class TurnIndicator:
    """Indicator showing current turn phase and player."""

    def __init__(self, x: int, y: int, width: int):
        """
        Initialize the turn indicator.

        Args:
            x: X position
            y: Y position
            width: Width of indicator
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = 80

        pygame.font.init()
        self.title_font = pygame.font.Font(None, 32)
        self.info_font = pygame.font.Font(None, 24)

    def render(self, surface: pygame.Surface, current_player: Optional[Player], turn_phase: TurnPhase, players: List[Player]):
        """
        Render the turn indicator.

        Args:
            surface: Surface to draw on
            current_player: Current player whose turn it is
            turn_phase: Current turn phase
            players: List of all players
        """
        if not current_player:
            return

        # Get player color
        player_index = next((i for i, p in enumerate(players) if p.id == current_player.id), 0)
        color = PLAYER_COLORS[player_index % len(PLAYER_COLORS)]

        # Draw background
        bg_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        draw_glow_rect(surface, color, bg_rect, width=2, glow_size=2)

        # Draw current player name
        player_text = f"{current_player.name}'s Turn"
        player_surface = self.title_font.render(player_text, True, color)
        player_rect = player_surface.get_rect(center=(self.x + self.width // 2, self.y + 25))
        surface.blit(player_surface, player_rect)

        # Draw turn phase
        phase_text = self._get_phase_text(turn_phase)
        phase_surface = self.info_font.render(phase_text, True, COLORS['white'])
        phase_rect = phase_surface.get_rect(center=(self.x + self.width // 2, self.y + 55))
        surface.blit(phase_surface, phase_rect)

    def _get_phase_text(self, turn_phase: TurnPhase) -> str:
        """
        Get display text for turn phase.

        Args:
            turn_phase: Current turn phase

        Returns:
            Display text
        """
        phase_map = {
            TurnPhase.MOVEMENT: "Movement Phase",
            TurnPhase.ACTION: "Action Phase",
            TurnPhase.END_TURN: "Ending Turn...",
        }
        return phase_map.get(turn_phase, "Unknown Phase")


class GeneratorStatus:
    """Shows status of generators on the map."""

    def __init__(self, x: int, y: int, width: int):
        """
        Initialize the generator status display.

        Args:
            x: X position
            y: Y position
            width: Width of display
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = 100

        pygame.font.init()
        self.title_font = pygame.font.Font(None, 24)
        self.info_font = pygame.font.Font(None, 18)

    def render(self, surface: pygame.Surface, game_state):
        """
        Render the generator status.

        Args:
            surface: Surface to draw on
            game_state: Current game state
        """
        # Draw background
        bg_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, COLORS['dark_gray'], bg_rect, 1)

        # Draw title
        title_surface = self.title_font.render("Generators", True, COLORS['white'])
        surface.blit(title_surface, (self.x + 10, self.y + 10))

        # Draw generator info
        disabled_count = len([g for g in game_state.generators if g.is_disabled])
        total_count = len(game_state.generators)

        info_text = f"Disabled: {disabled_count}/{total_count}"
        info_surface = self.info_font.render(info_text, True, COLORS['white'])
        surface.blit(info_surface, (self.x + 10, self.y + 40))

        # Show crystal requirement
        crystal_req = game_state.crystal.tokens_required
        req_text = f"Crystal Req: {crystal_req} tokens"
        req_surface = self.info_font.render(req_text, True, COLORS['white'])
        surface.blit(req_surface, (self.x + 10, self.y + 65))


class HUD:
    """Main HUD containing all UI elements."""

    def __init__(self, screen_width: int, screen_height: int):
        """
        Initialize the HUD.

        Args:
            screen_width: Width of the game window
            screen_height: Height of the game window
        """
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Create UI elements
        panel_width = 250

        # Right side panel
        self.player_panel = PlayerInfoPanel(screen_width - panel_width - 10, 10, panel_width)
        self.generator_status = GeneratorStatus(screen_width - panel_width - 10, 300, panel_width)

        # Top center
        self.turn_indicator = TurnIndicator(screen_width // 2 - 150, 10, 300)

        # Buttons (bottom center)
        button_y = screen_height - 60
        button_width = 120
        button_spacing = 10

        self.end_turn_button = Button(
            pygame.Rect(screen_width // 2 - button_width - button_spacing // 2, button_y, button_width, 40),
            "End Turn",
            COLORS['green']
        )

        self.cancel_button = Button(
            pygame.Rect(screen_width // 2 + button_spacing // 2, button_y, button_width, 40),
            "Cancel",
            COLORS['magenta']
        )

    def render(self, surface: pygame.Surface, game_state: GameState):
        """
        Render the entire HUD.

        Args:
            surface: Surface to draw on
            game_state: Current game state
        """
        if game_state.game_phase != GamePhase.PLAYING:
            return

        # Count alive tokens per player
        tokens_alive = {}
        for player in game_state.players.values():
            alive_count = sum(1 for token in game_state.tokens.values() if token.player_id == player.id and token.is_alive)
            tokens_alive[player.id] = alive_count

        # Render components
        current_player = game_state.get_current_player()
        players_list = list(game_state.players.values())

        self.player_panel.render(surface, players_list, game_state.current_player_id or game_state.current_turn_player_id, tokens_alive)
        self.turn_indicator.render(surface, current_player, game_state.turn_phase, players_list)
        self.generator_status.render(surface, game_state)
        self.end_turn_button.render(surface)
        self.cancel_button.render(surface)

    def handle_mouse_motion(self, pos: Tuple[int, int]):
        """
        Handle mouse motion events.

        Args:
            pos: Mouse position
        """
        self.end_turn_button.handle_mouse_motion(pos)
        self.cancel_button.handle_mouse_motion(pos)

    def handle_mouse_click(self, pos: Tuple[int, int]) -> Optional[str]:
        """
        Handle mouse click events.

        Args:
            pos: Mouse position

        Returns:
            Action string if a button was clicked, None otherwise
        """
        if self.end_turn_button.handle_click(pos):
            return "end_turn"
        elif self.cancel_button.handle_click(pos):
            return "cancel"

        return None
