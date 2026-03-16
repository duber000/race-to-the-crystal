"""
AI Client Spawning Utility for Race to the Crystal Server.

Handles spawning AI client processes to fill empty player slots.
"""

import asyncio
import logging
from typing import List, Optional
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class SpawnedAI:
    """Information about a spawned AI client process."""

    process: asyncio.subprocess.Process
    player_name: str
    strategy: str
    game_id: str


class AISpawner:
    """
    Manages spawning and lifecycle of server-side AI clients.

    Spawns AI client processes that connect back to the server
    and join games automatically.
    """

    def __init__(self):
        """Initialize the AI spawner."""
        self.spawned_processes: List[SpawnedAI] = []
        self.ai_counter = 0
        self.strategies = ["random", "aggressive", "defensive"]
        logger.info("AI Spawner initialized")

    async def spawn_ai_for_game(
        self,
        game_id: str,
        num_ai: int,
        host: str = "localhost",
        port: int = 8888,
        strategies: Optional[List[str]] = None,
    ) -> List[SpawnedAI]:
        """
        Spawn AI clients to join a specific game.

        Args:
            game_id: Game ID to join
            num_ai: Number of AI players to spawn
            host: Server host address
            port: Server port
            strategies: Optional list of strategies to use (cycles if fewer than num_ai)

        Returns:
            List of SpawnedAI objects for the spawned processes
        """
        if num_ai <= 0:
            return []

        if strategies is None:
            strategies = self.strategies

        spawned = []

        for i in range(num_ai):
            # Generate AI name
            self.ai_counter += 1
            ai_name = f"AI_Player_{self.ai_counter}"

            # Rotate through strategies
            strategy = strategies[i % len(strategies)]

            # Spawn AI client process
            try:
                process = await self._spawn_ai_process(
                    ai_name=ai_name,
                    game_id=game_id,
                    host=host,
                    port=port,
                    strategy=strategy,
                )

                if process:
                    # Check if process is still running after a brief moment
                    await asyncio.sleep(0.1)
                    if process.returncode is not None:
                        logger.error(
                            f"AI player {ai_name} process exited immediately with code {process.returncode}"
                        )
                        continue

                    spawned_ai = SpawnedAI(
                        process=process,
                        player_name=ai_name,
                        strategy=strategy,
                        game_id=game_id,
                    )
                    spawned.append(spawned_ai)
                    self.spawned_processes.append(spawned_ai)
                    logger.info(
                        f"Spawned AI player {ai_name} ({strategy}) for game {game_id[:8]}"
                    )
                else:
                    logger.error(f"Failed to spawn AI player {ai_name}")

            except asyncio.TimeoutError as e:
                logger.error(f"Timeout spawning AI player {ai_name}: {e}")
            except PermissionError as e:
                logger.error(f"Permission denied spawning AI player {ai_name}: {e}")
            except FileNotFoundError as e:
                logger.error(f"AI client executable not found: {e}")
            except Exception as e:
                logger.error(
                    f"Unexpected error spawning AI player {ai_name}: {e}", exc_info=True
                )

        if spawned:
            logger.info(
                f"Successfully spawned {len(spawned)}/{num_ai} AI players for game {game_id[:8]}"
            )
        else:
            logger.warning(f"Failed to spawn any AI players for game {game_id[:8]}")

        return spawned

    async def _spawn_ai_process(
        self, ai_name: str, game_id: str, host: str, port: int, strategy: str
    ) -> Optional[asyncio.subprocess.Process]:
        """
        Spawn a single AI client process.

        Args:
            ai_name: Name for the AI player
            game_id: Game to join
            host: Server host
            port: Server port
            strategy: AI strategy

        Returns:
            Process object or None if spawn failed
        """
        # Validate inputs for security (defense in depth)
        try:
            # Import validation functions
            from server.lobby import validate_player_name

            # Validate AI name
            validate_player_name(ai_name)

            # Validate game_id (should be UUID format)
            if not isinstance(game_id, str) or len(game_id) > 50:
                raise ValueError(
                    f"Invalid game_id length: {len(game_id) if game_id else 0}"
                )

            # Additional security checks for command arguments
            if any(
                char in ai_name for char in [";", "&", "|", "$", ">", "<", "`", "\\"]
            ):
                raise ValueError(f"AI name contains unsafe characters: {ai_name}")

            if any(
                char in game_id for char in [";", "&", "|", "$", ">", "<", "`", "\\"]
            ):
                raise ValueError(f"Game ID contains unsafe characters: {game_id}")

        except ValueError as e:
            logger.error(f"Security validation failed for AI spawn: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected validation error in AI spawn: {e}", exc_info=True)
            return None

        # Build command to spawn AI client
        # Use uv run to execute the AI client
        cmd = [
            "uv",
            "run",
            "race-ai-client",
            "--join",
            str(game_id),  # Ensure string type
            "--name",
            str(ai_name),  # Ensure string type
            "--host",
            str(host),
            "--port",
            str(port),
            "--strategy",
            strategy,
        ]

        try:
            # Spawn process with stdout/stderr redirected to avoid blocking
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
            )

            logger.debug(f"Spawned AI process with PID {process.pid}: {' '.join(cmd)}")

            # Start background task to log output
            asyncio.create_task(self._log_process_output(process, ai_name))

            return process

        except FileNotFoundError as e:
            logger.error(f"AI client executable not found: {e}")
            return None
        except PermissionError as e:
            logger.error(f"Permission denied executing AI client: {e}")
            return None
        except OSError as e:
            logger.error(f"OS error spawning AI process: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error spawning AI process: {e}", exc_info=True)
            return None

    async def _log_process_output(
        self, process: asyncio.subprocess.Process, ai_name: str
    ) -> None:
        """
        Log output from AI process.

        Args:
            process: AI process
            ai_name: Name of AI player
        """
        try:
            # Read stdout and stderr concurrently
            async def read_stdout():
                while True:
                    try:
                        line = await process.stdout.readline()
                        if not line:
                            break
                        logger.info(f"[{ai_name} OUT] {line.decode().strip()}")
                    except asyncio.CancelledError:
                        logger.debug(f"Output reader cancelled for {ai_name}")
                        break
                    except ConnectionError as e:
                        logger.debug(
                            f"Connection lost reading output from {ai_name}: {e}"
                        )
                        break
                    except Exception as e:
                        logger.debug(
                            f"Unexpected error reading output from {ai_name}: {e}"
                        )
                        break

            async def read_stderr():
                while True:
                    try:
                        line = await process.stderr.readline()
                        if not line:
                            break
                        logger.error(f"[{ai_name} ERR] {line.decode().strip()}")
                    except asyncio.CancelledError:
                        logger.debug(f"Output reader cancelled for {ai_name}")
                        break
                    except ConnectionError as e:
                        logger.debug(
                            f"Connection lost reading output from {ai_name}: {e}"
                        )
                        break
                    except Exception as e:
                        logger.debug(
                            f"Unexpected error reading output from {ai_name}: {e}"
                        )
                        break

            # Run both readers concurrently
            await asyncio.gather(read_stdout(), read_stderr(), return_exceptions=True)

            # Wait for process to complete and log exit code
            await process.wait()
            if process.returncode != 0:
                logger.error(
                    f"AI process {ai_name} exited with code {process.returncode}"
                )
            else:
                logger.info(f"AI process {ai_name} exited normally")

        except asyncio.CancelledError:
            logger.info(f"Output reader cancelled for {ai_name}")
        except asyncio.TimeoutError as e:
            logger.warning(f"Timeout reading output from {ai_name}: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error reading output from {ai_name}: {e}", exc_info=True
            )

    async def cleanup_ai_for_game(self, game_id: str) -> None:
        """
        Terminate AI processes for a finished game.

        Args:
            game_id: Game ID
        """
        to_remove = []

        for spawned_ai in self.spawned_processes:
            if spawned_ai.game_id == game_id:
                logger.info(
                    f"Terminating AI player {spawned_ai.player_name} for game {game_id[:8]}"
                )

                # Try graceful termination first
                try:
                    spawned_ai.process.terminate()

                    # Wait for termination with timeout
                    try:
                        await asyncio.wait_for(spawned_ai.process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        # Force kill if graceful termination failed
                        logger.warning(
                            f"AI player {spawned_ai.player_name} did not terminate, killing"
                        )
                        spawned_ai.process.kill()
                        await spawned_ai.process.wait()

                except ProcessLookupError as e:
                    logger.warning(
                        f"AI process already terminated: {spawned_ai.player_name}: {e}"
                    )
                except PermissionError as e:
                    logger.error(
                        f"Permission denied terminating AI: {spawned_ai.player_name}: {e}"
                    )
                except OSError as e:
                    logger.error(
                        f"OS error terminating AI: {spawned_ai.player_name}: {e}"
                    )
                except Exception as e:
                    logger.error(f"Unexpected error terminating AI: {e}", exc_info=True)

                to_remove.append(spawned_ai)

        # Remove from tracking list
        for spawned_ai in to_remove:
            self.spawned_processes.remove(spawned_ai)

        if to_remove:
            logger.info(
                f"Cleaned up {len(to_remove)} AI players for game {game_id[:8]}"
            )

    async def cleanup_all(self) -> None:
        """Terminate all spawned AI processes."""
        logger.info(f"Cleaning up {len(self.spawned_processes)} AI processes")

        for spawned_ai in self.spawned_processes[:]:
            try:
                spawned_ai.process.terminate()
                await asyncio.wait_for(spawned_ai.process.wait(), timeout=2.0)
            except ProcessLookupError as e:
                logger.warning(f"AI process already terminated: {e}")
            except PermissionError as e:
                logger.error(f"Permission denied terminating AI: {e}")
            except OSError as e:
                logger.error(f"OS error terminating AI: {e}")
            except Exception as e:
                logger.error(f"Unexpected error terminating AI: {e}", exc_info=True)
                try:
                    spawned_ai.process.kill()
                except (ProcessLookupError, PermissionError, OSError) as e:
                    logger.error(f"Failed to kill AI process: {e}")
                except Exception as e:
                    logger.error(
                        f"Unexpected error killing AI process: {e}", exc_info=True
                    )

        self.spawned_processes.clear()
        logger.info("All AI processes cleaned up")
