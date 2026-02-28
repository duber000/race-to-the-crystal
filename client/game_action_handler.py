"""
Game action handler for Race to the Crystal.

This module handles execution of all game actions including movement,
combat, deployment, and turn management.
"""


from client.sprites.token_sprite import TokenSprite
from game.combat import CombatSystem
from game.mystery_square import MysterySquareSystem
from shared.constants import PLAYER_COLORS
from shared.enums import CellType
from shared.logging_config import setup_logger
from shared.types import TokenID

logger = setup_logger(__name__)


class GameActionHandler:
    """
    Handles execution of game actions.

    The GameActionHandler is responsible for:
    - Move execution (including mystery square effects)
    - Attack resolution (including sprite updates)
    - Token deployment
    - Turn ending (including generator/crystal updates)
    - Post-action UI and rendering updates
    """

    def __init__(
        self,
        game_state,
        movement_system,
        renderer_2d,
        renderer_3d,
        ui_manager,
        audio_manager,
    ):
        """
        Initialize game action handler.

        Args:
            game_state: Game state object
            movement_system: Movement system for adjacency checks
            renderer_2d: 2D renderer for sprite updates
            renderer_3d: 3D renderer for model updates
            ui_manager: UI manager for rebuilding visuals
            audio_manager: Audio manager for sound updates
        """
        self.game_state = game_state
        self.movement_system = movement_system
        self.renderer_2d = renderer_2d
        self.renderer_3d = renderer_3d
        self.ui_manager = ui_manager
        self.audio_manager = audio_manager

        # Track mystery animations that should start after token movement completes
        # Maps token_id -> (target_position, should_play_sound)
        self.pending_mystery_animations: dict[
            TokenID[tuple[int, int], bool]
        ] = {}

    def process_pending_mystery_animations(
        self, mystery_animations: dict[tuple[int, int], float]
    ) -> None:
        """
        Check if any tokens have finished moving and start their mystery animations.

        This is called each frame to detect when token movement animations complete
        and start the mystery square animations (spin) at that point.

        Args:
            mystery_animations: The active mystery animations dict to update
        """
        completed_tokens = []

        for token_id, (
            target_pos,
            should_play_sound,
        ) in self.pending_mystery_animations.items():
            # Find the token sprite to check if it's still moving
            token_sprite = None
            for sprite in self.renderer_2d.token_sprites:
                if hasattr(sprite, "token") and sprite.token.id == token_id:
                    token_sprite = sprite
                    break

            if token_sprite and not token_sprite.is_moving:
                # Token has finished moving, start the mystery animation
                mystery_animations[target_pos] = 0.0

                if should_play_sound:
                    self.audio_manager.play_mystery_bing_sound()

                logger.info(f"🎲 Coin flip started at {target_pos}!")
                completed_tokens.append(token_id)

        # Remove completed animations
        for token_id in completed_tokens:
            del self.pending_mystery_animations[token_id]

    def execute_move(
        self,
        token_id: TokenID,
        target_cell: tuple[int, int],
        mystery_animations: dict[tuple[int, int], float],
        ctx,
        animate: bool = True,
    ) -> tuple[bool[tuple[int, int]]]:
        """
        Execute a token move action.

        Args:
            token_id: ID of token to move
            target_cell: Target cell coordinates
            mystery_animations: Dict for mystery square animations
            ctx: OpenGL context (for potential 3D token creation)

        Returns:
            Tuple of (success, final_position). final_position may differ from
            target_cell if token was teleported by mystery square.
        """
        token = self.game_state.get_token(token_id)
        if not token:
            return False, None

        old_pos = token.position

        # Move the token
        success = self.game_state.move_token(token_id, target_cell)

        if not success:
            return False, None

        logger.debug(f"Moved token {token_id} from {old_pos} to {target_cell}")

        # Play sliding sound effect for movement
        self.audio_manager.play_sliding_sound()

        # Check for mystery square effect
        board_cell = self.game_state.board.get_cell_at(target_cell)
        final_position = target_cell

        if board_cell and board_cell.cell_type == CellType.MYSTERY:
            # Queue mystery animation to start after token movement completes
            # This ensures the spin happens when the token arrives, not before
            self.pending_mystery_animations[token_id] = (target_cell, True)
            logger.info(
                f"🎲 Queued mystery animation for token {token_id} at {target_cell}"
            )

            # Get player's index for potential teleport to deployment area
            current_player = self.game_state.get_current_player()
            if current_player:
                player_index = current_player.color.value

                # Trigger the mystery event (50/50 heal or teleport)
                mystery_result = MysterySquareSystem.trigger_mystery_event(
                    token, self.game_state.board, player_index
                )

                if mystery_result.effect.name == "HEAL":
                    logger.info(
                        f"🎲 HEADS! Token healed from {mystery_result.old_health} to {mystery_result.new_health} HP!"
                    )
                else:
                    # Token was teleported - update board occupancy
                    self.game_state.board.clear_occupant(target_cell, token.id)
                    self.game_state.board.set_occupant(
                        mystery_result.new_position, token.id
                    )
                    final_position = mystery_result.new_position
                    logger.info(
                        f"🎲 TAILS! Token teleported back to deployment area {final_position}!"
                    )

        # Update sprite position and health display
        for sprite in self.renderer_2d.token_sprites:
            if isinstance(sprite, TokenSprite) and sprite.token.id == token_id:
                # In network mode we want to show the move animation during prediction
                sprite.update_position(
                    final_position[0],
                    final_position[1],
                    instant=not animate,
                )
                sprite.update_health()  # Refresh health display (for mystery heal)
                break

        # Sync 3D token positions
        self.renderer_3d.sync_tokens(self.game_state, ctx)

        # Update UI to reflect state changes
        self.ui_manager.rebuild_visuals(self.game_state)

        return True, final_position

    def execute_attack(self, attacker_id: int, target_id: int) -> bool:
        """
        Execute an attack action.

        Args:
            attacker_id: ID of attacking token
            target_id: ID of target token

        Returns:
            True if attack was successful, False otherwise
        """
        attacker = self.game_state.get_token(attacker_id)
        target_token = self.game_state.get_token(target_id)

        if not attacker or not target_token:
            return False

        # Check if adjacent
        if not self.movement_system.is_adjacent(
            attacker.position, target_token.position
        ):
            logger.warning("Target is not adjacent")
            return False

        # Perform attack
        result = CombatSystem.resolve_combat(attacker, target_token)

        logger.debug(f"Token {attacker.id} attacked token {target_token.id}: {result}")

        # Update token sprite health or remove if killed
        for sprite in self.renderer_2d.token_sprites:
            if isinstance(sprite, TokenSprite) and sprite.token.id == target_id:
                if target_token.is_alive:
                    sprite.update_health()
                else:
                    # Play flushing sound when enemy token is defeated
                    self.audio_manager.play_flushing_sound()
                    logger.info(f"💀 Token {target_id} defeated! Playing flush sound")

                    self.renderer_2d.token_sprites.remove(sprite)
                    self.game_state.board.clear_occupant(
                        target_token.position, target_token.id
                    )
                    # Remove 3D token if exists
                    self.renderer_3d.remove_token(target_id)
                break

        # Update UI to reflect state changes
        self.ui_manager.rebuild_visuals(self.game_state)

        return True

    def execute_deployment(
        self, player_id: int, health: int, position: tuple[int, int], ctx
    ):
        """
        Execute a token deployment action.

        Args:
            player_id: ID of player deploying token
            health: Health value of token to deploy
            position: Position to deploy token
            ctx: OpenGL context for 3D token creation

        Returns:
            Deployed token object if successful, None otherwise
        """
        deployed_token = self.game_state.deploy_token(player_id, health, position)

        if not deployed_token:
            logger.warning(
                f"Cannot deploy to {position} - position occupied or invalid"
            )
            return None

        logger.info(f"Deployed {health}hp token to {position}")

        # Get player color
        player = self.game_state.players.get(player_id)
        if not player:
            return None

        player_color = PLAYER_COLORS[player.color.value]

        # Create 2D sprite for the deployed token
        sprite = TokenSprite(deployed_token, player_color)
        self.renderer_2d.token_sprites.append(sprite)

        # Create 3D token
        self.renderer_3d.add_token(deployed_token, player_color, ctx)

        # Update UI to reflect state changes
        self.ui_manager.rebuild_visuals(self.game_state)

        return deployed_token

    def execute_end_turn(
        self, mystery_animations: dict[tuple[int, int], float]
    ) -> None:
        """
        Execute end turn action.

        Args:
            mystery_animations: Dict for mystery square animations
        """
        current_player = self.game_state.get_current_player()
        if not current_player:
            return

        logger.info(f"Ending turn for {current_player.name}")

        # Update objectives and then advance the turn
        newly_disabled_generators, crystal_captured = (
            self.game_state.end_turn_with_objective_update()
        )

        # Play sound effects for newly captured generators
        if newly_disabled_generators:
            for gen_id in newly_disabled_generators:
                self.audio_manager.play_generator_explosion_sound()
                logger.info(f"💥 Generator {gen_id} captured! Playing explosion sound")

        # Play sound effect if crystal was captured
        if crystal_captured:
            self.audio_manager.play_crystal_shatter_sound()
            logger.info("🏆 Crystal captured! Playing shatter sound")

        next_player = self.game_state.get_current_player()
        if next_player:
            logger.info(
                f"Turn {self.game_state.turn_number}: {next_player.name}'s turn"
            )

        # Rebuild board shapes to update generator lines (when generators are captured)
        self.renderer_2d.create_board_sprites(
            self.game_state.board,
            self.game_state.generators,
            self.game_state.crystal,
            mystery_animations,
        )

        # Update 3D board generator lines
        self.renderer_3d.update_generator_lines()

        # Update UI to reflect new turn
        self.ui_manager.rebuild_visuals(self.game_state)

        # Update generator hums based on captured state
        self.audio_manager.update_generator_hums(self.game_state.generators)
