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
from client.game_window import GameView


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
    player_colors = [
        PlayerColor.CYAN,
        PlayerColor.MAGENTA,
        PlayerColor.YELLOW,
        PlayerColor.GREEN,
    ]
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

    # Parse command-line arguments
    num_players = 4
    start_in_3d = False
    
    for arg in sys.argv[1:]:
        if arg == "--3d" or arg == "-3d":
            start_in_3d = True
        else:
            try:
                num_players = int(arg)
            except ValueError:
                print(f"Warning: Unknown argument '{arg}', ignoring")

    print(f"\nStarting {num_players}-player game...")
    if start_in_3d:
        print("(Starting in 3D mode)")
    print("\nControls:")
    print("  Left Click: Select token, then move OR attack (not both)")
    print("  Space / Enter: End turn")
    print("  Escape: Cancel selection")
    print("  V: Toggle 2D/3D view")
    print("  M: Toggle music on/off")
    print("  Arrow Keys / WASD: Pan camera")
    print("  +/-: Zoom in/out")
    print("  Mouse Wheel: Zoom in/out")
    print("  Ctrl+Q: Quit game")
    print("\n3D Mode Controls (press V to toggle):")
    print("  Right Mouse Button + Move: Mouse-look (free camera rotation)")
    print("  Q/E: Rotate camera left/right")
    print("  TAB: Cycle through your tokens")
    print("  (Arrow Keys/WASD pan camera in 3D mode too)")
    print("\nRules:")
    print("  - Fast tokens (4hp, 6hp): Move 2 spaces")
    print("  - Slow tokens (8hp, 10hp): Move 1 space")
    print("  - Each turn: Either move OR attack, but not both")
    print("\n" + "=" * 60 + "\n")

    # Set up game state
    game_state = setup_game_state(num_players)

    # Create Arcade window
    window = arcade.Window(
        DEFAULT_WINDOW_WIDTH,
        DEFAULT_WINDOW_HEIGHT,
        "Race to the Crystal - Local Hot-Seat Game",
        resizable=True
    )

    # Create and show game view
    game_view = GameView(game_state, start_in_3d=start_in_3d)
    window.show_view(game_view)

    # Arcade handles the game loop
    arcade.run()


if __name__ == "__main__":
    main()
