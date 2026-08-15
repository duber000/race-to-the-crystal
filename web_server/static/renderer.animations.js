/**
 * Renderer3D - Animations Module
 * Update loop, animations, particles, mystery animations
 */

import { Renderer3D, CYAN_GLOW } from './renderer.base.js';
import { BOARD_CONFIG, CELL_SIZE } from './game_client.constants.js';

const WALL_HEIGHT = BOARD_CONFIG.WALL_HEIGHT;
const BOARD_WIDTH = BOARD_CONFIG.WIDTH;
const BOARD_HEIGHT = BOARD_CONFIG.HEIGHT;

Renderer3D.prototype.updateAnimations = function() {
    this.generatorLineMeshes.forEach((lineData) => {
        if (!lineData.beams) return;

        lineData.beams.forEach((beam) => {
            const pulse = 0.5 + Math.random() * 0.5;
            if (beam.material) {
                beam.material.emissiveIntensity = 2.0 + pulse * 10;
                beam.visibility = 0.4 + pulse * 0.6;
            }
        });

        if (lineData.hitParticles && Math.random() > 0.7) {
            lineData.hitParticles.emitRate = 50;
            setTimeout(() => {
                if (lineData.hitParticles) lineData.hitParticles.emitRate = 0;
            }, 100);
        }
    });

    if (this.crystalMesh && this.crystalMesh.mesh) {
        this.crystalMesh.mesh.rotation.y += 0.005;
    }
    this.crystalFrames.forEach((frame, idx) => {
        frame.rotation.y += 0.003 * (idx % 2 === 0 ? 1 : -1);
        frame.rotation.z += 0.001 * (idx % 2 === 0 ? 1 : -1);
    });

    if (this.vls) {
        this.vls.weight = 0.5 + Math.sin(this.animationTime * 2) * 0.2;
    }

    this.mysteryRings.forEach((ring) => {
        const name = ring.name;
        const match = name.match(/mystery_(\d+)_(\d+)/);
        if (!match) return;

        const x = parseInt(match[1]);
        const y = parseInt(match[2]);
        const posKey = `${x},${y}`;
        const animationProgress = this.mysteryAnimations.get(posKey);

        if (animationProgress !== undefined) {
            return;
        }

        if (ring.material && ring.material.emissiveColor) {
            const pulse = 0.4 + 0.2 * Math.sin(this.animationTime * 4);
            ring.material.emissiveColor.r = CYAN_GLOW.r * pulse;
            ring.material.emissiveColor.g = CYAN_GLOW.g * pulse;
            ring.material.emissiveColor.b = CYAN_GLOW.b * pulse;
            ring.scaling.x = 1 + 0.1 * Math.sin(this.animationTime * 3);
            ring.scaling.z = 1 + 0.1 * Math.sin(this.animationTime * 3);
        }
    });

    this.updateMysteryAnimations();
    this.updateExplosionParticles();

    const crystal = this.scene.getMeshByName("crystal");
    if (crystal) {
        const pulse = 1 + 0.15 * Math.sin(this.animationTime * 2);
        crystal.scaling.x = pulse;
        crystal.scaling.z = pulse;
        crystal.rotation.y = this.animationTime * 0.5;

        for (let i = 1; i <= 6; i++) {
            const glowLayer = this.scene.getMeshByName(`crystal_glow_${i}`);
            if (glowLayer) {
                glowLayer.scaling.x = pulse;
                glowLayer.scaling.z = pulse;
                glowLayer.rotation.y = this.animationTime * 0.5;
            }
        }
    }

    if (this.confettiParticles.length > 0) {
        this.confettiParticles.forEach((p) => {
            p.mesh.position.x += p.vx * 0.016;
            p.mesh.position.y += p.vy * 0.016;
            p.mesh.position.z += p.vz * 0.016;
            p.vy -= 50 * 0.016;
            p.mesh.rotation.x += p.rotX * 0.016;
            p.mesh.rotation.y += p.rotY * 0.016;

            if (p.mesh.position.y < 0) {
                p.mesh.position.y = 200;
                p.mesh.position.x = Math.random() * BOARD_WIDTH * CELL_SIZE;
                p.mesh.position.z = Math.random() * BOARD_HEIGHT * CELL_SIZE;
                p.vy = -50 - Math.random() * 50;
            }
        });
    }

    if (this.crystalEffectAnimator) {
        this.crystalEffectAnimator.update(0.016);
    }
};

