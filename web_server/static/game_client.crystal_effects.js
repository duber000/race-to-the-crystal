/**
 * CrystalEffectAnimator - Particle-based visual effects for crystal effects
 *
 * Responsibilities:
 * - FOG_OF_WAR: Fog particles spreading from crystal
 * - PHANTOM_ENEMIES: Ghostly particles with wobble effect
 * - DAMAGE_BOOST: Lightning strikes on affected tokens
 * - SPEED_BOOST: Whirlwind particles with spiral motion
 *
 * Usage:
 *   const animator = new CrystalEffectAnimator(scene);
 *   animator.startEffect(CrystalEffect.FOG_OF_WAR, crystalPosition, affectedTokens);
 *   // In render loop:
 *   animator.update(deltaTime);
 */

class CrystalEffectAnimator {
    constructor(scene) {
        this.scene = scene;
        this.activeAnimation = null;
        this.animationTime = 0.0;
        this.crystalPosition = null;

        // Particle systems
        this.fogParticles = [];
        this.ghostParticles = [];
        this.lightningFlashes = [];
        this.whirlwindParticles = [];

        // Affected tokens for lightning
        this.affectedTokens = [];
    }

    /**
     * Start a crystal effect animation
     * @param {number} effectType - CrystalEffect enum value
     * @param {Array} crystalPos - [x, y] crystal grid position
     * @param {Array} affectedTokens - Array of tokens for DAMAGE_BOOST
     */
    startEffect(effectType, crystalPos, affectedTokens = []) {
        // Clean up previous animation
        this.cleanup();

        this.activeAnimation = effectType;
        this.animationTime = 0.0;
        this.crystalPosition = crystalPos;
        this.affectedTokens = affectedTokens || [];

        // Initialize particles based on effect type
        switch (effectType) {
            case CrystalEffect.FOG_OF_WAR:
                this._initFogParticles();
                break;
            case CrystalEffect.PHANTOM_ENEMIES:
                this._initGhostParticles();
                break;
            case CrystalEffect.DAMAGE_BOOST:
                this._initLightningFlashes();
                break;
            case CrystalEffect.SPEED_BOOST:
                this._initWhirlwindParticles();
                break;
        }
    }

    _initFogParticles() {
        const numParticles = 16;
        const worldX = this.crystalPosition[0] * CELL_SIZE + CELL_SIZE / 2;
        const worldZ = this.crystalPosition[1] * CELL_SIZE + CELL_SIZE / 2;

        for (let i = 0; i < numParticles; i++) {
            const angle = (i / numParticles) * Math.PI * 2;
            const particle = {
                angle: angle,
                distance: 0.0,
                speed: CRYSTAL_FOG_SPREAD_SPEED + (Math.random() - 0.5) * 40,
                size: 30 + Math.random() * 30,
                alpha: 0.7,
                mesh: null
            };

            // Create sphere mesh for fog particle
            const sphere = BABYLON.MeshBuilder.CreateSphere(
                `fogParticle_${i}`,
                { diameter: particle.size },
                this.scene
            );
            sphere.position = new BABYLON.Vector3(worldX, 20, worldZ);

            // Create material with emissive glow
            const material = new BABYLON.StandardMaterial(`fogMat_${i}`, this.scene);
            material.emissiveColor = new BABYLON.Color3(0.8, 0.8, 0.9);
            material.alpha = particle.alpha;
            sphere.material = material;

            particle.mesh = sphere;
            this.fogParticles.push(particle);
        }
    }

    _initGhostParticles() {
        const worldX = this.crystalPosition[0] * CELL_SIZE + CELL_SIZE / 2;
        const worldZ = this.crystalPosition[1] * CELL_SIZE + CELL_SIZE / 2;

        for (let i = 0; i < CRYSTAL_GHOST_COUNT; i++) {
            const angle = Math.random() * Math.PI * 2;
            const particle = {
                angle: angle,
                distance: 0.0,
                speed: 80 + Math.random() * 40,
                wobble: Math.random() * Math.PI * 2,
                wobbleSpeed: 3 + Math.random() * 3,
                alpha: 0.8,
                mesh: null
            };

            // Create ghost mesh (sphere with trail effect)
            const sphere = BABYLON.MeshBuilder.CreateSphere(
                `ghostParticle_${i}`,
                { diameter: 15 },
                this.scene
            );
            sphere.position = new BABYLON.Vector3(worldX, 20, worldZ);

            // Create ghostly cyan material
            const material = new BABYLON.StandardMaterial(`ghostMat_${i}`, this.scene);
            material.emissiveColor = new BABYLON.Color3(0.6, 1.0, 1.0);
            material.alpha = particle.alpha;
            sphere.material = material;

            particle.mesh = sphere;
            this.ghostParticles.push(particle);
        }
    }

