/**
 * Renderer3D - Phase 1.1 juice module
 *
 * Trauma-based camera shake, impact particle bursts and floating combat text.
 * Side-effect module: patches Renderer3D.prototype, mirroring the pattern used
 * by renderer.animations.js.
 *
 * Imported by game_client.renderer.js (after renderer.animations.js so the
 * patched animation methods wrap the originals).
 */

import { Renderer3D } from './renderer.base.js';
import { BOARD_CONFIG, CELL_SIZE, GLOW_COLORS } from './game_client.constants.js';

const WALL_HEIGHT = BOARD_CONFIG.WALL_HEIGHT;
const TRAUMA_DECAY = 2.0;       // trauma units per second
const TRAUMA_CAP = 1.0;

// --- Trauma ---------------------------------------------------------------

Renderer3D.prototype.addTrauma = function(amount) {
    amount = amount || 0;
    // Budget: low-end devices get a fraction of the shake.
    if (this.deviceCapabilities && typeof this.deviceCapabilities.shouldOptimizePerformance === 'function' && this.deviceCapabilities.shouldOptimizePerformance()) {
        amount *= 0.35;
    }
    this.trauma = Math.min(TRAUMA_CAP, (this.trauma || 0) + amount);
};

Renderer3D.prototype.updateTrauma = function(dt) {
    this.trauma = Math.max(0, (this.trauma || 0) - dt * TRAUMA_DECAY);
    // decay bookkeeping for shake
    this._currentShake = this.trauma * this.trauma;
};

Renderer3D.prototype.applyCameraShake = function() {
    const cc = this.cameraController;
    const camera = cc && cc.camera;
    if (!camera) return;
    const shake = this._currentShake || 0;
    if (shake <= 0.0001) return;
    const amp = shake * 10;
    const t = this.animationTime || 0;
    // Jitter the ArcRotate target (the rig itself stays intact).
    camera.target.x += Math.sin(t * 37.7) * amp + Math.cos(t * 17.3) * amp * 0.4;
    camera.target.y += Math.cos(t * 23.1) * amp * 0.6;
    camera.target.z += Math.sin(t * 29.4) * amp;
};

// --- Impact particles / bursts -------------------------------------------

Renderer3D.prototype.triggerTokenBurst = function(position, color) {
    if (!position || position.length < 2) return;
    this.triggerExplosion(position, color || new BABYLON.Color3(1, 1, 1));
};

Renderer3D.prototype.triggerCrystalBurst = function(position) {
    if (!position || position.length < 2) return;
    this.triggerExplosion(position, new BABYLON.Color3(0.2, 0.9, 1.0));
    this.triggerExplosion(position, new BABYLON.Color3(1.0, 0.9, 0.3));
};

// --- Floating combat text -------------------------------------------------

if (!Renderer3D.prototype._floatingTextsInit) {
    const orig = Renderer3D.prototype.updateAnimations;
    // storage initialised lazily inside methods
}

Renderer3D.prototype._ensureFloatingArrays = function() {
    if (!this.floatingTexts) this.floatingTexts = [];
    if (!this.pulseRings) this.pulseRings = [];
    if (!this.trauma) this.trauma = 0;
};

Renderer3D.prototype.showFloatingText = function(worldPos, text, colorHex) {
    if (!this.scene || !worldPos || worldPos.length < 2) return;
    this._ensureFloatingArrays();

    const centerX = worldPos[0] * CELL_SIZE + CELL_SIZE / 2;
    const centerZ = worldPos[1] * CELL_SIZE + CELL_SIZE / 2;
    const centerY = WALL_HEIGHT * 0.6 + 6;

    const plane = BABYLON.MeshBuilder.CreatePlane(
        'fct_' + Date.now() + '_' + Math.random().toString(36).slice(2),
        { width: 12, height: 3 },
        this.scene,
    );
    plane.billboardMode = BABYLON.Mesh.BILLBOARDMODE_ALL;
    plane.position = new BABYLON.Vector3(centerX, centerY, centerZ);
    plane.isPickable = false;

    const tex = new BABYLON.DynamicTexture(
        'fctTex_' + Date.now(),
        { width: 256, height: 64 },
        this.scene,
        false,
    );
    const ctx = tex.getContext();
    ctx.clearRect(0, 0, 256, 64);
    ctx.font = 'bold 40px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = colorHex || '#ff4444';
    ctx.strokeStyle = 'rgba(0,0,0,0.8)';
    ctx.lineWidth = 4;
    ctx.strokeText(String(text), 128, 32);
    ctx.fillText(String(text), 128, 32);
    tex.update();

    const mat = new BABYLON.StandardMaterial('fctMat_' + Date.now(), this.scene);
    mat.diffuseTexture = tex;
    mat.emissiveColor = new BABYLON.Color3(1, 1, 1);
    mat.disableLighting = true;
    mat.hasAlpha = true;
    mat.alpha = 1.0;
    mat.backFaceCulling = false;
    plane.material = mat;

    this.floatingTexts.push({ mesh: plane, texture: tex, life: 1.2, vy: 22 });
};

Renderer3D.prototype.showPulseRing = function(position, color) {
    if (!position || position.length < 2) return;
    this._ensureFloatingArrays();
    const centerX = position[0] * CELL_SIZE + CELL_SIZE / 2;
    const centerZ = position[1] * CELL_SIZE + CELL_SIZE / 2;
    const ring = BABYLON.MeshBuilder.CreateTorus(
        'pulse_' + Date.now(),
        { diameter: CELL_SIZE * 1.6, thickness: 0.4, tessellation: 24 },
        this.scene,
    );
    ring.position = new BABYLON.Vector3(centerX, 0.4, centerZ);
    ring.isPickable = false;
    const mat = new BABYLON.StandardMaterial('pulseMat_' + Date.now(), this.scene);
    mat.emissiveColor = color || new BABYLON.Color3(1, 1, 1);
    mat.disableLighting = true;
    mat.alpha = 0.9;
    ring.material = mat;
    this.pulseRings.push({ mesh: ring, life: 0.6, scale: 1.0 });
};

