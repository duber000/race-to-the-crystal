"""
Shared AI Strategy Module - Unified strategy logic for all AI clients.

Provides consistent strategy implementations (random, aggressive, defensive)
usable by both TCP and HTTP AI clients, with generator awareness and
movement range considerations.
"""

import random
from game.game_state import GameState
from game.token import Token
from shared.constants import BOARD_WIDTH, BOARD_HEIGHT
from shared.types import PlayerID


CRYSTAL_POSITION = (BOARD_WIDTH // 2, BOARD_HEIGHT // 2)


class ChosenAction:
    """
    Represents an AI's chosen action with all required parameters resolved.

    This is the universal action format that both TCP and HTTP clients
    can convert to their specific wire formats.
    """

    __slots__ = ("action_type", "params")

    def __init__(self, action_type: str, params: dict | None = None):
        self.action_type = action_type
        self.params = params or {}

    def __repr__(self) -> str:
        return f"ChosenAction({self.action_type}, {self.params})"


class AIStrategy:
    """
    Unified AI strategy with generator awareness and movement scoring.

    Strategies:
        random: Pick a random action each turn.
        aggressive: Prioritize kills > attacks > move toward objectives > deploy > end turn.
        defensive: Prioritize deploy > move toward crystal > opportunistic attack > end turn.
    """

    def __init__(self, strategy_name: str = "random"):
        if strategy_name not in ("random", "aggressive", "defensive"):
            strategy_name = "random"
        self.strategy_name = strategy_name

    def choose_action(
        self, actions: list[dict], game_state: GameState, player_id: PlayerID
    ) -> ChosenAction | None:
        """
        Choose an action from available actions based on strategy.

        Args:
            actions: List of action dicts from AIObserver.list_available_actions
            game_state: Current game state
            player_id: AI's player ID

        Returns:
            ChosenAction with resolved parameters, or None
        """
        if not actions:
            return None

        match self.strategy_name:
            case "aggressive":
                return self._choose_aggressive(actions, game_state, player_id)
            case "defensive":
                return self._choose_defensive(actions, game_state, player_id)
            case _:
                return self._choose_random(actions)

    def _choose_random(self, actions: list[dict]) -> ChosenAction:
        """Choose a random action with a random valid destination/position."""
        action = random.choice(actions)
        return self._resolve_action(action)

    def _choose_aggressive(
        self, actions: list[dict], game_state: GameState, player_id: PlayerID
    ) -> ChosenAction:
        """
        Aggressive strategy: prioritize dealing damage, then move toward objectives.

        Priority order:
        1. Attack (prefer kills, then highest damage)
        2. Move toward best objective (generator or crystal)
        3. Deploy (prefer highest health)
        4. End turn
        """
        attacks = [a for a in actions if a["type"] == "ATTACK"]
        if attacks:
            return self._best_attack(attacks)

        moves = [a for a in actions if a["type"] == "MOVE"]
        if moves:
            return self._best_move(moves, game_state, player_id)

        deploys = [a for a in actions if a["type"] == "DEPLOY"]
        if deploys:
            return self._best_deploy(deploys)

        end_turns = [a for a in actions if a["type"] == "END_TURN"]
        if end_turns:
            return ChosenAction("END_TURN")

        return self._choose_random(actions)

    def _choose_defensive(
        self, actions: list[dict], game_state: GameState, player_id: PlayerID
    ) -> ChosenAction:
        """
        Defensive strategy: build up forces, move toward objectives safely.

        Priority order:
        1. Deploy (50% chance when available)
        2. Move toward crystal
        3. Opportunistic attack (30% chance when available)
        4. End turn
        """
        deploys = [a for a in actions if a["type"] == "DEPLOY"]
        if deploys and random.random() > 0.5:
            return self._best_deploy(deploys)

        moves = [a for a in actions if a["type"] == "MOVE"]
        if moves:
            return self._best_move(
                moves, game_state, player_id, prioritize_crystal=True
            )

        attacks = [a for a in actions if a["type"] == "ATTACK"]
        if attacks and random.random() > 0.7:
            return self._best_attack(attacks)

        end_turns = [a for a in actions if a["type"] == "END_TURN"]
        if end_turns:
            return ChosenAction("END_TURN")

        return self._choose_random(actions)

    def _best_attack(self, attacks: list[dict]) -> ChosenAction:
        """Pick best attack: prefer kills, then highest damage."""
        killing = [a for a in attacks if a.get("will_kill", False)]
        if killing:
            chosen = max(killing, key=lambda a: a.get("damage", 0))
        else:
            chosen = max(attacks, key=lambda a: a.get("damage", 0))

        return ChosenAction(
            "ATTACK",
            {
                "attacker_id": chosen["attacker_id"],
                "defender_id": chosen["defender_id"],
            },
        )

    def _best_move(
        self,
        moves: list[dict],
        game_state: GameState,
        player_id: PlayerID,
        prioritize_crystal: bool = False,
    ) -> ChosenAction:
        """
        Score move destinations by distance to best objective.

        Considers crystal and uncaptured generators. Tokens with
        movement range 2 (damaged) are not penalized — their
        expanded destinations are naturally scored.

        Args:
            moves: Available MOVE actions
            game_state: Current game state
            player_id: AI's player ID
            prioritize_crystal: If True, score moves toward crystal only
        """
        objectives = self._get_objectives(game_state, player_id, prioritize_crystal)

        best_move = None
        best_dest = None
        best_score = float("inf")

        for move in moves:
            token_id = move["token_id"]
            token = game_state.get_token(token_id)
            for dest_list in move["valid_destinations"]:
                dest = tuple(dest_list)
                score = self._score_destination(dest, objectives, token)
                if score < best_score:
                    best_score = score
                    best_move = move
                    best_dest = dest

        if best_move and best_dest:
            return ChosenAction(
                "MOVE",
                {"token_id": best_move["token_id"], "destination": list(best_dest)},
            )

        action = random.choice(moves)
        return ChosenAction(
            "MOVE",
            {
                "token_id": action["token_id"],
                "destination": action["valid_destinations"][0],
            },
        )

    def _best_deploy(self, deploys: list[dict]) -> ChosenAction:
        """Pick best deploy: prefer highest health, then first available position."""
        chosen = max(deploys, key=lambda a: a.get("health_value", 0))
        positions = chosen.get("positions", [])
        position = positions[0] if positions else None

        if position is None:
            return self._choose_random(deploys)

        return ChosenAction(
            "DEPLOY",
            {"health_value": chosen["health_value"], "position": position},
        )

    def _resolve_action(self, action: dict) -> ChosenAction:
        """Convert a raw action dict to a ChosenAction with resolved params."""
        action_type = action["type"]

        if action_type == "MOVE":
            dests = action.get("valid_destinations", [])
            dest = (
                random.choice(dests)
                if len(dests) > 1
                else (dests[0] if dests else None)
            )
            return ChosenAction(
                "MOVE",
                {"token_id": action["token_id"], "destination": dest},
            )

        if action_type == "ATTACK":
            return ChosenAction(
                "ATTACK",
                {
                    "attacker_id": action["attacker_id"],
                    "defender_id": action["defender_id"],
                },
            )

        if action_type == "DEPLOY":
            positions = action.get("positions", [])
            pos = (
                random.choice(positions)
                if len(positions) > 1
                else (positions[0] if positions else None)
            )
            return ChosenAction(
                "DEPLOY",
                {"health_value": action["health_value"], "position": pos},
            )

        if action_type == "END_TURN":
            return ChosenAction("END_TURN")

        return ChosenAction("END_TURN")

    def _get_objectives(
        self, game_state: GameState, player_id: PlayerID, crystal_only: bool = False
    ) -> list[tuple[int, int]]:
        """
        Get list of objective positions to move toward.

        Includes crystal always, and uncaptured generators unless crystal_only.
        Generator objectives are sorted by capture progress (closest to capture first)
        so the AI can finish capturing them.
        """
        objectives = [CRYSTAL_POSITION]

        if crystal_only or not game_state.generators:
            return objectives

        for gen in game_state.generators:
            if gen.is_disabled:
                continue
            if gen.capturing_player_id == player_id:
                objectives.insert(0, gen.position)
            elif gen.capturing_player_id is None:
                objectives.append(gen.position)
            else:
                objectives.append(gen.position)

        return objectives

    def _score_destination(
        self,
        dest: tuple[int, int],
        objectives: list[tuple[int, int]],
        token: Token | None,
    ) -> float:
        """
        Score a destination — lower is better.

        Distance to the nearest objective is the primary score.
        A small bonus is given for tokens with movement range 2
        (damaged = faster) to prefer advancing them when scores
        are otherwise close.
        """
        min_dist = float("inf")
        for obj in objectives:
            dist = abs(dest[0] - obj[0]) + abs(dest[1] - obj[1])
            if dist < min_dist:
                min_dist = dist

        if token is not None and token.movement_range >= 2:
            min_dist -= 0.5

        return min_dist