    _initLightningFlashes() {
        for (let token of this.affectedTokens) {
            if (!token.position) continue;

            const flash = {
                token: token,
                flashTime: 0.0,
                numFlashes: 2 + Math.floor(Math.random() * 3),
                currentFlash: 0,
                meshes: []
            };

            // Create lightning effect meshes
            const worldX = token.position[0] * CELL_SIZE + CELL_SIZE / 2;
            const worldZ = token.position[1] * CELL_SIZE + CELL_SIZE / 2;

            // Central flash sphere
            const flashSphere = BABYLON.MeshBuilder.CreateSphere(
                `lightningFlash_${token.id}`,
                { diameter: CELL_SIZE * 2 },
                this.scene
            );
            flashSphere.position = new BABYLON.Vector3(worldX, 20, worldZ);

            const material = new BABYLON.StandardMaterial(`lightningMat_${token.id}`, this.scene);
            material.emissiveColor = new BABYLON.Color3(1, 1, 0.4);
            material.alpha = 0;
            flashSphere.material = material;

            flash.meshes.push(flashSphere);
            this.lightningFlashes.push(flash);
        }
    }

    _initWhirlwindParticles() {
        const worldX = this.crystalPosition[0] * CELL_SIZE + CELL_SIZE / 2;
        const worldZ = this.crystalPosition[1] * CELL_SIZE + CELL_SIZE / 2;

        for (let i = 0; i < CRYSTAL_WHIRLWIND_COUNT; i++) {
            const angle = Math.random() * Math.PI * 2;
            const particle = {
                angle: angle,
                distance: 0.0,
                speed: 100 + Math.random() * 50,
                rotation: Math.random() * Math.PI * 2,
                rotationSpeed: 5 + Math.random() * 5,
                spiralRate: 0.5 + Math.random(),
                alpha: 0.9,
                lines: []
            };

            // Create spinning line effect for whirlwind
            for (let j = 0; j < 3; j++) {
                const lineAngle = (j / 3) * Math.PI * 2;
                const points = [
                    new BABYLON.Vector3(
                        worldX + Math.cos(lineAngle) * 5,
                        20,
                        worldZ + Math.sin(lineAngle) * 5
                    ),
                    new BABYLON.Vector3(
                        worldX + Math.cos(lineAngle) * 25,
                        20,
                        worldZ + Math.sin(lineAngle) * 25
                    )
                ];

                const line = BABYLON.MeshBuilder.CreateLines(
                    `whirlwindLine_${i}_${j}`,
                    { points: points },
                    this.scene
                );
                line.color = new BABYLON.Color3(0.4, 1.0, 1.0);
                line.alpha = particle.alpha;

                particle.lines.push(line);
            }

            this.whirlwindParticles.push(particle);
        }
    }

    update(deltaTime) {
        if (!this.activeAnimation) return;

        this.animationTime += deltaTime;

        // End animation after duration
        if (this.animationTime >= CRYSTAL_EFFECT_ANIMATION_DURATION) {
            this.cleanup();
            return;
        }

        // Update particles based on effect type
        switch (this.activeAnimation) {
            case CrystalEffect.FOG_OF_WAR:
                this._updateFogParticles(deltaTime);
                break;
            case CrystalEffect.PHANTOM_ENEMIES:
                this._updateGhostParticles(deltaTime);
                break;
            case CrystalEffect.DAMAGE_BOOST:
                this._updateLightningFlashes(deltaTime);
                break;
            case CrystalEffect.SPEED_BOOST:
                this._updateWhirlwindParticles(deltaTime);
                break;
        }
    }

    _updateFogParticles(deltaTime) {
        const worldX = this.crystalPosition[0] * CELL_SIZE + CELL_SIZE / 2;
        const worldZ = this.crystalPosition[1] * CELL_SIZE + CELL_SIZE / 2;
        const fadeProgress = this.animationTime / CRYSTAL_EFFECT_ANIMATION_DURATION;

        for (let particle of this.fogParticles) {
            particle.distance += particle.speed * deltaTime;

            // Update position
            const x = worldX + Math.cos(particle.angle) * particle.distance;
            const z = worldZ + Math.sin(particle.angle) * particle.distance;
            particle.mesh.position.x = x;
            particle.mesh.position.z = z;

            // Fade out
            particle.mesh.material.alpha = 0.7 * (1.0 - fadeProgress);
        }
    }

