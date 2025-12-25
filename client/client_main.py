"""
Main client entry point for local hot-seat gameplay.

This module implements a fully playable local game with Arcade graphics.
"""

import sys
import arcade

from game.game_state import GameState
from game.generator import Generator
from game.crystal import Crystal
from shared.enums import PlayerColor
from shared.constants import (
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
)
from client.game_window import GameWindow


def setup_game_state(num_players: int = 2) -> GameState:
    """
    Set up a new game state with players, tokens, generators, and crystal.

    Args:
        num_players: Number of players (2-4)

    Returns:
        Configured game state ready to play
    """
    print("Setting up game...")

    game_state = GameState()
    num_players = max(2, min(4, num_players))

    # Create players
    player_colors = [PlayerColor.CYAN, PlayerColor.MAGENTA, PlayerColor.YELLOW, PlayerColor.GREEN]
    player_names = ["Player 1", "Player 2", "Player 3", "Player 4"]

    for i in range(num_players):
        player_id = f"player_{i}"
        game_state.add_player(player_id, player_names[i], player_colors[i])
        print(f"Added {player_names[i]} ({player_colors[i].name})")

    # Start the game (creates tokens)
    game_state.start_game()

    # Initialize generators
    generator_positions = game_state.board.get_generator_positions()
    for i, pos in enumerate(generator_positions):
        generator = Generator(id=i, position=pos)
        game_state.generators.append(generator)

    print(f"Created {len(game_state.generators)} generators")

    # Initialize crystal
    crystal_pos = game_state.board.get_crystal_position()
    game_state.crystal = Crystal(position=crystal_pos)

    print(f"Created crystal at {crystal_pos}")

    print("Game setup complete!")

    return game_state


def main():
    """Main entry point for local gameplay."""
    print("=" * 60)
    print("Race to the Crystal - Local Hot-Seat Game (Arcade)")
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
    print("  Left Click: Select tokens and move")
    print("  Arrow Keys / WASD: Pan camera")
    print("  +/-: Zoom in/out")
    print("  Mouse Wheel: Zoom in/out")
    print("  Space / Enter: End turn")
    print("  Escape: Cancel selection")
    print("  Ctrl+Q: Quit game")
    print("\n" + "=" * 60 + "\n")

    # Set up game state
    game_state = setup_game_state(num_players)

    # Create and run Arcade window
    window = GameWindow(game_state, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
    window.setup()

    # Arcade handles the game loop
    arcade.run()


if __name__ == "__main__":
    main()