// --- Patch animation hooks -----------------------------------------------

// Wrap updateAnimations to fold in trauma decay + fx housekeeping.
const _origUpdateAnimations = Renderer3D.prototype.updateAnimations;
Renderer3D.prototype.updateAnimations = function() {
    this._ensureFloatingArrays();
    this.updateTrauma(0.016);
    if (typeof _origUpdateAnimations === 'function') {
        _origUpdateAnimations.call(this);
    }
    this._updateFloatingTexts(0.016);
    this._updatePulseRings(0.016);
};

Renderer3D.prototype._updateFloatingTexts = function(dt) {
    if (!this.floatingTexts) return;
    for (let i = this.floatingTexts.length - 1; i >= 0; i--) {
        const f = this.floatingTexts[i];
        f.life -= dt;
        f.mesh.position.y += f.vy * dt;
        f.vy *= 0.95;
        if (f.mesh.material) f.mesh.material.alpha = Math.max(0, f.life / 1.2);
        if (f.life <= 0) {
            try { f.mesh.dispose(); } catch (e) {}
            try { f.texture.dispose(); } catch (e) {}
            this.floatingTexts.splice(i, 1);
        }
    }
};

Renderer3D.prototype._updatePulseRings = function(dt) {
    if (!this.pulseRings) return;
    for (let i = this.pulseRings.length - 1; i >= 0; i--) {
        const p = this.pulseRings[i];
        p.life -= dt;
        p.scale += dt * 4;
        p.mesh.scaling.x = p.scale;
        p.mesh.scaling.z = p.scale;
        if (p.mesh.material) p.mesh.material.alpha = Math.max(0, p.life / 0.6);
        if (p.life <= 0) {
            try { p.mesh.dispose(); } catch (e) {}
            this.pulseRings.splice(i, 1);
        }
    }
};

// Enhance existing event animation methods.

const _origAnimateCombat = Renderer3D.prototype.animateCombat;
Renderer3D.prototype.animateCombat = function(data) {
    if (!data) return;
    const killed = data.defender_killed === true;
    this.addTrauma(killed ? 0.6 : 0.25);
    const position = data.defender_position;
    this.triggerTokenBurst(position, killed
        ? new BABYLON.Color3(1, 0.2, 0.2)
        : new BABYLON.Color3(1, 0.8, 0.2));
    if (position && position.length >= 2 && data.damage !== undefined) {
        this.showFloatingText(position, '-' + data.damage, killed ? '#ff3333' : '#ffcc33');
    }
    if (typeof _origAnimateCombat === 'function') {
        _origAnimateCombat.call(this, data);
    }
};

const _origAnimateTokenMove = Renderer3D.prototype.animateTokenMove;
Renderer3D.prototype.animateTokenMove = function(tokenId, oldPos, newPos) {
    this.playSound('whoosh');
    if (typeof _origAnimateTokenMove === 'function') {
        _origAnimateTokenMove.call(this, tokenId, oldPos, newPos);
    }
};

const _origAnimateTokenDeploy = Renderer3D.prototype.animateTokenDeploy;
Renderer3D.prototype.animateTokenDeploy = function(data) {
    if (data && data.position) {
        this.showPulseRing(data.position, new BABYLON.Color3(0.3, 0.8, 1.0));
    }
    if (typeof _origAnimateTokenDeploy === 'function') {
        _origAnimateTokenDeploy.call(this, data);
    }
};

const _origAnimateGeneratorUpdate = Renderer3D.prototype.animateGeneratorUpdate;
Renderer3D.prototype.animateGeneratorUpdate = function(data) {
    if (data && data.is_disabled) {
        this.addTrauma(0.8);
        if (data.position) {
            this.triggerExplosion(data.position, new BABYLON.Color3(1.0, 0.5, 0.1));
        }
    }
    if (typeof _origAnimateGeneratorUpdate === 'function') {
        _origAnimateGeneratorUpdate.call(this, data);
    }
};

const _origAnimateCrystalUpdate = Renderer3D.prototype.animateCrystalUpdate;
Renderer3D.prototype.animateCrystalUpdate = function(data) {
    if (data && data.holding_player_id && data.holding_player_id !== '' && !data.is_contested) {
        // A capture in progress — light excitement.
        // We only do the full victory burst on game end.
    }
    if (typeof _origAnimateCrystalUpdate === 'function') {
        _origAnimateCrystalUpdate.call(this, data);
    }
};

const _origAnimateMysteryEvent = Renderer3D.prototype.animateMysteryEvent;
Renderer3D.prototype.animateMysteryEvent = function(data) {
    this.addTrauma(0.2);
    if (data && data.position) {
        this.triggerTokenBurst(data.position, new BABYLON.Color3(0.6, 1.0, 0.6));
    }
    if (typeof _origAnimateMysteryEvent === 'function') {
        _origAnimateMysteryEvent.call(this, data);
    }
};

const _origTriggerVictoryEffect = Renderer3D.prototype.triggerVictoryEffect;
Renderer3D.prototype.triggerVictoryEffect = function() {
    this.addTrauma(0.9);
    if (this.crystalMesh && this.crystalMesh.mesh) {
        const pos = this.crystalMesh.mesh.position;
        try { this.triggerCrystalBurst([pos.x / CELL_SIZE, pos.z / CELL_SIZE]); } catch (e) {}
    }
    if (typeof _origTriggerVictoryEffect === 'function') {
        _origTriggerVictoryEffect.call(this);
    }
};
