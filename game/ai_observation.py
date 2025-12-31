"""
AI Observation Module - Convert game state to text descriptions for AI players.

This module provides functions to make the game state observable to AI players
(like Claude) without requiring visual rendering. All functions produce
human-readable text descriptions of the game state.
"""
from typing import Dict, List, Tuple, Optional
from game.game_state import GameState
from game.token import Token
from game.movement import MovementSystem
from game.combat import CombatSystem
from shared.enums import GamePhase, TurnPhase, PlayerColor, CellType
from shared.constants import (
    BOARD_WIDTH,
    BOARD_HEIGHT,
    CRYSTAL_BASE_TOKENS_REQUIRED,
    GENERATOR_TOKEN_REDUCTION,
)


class AIObserver:
    """Provides text-based observations of game state for AI players."""

    # Color name mappings for readable output
    COLOR_NAMES = {
        PlayerColor.CYAN: "Cyan",
        PlayerColor.MAGENTA: "Magenta",
        PlayerColor.YELLOW: "Yellow",
        PlayerColor.GREEN: "Green",
    }

    # Symbol mappings for board visualization
    SYMBOL_EMPTY = "."
    SYMBOL_GENERATOR = "G"
    SYMBOL_CRYSTAL = "C"
    SYMBOL_MYSTERY = "M"
    SYMBOL_CORNER = "*"

    @staticmethod
    def _get_generator_status(generator, game_state: GameState) -> str:
        """Get human-readable status string for a generator."""
        if generator.is_disabled:
            return "DISABLED"
        elif generator.capturing_player_id:
            player = game_state.get_player(generator.capturing_player_id)
            if player:
                color_name = AIObserver.COLOR_NAMES.get(player.color, "Unknown")
                token_count = len(generator.capture_token_ids)
                turns_held, turns_required = generator.get_capture_progress()
                return (
                    f"Being captured by {player.name} ({color_name}) - "
                    f"{token_count} tokens, {turns_held}/{turns_required} turns"
                )
        return "Uncontested"

    @staticmethod
    def _get_crystal_holders(crystal, game_state: GameState) -> Dict[str, int]:
        """Get dictionary mapping player_id to number of tokens on crystal."""
        # Count tokens at crystal position
        tokens_at_crystal = game_state.get_tokens_at_position(crystal.position)
        player_counts = {}
        for token in tokens_at_crystal:
            if token.player_id not in player_counts:
                player_counts[token.player_id] = 0
            player_counts[token.player_id] += 1
        return player_counts

    @staticmethod
    def _get_deployable_positions(board, player_index: int) -> List[Tuple[int, int]]:
        """Get valid deployment positions for a player (corner and adjacent cells)."""
        corner = board.get_starting_position(player_index)
        cx, cy = corner

        # Include corner and all 8 adjacent cells
        positions = [corner]
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue  # Skip corner itself (already added)
                x, y = cx + dx, cy + dy
                if 0 <= x < board.width and 0 <= y < board.height:
                    positions.append((x, y))

        return positions

    @staticmethod
    def describe_game_state(
        game_state: GameState, perspective_player_id: str
    ) -> str:
        """
        Generate comprehensive text description of current game state.

        Args:
            game_state: Current game state
            perspective_player_id: Player ID to generate description for

        Returns:
            Formatted multi-line string describing the complete game state
        """
        lines = []
        lines.append("=" * 60)

        # Game header
        if game_state.phase == GamePhase.ENDED:
            winner = game_state.get_player(game_state.winner_id)
            winner_name = winner.name if winner else "Unknown"
            lines.append(f"GAME OVER - Winner: {winner_name}")
        elif game_state.phase == GamePhase.SETUP:
            lines.append("GAME SETUP - Waiting for players")
        else:
            current_player = game_state.get_current_player()
            is_your_turn = game_state.current_turn_player_id == perspective_player_id

            turn_indicator = "YOUR TURN" if is_your_turn else "WAITING"
            player_name = current_player.name if current_player else "Unknown"
            player_color = AIObserver.COLOR_NAMES.get(
                current_player.color, "Unknown"
            ) if current_player else "Unknown"

            lines.append(
                f"TURN {game_state.turn_number} - {turn_indicator} "
                f"(Current: {player_name} - {player_color})"
            )

        lines.append("=" * 60)
        lines.append("")

        # Turn phase information
        if game_state.phase == GamePhase.PLAYING:
            phase_name = game_state.turn_phase.name
            lines.append(f"Phase: {phase_name}")
            if game_state.turn_phase == TurnPhase.MOVEMENT:
                lines.append("  → You can move a token or deploy a new token")
            elif game_state.turn_phase == TurnPhase.ACTION:
                lines.append("  → You can attack with a token or end your turn")
            lines.append("")

        # Your tokens
        player = game_state.get_player(perspective_player_id)
        if player:
            deployed_tokens = [
                game_state.tokens[tid]
                for tid in player.token_ids
                if tid in game_state.tokens and game_state.tokens[tid].is_deployed
            ]
            reserve_tokens = game_state.get_reserve_tokens(perspective_player_id)
            reserve_counts = game_state.get_reserve_token_counts(perspective_player_id)

            lines.append(
                f"YOUR TOKENS ({len(deployed_tokens)} deployed, "
                f"{len(reserve_tokens)} in reserve):"
            )
            if deployed_tokens:
                for token in sorted(deployed_tokens, key=lambda t: t.id):
                    x, y = token.position
                    lines.append(
                        f"  Token #{token.id:2d} @ ({x:2d},{y:2d}) - "
                        f"{token.health}/{token.max_health}hp  "
                        f"[Move range: {token.movement_range}]"
                    )
            else:
                lines.append("  (none deployed)")

            lines.append("")
            lines.append("RESERVE TOKENS:")
            lines.append(
                f"  10hp: {reserve_counts[10]}  |  8hp: {reserve_counts[8]}  |  "
                f"6hp: {reserve_counts[6]}  |  4hp: {reserve_counts[4]}"
            )
            lines.append("")

        # Enemy tokens
        enemy_players = [
            p for pid, p in game_state.players.items()
            if pid != perspective_player_id
        ]
        if enemy_players:
            lines.append("ENEMY TOKENS:")
            for enemy in enemy_players:
                enemy_tokens = [
                    game_state.tokens[tid]
                    for tid in enemy.token_ids
                    if tid in game_state.tokens and game_state.tokens[tid].is_deployed
                ]
                color_name = AIObserver.COLOR_NAMES.get(enemy.color, "Unknown")
                lines.append(
                    f"  {enemy.name} ({color_name}): {len(enemy_tokens)} deployed"
                )
                for token in sorted(enemy_tokens, key=lambda t: t.id):
                    x, y = token.position
                    lines.append(
                        f"    Token #{token.id:2d} @ ({x:2d},{y:2d}) - "
                        f"{token.health}/{token.max_health}hp"
                    )
            lines.append("")

        # Generators
        if game_state.generators:
            lines.append("GENERATORS:")
            for i, gen in enumerate(game_state.generators, 1):
                status = AIObserver._get_generator_status(gen, game_state)
                lines.append(f"  G{i} @ ({gen.position[0]},{gen.position[1]}): {status}")
            lines.append("")

        # Crystal
        if game_state.crystal:
            crystal = game_state.crystal
            cx, cy = crystal.position
            disabled_gens = sum(1 for g in game_state.generators if g.is_disabled)
            tokens_required = max(
                1,
                CRYSTAL_BASE_TOKENS_REQUIRED - (disabled_gens * GENERATOR_TOKEN_REDUCTION)
            )

            lines.append("CRYSTAL:")
            lines.append(f"  Location: ({cx},{cy})")
            lines.append(f"  Tokens needed to capture: {tokens_required}")
            if disabled_gens > 0:
                lines.append(
                    f"  (Base: {CRYSTAL_BASE_TOKENS_REQUIRED}, "
                    f"reduced by {disabled_gens} disabled generator(s))"
                )

            # Show who has tokens on crystal
            crystal_holders = AIObserver._get_crystal_holders(crystal, game_state)
            if crystal_holders:
                lines.append("  Current holders:")
                for pid, count in crystal_holders.items():
                    p = game_state.get_player(pid)
                    if p:
                        color_name = AIObserver.COLOR_NAMES.get(p.color, "Unknown")
                        lines.append(f"    {p.name} ({color_name}): {count} tokens")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    @staticmethod
    def get_board_map(
        game_state: GameState, perspective_player_id: str
    ) -> str:
        """
        Generate ASCII art map of the board.

        Args:
            game_state: Current game state
            perspective_player_id: Player ID viewing the board

        Returns:
            Multi-line string showing ASCII representation of the board
        """
        lines = []
        lines.append("BOARD MAP (24x24):")
        lines.append("")

        # Create empty board grid
        board_grid = [[AIObserver.SYMBOL_EMPTY for _ in range(BOARD_WIDTH)]
                      for _ in range(BOARD_HEIGHT)]

        # Mark special cells
        # Generators
        if game_state.generators:
            for i, gen in enumerate(game_state.generators):
                x, y = gen.position
                board_grid[y][x] = f"{i+1}"  # G1, G2, G3, G4 shown as 1,2,3,4

        # Crystal
        if game_state.crystal:
            cx, cy = game_state.crystal.position
            board_grid[cy][cx] = AIObserver.SYMBOL_CRYSTAL

        # Mystery squares
        mystery_positions = game_state.board.get_mystery_positions()
        for mx, my in mystery_positions:
            if board_grid[my][mx] == AIObserver.SYMBOL_EMPTY:
                board_grid[my][mx] = AIObserver.SYMBOL_MYSTERY

        # Deployment corners (starting positions)
        for i in range(4):
            corner_x, corner_y = game_state.board.get_starting_position(i)
            if board_grid[corner_y][corner_x] == AIObserver.SYMBOL_EMPTY:
                board_grid[corner_y][corner_x] = AIObserver.SYMBOL_CORNER

        # Place tokens (tokens override other symbols)
        for token in game_state.tokens.values():
            if token.is_deployed:
                x, y = token.position
                player = game_state.get_player(token.player_id)
                if player:
                    # Use color-coded letters: C=Cyan, M=Magenta, Y=Yellow, G=Green
                    if player.color == PlayerColor.CYAN:
                        symbol = "c"
                    elif player.color == PlayerColor.MAGENTA:
                        symbol = "m"
                    elif player.color == PlayerColor.YELLOW:
                        symbol = "y"
                    elif player.color == PlayerColor.GREEN:
                        symbol = "g"
                    else:
                        symbol = "?"

                    # Uppercase for your tokens, lowercase for enemies
                    if token.player_id == perspective_player_id:
                        symbol = symbol.upper()

                    board_grid[y][x] = symbol

        # Print header with column numbers
        lines.append("     " + "".join(f"{i:2d}" for i in range(0, BOARD_WIDTH, 2)))
        lines.append("   +" + "-" * (BOARD_WIDTH * 2) + "+")

        # Print each row
        for y in range(BOARD_HEIGHT):
            row_str = f"{y:2d} | " + " ".join(board_grid[y]) + " |"
            lines.append(row_str)

        lines.append("   +" + "-" * (BOARD_WIDTH * 2) + "+")
        lines.append("")

        # Legend
        lines.append("LEGEND:")
        player = game_state.get_player(perspective_player_id)
        if player:
            your_symbol = {
                PlayerColor.CYAN: "C",
                PlayerColor.MAGENTA: "M",
                PlayerColor.YELLOW: "Y",
                PlayerColor.GREEN: "G",
            }.get(player.color, "?")
            lines.append(f"  {your_symbol} = Your tokens")
        lines.append("  c/m/y/g = Enemy tokens (cyan/magenta/yellow/green)")
        lines.append("  C = Crystal")
        lines.append("  1,2,3,4 = Generators (G1-G4)")
        lines.append("  M = Mystery square")
        lines.append("  * = Deployment corner")
        lines.append("  . = Empty cell")
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def list_available_actions(
        game_state: GameState, player_id: str
    ) -> Dict:
        """
        Return structured dictionary of all valid actions for current turn phase.

        Args:
            game_state: Current game state
            player_id: Player ID to get actions for

        Returns:
            Dictionary with 'phase' and 'actions' list
        """
        if game_state.phase != GamePhase.PLAYING:
            return {"phase": "NOT_PLAYING", "actions": []}

        if game_state.current_turn_player_id != player_id:
            return {"phase": "NOT_YOUR_TURN", "actions": []}

        actions = []
        phase = game_state.turn_phase.name

        player = game_state.get_player(player_id)
        if not player:
            return {"phase": phase, "actions": []}

        # Get player's deployed tokens
        deployed_tokens = [
            game_state.tokens[tid]
            for tid in player.token_ids
            if tid in game_state.tokens and game_state.tokens[tid].is_deployed
        ]

        if game_state.turn_phase == TurnPhase.MOVEMENT:
            # Movement actions
            for token in deployed_tokens:
                valid_moves = MovementSystem.get_valid_moves(token, game_state.board, tokens_dict=game_state.tokens)
                if valid_moves:
                    actions.append({
                        "type": "MOVE",
                        "token_id": token.id,
                        "token_position": list(token.position),
                        "token_health": f"{token.health}/{token.max_health}",
                        "valid_destinations": [list(pos) for pos in valid_moves],
                        "description": (
                            f"Move token #{token.id} ({token.max_health}hp) "
                            f"from ({token.position[0]},{token.position[1]})"
                        ),
                    })

            # Deployment actions
            reserve_counts = game_state.get_reserve_token_counts(player_id)
            corner_positions = AIObserver._get_deployable_positions(
                game_state.board, player.color.value
            )
            for health_value in [10, 8, 6, 4]:
                if reserve_counts[health_value] > 0:
                    # Check which corner positions are actually available
                    available_corners = [
                        pos for pos in corner_positions
                        if game_state.board.get_cell_at(pos) and
                           not game_state.board.get_cell_at(pos).is_occupied()
                    ]
                    if available_corners:
                        actions.append({
                            "type": "DEPLOY",
                            "health_value": health_value,
                            "positions": [list(pos) for pos in available_corners],
                            "remaining": reserve_counts[health_value],
                            "description": (
                                f"Deploy {health_value}hp token from reserve "
                                f"({reserve_counts[health_value]} remaining)"
                            ),
                        })

        elif game_state.turn_phase == TurnPhase.ACTION:
            # Attack actions
            for token in deployed_tokens:
                attackable = CombatSystem.get_attackable_targets(token, game_state.tokens)
                for target in attackable:
                    damage = token.health // 2
                    will_kill = CombatSystem.would_kill(token, target)
                    target_player = game_state.get_player(target.player_id)
                    target_color = AIObserver.COLOR_NAMES.get(
                        target_player.color, "Unknown"
                    ) if target_player else "Unknown"

                    actions.append({
                        "type": "ATTACK",
                        "attacker_id": token.id,
                        "attacker_position": list(token.position),
                        "defender_id": target.id,
                        "defender_position": list(target.position),
                        "defender_owner": target_color,
                        "damage": damage,
                        "will_kill": will_kill,
                        "description": (
                            f"Attack token #{target.id} ({target_color}) "
                            f"with token #{token.id} for {damage} damage"
                            f"{' (KILL)' if will_kill else ''}"
                        ),
                    })

        # End turn is always available in ACTION phase
        if game_state.turn_phase == TurnPhase.ACTION:
            actions.append({
                "type": "END_TURN",
                "description": "End your turn",
            })

        return {"phase": phase, "actions": actions}

    @staticmethod
    def explain_victory_conditions(game_state: GameState) -> str:
        """
        Explain current win conditions and progress.

        Args:
            game_state: Current game state

        Returns:
            Multi-line string explaining victory conditions
        """
        lines = []
        lines.append("VICTORY CONDITIONS:")
        lines.append("")

        # Calculate current requirements
        disabled_gens = sum(1 for g in game_state.generators if g.is_disabled)
        tokens_required = max(
            1,
            CRYSTAL_BASE_TOKENS_REQUIRED - (disabled_gens * GENERATOR_TOKEN_REDUCTION)
        )

        lines.append(f"Win by holding the crystal with {tokens_required} tokens for 3 consecutive turns")
        lines.append(f"  Base requirement: {CRYSTAL_BASE_TOKENS_REQUIRED} tokens")
        if disabled_gens > 0:
            lines.append(
                f"  Disabled generators: {disabled_gens} "
                f"(-{disabled_gens * GENERATOR_TOKEN_REDUCTION} tokens)"
            )
        lines.append("")

        # Current crystal progress
        if game_state.crystal:
            crystal = game_state.crystal
            crystal_holders = AIObserver._get_crystal_holders(crystal, game_state)

            if crystal_holders:
                lines.append("Current crystal progress:")
                for pid, count in crystal_holders.items():
                    player = game_state.get_player(pid)
                    if player:
                        color_name = AIObserver.COLOR_NAMES.get(player.color, "Unknown")
                        # Get turns held for this player (from crystal holding_player_id)
                        turns_held = crystal.turns_held if crystal.holding_player_id == pid else 0
                        progress = f"{count}/{tokens_required} tokens, held for {turns_held}/3 turns"

                        if count >= tokens_required and turns_held >= 3:
                            lines.append(f"  {player.name} ({color_name}): {progress} ✓ WINNING!")
                        elif count >= tokens_required:
                            lines.append(
                                f"  {player.name} ({color_name}): {progress} "
                                f"(needs {3 - turns_held} more turn(s))"
                            )
                        else:
                            lines.append(
                                f"  {player.name} ({color_name}): {progress} "
                                f"(needs {tokens_required - count} more token(s))"
                            )
            else:
                lines.append("  No players currently on crystal")
            lines.append("")

        # Generator bonuses
        lines.append("Generator bonuses:")
        lines.append(
            f"  Disable generators to reduce crystal requirement "
            f"(each generator = -{GENERATOR_TOKEN_REDUCTION} tokens)"
        )
        if game_state.generators:
            for i, gen in enumerate(game_state.generators, 1):
                if gen.is_disabled:
                    lines.append(f"  Generator {i}: DISABLED ✓")
                else:
                    status = AIObserver._get_generator_status(gen, game_state)
                    lines.append(f"  Generator {i}: {status}")

        return "\n".join(lines)

    @staticmethod
    def get_situation_report(
        game_state: GameState, perspective_player_id: str
    ) -> str:
        """
        Get complete situation report combining all observations.

        This is the main function AI players should call to get full game state.

        Args:
            game_state: Current game state
            perspective_player_id: Player ID to generate report for

        Returns:
            Comprehensive multi-section report as formatted text
        """
        sections = []

        # Main game state
        sections.append(
            AIObserver.describe_game_state(game_state, perspective_player_id)
        )

        # Board map
        sections.append(AIObserver.get_board_map(game_state, perspective_player_id))

        # Available actions
        actions_data = AIObserver.list_available_actions(game_state, perspective_player_id)
        sections.append("AVAILABLE ACTIONS:")
        if actions_data["actions"]:
            for i, action in enumerate(actions_data["actions"], 1):
                sections.append(f"  {i}. {action['description']}")
        else:
            if actions_data["phase"] == "NOT_YOUR_TURN":
                sections.append("  (waiting for other player's turn)")
            else:
                sections.append("  (no actions available)")
        sections.append("")

        # Victory conditions
        sections.append(AIObserver.explain_victory_conditions(game_state))

        return "\n".join(sections)
