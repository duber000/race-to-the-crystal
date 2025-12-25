"""
Main client entry point for local hot-seat gameplay.

This module implements a fully playable local game with vector graphics.
"""

import sys
from typing import Optional, Tuple, List

from game.game_state import GameState
from game.generator import Generator
from game.crystal import Crystal
from game.movement import MovementSystem
from game.combat import CombatSystem
from shared.enums import PlayerColor, GamePhase, TurnPhase
from shared.constants import (
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
)
from client.ui.renderer import Renderer
from client.input_handler import InputHandler, InputAction


class LocalGameClient:
    """
    Main client for local hot-seat gameplay.

    Manages game state, rendering, and input handling for a local multiplayer game.
    """

    def __init__(self, num_players: int = 2):
        """
        Initialize the local game client.

        Args:
            num_players: Number of players (2-4)
        """
        # Initialize game state
        self.game_state = GameState()
        self.num_players = max(2, min(4, num_players))

        # Initialize systems
        self.movement_system = MovementSystem()
        self.combat_system = CombatSystem()

        # Initialize renderer
        self.renderer = Renderer(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)

        # Initialize input handler
        self.input_handler = InputHandler()

        # Game state
        self.running = True
        self.selected_token_id: Optional[int] = None
        self.valid_moves: List[Tuple[int, int]] = []
        self.turn_phase = TurnPhase.MOVEMENT

    def setup_game(self):
        """Set up a new game with players, tokens, generators, and crystal."""
        print("Setting up game...")

        # Create players
        player_colors = [PlayerColor.CYAN, PlayerColor.MAGENTA, PlayerColor.YELLOW, PlayerColor.GREEN]
        player_names = ["Player 1", "Player 2", "Player 3", "Player 4"]

        for i in range(self.num_players):
            player_id = f"player_{i}"
            self.game_state.add_player(player_id, player_names[i], player_colors[i])
            print(f"Added {player_names[i]} ({player_colors[i].name})")

        # Start the game (creates tokens)
        self.game_state.start_game()

        # Initialize generators
        generator_positions = self.game_state.board.get_generator_positions()
        for i, pos in enumerate(generator_positions):
            generator = Generator(id=i, position=pos)
            self.game_state.generators.append(generator)

        print(f"Created {len(self.game_state.generators)} generators")

        # Initialize crystal
        crystal_pos = self.game_state.board.get_crystal_position()
        self.game_state.crystal = Crystal(position=crystal_pos)

        print(f"Created crystal at {crystal_pos}")

        # Initialize turn phase tracking
        self.game_state.turn_phase = TurnPhase.MOVEMENT

        print("Game setup complete!")

    def run(self):
        """Run the main game loop."""
        print("Starting game...")

        while self.running:
            # Process input
            self._process_input()

            # Render game
            if self.selected_token_id is not None:
                self.renderer.render_with_selection(
                    self.game_state,
                    self.selected_token_id,
                    self.valid_moves
                )
            else:
                self.renderer.render(self.game_state)

        # Cleanup
        self.renderer.quit()
        print("Game ended.")

    def _process_input(self):
        """Process all input events."""
        actions = self.input_handler.process_events()

        for action, data in actions:
            if action == InputAction.QUIT:
                self.running = False

            elif action == InputAction.ZOOM_IN:
                self.renderer.handle_zoom(True)

            elif action == InputAction.ZOOM_OUT:
                self.renderer.handle_zoom(False)

            elif action == InputAction.PAN_UP:
                self.renderer.handle_pan(0, data)

            elif action == InputAction.PAN_DOWN:
                self.renderer.handle_pan(0, -data)

            elif action == InputAction.PAN_LEFT:
                self.renderer.handle_pan(data, 0)

            elif action == InputAction.PAN_RIGHT:
                self.renderer.handle_pan(-data, 0)

            elif action == InputAction.SELECT:
                self._handle_select(data)

            elif action == InputAction.CANCEL:
                self._handle_cancel()

            elif action == InputAction.END_TURN:
                self._handle_end_turn()

            elif action == 'pan':
                self.renderer.handle_pan(data[0], data[1])

        # Also handle HUD mouse motion
        mouse_pos = self.input_handler.get_mouse_pos()
        self.renderer.handle_mouse_motion(mouse_pos)

    def _handle_select(self, mouse_pos: Tuple[int, int]):
        """
        Handle selection (left click).

        Args:
            mouse_pos: Mouse position in screen coordinates
        """
        # Check if clicked on HUD button
        action = self.renderer.handle_mouse_click(mouse_pos)
        if action == "end_turn":
            self._handle_end_turn()
            return
        elif action == "cancel":
            self._handle_cancel()
            return

        # Get current player
        current_player = self.game_state.get_current_player()
        if not current_player:
            return

        # Check if clicked on a token
        token = self.renderer.get_token_at_mouse(mouse_pos, self.game_state)

        if token:
            # Can only select own tokens
            if token.player_id == current_player.id:
                if self.turn_phase == TurnPhase.MOVEMENT:
                    # Select token and show valid moves
                    self.selected_token_id = token.id
                    self.valid_moves = self.movement_system.get_valid_moves(
                        token,
                        self.game_state.board
                    )
                    print(f"Selected token {token.id} at {token.position}")
                elif self.turn_phase == TurnPhase.ACTION:
                    # Could implement attack selection here
                    pass
            else:
                # Clicked on enemy token - could be attack target
                if self.turn_phase == TurnPhase.ACTION and self.selected_token_id:
                    self._try_attack(token)
        else:
            # Clicked on empty cell
            cell = self.renderer.get_cell_at_mouse(mouse_pos)
            if cell and self.selected_token_id and self.turn_phase == TurnPhase.MOVEMENT:
                self._try_move_to_cell(cell)

    def _try_move_to_cell(self, cell: Tuple[int, int]):
        """
        Try to move the selected token to a cell.

        Args:
            cell: Target cell coordinates
        """
        if cell not in self.valid_moves:
            print(f"Cannot move to {cell} - not a valid move")
            return

        token = self.game_state.get_token(self.selected_token_id)
        if not token:
            return

        old_pos = token.position

        # Move the token
        success = self.game_state.move_token(self.selected_token_id, cell)

        if success:
            print(f"Moved token {self.selected_token_id} from {old_pos} to {cell}")

            # Start animation
            self.renderer.start_move_animation(self.selected_token_id, old_pos, cell, self.game_state)

            # Clear selection
            self.selected_token_id = None
            self.valid_moves = []

            # Move to action phase
            self.turn_phase = TurnPhase.ACTION

    def _try_attack(self, target_token):
        """
        Try to attack a target token.

        Args:
            target_token: Token to attack
        """
        if not self.selected_token_id:
            return

        attacker = self.game_state.get_token(self.selected_token_id)
        if not attacker:
            return

        # Check if adjacent
        if not self.combat_system.is_adjacent(attacker.position, target_token.position):
            print("Target is not adjacent")
            return

        # Perform attack
        result = self.combat_system.attack(attacker, target_token)

        print(f"Token {attacker.id} attacked token {target_token.id}: {result}")

        # Clear occupant if token was killed
        if not target_token.is_alive:
            self.game_state.board.clear_occupant(target_token.position)

        # Clear selection and move to end turn phase
        self.selected_token_id = None
        self.valid_moves = []
        self.turn_phase = TurnPhase.END_TURN

    def _handle_cancel(self):
        """Handle cancel action."""
        if self.selected_token_id:
            print("Cancelled selection")
            self.selected_token_id = None
            self.valid_moves = []

    def _handle_end_turn(self):
        """Handle end turn action."""
        current_player = self.game_state.get_current_player()
        if not current_player:
            return

        print(f"Ending turn for {current_player.name}")

        # Clear selection
        self.selected_token_id = None
        self.valid_moves = []

        # Advance to next player
        self.game_state.end_turn()

        # Reset to movement phase
        self.turn_phase = TurnPhase.MOVEMENT

        # Update game state turn phase
        self.game_state.turn_phase = TurnPhase.MOVEMENT

        next_player = self.game_state.get_current_player()
        if next_player:
            print(f"Turn {self.game_state.turn_number}: {next_player.name}'s turn")


def main():
    """Main entry point for local gameplay."""
    print("=" * 60)
    print("Race to the Crystal - Local Hot-Seat Game")
    print("=" * 60)

    # Get number of players
    if len(sys.argv) > 1:
        try:
            num_players = int(sys.argv[1])
        except ValueError:
            num_players = 2
    else:
        num_players = 2

    print(f"\nStarting {num_players}-player game...")
    print("\nControls:")
    print("  Mouse: Click to select tokens and move")
    print("  Arrow Keys / WASD: Pan camera")
    print("  +/-: Zoom in/out")
    print("  Mouse Wheel: Zoom in/out")
    print("  Right Mouse Drag: Pan camera")
    print("  Space / Enter: End turn")
    print("  Escape: Cancel selection")
    print("  Ctrl+Q: Quit game")
    print("\n" + "=" * 60 + "\n")

    # Create and run game
    client = LocalGameClient(num_players)
    client.setup_game()
    client.run()


if __name__ == "__main__":
    main()
