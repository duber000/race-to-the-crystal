"""
Audio management for Race to the Crystal.

This module handles all audio functionality including background music,
generator hum tracks, and game sound effects.
"""

import os

import arcade

from client.music_generator import generate_techno_music
from shared.constants import (
    BACKGROUND_MUSIC_VOLUME,
    GENERATOR_HUM_VOLUME,
    SOUND_EFFECTS_VOLUME,
)
from shared.logging_config import setup_logger

logger = setup_logger(__name__)


class AudioManager:
    """
    Manages all audio for the game including background music, generator hums, and sound effects.

    The AudioManager handles:
    - Loading and playing background music (with fallback generation)
    - Managing 4 separate generator hum tracks that can be individually controlled
    - Loading and playing game sound effects (movement, mystery squares, explosions, etc.)
    - Toggling music on/off
    - Updating generator hums based on game state
    - Pausing and cleaning up audio resources
    """

    def __init__(self):
        """Initialize audio manager."""
        # Background music
        self.background_music: arcade.Sound | None = None
        self.music_player: object | None = None
        self.music_volume = BACKGROUND_MUSIC_VOLUME
        self.music_playing = True

        # Generator hum tracks (separate audio for each generator)
        self.generator_hums: list = []  # List of Sound objects
        self.generator_hum_players: list = []  # List of MediaPlayer objects
        self.generator_hum_volume = GENERATOR_HUM_VOLUME

        # Sound effects
        self.sound_effects_volume = SOUND_EFFECTS_VOLUME
        self.sound_effects: dict = {}
        self.sound_effect_players: list = []  # Keep references to playing sound effects
        self._load_sound_effects()

    def load_background_music(self) -> None:
        """
        Load and play background techno music with separate generator hums.

        Tries to load music in this order:
        1. MP3 file (client/assets/music/techno.mp3)
        2. WAV file (client/assets/music/techno.wav)
        3. Generate WAV file if neither exists

        Also loads and starts the 4 generator hum tracks.
        """
        music_path = "client/assets/music/techno.mp3"
        wav_path = "client/assets/music/techno.wav"

        try:
            # Try MP3 first
            self.background_music = arcade.Sound(music_path, streaming=True)
            if self.background_music:
                self.music_player = self.background_music.play(
                    self.music_volume, loop=True
                )
                logger.info("Background music loaded and playing (looping)")
        except FileNotFoundError:
            # Try WAV format
            try:
                self.background_music = arcade.Sound(wav_path, streaming=True)
                if self.background_music:
                    self.music_player = self.background_music.play(
                        self.music_volume, loop=True
                    )
                    logger.info("Background music loaded and playing (looping)")
            except FileNotFoundError:
                # Generate music if neither file exists
                logger.warning("No music file found, generating techno track...")
                try:
                    generate_techno_music(duration=30.0)
                    self.background_music = arcade.Sound(wav_path, streaming=True)
                    if self.background_music:
                        self.music_player = self.background_music.play(
                            self.music_volume, loop=True
                        )
                        logger.info("Generated background music playing (looping)")
                except FileNotFoundError as e:
                    logger.warning(f"Generated music file not found: {e}")
                except OSError as e:
                    logger.error(f"OS error generating music: {e}")
                except Exception as e:
                    logger.error(
                        f"Unexpected error generating music: {e}", exc_info=True
                    )
        except FileNotFoundError as e:
            logger.warning(f"Music file not found: {e}")
        except OSError as e:
            logger.error(f"OS error loading music: {e}")
        except Exception as e:
            logger.error(f"Unexpected error loading music: {e}", exc_info=True)

        # Load and play generator hum tracks
        self._load_generator_hums()

    def _load_sound_effects(self) -> None:
        """Load all sound effects."""
        sound_effects_dir = "client/assets/sounds"

        # Define sound effects to load
        sound_effects = {
            "sliding": f"{sound_effects_dir}/sliding.wav",
            "mystery_bing": f"{sound_effects_dir}/mystery_bing.wav",
            "generator_explosion": f"{sound_effects_dir}/generator_explosion.wav",
            "crystal_shatter": f"{sound_effects_dir}/crystal_shatter.wav",
            "flushing": f"{sound_effects_dir}/flushing.wav",
            # Crystal effect sounds
            "fog_horn": f"{sound_effects_dir}/fog_horn.wav",
            "ghost": f"{sound_effects_dir}/ghost.wav",
            "lightning": f"{sound_effects_dir}/lightning.wav",
            "whoosh": f"{sound_effects_dir}/whoosh.wav",
        }

        for name, path in sound_effects.items():
            try:
                if os.path.exists(path):
                    sound = arcade.Sound(path)
                    self.sound_effects[name] = sound
                    logger.info(f"✓ Loaded sound effect: {name}")
                else:
                    logger.warning(f"Sound effect file not found: {path}")
                    self.sound_effects[name] = None
            except FileNotFoundError as e:
                logger.warning(f"Sound effect file not found: {path}: {e}")
            except OSError as e:
                logger.error(f"OS error loading sound effect: {e}")
            except Exception as e:
                logger.error(
                    f"Unexpected error loading sound effect: {e}", exc_info=True
                )
                self.sound_effects[name] = None

    def _load_generator_hums(self) -> None:
        """Load and play the 4 generator hum tracks that can be individually controlled."""
        for gen_id in range(4):
            hum_path = f"client/assets/music/generator_{gen_id}_hum.wav"

            # Check if file exists
            if not os.path.exists(hum_path):
                logger.error(f"Generator {gen_id} hum file not found: {hum_path}")
                self.generator_hums.append(None)
                self.generator_hum_players.append(None)
                continue

            try:
                logger.debug(f"Loading generator {gen_id} hum from: {hum_path}")
                hum_sound = arcade.Sound(hum_path, streaming=True)
                logger.debug(f"  Sound object created: {hum_sound}")

                hum_player = hum_sound.play(self.generator_hum_volume, loop=True)
                logger.debug(f"  Player created: {hum_player}")

                if hum_player is None:
                    logger.warning(f"  Player is None for generator {gen_id}!")

                self.generator_hums.append(hum_sound)
                self.generator_hum_players.append(hum_player)
                logger.info(f"✓ Generator {gen_id} hum loaded and playing")
            except FileNotFoundError as e:
                logger.error(f"Generator hum file not found: {e}")
            except OSError as e:
                logger.error(f"OS error loading generator hum: {e}")
            except Exception as e:
                logger.error(
                    f"Unexpected error loading generator hum: {e}", exc_info=True
                )
                import traceback

                traceback.print_exc()
                self.generator_hums.append(None)
                self.generator_hum_players.append(None)

    def toggle_music(self) -> None:
        """
        Toggle background music and generator hums on/off.

        When pausing, all audio is paused.
        When resuming, background music restarts and generator hums are updated
        based on current game state (via update_generator_hums).
        """
        if not self.background_music:
            # If music isn't loaded yet, interpret toggle as enable → load, disable → just flip flag
            if self.music_playing:
                self.music_playing = False
                logger.info("Music paused (not loaded)")
                return

            self.load_background_music()
            self.music_playing = bool(
                self.music_player or any(self.generator_hum_players)
            )
            if self.music_playing:
                logger.info("Music playing")
            return

        if self.music_playing:
            if self.music_player:
                self.music_player.pause()  # type: ignore
            # Pause all generator hums
            for player in self.generator_hum_players:
                if player:
                    player.pause()  # type: ignore
            self.music_playing = False
            logger.info("Music paused")
        else:
            # Restart the music with looping
            self.music_player = self.background_music.play(self.music_volume, loop=True)
            # Generator hums will be restarted via update_generator_hums()
            # (caller should call update_generator_hums after this)
            self.music_playing = True
            logger.info("Music playing")

    def update_generator_hums(self, generators: list) -> None:
        """
        Update generator hum audio based on which generators are captured.

        Args:
            generators: List of Generator objects from game state

        Generator hums are:
        - Stopped when a generator is disabled (fully captured)
        - Restarted when a generator becomes active again
        - Playing continuously when a generator is active
        """
        if not self.music_playing:
            return

        logger.debug("\n=== Updating Generator Hums ===")
        active_hums = 0
        for gen_id, generator in enumerate(generators):
            logger.debug(
                f"Generator {gen_id}: is_disabled={generator.is_disabled}, "
                f"turns_held={generator.turns_held}, capturing_player={generator.capturing_player_id}"
            )

            if gen_id < len(self.generator_hum_players):
                player = self.generator_hum_players[gen_id]
                hum_sound = self.generator_hums[gen_id]

                if player is not None:
                    active_hums += 1
                logger.debug(f"  player={player}, hum_sound={hum_sound}")

                if player and hum_sound:
                    # Check if generator is disabled (fully captured)
                    if generator.is_disabled:
                        # Generator is captured - stop this hum completely
                        try:
                            player.pause()
                            player.delete()
                            self.generator_hum_players[gen_id] = None
                            logger.debug(f"  Generator {gen_id} DISABLED - HUM STOPPED")
                        except AttributeError as e:
                            logger.debug(f"Player already None: {e}")
                        except OSError as e:
                            logger.error(f"OS error stopping hum: {e}")
                        except Exception as e:
                            logger.error(
                                f"Unexpected error managing hum: {e}", exc_info=True
                            )
                    else:
                        logger.debug(f"  Generator {gen_id} active - hum playing")
                elif (
                    not generator.is_disabled
                    and hum_sound
                    and self.generator_hum_players[gen_id] is None
                ):
                    # Generator is free and hum was stopped - restart it
                    try:
                        self.generator_hum_players[gen_id] = hum_sound.play(
                            self.generator_hum_volume, loop=True
                        )
                        logger.debug(f"  Generator {gen_id} freed - HUM RESTARTED")
                    except AttributeError as e:
                        logger.debug(f"Hum sound not loaded: {e}")
                    except OSError as e:
                        logger.error(f"OS error restarting hum: {e}")
                    except Exception as e:
                        logger.error(
                            f"Unexpected error managing hum: {e}", exc_info=True
                        )
                elif generator.is_disabled and hum_sound:
                    # Player is None but generator is disabled (already stopped)
                    logger.debug(
                        f"  Generator {gen_id} disabled but player is None (already stopped)"
                    )
                else:
                    logger.debug(
                        f"  Generator {gen_id} - player or hum_sound is None, skipping"
                    )
        logger.debug(f"=== Active Generator Hums: {active_hums}/4 ===\n")

    def play_sliding_sound(self) -> None:
        """Play the sliding sound effect for token movement."""
        if "sliding" in self.sound_effects and self.sound_effects["sliding"]:
            try:
                player = self.sound_effects["sliding"].play(self.sound_effects_volume)
                # Keep a reference to prevent garbage collection
                if player:
                    self.sound_effect_players.append(player)
                    if len(self.sound_effect_players) > 20:
                        self.sound_effect_players.pop(0)
                logger.debug("Playing sliding sound effect")
            except AttributeError as e:
                logger.debug(f"Sound effect not loaded: {e}")
            except OSError as e:
                logger.error(f"OS error playing sound: {e}")
            except Exception as e:
                logger.error(f"Unexpected error playing sound: {e}", exc_info=True)

    def play_mystery_bing_sound(self) -> None:
        """Play the mystery bing sound effect for landing on mystery squares."""
        if "mystery_bing" in self.sound_effects and self.sound_effects["mystery_bing"]:
            try:
                player = self.sound_effects["mystery_bing"].play(
                    self.sound_effects_volume
                )
                # Keep a reference to prevent garbage collection
                if player:
                    self.sound_effect_players.append(player)
                    if len(self.sound_effect_players) > 20:
                        self.sound_effect_players.pop(0)
                logger.debug("Playing mystery bing sound effect")
            except AttributeError as e:
                logger.debug(f"Sound effect not loaded: {e}")
            except OSError as e:
                logger.error(f"OS error playing sound: {e}")
            except Exception as e:
                logger.error(f"Unexpected error playing sound: {e}", exc_info=True)

    def play_generator_explosion_sound(self) -> None:
        """Play the generator explosion sound effect for capturing generators."""
        if (
            "generator_explosion" in self.sound_effects
            and self.sound_effects["generator_explosion"]
        ):
            try:
                player = self.sound_effects["generator_explosion"].play(
                    self.sound_effects_volume
                )
                # Keep a reference to prevent garbage collection
                if player:
                    self.sound_effect_players.append(player)
                    # Clean up old players to prevent memory leak
                    if len(self.sound_effect_players) > 20:
                        self.sound_effect_players.pop(0)
                logger.debug("Playing generator explosion sound effect")
            except AttributeError as e:
                logger.debug(f"Sound effect not loaded: {e}")
            except OSError as e:
                logger.error(f"OS error playing sound: {e}")
            except Exception as e:
                logger.error(f"Unexpected error playing sound: {e}", exc_info=True)

    def play_crystal_shatter_sound(self) -> None:
        """Play the crystal shatter sound effect for capturing the crystal."""
        if (
            "crystal_shatter" in self.sound_effects
            and self.sound_effects["crystal_shatter"]
        ):
            try:
                player = self.sound_effects["crystal_shatter"].play(
                    self.sound_effects_volume
                )
                # Keep a reference to prevent garbage collection
                if player:
                    self.sound_effect_players.append(player)
                    if len(self.sound_effect_players) > 20:
                        self.sound_effect_players.pop(0)
                logger.debug("Playing crystal shatter sound effect")
            except AttributeError as e:
                logger.debug(f"Sound effect not loaded: {e}")
            except OSError as e:
                logger.error(f"OS error playing sound: {e}")
            except Exception as e:
                logger.error(f"Unexpected error playing sound: {e}", exc_info=True)

    def play_flushing_sound(self) -> None:
        """Play the flushing sound effect for defeating enemy tokens."""
        if "flushing" in self.sound_effects and self.sound_effects["flushing"]:
            try:
                player = self.sound_effects["flushing"].play(self.sound_effects_volume)
                # Keep a reference to prevent garbage collection
                if player:
                    self.sound_effect_players.append(player)
                    if len(self.sound_effect_players) > 20:
                        self.sound_effect_players.pop(0)
                logger.debug("Playing flushing sound effect")
            except AttributeError as e:
                logger.debug(f"Sound effect not loaded: {e}")
            except OSError as e:
                logger.error(f"OS error playing sound: {e}")
            except Exception as e:
                logger.error(f"Unexpected error playing sound: {e}", exc_info=True)

    def pause_all(self) -> None:
        """
        Pause all audio (called when view is hidden).

        Pauses background music and all generator hums without changing
        the music_playing state.
        """
        # Pause music
        if self.music_player and self.music_playing:
            self.music_player.pause()  # type: ignore

        # Pause all generator hums
        for player in self.generator_hum_players:
            if player:
                player.pause()  # type: ignore

    def cleanup(self) -> None:
        """
        Clean up audio resources.

        Stops and deletes all audio players and clears references.
        """
        # Stop background music
        if self.music_player:
            self.music_player.pause()  # type: ignore
            self.music_player.delete()  # type: ignore
            self.music_player = None

        # Stop and delete all generator hum players
        for player in self.generator_hum_players:
            if player:
                player.pause()  # type: ignore
                player.delete()  # type: ignore
        self.generator_hum_players.clear()
        self.generator_hums.clear()

        # Stop and delete all sound effect players
        for player in self.sound_effect_players:
            if player:
                try:
                    player.pause()
                    player.delete()
                except AttributeError as e:
                    logger.debug(f"Player already None: {e}")
                except OSError as e:
                    logger.error(f"OS error in sound operation: {e}")
                except Exception as e:
                    logger.error(
                        f"Unexpected error in sound operation: {e}", exc_info=True
                    )
        self.sound_effect_players.clear()

        # Clear sound effects
        self.sound_effects.clear()

        self.background_music = None

    def play_fog_horn_sound(self) -> None:
        """Play the fog horn sound effect for FOG_OF_WAR crystal effect."""
        if "fog_horn" in self.sound_effects and self.sound_effects["fog_horn"]:
            try:
                player = self.sound_effects["fog_horn"].play(self.sound_effects_volume)
                if player:
                    self.sound_effect_players.append(player)
                    if len(self.sound_effect_players) > 20:
                        self.sound_effect_players.pop(0)
                logger.debug("Playing fog horn sound effect")
            except AttributeError as e:
                logger.debug(f"Sound effect not loaded: {e}")
            except OSError as e:
                logger.error(f"OS error playing sound: {e}")
            except Exception as e:
                logger.error(f"Unexpected error playing sound: {e}", exc_info=True)

    def play_ghost_sound(self) -> None:
        """Play the ghost sound effect for PHANTOM_ENEMIES crystal effect."""
        if "ghost" in self.sound_effects and self.sound_effects["ghost"]:
            try:
                player = self.sound_effects["ghost"].play(self.sound_effects_volume)
                if player:
                    self.sound_effect_players.append(player)
                    if len(self.sound_effect_players) > 20:
                        self.sound_effect_players.pop(0)
                logger.debug("Playing ghost sound effect")
            except AttributeError as e:
                logger.debug(f"Sound effect not loaded: {e}")
            except OSError as e:
                logger.error(f"OS error playing sound: {e}")
            except Exception as e:
                logger.error(f"Unexpected error playing sound: {e}", exc_info=True)

    def play_lightning_sound(self) -> None:
        """Play the lightning sound effect for DAMAGE_BOOST crystal effect."""
        if "lightning" in self.sound_effects and self.sound_effects["lightning"]:
            try:
                player = self.sound_effects["lightning"].play(self.sound_effects_volume)
                if player:
                    self.sound_effect_players.append(player)
                    if len(self.sound_effect_players) > 20:
                        self.sound_effect_players.pop(0)
                logger.debug("Playing lightning sound effect")
            except AttributeError as e:
                logger.debug(f"Sound effect not loaded: {e}")
            except OSError as e:
                logger.error(f"OS error playing sound: {e}")
            except Exception as e:
                logger.error(f"Unexpected error playing sound: {e}", exc_info=True)

    def play_whoosh_sound(self) -> None:
        """Play the whoosh sound effect for SPEED_BOOST crystal effect."""
        if "whoosh" in self.sound_effects and self.sound_effects["whoosh"]:
            try:
                player = self.sound_effects["whoosh"].play(self.sound_effects_volume)
                if player:
                    self.sound_effect_players.append(player)
                    if len(self.sound_effect_players) > 20:
                        self.sound_effect_players.pop(0)
                logger.debug("Playing whoosh sound effect")
            except AttributeError as e:
                logger.debug(f"Sound effect not loaded: {e}")
            except OSError as e:
                logger.error(f"OS error playing sound: {e}")
            except Exception as e:
                logger.error(f"Unexpected error playing sound: {e}", exc_info=True)