Renderer3D.prototype.updateMysteryAnimations = function() {
    this.mysteryAnimations.forEach((progress, posKey) => {
        const [x, y] = posKey.split(",").map(Number);
        const ring = this.scene.getMeshByName(`mystery_${x}_${y}`);

        if (ring) {
            const rotationAngle = progress * 3 * 2 * Math.PI;
            const scaleX = Math.abs(Math.cos(rotationAngle));

            ring.rotation.y = rotationAngle;
            ring.scaling.x = scaleX;
            ring.scaling.z = 1;

            const pulseProgress = Math.max(0, (progress - 0.3) * 1.5);
            if (ring.material && ring.material.emissiveColor) {
                const brightness = 0.6 + 0.4 * Math.sin(pulseProgress * Math.PI);
                ring.material.emissiveColor.r = CYAN_GLOW.r * brightness;
                ring.material.emissiveColor.g = CYAN_GLOW.g * brightness;
                ring.material.emissiveColor.b = CYAN_GLOW.b * brightness;
            }
        }

        this.mysteryAnimations.set(posKey, progress + 0.016);
    });
};

Renderer3D.prototype.checkMysteryLandings = function(gameState) {
    if (!gameState.tokens || !gameState.board) return;

    if (gameState.last_triggered_mystery_event) {
        const eventKey = JSON.stringify(gameState.last_triggered_mystery_event);

        if (eventKey !== this.lastProcessedMysteryEvent) {
            const [tokenId, position, effect] = gameState.last_triggered_mystery_event;
            const posKey = `${position[0]},${position[1]}`;

            this.mysteryAnimations.set(posKey, 0.0);
            console.log(`Token ${tokenId} triggered mystery square at ${posKey} - Effect: ${effect}`);
            this.playSound("mystery");

            this.lastProcessedMysteryEvent = eventKey;
        }
    }

    for (const [posKey, progress] of this.mysteryAnimations) {
        if (progress >= 1.0) {
            this.mysteryAnimations.delete(posKey);
        }
    }
};

Renderer3D.prototype.isMysterySquare = function(x, y, gameState) {
    if (!gameState.board || !gameState.board.grid) return false;
    if (y < 0 || y >= gameState.board.grid.length) return false;
    if (x < 0 || x >= gameState.board.grid[y].length) return false;
    return gameState.board.grid[y][x].cell_type === 3;
};

Renderer3D.prototype.checkCrystalEffectTrigger = function(gameState) {
    if (!gameState.last_triggered_crystal_effect || !this.crystalEffectAnimator) return;
    if (!gameState.crystal) return;

    const [affectedPlayerId, effectType] = gameState.last_triggered_crystal_effect;

    let affectedTokens = [];
    if (effectType === CrystalEffect.DAMAGE_BOOST) {
        affectedTokens = Object.values(gameState.tokens || {}).filter(
            t => t.player_id === affectedPlayerId && t.is_deployed && t.is_alive
        );
    }

    this.crystalEffectAnimator.startEffect(
        effectType,
        gameState.crystal.position,
        affectedTokens
    );

    switch (effectType) {
        case CrystalEffect.FOG_OF_WAR:
            this.playSound("fog_horn");
            break;
        case CrystalEffect.PHANTOM_ENEMIES:
            this.playSound("ghost");
            break;
        case CrystalEffect.DAMAGE_BOOST:
            this.playSound("lightning");
            break;
        case CrystalEffect.SPEED_BOOST:
            this.playSound("whoosh");
            break;
    }

    console.log(`Crystal effect triggered: ${effectType} for player ${affectedPlayerId}`);
};

Renderer3D.prototype.triggerExplosion = function(position, color) {
    const centerX = position[0] * CELL_SIZE + CELL_SIZE / 2;
    const centerZ = position[1] * CELL_SIZE + CELL_SIZE / 2;

    for (let i = 0; i < 30; i++) {
        const size = 2 + Math.random() * 4;
        const particle = BABYLON.MeshBuilder.CreateBox(
            `explosion_${Date.now()}_${i}`,
            { size: size },
            this.scene,
        );

        particle.position = new BABYLON.Vector3(
            centerX + (Math.random() - 0.5) * CELL_SIZE * 0.5,
            WALL_HEIGHT * 0.3 + Math.random() * CELL_SIZE * 0.3,
            centerZ + (Math.random() - 0.5) * CELL_SIZE * 0.5,
        );

        const material = new BABYLON.StandardMaterial("explosionMat", this.scene);
        material.emissiveColor = color;
        material.disableLighting = true;
        particle.material = material;

        this.explosionParticles.push({
            mesh: particle,
            vx: (Math.random() - 0.5) * 100,
            vy: 50 + Math.random() * 100,
            vz: (Math.random() - 0.5) * 100,
            life: 1.0,
        });
    }
};

