/**
 * webgl2_crystal_effects.js - Crystal effect visuals for the vanilla renderer
 *
 * WebGL2 port of game_client.crystal_effects.js (the Babylon animator).
 * Same public interface as the Babylon class so the renderer drives it
 * unchanged: startEffect() on trigger, update() every frame, cleanup() on
 * completion. Visuals are built from the renderer's existing primitives:
 *
 *  FOG_OF_WAR      - 16 soft smoke billboards spreading radially from the
 *                    crystal point of origin, growing and fading.
 *  PHANTOM_ENEMIES - GHOST_COUNT cyan billboards wobbling outward from the
 *                    crystal; bright enough to catch the bloom knee.
 *  DAMAGE_BOOST    - A jagged lightning bolt from the sky to each affected
 *                    token plus an additive flash sphere and spark burst,
 *                    LIGHTNING_FLASH_DURATION per strike.
 *  SPEED_BOOST     - WHIRLWIND_COUNT spiral emitters that stream short-lived
 *                    cyan point sprites in an expanding spiral.
 *
 * Objects are emitted per-frame via renderObjects() and spliced into the
 * renderer's transparent draw list; point sprites go through the renderer's
 * particle system.
 */

import {
    CELL_SIZE, WALL_HEIGHT, CRYSTAL_EFFECT, CRYSTAL_EFFECT_ANIMATION,
} from '../game_client.constants.js';
import { buildIcoSphere } from './webgl2_geometry.js';
import { createLineMesh } from './webgl2_core.js';
import { createSoftCircleTexture } from './webgl2_textures.js';

const FOG_COLOR = [0.85, 0.88, 1.05];
const GHOST_COLOR = [0.65, 1.5, 1.5];    // >1 so the bloom pass picks it up
const BOLT_COLOR = [1.0, 1.0, 0.55];
const FLASH_COLOR = [1.0, 0.95, 0.4];
const SPARK_COLOR = [1.0, 0.9, 0.45];
const WHIRLWIND_COLOR = [0.4, 1.0, 1.0];

class WebGL2CrystalEffectAnimator {
    constructor(renderer) {
        this.renderer = renderer;
        this.activeAnimation = null;
        this.animationTime = 0.0;
        this.crystalPosition = null;
        this.affectedTokens = [];

        this.fogPuffs = [];
        this.ghosts = [];
        this.flashes = [];
        this.whirlwinds = [];

        this.softTexture = null;
    }

    startEffect(effectType, crystalPos, affectedTokens = []) {
        this.cleanup();

        this.activeAnimation = effectType;
        this.animationTime = 0.0;
        this.crystalPosition = crystalPos;
        this.affectedTokens = affectedTokens || [];

        switch (effectType) {
            case CRYSTAL_EFFECT.FOG_OF_WAR:
                this._initFogPuffs();
                break;
            case CRYSTAL_EFFECT.PHANTOM_ENEMIES:
                this._initGhosts();
                break;
            case CRYSTAL_EFFECT.DAMAGE_BOOST:
                this._initLightning();
                break;
            case CRYSTAL_EFFECT.SPEED_BOOST:
                this._initWhirlwind();
                break;
        }
    }

    update(deltaTime) {
        if (!this.activeAnimation) return;

        this.animationTime += deltaTime;
        if (this.animationTime >= CRYSTAL_EFFECT_ANIMATION.DURATION) {
            this.cleanup();
            return;
        }

        switch (this.activeAnimation) {
            case CRYSTAL_EFFECT.FOG_OF_WAR:
                this._updateFog(deltaTime);
                break;
            case CRYSTAL_EFFECT.PHANTOM_ENEMIES:
                this._updateGhosts(deltaTime);
                break;
            case CRYSTAL_EFFECT.DAMAGE_BOOST:
                this._updateLightning(deltaTime);
                break;
            case CRYSTAL_EFFECT.SPEED_BOOST:
                this._updateWhirlwind(deltaTime);
                break;
        }
    }

