"""
Crystal effect animations for Race to the Crystal.

This module handles visual animations for crystal effects including fog,
ghosts, lightning, and whirlwinds.
"""

import math
import random
from typing import Optional

import arcade

from shared.constants import (
    CELL_SIZE,
    CRYSTAL_EFFECT_ANIMATION_DURATION,
    CRYSTAL_FOG_SPREAD_SPEED,
    CRYSTAL_GHOST_COUNT,
    CRYSTAL_LIGHTNING_FLASH_DURATION,
    CRYSTAL_WHIRLWIND_COUNT,
)
from shared.enums import CrystalEffect
from shared.logging_config import setup_logger

logger = setup_logger(__name__)


class CrystalEffectAnimator:
    """
    Manages visual animations for crystal effects.

    Handles animations for:
    - FOG_OF_WAR: Fog spreading from crystal
    - PHANTOM_ENEMIES: Ghostly particles spreading
    - DAMAGE_BOOST: Lightning strikes on tokens
    - SPEED_BOOST: Whirlwind particles spreading
    """

    def __init__(self):
        """Initialize the crystal effect animator."""
        self.active_animation: Optional[CrystalEffect] = None
        self.animation_time = 0.0
        self.crystal_position: Optional[tuple[int, int]] = None

        # Fog animation state
        self.fog_particles: list[dict] = []

        # Ghost animation state
        self.ghost_particles: list[dict] = []

        # Lightning animation state
        self.lightning_flashes: list[dict] = []
        self.affected_tokens: list = []

        # Whirlwind animation state
        self.whirlwind_particles: list[dict] = []

    def start_effect_animation(
        self,
        effect_type: CrystalEffect,
        crystal_pos: tuple[int, int],
        affected_tokens: list = None
    ) -> None:
        """
        Start a crystal effect animation.

        Args:
            effect_type: Type of crystal effect to animate
            crystal_pos: Position of the crystal (grid coordinates)
            affected_tokens: List of tokens affected (for DAMAGE_BOOST)
        """
        self.active_animation = effect_type
        self.animation_time = 0.0
        self.crystal_position = crystal_pos
        self.affected_tokens = affected_tokens or []

        # Initialize particles based on effect type
        if effect_type == CrystalEffect.FOG_OF_WAR:
            self._init_fog_particles()
        elif effect_type == CrystalEffect.PHANTOM_ENEMIES:
            self._init_ghost_particles()
        elif effect_type == CrystalEffect.DAMAGE_BOOST:
            self._init_lightning_flashes()
        elif effect_type == CrystalEffect.SPEED_BOOST:
            self._init_whirlwind_particles()

    def _init_fog_particles(self) -> None:
        """Initialize fog particles spreading from crystal."""
        if not self.crystal_position:
            return

        # Create fog particles in all directions
        self.fog_particles = []
        num_particles = 16

        for i in range(num_particles):
            angle = (i / num_particles) * 2 * math.pi
            self.fog_particles.append({
                'angle': angle,
                'distance': 0.0,
                'speed': CRYSTAL_FOG_SPREAD_SPEED + random.uniform(-20, 20),
                'size': random.uniform(30, 60),
                'alpha': 180,
            })

    def _init_ghost_particles(self) -> None:
        """Initialize ghost particles for phantom enemies effect."""
        if not self.crystal_position:
            return

        self.ghost_particles = []

        for _ in range(CRYSTAL_GHOST_COUNT):
            angle = random.uniform(0, 2 * math.pi)
            self.ghost_particles.append({
                'angle': angle,
                'distance': 0.0,
                'speed': random.uniform(80, 120),
                'wobble': random.uniform(0, 2 * math.pi),
                'wobble_speed': random.uniform(3, 6),
                'alpha': 200,
            })

    def _init_lightning_flashes(self) -> None:
        """Initialize lightning flashes for damage boost effect."""
        self.lightning_flashes = []

        for token in self.affected_tokens:
            self.lightning_flashes.append({
                'token': token,
                'flash_time': 0.0,
                'num_flashes': random.randint(2, 4),
                'current_flash': 0,
            })

    def _init_whirlwind_particles(self) -> None:
        """Initialize whirlwind particles for speed boost effect."""
        if not self.crystal_position:
            return

        self.whirlwind_particles = []

        for _ in range(CRYSTAL_WHIRLWIND_COUNT):
            angle = random.uniform(0, 2 * math.pi)
            self.whirlwind_particles.append({
                'angle': angle,
                'distance': 0.0,
                'speed': random.uniform(100, 150),
                'rotation': random.uniform(0, 2 * math.pi),
                'rotation_speed': random.uniform(5, 10),
                'spiral_rate': random.uniform(0.5, 1.5),
                'alpha': 220,
            })

    def update(self, delta_time: float) -> None:
        """
        Update animation state.

        Args:
            delta_time: Time since last update in seconds
        """
        if not self.active_animation:
            return

        self.animation_time += delta_time

        # End animation after duration
        if self.animation_time >= CRYSTAL_EFFECT_ANIMATION_DURATION:
            self.active_animation = None
            self.fog_particles.clear()
            self.ghost_particles.clear()
            self.lightning_flashes.clear()
            self.whirlwind_particles.clear()
            return

        # Update particles based on effect type
        if self.active_animation == CrystalEffect.FOG_OF_WAR:
            self._update_fog_particles(delta_time)
        elif self.active_animation == CrystalEffect.PHANTOM_ENEMIES:
            self._update_ghost_particles(delta_time)
        elif self.active_animation == CrystalEffect.DAMAGE_BOOST:
            self._update_lightning_flashes(delta_time)
        elif self.active_animation == CrystalEffect.SPEED_BOOST:
            self._update_whirlwind_particles(delta_time)

    def _update_fog_particles(self, delta_time: float) -> None:
        """Update fog particle positions and alpha."""
        for particle in self.fog_particles:
            particle['distance'] += particle['speed'] * delta_time
            # Fade out fog near the end
            fade_progress = self.animation_time / CRYSTAL_EFFECT_ANIMATION_DURATION
            particle['alpha'] = int(180 * (1.0 - fade_progress))

    def _update_ghost_particles(self, delta_time: float) -> None:
        """Update ghost particle positions with wobble effect."""
        for particle in self.ghost_particles:
            particle['distance'] += particle['speed'] * delta_time
            particle['wobble'] += particle['wobble_speed'] * delta_time
            # Fade out ghosts near the end
            fade_progress = self.animation_time / CRYSTAL_EFFECT_ANIMATION_DURATION
            particle['alpha'] = int(200 * (1.0 - fade_progress))

    def _update_lightning_flashes(self, delta_time: float) -> None:
        """Update lightning flash timing."""
        for flash in self.lightning_flashes:
            flash['flash_time'] += delta_time

            # Check if it's time for next flash
            flash_interval = CRYSTAL_EFFECT_ANIMATION_DURATION / flash['num_flashes']
            if flash['flash_time'] >= flash_interval and flash['current_flash'] < flash['num_flashes']:
                flash['current_flash'] += 1
                flash['flash_time'] = 0.0

    def _update_whirlwind_particles(self, delta_time: float) -> None:
        """Update whirlwind particle positions with spiral effect."""
        for particle in self.whirlwind_particles:
            particle['distance'] += particle['speed'] * delta_time
            particle['rotation'] += particle['rotation_speed'] * delta_time
            particle['angle'] += particle['spiral_rate'] * delta_time
            # Fade out whirlwinds near the end
            fade_progress = self.animation_time / CRYSTAL_EFFECT_ANIMATION_DURATION
            particle['alpha'] = int(220 * (1.0 - fade_progress))

    def draw(self, crystal_screen_x: float, crystal_screen_y: float) -> None:
        """
        Draw the active crystal effect animation.

        Args:
            crystal_screen_x: Crystal X position in screen coordinates
            crystal_screen_y: Crystal Y position in screen coordinates
        """
        if not self.active_animation:
            return

        if self.active_animation == CrystalEffect.FOG_OF_WAR:
            self._draw_fog_effect(crystal_screen_x, crystal_screen_y)
        elif self.active_animation == CrystalEffect.PHANTOM_ENEMIES:
            self._draw_ghost_effect(crystal_screen_x, crystal_screen_y)
        elif self.active_animation == CrystalEffect.DAMAGE_BOOST:
            self._draw_lightning_effect()
        elif self.active_animation == CrystalEffect.SPEED_BOOST:
            self._draw_whirlwind_effect(crystal_screen_x, crystal_screen_y)

    def _draw_fog_effect(self, center_x: float, center_y: float) -> None:
        """Draw fog particles spreading from crystal."""
        for particle in self.fog_particles:
            # Calculate particle position
            x = center_x + math.cos(particle['angle']) * particle['distance']
            y = center_y + math.sin(particle['angle']) * particle['distance']

            # Draw fog as semi-transparent gray circles
            color = (200, 200, 220, particle['alpha'])
            arcade.draw_circle_filled(x, y, particle['size'], color)

    def _draw_ghost_effect(self, center_x: float, center_y: float) -> None:
        """Draw ghost particles with wobble effect."""
        for particle in self.ghost_particles:
            # Add wobble to position
            wobble_offset = math.sin(particle['wobble']) * 20
            x = center_x + math.cos(particle['angle']) * particle['distance'] + wobble_offset
            y = center_y + math.sin(particle['angle']) * particle['distance']

            # Draw ghost as semi-transparent white/cyan shapes
            color = (150, 255, 255, particle['alpha'])
            arcade.draw_circle_filled(x, y, 15, color)
            # Add eyes
            arcade.draw_circle_filled(x - 5, y + 3, 3, (0, 0, 0, particle['alpha']))
            arcade.draw_circle_filled(x + 5, y + 3, 3, (0, 0, 0, particle['alpha']))

    def _draw_lightning_effect(self) -> None:
        """Draw lightning flashes on affected tokens."""
        for flash in self.lightning_flashes:
            # Only draw during flash window
            if flash['flash_time'] < CRYSTAL_LIGHTNING_FLASH_DURATION:
                token = flash['token']
                if hasattr(token, 'position'):
                    # Convert grid position to screen position
                    screen_x = token.position[0] * CELL_SIZE + CELL_SIZE / 2
                    screen_y = token.position[1] * CELL_SIZE + CELL_SIZE / 2

                    # Draw yellow/white lightning flash
                    flash_alpha = int(255 * (1.0 - flash['flash_time'] / CRYSTAL_LIGHTNING_FLASH_DURATION))
                    color = (255, 255, 100, flash_alpha)
                    arcade.draw_circle_filled(screen_x, screen_y, CELL_SIZE, color)

                    # Draw lightning bolts
                    for i in range(6):
                        angle = (i / 6) * 2 * math.pi
                        end_x = screen_x + math.cos(angle) * CELL_SIZE * 1.5
                        end_y = screen_y + math.sin(angle) * CELL_SIZE * 1.5
                        arcade.draw_line(screen_x, screen_y, end_x, end_y, (255, 255, 200, flash_alpha), 2)

    def _draw_whirlwind_effect(self, center_x: float, center_y: float) -> None:
        """Draw whirlwind particles with spiral motion."""
        for particle in self.whirlwind_particles:
            # Calculate particle position with spiral
            x = center_x + math.cos(particle['angle']) * particle['distance']
            y = center_y + math.sin(particle['angle']) * particle['distance']

            # Draw whirlwind as rotating lines
            color = (100, 255, 255, particle['alpha'])

            # Draw spinning lines to create whirlwind effect
            for i in range(3):
                line_angle = particle['rotation'] + (i / 3) * 2 * math.pi
                start_x = x + math.cos(line_angle) * 5
                start_y = y + math.sin(line_angle) * 5
                end_x = x + math.cos(line_angle) * 25
                end_y = y + math.sin(line_angle) * 25
                arcade.draw_line(start_x, start_y, end_x, end_y, color, 2)

    def is_animating(self) -> bool:
        """Check if an animation is currently active."""
        return self.active_animation is not None
