"""
Central game state management.
"""

from dataclasses import dataclass, field
from typing import Self
import json

from shared.enums import (
    CellType,
    GamePhase,
    PlayerColor,
    TurnPhase,
    CrystalEffect,
)
from shared.constants import (
    TOKEN_HEALTH_VALUES,
    TOKENS_PER_HEALTH_VALUE,
)
from shared.types import TokenID, PlayerID
from game.board import Board
from game.combat import CombatOutcome
from game.player import Player
from game.token import Token
from game.generator import Generator
from game.crystal import Crystal
from game.crystal_effects import CrystalEffectsManager

SERIALIZATION_VERSION = 1


@dataclass
class GameState:
    """
    Central game state containing all game entities and status.

    Attributes:
        board: The game board
        players: Dictionary of player_id -> Player
        tokens: Dictionary of token_id -> Token
        generators: List of generator objects
        crystal: The power crystal object
        crystal_effects: Manager for crystal effects (fog of war, phantom enemies)
        current_turn_player_id: ID of player whose turn it is
        turn_number: Current turn number
        phase: Current game phase
        winner_id: ID of winning player (None if game not won)
    """

    board: Board = field(default_factory=Board)
    players: dict[PlayerID, Player] = field(default_factory=dict)
    tokens: dict[TokenID, Token] = field(default_factory=dict)
    generators: list = field(
        default_factory=list
    )  # Will be list[Generator] when created
    crystal: "Crystal | None" = None  # Will be Crystal object when created
    crystal_effects: CrystalEffectsManager = field(
        default_factory=CrystalEffectsManager
    )
    current_turn_player_id: PlayerID | None = None
    turn_number: int = 0
    phase: GamePhase = GamePhase.SETUP
    turn_phase: TurnPhase = TurnPhase.MOVEMENT
    winner_id: PlayerID | None = None
    _next_token_id: int = 0
    last_triggered_crystal_effect: tuple[PlayerID, CrystalEffect] | None = None
    last_triggered_mystery_event: tuple[TokenID, tuple[int, int], str] | None = (
        None  # (token_id, position, effect)
    )

    @property
    def current_player_id(self) -> PlayerID | None:
        """Alias for current_turn_player_id."""
        return self.current_turn_player_id

    @property
    def game_phase(self) -> GamePhase:
        """Alias for phase."""
        return self.phase

    def add_player(self, player_id: PlayerID, name: str, color: PlayerColor) -> Player:
        """
        Add a new player to the game.

        Args:
            player_id: Unique identifier for the player
            name: Player's display name
            color: Player's color

        Returns:
            The created Player object
        """
        player = Player(id=player_id, name=name, color=color)
        self.players[player_id] = player
        return player

    def remove_player(self, player_id: PlayerID) -> None:
        """Remove a player from the game."""
        if player_id in self.players:
            del self.players[player_id]

    def create_tokens_for_player(self, player_id: PlayerID) -> list[Token]:
        """
        Create all tokens for a player in reserve (not deployed to board).

        Args:
            player_id: ID of player to create tokens for

        Returns:
            List of created tokens
        """
        if player_id not in self.players:
            raise ValueError(f"Player {player_id} not found")

        player = self.players[player_id]
        tokens = []

        # Get player's starting corner position (used as reference for deployment)
        player_index = player.color.value
        corner_pos = self.board.get_starting_position(player_index)

        # Create tokens with different health values
        # Tokens start in reserve (is_deployed=False) and are not placed on board
        for health_value in TOKEN_HEALTH_VALUES:
            for _ in range(TOKENS_PER_HEALTH_VALUE):
                token = Token(
                    id=TokenID(self._next_token_id),
                    player_id=player_id,
                    health=health_value,
                    max_health=health_value,
                    position=corner_pos,  # Reference position (not actually on board yet)
                    is_deployed=False,  # Starts in reserve
                )
                self.tokens[token.id] = token
                player.add_token(token.id)
                tokens.append(token)
                self._next_token_id += 1

        return tokens

    def get_token(self, token_id: TokenID) -> Token | None:
        """Get token by ID."""
        return self.tokens.get(token_id)

    def get_reserve_tokens(self, player_id: PlayerID) -> list[Token]:
        """
        Get all tokens in reserve (not deployed) for a player.

        Args:
            player_id: Player ID

        Returns:
            List of tokens not yet deployed
        """
        player = self.get_player(player_id)
        if not player:
            return []

        return [
            self.tokens[tid]
            for tid in player.token_ids
            if tid in self.tokens and not self.tokens[tid].is_deployed
        ]

    def get_reserve_token_counts(self, player_id: PlayerID) -> dict:
        """
        Get count of reserve tokens by health value.

        Args:
            player_id: Player ID

        Returns:
            Dictionary mapping health value to count
        """
        reserve = self.get_reserve_tokens(player_id)
        counts = {10: 0, 8: 0, 6: 0, 4: 0}
        for token in reserve:
            if token.max_health in counts:
                counts[token.max_health] += 1
        return counts

    def deploy_token(
        self, player_id: PlayerID, health_value: int, position: tuple[int, int]
    ) -> Token | None:
        """
        Deploy a token from reserve to the board.

        Args:
            player_id: Player ID
            health_value: Health value of token to deploy (10, 8, 6, or 4)
            position: Position to deploy to

        Returns:
            The deployed token, or None if no token available
        """
        # Find first available token of requested type in reserve
        reserve = self.get_reserve_tokens(player_id)
        for token in reserve:
            if token.max_health == health_value:
                # Deploy the token
                token.position = position
                token.is_deployed = True
                self.board.set_occupant(position, token.id)
                return token

        return None

    def get_player(self, player_id: PlayerID) -> Player | None:
        """Get player by ID."""
        return self.players.get(player_id)

    def get_current_player(self) -> Player | None:
        """Get the current player whose turn it is."""
        if self.current_turn_player_id:
            return self.get_player(self.current_turn_player_id)
        elif self.current_player_id:
            return self.get_player(self.current_player_id)
        return None

    def get_tokens_at_position(self, position: tuple) -> list[Token]:
        """
        Get all tokens at a specific position.

        Args:
            position: (x, y) position

        Returns:
            List of tokens at that position
        """
        return [
            t for t in self.tokens.values() if t.position == position and t.is_alive
        ]

    def get_player_tokens(self, player_id: PlayerID) -> list[Token]:
        """
        Get all alive, deployed tokens for a player.

        Args:
            player_id: Player ID

        Returns:
            List of alive, deployed tokens owned by player
        """
        player = self.get_player(player_id)
        if not player:
            return []

        return [
            self.tokens[tid]
            for tid in player.token_ids
            if tid in self.tokens
            and self.tokens[tid].is_alive
            and self.tokens[tid].is_deployed
        ]

    def get_token_movement_range(self, token: Token) -> int:
        """
        Get effective movement range for a token, including crystal effect bonuses.

        Args:
            token: Token to get movement range for

        Returns:
            Effective movement range
        """
        from shared.constants import CRYSTAL_SPEED_BOOST_AMOUNT

        base_range = token.movement_range

        # Apply speed boost if player has the effect
        player_effects = self.crystal_effects.get_player_effects(token.player_id)
        if player_effects.has_effect(CrystalEffect.SPEED_BOOST):
            return base_range + CRYSTAL_SPEED_BOOST_AMOUNT

        return base_range

    def move_token(self, token_id: TokenID, new_position: tuple) -> bool:
        """
        Move a token to a new position.

        Args:
            token_id: ID of token to move
            new_position: Target (x, y) position

        Returns:
            True if move was successful
        """
        if not (token := self.get_token(token_id)) or not token.is_alive:
            return False

        # Clear old position (remove specific token)
        self.board.clear_occupant(token.position, token_id)

        # Move token
        token.move_to(new_position)

        # Set new position (add to occupants list)
        self.board.set_occupant(new_position, token_id)

        return True

    def remove_token(self, token_id: TokenID) -> None:
        """
        Remove a dead token from play.

        Args:
            token_id: ID of token to remove
        """
        if not (token := self.get_token(token_id)):
            return

        # Clear from board (remove specific token)
        self.board.clear_occupant(token.position, token_id)

        # Remove from player
        if player := self.get_player(token.player_id):
            player.remove_token(token_id)

        # Mark as not alive
        token.is_alive = False

    def attack_token(
        self, attacker_id: TokenID, defender_id: TokenID
    ) -> CombatOutcome | None:
        """
        Execute an attack between two tokens.

        Args:
            attacker_id: ID of attacking token
            defender_id: ID of defending token

        Returns:
            CombatOutcome with damage information, or None if attack was invalid
        """
        from game.combat import CombatSystem, CombatOutcome
        from shared.constants import CRYSTAL_DAMAGE_BOOST_MULTIPLIER
        from shared.enums import CombatResult

        attacker = self.get_token(attacker_id)
        defender = self.get_token(defender_id)

        if not attacker or not defender:
            return None

        # Check if attack is valid
        if not CombatSystem.can_attack(attacker, defender):
            return None

        # Calculate damage with potential boost
        damage = attacker.attack_power

        # Apply damage boost if attacker's player has the effect
        player_effects = self.crystal_effects.get_player_effects(attacker.player_id)
        if player_effects.has_effect(CrystalEffect.DAMAGE_BOOST):
            damage = int(damage * CRYSTAL_DAMAGE_BOOST_MULTIPLIER)

        # Apply damage to defender
        was_killed = defender.take_damage(damage)

        # If defender was killed, remove them from the board
        if was_killed:
            self.remove_token(defender_id)

        # Return combat outcome
        result = CombatResult.KILLED if was_killed else CombatResult.HIT
        return CombatOutcome(
            result=result,
            damage_dealt=damage,
            attacker_id=attacker_id,
            defender_id=defender_id,
            defender_killed=was_killed,
        )

    def _auto_deploy_starting_tokens(
        self, player_id: PlayerID, player_index: int
    ) -> None:
        """
        Automatically deploy tokens to starting corner positions at game start.

        Args:
            player_id: Player ID
            player_index: Player index (0-3) for determining starting corner
        """
        # Get deployable positions for this player
        deployable_positions = self.board.get_deployable_positions(player_index)

        # Get reserve tokens sorted by health (deploy strongest first)
        reserve = self.get_reserve_tokens(player_id)
        reserve_sorted = sorted(reserve, key=lambda t: t.max_health, reverse=True)

        # Deploy exactly 3 tokens to starting positions
        deployed_count = 0
        for position in deployable_positions:
            if deployed_count >= 3:
                break

            # Check if position is not occupied and not a special cell
            cell = self.board.get_cell_at(position)
            if not cell or cell.is_occupied():
                continue

            # Don't deploy on generators, crystal, or mystery squares
            if cell.cell_type != CellType.NORMAL:
                continue

            # Deploy the next token from reserve
            token = reserve_sorted[deployed_count]
            token.position = position
            token.is_deployed = True
            self.board.set_occupant(position, token.id)
            deployed_count += 1

    def start_game(self) -> None:
        """Start the game and set up initial state."""
        if self.phase != GamePhase.SETUP:
            return

        # Create tokens for all players
        for player_id in self.players.keys():
            self.create_tokens_for_player(player_id)

        # Auto-deploy tokens to starting positions for all players
        for player_id, player in self.players.items():
            self._auto_deploy_starting_tokens(player_id, player.color.value)

        # Initialize generators and crystal (will implement when those classes exist)
        # self.generators = [...]
        # self.crystal = Crystal(...)

        # Set first player
        if self.players:
            self.current_turn_player_id = list(self.players.keys())[0]

        self.phase = GamePhase.PLAYING
        self.turn_number = 1

    def end_turn(self) -> None:
        """End current turn and advance to next player."""
        if not self.current_turn_player_id:
            return

        # Note: _update_generators_and_crystal() is now called separately
        # in the game action handler to allow for sound effects
        # self._update_generators_and_crystal()

        # Clear mystery event from previous action
        self.last_triggered_mystery_event = None

        # Update crystal effects (clear expired effects)
        self.crystal_effects.end_turn_update()

        # Get list of active players
        active_players = [
            pid for pid, player in self.players.items() if player.is_active
        ]

        if not active_players:
            return

        # Find current player index
        try:
            current_index = active_players.index(self.current_turn_player_id)
        except ValueError:
            current_index = -1

        # Move to next active player
        next_index = (current_index + 1) % len(active_players)
        self.current_turn_player_id = active_players[next_index]

        # If we wrapped around to first player, increment turn number
        if next_index == 0:
            # Check if we should trigger a random crystal effect
            # turn_number already represents the current round (increments once per full rotation)
            from shared.constants import CRYSTAL_RANDOM_EFFECT_ROUND_INTERVAL

            # Trigger effect every N rounds (after completing round 5, 10, 15, etc.)
            if (
                self.turn_number > 0
                and self.turn_number % CRYSTAL_RANDOM_EFFECT_ROUND_INTERVAL == 0
            ):
                self.trigger_random_crystal_effect()

            # Increment turn number for new round
            self.turn_number += 1

        # Reset turn phase to MOVEMENT for next player
        self.turn_phase = TurnPhase.MOVEMENT

    def _update_generators_and_crystal(self) -> tuple[list[int], bool]:
        """
        Update generator capture status and check crystal win condition.
        Called at the end of each turn.

        Returns:
            Tuple of (newly_disabled_generator_ids, crystal_captured)
        """
        # Only update if generators and crystal exist
        if not self.generators or not self.crystal:
            return [], False

        # Build a map of positions to tokens (token_id, player_id)
        tokens_by_position = {}
        for token in self.tokens.values():
            if token.is_alive and token.is_deployed:
                pos = token.position
                if pos not in tokens_by_position:
                    tokens_by_position[pos] = []
                tokens_by_position[pos].append((token.id, token.player_id))

        # Update generators
        from game.generator import GeneratorManager

        newly_disabled, capturing_players = GeneratorManager.update_all_generators(
            self.generators, tokens_by_position
        )

        # Reduce crystal effect durations for players who captured generators
        for generator_id, player_id in capturing_players.items():
            self.crystal_effects.reduce_effect_durations_for_generator_capture(
                player_id
            )

        # Update crystal and check for winner
        from game.crystal import CrystalManager

        tokens_at_crystal = tokens_by_position.get(self.crystal.position, [])
        disabled_count = GeneratorManager.count_disabled_generators(self.generators)

        winner_id = CrystalManager.check_win_condition(
            self.crystal, tokens_at_crystal, disabled_count
        )

        # Set winner if win condition met
        crystal_captured = False
        if winner_id:
            self.set_winner(winner_id)
            crystal_captured = True

        return newly_disabled, crystal_captured

    def check_win_condition(self) -> str | None:
        """
        Check if any player has won the game.

        Returns:
            Player ID of winner, or None if no winner yet

        Note:
            Win condition checking is performed automatically in end_turn()
            via _update_generators_and_crystal(). This method just returns
            the cached winner_id value.
        """
        return self.winner_id

    def set_winner(self, player_id: PlayerID) -> None:
        """
        Set the game winner and end the game.

        Args:
            player_id: ID of winning player
        """
        self.winner_id = player_id
        self.phase = GamePhase.ENDED

    def apply_crystal_effect(
        self,
        player_id: PlayerID,
        effect_type: "CrystalEffect",
        duration: int | None = None,
    ) -> None:
        """
        Apply a crystal effect to a player.

        Args:
            player_id: Player to affect
            effect_type: Type of effect (FOG_OF_WAR or PHANTOM_ENEMIES)
            duration: Effect duration in turns (uses default if None)
        """
        self.crystal_effects.apply_effect(
            player_id, effect_type, self.turn_number, duration
        )

        # If phantom enemies effect, generate phantom tokens
        if effect_type == CrystalEffect.PHANTOM_ENEMIES:
            self.generate_phantom_tokens_for_player(player_id)

    def generate_phantom_tokens_for_player(self, player_id: PlayerID) -> None:
        """
        Generate phantom tokens for a player affected by phantom enemies.

        Args:
            player_id: Player who will see phantom tokens
        """
        # Get other players
        other_players = [pid for pid in self.players.keys() if pid != player_id]

        # Get occupied positions
        occupied = set()
        for token in self.tokens.values():
            if token.is_alive and token.is_deployed:
                occupied.add(token.position)

        # Generate phantoms
        self.crystal_effects.generate_phantom_tokens(
            player_id, other_players, self.board.width, self.board.height, occupied
        )

    def get_visible_tokens_for_player(
        self, player_id: PlayerID
    ) -> tuple[list[Token], list]:
        """
        Get tokens visible to a specific player (considering fog of war and phantoms).

        Args:
            player_id: Player viewing the board

        Returns:
            Tuple of (visible_real_tokens, phantom_tokens)
        """
        # Get all alive, deployed tokens
        all_tokens = [t for t in self.tokens.values() if t.is_alive and t.is_deployed]

        # Filter and get phantoms
        return self.crystal_effects.get_tokens_for_player_view(
            player_id, all_tokens, lambda t: t.player_id
        )

    def trigger_random_crystal_effect(
        self,
    ) -> tuple[PlayerID | None, CrystalEffect] | None:
        """
        Trigger a random crystal effect on all active players.

        Returns:
            Tuple of (None, effect_type) if triggered (None indicates all players), None otherwise
        """
        import random

        # Get active players
        active_players = [
            pid for pid, player in self.players.items() if player.is_active
        ]

        if not active_players:
            return None

        # Select random effect
        all_effects = list(CrystalEffect)
        effect_type = random.choice(all_effects)

        # Apply the effect to ALL active players
        for player_id in active_players:
            self.apply_crystal_effect(player_id, effect_type)

        # Store for client to detect and play animations/sounds
        # None for player_id indicates all players were affected
        self.last_triggered_crystal_effect = (None, effect_type)

        return (None, effect_type)

    def to_dict(self) -> dict:
        """Convert game state to dictionary for serialization."""
        return {
            "schema_version": SERIALIZATION_VERSION,
            "board": self.board.to_dict(),
            "players": {pid: p.to_dict() for pid, p in self.players.items()},
            "tokens": {tid: t.to_dict() for tid, t in self.tokens.items()},
            "generators": [g.to_dict() for g in self.generators],
            "crystal": self.crystal.to_dict() if self.crystal else None,
            "crystal_effects": self.crystal_effects.to_dict(),
            "current_turn_player_id": self.current_turn_player_id,
            "turn_number": self.turn_number,
            "phase": self.phase.value,
            "turn_phase": self.turn_phase.value,
            "winner_id": self.winner_id,
            "last_triggered_crystal_effect": (
                self.last_triggered_crystal_effect[0],
                self.last_triggered_crystal_effect[1].value,
            )
            if self.last_triggered_crystal_effect
            else None,
            "last_triggered_mystery_event": self.last_triggered_mystery_event,
        }

    def to_json(self) -> str:
        """Convert game state to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Create game state from dictionary."""
        state = cls()
        state.board = Board.from_dict(data["board"])
        state.players = {
            pid: Player.from_dict(pdata) for pid, pdata in data["players"].items()
        }
        state.tokens = {
            int(tid): Token.from_dict(tdata) for tid, tdata in data["tokens"].items()
        }
        # Generators/crystal may be absent in older saves
        gen_data = data.get("generators", [])
        state.generators = [Generator.from_dict(g) for g in gen_data]

        crystal_data = data.get("crystal")
        state.crystal = Crystal.from_dict(crystal_data) if crystal_data else None

        # Crystal effects may be absent in older saves
        effects_data = data.get("crystal_effects")
        state.crystal_effects = (
            CrystalEffectsManager.from_dict(effects_data)
            if effects_data
            else CrystalEffectsManager()
        )

        state.current_turn_player_id = data["current_turn_player_id"]
        state.turn_number = data["turn_number"]
        state.phase = GamePhase(data["phase"])
        state.turn_phase = TurnPhase(data["turn_phase"])
        state.winner_id = data["winner_id"]
        # Handle last_triggered_crystal_effect deserialization
        effect_data = data.get("last_triggered_crystal_effect")
        if effect_data:
            from shared.enums import CrystalEffect

            state.last_triggered_crystal_effect = (
                effect_data[0],
                CrystalEffect(effect_data[1]),
            )
        else:
            state.last_triggered_crystal_effect = None

        # Handle last_triggered_mystery_event deserialization
        state.last_triggered_mystery_event = data.get("last_triggered_mystery_event")

        return state

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create game state from JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def create_game(cls, num_players: int) -> Self:
        """
        Create a new game state with the specified number of players.

        Args:
            num_players: Number of players (2-4)

        Returns:
            Configured GameState instance
        """
        if num_players < 2 or num_players > 4:
            raise ValueError("Number of players must be between 2 and 4")

        # Create game state instance
        game_state = cls()

        # Add players with appropriate colors
        player_colors = [
            PlayerColor.CYAN,
            PlayerColor.MAGENTA,
            PlayerColor.YELLOW,
            PlayerColor.GREEN,
        ]

        for i in range(num_players):
            player_id = f"player_{i}"
            player_name = f"Player {i + 1}"
            player_color = player_colors[i]

            game_state.add_player(player_id, player_name, player_color)

        return game_state

    def __repr__(self) -> str:
        return f"GameState(Phase={self.phase.name}, Turn={self.turn_number}, Players={len(self.players)})"