    /** Transparent draw-list entries for this frame (fresh objects). */
    renderObjects() {
        const objects = [];
        const fade = 1 - this.animationTime / CRYSTAL_EFFECT_ANIMATION.DURATION;

        for (const puff of this.fogPuffs) {
            objects.push({
                billboard: true,
                pos: { x: puff.x, y: puff.y, z: puff.z },
                width: puff.size,
                height: puff.size,
                texture: this._softTexture(),
                useMap: true,
                color: FOG_COLOR,
                alpha: puff.alpha * Math.max(0, fade),
            });
        }

        for (const ghost of this.ghosts) {
            objects.push({
                billboard: true,
                pos: { x: ghost.x, y: ghost.y, z: ghost.z },
                width: 15,
                height: 15,
                texture: this._softTexture(),
                useMap: true,
                color: GHOST_COLOR,
                alpha: ghost.alpha * Math.max(0, fade),
            });
        }

        for (const flash of this.flashes) {
            if (flash.envelope <= 0) continue;
            // Flash sphere: additive, catches the bloom knee.
            objects.push({
                kind: 'unlit',
                mesh: this.renderer._mesh('flashSphere', () => buildIcoSphere(CELL_SIZE * 0.9, 1)),
                pos: { x: flash.x, y: flash.y, z: flash.z },
                rot: { x: 0, y: 0, z: 0 },
                scale: { x: 1 + (1 - flash.envelope) * 0.6, y: 1 + (1 - flash.envelope) * 0.6, z: 1 + (1 - flash.envelope) * 0.6 },
                color: FLASH_COLOR,
                alpha: flash.envelope,
                brightness: 2.5,
                additive: true,
            });
            // Jagged bolt from the sky to the token.
            if (flash.boltMesh) {
                objects.push({
                    kind: 'line',
                    mesh: flash.boltMesh,
                    pos: { x: 0, y: 0, z: 0 },
                    rot: { x: 0, y: 0, z: 0 },
                    scale: { x: 1, y: 1, z: 1 },
                    color: BOLT_COLOR,
                    alpha: flash.envelope,
                    brightness: 2.0,
                    lineLoop: false,
                    additive: true,
                });
            }
        }

        return objects;
    }

    isAnimating() {
        return this.activeAnimation !== null;
    }

    cleanup() {
        for (const flash of this.flashes) {
            if (flash.boltMesh) flash.boltMesh.dispose();
        }
        this.fogPuffs = [];
        this.ghosts = [];
        this.flashes = [];
        this.whirlwinds = [];
        this.activeAnimation = null;
        this.animationTime = 0.0;
    }

    // --- Internals -----------------------------------------------------------

    _softTexture() {
        if (!this.softTexture) {
            this.softTexture = createSoftCircleTexture(this.renderer.gl);
            this.renderer.textures.push(this.softTexture);
        }
        return this.softTexture;
    }

    _crystalCenter() {
        const [gx, gy] = this.crystalPosition;
        return {
            x: gx * CELL_SIZE + CELL_SIZE / 2,
            y: WALL_HEIGHT * 0.5,
            z: gy * CELL_SIZE + CELL_SIZE / 2,
        };
    }

    _initFogPuffs() {
        const count = 16;
        const origin = this._crystalCenter();
        for (let i = 0; i < count; i++) {
            this.fogPuffs.push({
                angle: (i / count) * Math.PI * 2,
                // Start outside the crystal hub silhouette — puffs spawned
                // at the origin are depth-occluded by it and never seen.
                distance: 42,
                speed: CRYSTAL_EFFECT_ANIMATION.FOG_SPREAD_SPEED + (Math.random() - 0.5) * 40,
                size: 42 + Math.random() * 38,
                alpha: 0.85,
                x: origin.x,
                y: origin.y,
                z: origin.z,
            });
        }
    }

    _initGhosts() {
        const origin = this._crystalCenter();
        for (let i = 0; i < CRYSTAL_EFFECT_ANIMATION.GHOST_COUNT; i++) {
            this.ghosts.push({
                angle: Math.random() * Math.PI * 2,
                distance: 45,
                speed: 80 + Math.random() * 40,
                wobble: Math.random() * Math.PI * 2,
                wobbleSpeed: 3 + Math.random() * 3,
                alpha: 0.85,
                x: origin.x,
                y: origin.y,
                z: origin.z,
            });
        }
    }

    _initLightning() {
        for (const token of this.affectedTokens) {
            // A token hidden by fog of war has no position.
            if (!token.position) continue;
            const flash = {
                x: token.position[0] * CELL_SIZE + CELL_SIZE / 2,
                y: WALL_HEIGHT * 0.5,
                z: token.position[1] * CELL_SIZE + CELL_SIZE / 2,
                flashTime: 0,
                numFlashes: 2 + Math.floor(Math.random() * 3),
                currentFlash: 0,
                envelope: 0,
                boltMesh: null,
            };
            this.flashes.push(flash);
        }
    }