    _updateGhostParticles(deltaTime) {
        const worldX = this.crystalPosition[0] * CELL_SIZE + CELL_SIZE / 2;
        const worldZ = this.crystalPosition[1] * CELL_SIZE + CELL_SIZE / 2;
        const fadeProgress = this.animationTime / CRYSTAL_EFFECT_ANIMATION_DURATION;

        for (let particle of this.ghostParticles) {
            particle.distance += particle.speed * deltaTime;
            particle.wobble += particle.wobbleSpeed * deltaTime;

            // Add wobble to position
            const wobbleOffset = Math.sin(particle.wobble) * 20;
            const x = worldX + Math.cos(particle.angle) * particle.distance + wobbleOffset;
            const z = worldZ + Math.sin(particle.angle) * particle.distance;
            particle.mesh.position.x = x;
            particle.mesh.position.z = z;

            // Fade out
            particle.mesh.material.alpha = 0.8 * (1.0 - fadeProgress);
        }
    }

    _updateLightningFlashes(deltaTime) {
        for (let flash of this.lightningFlashes) {
            flash.flashTime += deltaTime;

            // Check if it's time for next flash
            const flashInterval = CRYSTAL_EFFECT_ANIMATION_DURATION / flash.numFlashes;
            if (flash.flashTime >= flashInterval && flash.currentFlash < flash.numFlashes) {
                flash.currentFlash++;
                flash.flashTime = 0.0;

                // Show flash
                for (let mesh of flash.meshes) {
                    mesh.material.alpha = 1.0;
                }
            }

            // Fade out current flash
            if (flash.flashTime < CRYSTAL_LIGHTNING_FLASH_DURATION) {
                const flashProgress = flash.flashTime / CRYSTAL_LIGHTNING_FLASH_DURATION;
                for (let mesh of flash.meshes) {
                    mesh.material.alpha = 1.0 - flashProgress;
                }
            } else {
                for (let mesh of flash.meshes) {
                    mesh.material.alpha = 0;
                }
            }
        }
    }

    _updateWhirlwindParticles(deltaTime) {
        const worldX = this.crystalPosition[0] * CELL_SIZE + CELL_SIZE / 2;
        const worldZ = this.crystalPosition[1] * CELL_SIZE + CELL_SIZE / 2;
        const fadeProgress = this.animationTime / CRYSTAL_EFFECT_ANIMATION_DURATION;

        for (let particle of this.whirlwindParticles) {
            particle.distance += particle.speed * deltaTime;
            particle.rotation += particle.rotationSpeed * deltaTime;
            particle.angle += particle.spiralRate * deltaTime;

            // Update spinning lines
            for (let i = 0; i < particle.lines.length; i++) {
                const lineAngle = particle.rotation + (i / 3) * Math.PI * 2;
                const x = worldX + Math.cos(particle.angle) * particle.distance;
                const z = worldZ + Math.sin(particle.angle) * particle.distance;

                const points = [
                    new BABYLON.Vector3(
                        x + Math.cos(lineAngle) * 5,
                        20,
                        z + Math.sin(lineAngle) * 5
                    ),
                    new BABYLON.Vector3(
                        x + Math.cos(lineAngle) * 25,
                        20,
                        z + Math.sin(lineAngle) * 25
                    )
                ];

                particle.lines[i] = BABYLON.MeshBuilder.CreateLines(
                    particle.lines[i].name,
                    { points: points, instance: particle.lines[i] },
                    this.scene
                );

                // Fade out
                particle.lines[i].alpha = 0.9 * (1.0 - fadeProgress);
            }
        }
    }

    cleanup() {
        // Dispose fog particles
        for (let particle of this.fogParticles) {
            if (particle.mesh) {
                particle.mesh.dispose();
            }
        }
        this.fogParticles = [];

        // Dispose ghost particles
        for (let particle of this.ghostParticles) {
            if (particle.mesh) {
                particle.mesh.dispose();
            }
        }
        this.ghostParticles = [];

        // Dispose lightning flashes
        for (let flash of this.lightningFlashes) {
            for (let mesh of flash.meshes) {
                if (mesh) {
                    mesh.dispose();
                }
            }
        }
        this.lightningFlashes = [];

        // Dispose whirlwind particles
        for (let particle of this.whirlwindParticles) {
            for (let line of particle.lines) {
                if (line) {
                    line.dispose();
                }
            }
        }
        this.whirlwindParticles = [];

        this.activeAnimation = null;
        this.animationTime = 0.0;
    }

    isAnimating() {
        return this.activeAnimation !== null;
    }
}