Renderer3D.prototype.updateExplosionParticles = function() {
    for (let i = this.explosionParticles.length - 1; i >= 0; i--) {
        const p = this.explosionParticles[i];
        p.life -= 0.016;

        p.mesh.position.x += p.vx * 0.016;
        p.mesh.position.y += p.vy * 0.016;
        p.mesh.position.z += p.vz * 0.016;
        p.vy -= 150 * 0.016;

        p.mesh.material.alpha = p.life;

        if (p.life <= 0) {
            p.mesh.dispose();
            this.explosionParticles.splice(i, 1);
        }
    }
};

Renderer3D.prototype.triggerVictoryEffect = function() {
    const colors = [
        new BABYLON.Color3(1, 0, 0),
        new BABYLON.Color3(0, 1, 0),
        new BABYLON.Color3(0, 0, 1),
        new BABYLON.Color3(1, 1, 0),
        new BABYLON.Color3(1, 0, 1),
        new BABYLON.Color3(0, 1, 1),
    ];

    for (let i = 0; i < 100; i++) {
        const size = 2 + Math.random() * 3;
        const confetti = BABYLON.MeshBuilder.CreateBox(
            `confetti_${i}`,
            { size: size },
            this.scene,
        );

        confetti.position = new BABYLON.Vector3(
            Math.random() * BOARD_WIDTH * CELL_SIZE,
            100 + Math.random() * 100,
            Math.random() * BOARD_HEIGHT * CELL_SIZE,
        );

        const color = colors[Math.floor(Math.random() * colors.length)];
        const material = new BABYLON.StandardMaterial(`confettiMat_${i}`, this.scene);
        material.emissiveColor = color;
        material.disableLighting = true;
        confetti.material = material;

        this.confettiParticles.push({
            mesh: confetti,
            vx: (Math.random() - 0.5) * 20,
            vy: -50 - Math.random() * 50,
            vz: (Math.random() - 0.5) * 20,
            rotX: Math.random() * 5,
            rotY: Math.random() * 5,
        });
    }

    this.playSound("crystal");
};

// --- Event-Based Animation Methods ---

Renderer3D.prototype.animateTokenMove = function(tokenId, oldPos, newPos) {
    if (this.tokenRenderer) {
        // We simulate a token object that TokenRenderer expects
        const token = {
            id: tokenId,
            position: newPos,
            // (other fields aren't strictly necessary for movement but might be needed for health display)
        };
        // TokenRenderer.updateTokenPosition will handle the animation
        this.tokenRenderer.updateTokenPosition(tokenId, token);
    }
};

Renderer3D.prototype.animateCombat = function(data) {
    // Find absolute world position of defender
    const defenderX = data.defender_position ? data.defender_position[0] : null;
    const defenderY = data.defender_position ? data.defender_position[1] : null;
    
    // If we don't have position in event, we might need to look up in local state
    // but the server should ideally send it. 
    // For now, let's assume we can find the mesh.
    const tokenData = this.tokenRenderer ? this.tokenRenderer.tokens3D.get(data.defender_id) : null;
    if (tokenData && tokenData.mesh) {
        const pos = [
            Math.floor(tokenData.mesh.position.x / CELL_SIZE),
            Math.floor(tokenData.mesh.position.z / CELL_SIZE)
        ];
        this.triggerExplosion(pos, new BABYLON.Color3(1, 0.2, 0.2));
        this.playSound("attack");
    }
};

Renderer3D.prototype.animateTokenDeploy = function(data) {
    this.playSound("deploy");
    // (Could add particle effect at data.position)
};

Renderer3D.prototype.animateGeneratorUpdate = function(data) {
    if (data.is_disabled) {
        this.playSound("power_down");
    }
};

Renderer3D.prototype.animateCrystalUpdate = function(data) {
    // (Could add visual pulses based on tokens_held)
};

Renderer3D.prototype.animateMysteryEvent = function(data) {
    const posKey = `${data.details.position[0]},${data.details.position[1]}`;
    this.mysteryAnimations.set(posKey, 0.0);
    this.playSound("mystery");
};