    _initWhirlwind() {
        const origin = this._crystalCenter();
        for (let i = 0; i < CRYSTAL_EFFECT_ANIMATION.WHIRLWIND_COUNT; i++) {
            this.whirlwinds.push({
                angle: Math.random() * Math.PI * 2,
                distance: 6,
                speed: 100 + Math.random() * 50,
                spiralRate: 0.5 + Math.random(),
                origin,
            });
        }
    }

    _updateFog(dt) {
        const origin = this._crystalCenter();
        for (const puff of this.fogPuffs) {
            puff.distance += puff.speed * dt;
            puff.x = origin.x + Math.cos(puff.angle) * puff.distance;
            puff.z = origin.z + Math.sin(puff.angle) * puff.distance;
            // Puffs billow outward as they spread.
            puff.size += 30 * dt;
        }
    }

    _updateGhosts(dt) {
        const origin = this._crystalCenter();
        for (const ghost of this.ghosts) {
            ghost.distance += ghost.speed * dt;
            ghost.wobble += ghost.wobbleSpeed * dt;
            const wobbleOffset = Math.sin(ghost.wobble) * 20;
            ghost.x = origin.x + Math.cos(ghost.angle) * ghost.distance + wobbleOffset;
            ghost.y = origin.y + Math.sin(ghost.wobble * 0.7) * 6;
            ghost.z = origin.z + Math.sin(ghost.angle) * ghost.distance;
        }
    }

    _updateLightning(dt) {
        for (const flash of this.flashes) {
            const interval = CRYSTAL_EFFECT_ANIMATION.DURATION / flash.numFlashes;
            flash.flashTime += dt;

            if (flash.flashTime >= interval && flash.currentFlash < flash.numFlashes) {
                flash.currentFlash++;
                flash.flashTime = 0;
                flash.envelope = 1;
                this._strikeLightning(flash);
            }

            if (flash.envelope > 0) {
                const progress = flash.flashTime / CRYSTAL_EFFECT_ANIMATION.LIGHTNING_FLASH_DURATION;
                flash.envelope = Math.max(0, 1 - progress);
            }
        }
    }

    _strikeLightning(flash) {
        const gl = this.renderer.gl;
        const top = WALL_HEIGHT * 3.5;
        const segments = 9;
        const points = [flash.x, top, flash.z];
        for (let i = 1; i < segments; i++) {
            const f = i / segments;
            const jitter = (1 - f * 0.5) * 14;
            points.push(
                flash.x + (Math.random() - 0.5) * jitter,
                top * (1 - f) + flash.y * f,
                flash.z + (Math.random() - 0.5) * jitter,
            );
        }
        points.push(flash.x, flash.y, flash.z);
        if (flash.boltMesh) flash.boltMesh.dispose();
        flash.boltMesh = createLineMesh(gl, new Float32Array(points));

        // Spark burst at the token.
        for (let i = 0; i < 22; i++) {
            this.renderer._spawnParticle({
                x: flash.x + (Math.random() - 0.5) * CELL_SIZE * 0.4,
                y: flash.y + (Math.random() - 0.5) * 10,
                z: flash.z + (Math.random() - 0.5) * CELL_SIZE * 0.4,
                vx: (Math.random() - 0.5) * 140,
                vy: 40 + Math.random() * 120,
                vz: (Math.random() - 0.5) * 140,
                life: 0.5 + Math.random() * 0.3,
                maxLife: 0.8,
                size: 1.5 + Math.random() * 2,
                color: SPARK_COLOR.slice(),
                gravity: 220,
            });
        }
    }

    _updateWhirlwind(dt) {
        for (const w of this.whirlwinds) {
            w.distance += w.speed * dt;
            w.angle += w.spiralRate * dt;
            // Stream short-lived point sprites along the spiral.
            this.renderer._spawnParticle({
                x: w.origin.x + Math.cos(w.angle) * w.distance,
                y: w.origin.y - 6 + Math.random() * 22,
                z: w.origin.z + Math.sin(w.angle) * w.distance,
                vx: (Math.random() - 0.5) * 15,
                vy: 5 + Math.random() * 15,
                vz: (Math.random() - 0.5) * 15,
                life: 0.45,
                maxLife: 0.45,
                size: 1.6 + Math.random() * 1.6,
                color: WHIRLWIND_COLOR.slice(),
                gravity: 0,
            });
        }
    }
}

export { WebGL2CrystalEffectAnimator };
