/**
 * Renderer3D - Base Module
 * Core class structure, scene initialization, and board rendering
 */

import { AudioManager } from './audio_manager.js';

const BOARD_CAGE_TOP_Y = WALL_HEIGHT;
const TOKEN_CENTER_Y = Math.max(TOKEN_HEIGHT / 2, BOARD_CAGE_TOP_Y - (TOKEN_HEIGHT / 2));
const GENERATOR_HEIGHT = Math.min(60, BOARD_CAGE_TOP_Y * 0.9);
const GENERATOR_CENTER_Y = BOARD_CAGE_TOP_Y - (GENERATOR_HEIGHT / 2);

class Renderer3D {
    constructor(canvas, deviceCapabilities) {
        this.canvas = canvas;
        this.deviceCapabilities = deviceCapabilities;
        this.engine = null;
        this.scene = null;
        this.glowLayer = null;

        this.board3D = [];
        this.tokens3D = new Map();
        this.phantomTokens3D = new Map();
        this.specialCellMeshes = [];
        this.validMoveMeshes = [];
        this.validAttackMeshes = [];
        this.hoverMesh = null;
        this.generatorLines = [];
        this.generatorLineMeshes = [];
        this.healthLabels = new Map();
        this.mysteryRings = [];
        this.mysteryAnimations = new Map();
        this.generatorMeshes = new Map();
        this.crystalMesh = null;
        this.explosionParticles = [];
        this.confettiParticles = [];
        this.crystalFrames = [];

        this.localPlayerId = null;
        this.animationTime = 0;
        this.animationCallbacks = new Map();
        this.lastProcessedMysteryEvent = null;
        this.crystalEffectAnimator = null;

        this.audioManager = new AudioManager();
        this.cleanupCallbacks = [];
    }

    initScene() {
        const renderConfig = this.deviceCapabilities ?
            this.deviceCapabilities.getRenderingConfig() :
            { hardwareScaling: 1.0, antialiasing: true };

        console.log('[Renderer3D] Initializing scene with config:', renderConfig);

        this.engine = new BABYLON.Engine(this.canvas, renderConfig.antialiasing);
        this.scene = new BABYLON.Scene(this.engine);
        this.scene.clearColor = new BABYLON.Color4(0, 0, 0, 1);

        this.applyPerformanceSettings(renderConfig);
        this.initLights();
        this.createBoard();

        this.crystalEffectAnimator = new CrystalEffectAnimator(this.scene);

        return this.scene;
    }

    applyPerformanceSettings(renderConfig) {
        if (!this.deviceCapabilities || !this.deviceCapabilities.shouldOptimizePerformance()) {
            console.log('[Renderer3D] Using high-quality settings');
            return;
        }

        console.log('[Renderer3D] Applying mobile performance optimizations');

        this.engine.setHardwareScalingLevel(renderConfig.hardwareScaling);
        this.scene.shadowsEnabled = renderConfig.shadowsEnabled;
        this.scene.skipFrustumClipping = true;
        this.scene.fogEnabled = false;

        if (this.glowLayer) {
            this.glowLayer.intensity = 1.0;
        }

        console.log('[Renderer3D] Performance optimizations applied');
    }

    initLights() {
        const ambientLight = new BABYLON.HemisphericLight(
            "ambientLight",
            new BABYLON.Vector3(0, 1, 0),
            this.scene,
        );
        ambientLight.intensity = 0.4;
        ambientLight.groundColor = new BABYLON.Color3(0.1, 0.1, 0.2);

        const dirLight = new BABYLON.DirectionalLight(
            "dirLight",
            new BABYLON.Vector3(-1, -2, -1),
            this.scene
        );
        dirLight.position = new BABYLON.Vector3(20, 40, 20);
        dirLight.intensity = 0.6;

        this.glowLayer = new BABYLON.GlowLayer("glow", this.scene);
        this.glowLayer.intensity = 1.5;

        this.pipeline = null;

        this.createSkybox();
        this.createAmbientParticles();
    }

    initPipeline(camera) {
        if (!camera || this.pipeline) return;

        console.log('[Renderer3D] Initializing rendering pipeline with camera:', camera.name);

        this.pipeline = new BABYLON.DefaultRenderingPipeline(
            "defaultPipeline",
            true,
            this.scene,
            [camera]
        );

        this.pipeline.bloomEnabled = true;
        this.pipeline.bloomThreshold = 0.8;
        this.pipeline.bloomWeight = 0.3;
        this.pipeline.bloomKernel = 64;
        this.pipeline.bloomScale = 0.5;

        this.pipeline.chromaticAberrationEnabled = true;
        this.pipeline.chromaticAberration.aberrationAmount = 5;

        this.pipeline.sharpenEnabled = true;
        this.pipeline.sharpen.edgeAmount = 0.2;

        this.pipeline.grainEnabled = true;
        this.pipeline.grain.intensity = 5;
        this.pipeline.grain.animated = true;

        if (this.crystalMesh && this.crystalMesh.mesh && !this.vls) {
            this.initGodRays(this.crystalMesh.mesh);
        }
    }

    initGodRays(mesh) {
        if (this.vls || !mesh || !this.scene || !this.scene.activeCamera) return;
        try {
            this.vls = new BABYLON.VolumetricLightScatteringPostProcess(
                'vls', 1.0, this.scene.activeCamera, mesh, 100,
                BABYLON.Texture.BILINEAR_SAMPLINGMODE, this.engine, false
            );
            this.vls.exposure = 0.2;
            this.vls.decay = 0.95;
            this.vls.weight = 0.7;
            this.vls.density = 0.5;
        } catch (e) {
            console.error('[Renderer3D] Failed to initialize God Rays:', e);
            this.vls = null;
        }
    }

    createSkybox() {
        const skybox = BABYLON.MeshBuilder.CreateSphere(
            "stars", { diameter: 5000, segments: 8 }, this.scene
        );
        const skyboxMaterial = new BABYLON.StandardMaterial("starsMate", this.scene);
        skyboxMaterial.backFaceCulling = false;
        skyboxMaterial.disableLighting = true;
        skybox.material = skyboxMaterial;
        skybox.infiniteDistance = true;

        const starTexture = new BABYLON.DynamicTexture("starTexture", 512, this.scene);
        const ctx = starTexture.getContext();
        ctx.fillStyle = "black";
        ctx.fillRect(0, 0, 512, 512);

        for (let i = 0; i < 500; i++) {
            const x = Math.random() * 512;
            const y = Math.random() * 512;
            const size = Math.random() * 1.5;
            const alpha = 0.2 + Math.random() * 0.8;
            ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
            ctx.beginPath();
            ctx.arc(x, y, size, 0, Math.PI * 2);
            ctx.fill();
        }
        starTexture.update();

        skyboxMaterial.emissiveTexture = starTexture;
        skyboxMaterial.diffuseColor = new BABYLON.Color3(0, 0, 0);
        skyboxMaterial.specularColor = new BABYLON.Color3(0, 0, 0);

        this.scene.onBeforeRenderObservable.add(() => {
            skybox.rotation.y += 0.0002;
            skybox.rotation.x += 0.0001;
        });
    }

    createAmbientParticles() {
        const particleSystem = new BABYLON.ParticleSystem("ambientParticles", 2000, this.scene);

        const texture = new BABYLON.DynamicTexture("pTex", 32, this.scene);
        const ctxP = texture.getContext();
        ctxP.fillStyle = "white";
        ctxP.beginPath();
        ctxP.arc(16, 16, 8, 0, Math.PI * 2);
        ctxP.fill();
        texture.update();

        particleSystem.particleTexture = texture;
        particleSystem.emitter = new BABYLON.Vector3(
            (BOARD_WIDTH * CELL_SIZE) / 2,
            0,
            (BOARD_HEIGHT * CELL_SIZE) / 2
        );

        particleSystem.minEmitBox = new BABYLON.Vector3(-400, 0, -400);
        particleSystem.maxEmitBox = new BABYLON.Vector3(400, 200, 400);

        particleSystem.color1 = new BABYLON.Color4(0.4, 0.8, 1.0, 0.3);
        particleSystem.color2 = new BABYLON.Color4(0.2, 0.5, 1.0, 0.2);
        particleSystem.colorDead = new BABYLON.Color4(0, 0, 0.2, 0.0);

        particleSystem.minSize = 0.5;
        particleSystem.maxSize = 2.0;
        particleSystem.minLifeTime = 10;
        particleSystem.maxLifeTime = 20;
        particleSystem.emitRate = 100;
        particleSystem.gravity = new BABYLON.Vector3(0, 0, 0);
        particleSystem.direction1 = new BABYLON.Vector3(-1, 1, -1);
        particleSystem.direction2 = new BABYLON.Vector3(1, 1, 1);
        particleSystem.minAngularSpeed = 0;
        particleSystem.maxAngularSpeed = Math.PI;
        particleSystem.minEmitPower = 0.1;
        particleSystem.maxEmitPower = 0.5;
        particleSystem.updateSpeed = 0.005;

        particleSystem.start();
    }

    createBoard() {
        const boardMeshes = [];

        for (let x = 0; x <= BOARD_WIDTH; x++) {
            for (let y = 0; y <= BOARD_HEIGHT; y++) {
                const worldX = x * CELL_SIZE;
                const worldZ = y * CELL_SIZE;

                const line = BABYLON.MeshBuilder.CreateLines(
                    `gridLine_${x}_${y}`,
                    {
                        points: [
                            new BABYLON.Vector3(worldX, 0, worldZ),
                            new BABYLON.Vector3(worldX, WALL_HEIGHT, worldZ),
                        ],
                    },
                    this.scene,
                );
                line.color = CYAN_GLOW;
                boardMeshes.push(line);
            }
        }

        for (let y = 0; y <= BOARD_HEIGHT; y++) {
            for (let x = 0; x < BOARD_WIDTH; x++) {
                const worldZ = y * CELL_SIZE;
                const x1 = x * CELL_SIZE;
                const x2 = (x + 1) * CELL_SIZE;

                const line = BABYLON.MeshBuilder.CreateLines(
                    `hLineX_${x}_${y}`,
                    {
                        points: [
                            new BABYLON.Vector3(x1, WALL_HEIGHT, worldZ),
                            new BABYLON.Vector3(x2, WALL_HEIGHT, worldZ),
                        ],
                    },
                    this.scene,
                );
                line.color = CYAN_GLOW;
                boardMeshes.push(line);
            }
        }

        for (let x = 0; x <= BOARD_WIDTH; x++) {
            for (let y = 0; y < BOARD_HEIGHT; y++) {
                const worldX = x * CELL_SIZE;
                const z1 = y * CELL_SIZE;
                const z2 = (y + 1) * CELL_SIZE;

                const line = BABYLON.MeshBuilder.CreateLines(
                    `hLineY_${x}_${y}`,
                    {
                        points: [
                            new BABYLON.Vector3(worldX, WALL_HEIGHT, z1),
                            new BABYLON.Vector3(worldX, WALL_HEIGHT, z2),
                        ],
                    },
                    this.scene,
                );
                line.color = CYAN_GLOW;
                boardMeshes.push(line);
            }
        }

        this.board3D = boardMeshes;
        console.log("Board created with", boardMeshes.length, "meshes");

        const ground = BABYLON.MeshBuilder.CreateGround(
            "boardGround",
            { width: BOARD_WIDTH * CELL_SIZE, height: BOARD_HEIGHT * CELL_SIZE },
            this.scene,
        );
        ground.position = new BABYLON.Vector3(
            (BOARD_WIDTH * CELL_SIZE) / 2,
            0,
            (BOARD_HEIGHT * CELL_SIZE) / 2
        );

        const groundMat = new BABYLON.PBRMaterial("groundMat", this.scene);
        groundMat.albedoColor = new BABYLON.Color3(0.02, 0.02, 0.05);
        groundMat.metallic = 0.1;
        groundMat.roughness = 0.8;

        const gridTexture = new BABYLON.DynamicTexture("gridTexture", 1024, this.scene);
        const ctxG = gridTexture.getContext();
        ctxG.fillStyle = "black";
        ctxG.fillRect(0, 0, 1024, 1024);

        ctxG.strokeStyle = "rgba(0, 200, 255, 0.2)";
        ctxG.lineWidth = 2;
        const spacing = 1024 / BOARD_WIDTH;
        for (let i = 0; i <= BOARD_WIDTH; i++) {
            ctxG.beginPath();
            ctxG.moveTo(i * spacing, 0);
            ctxG.lineTo(i * spacing, 1024);
            ctxG.stroke();

            ctxG.beginPath();
            ctxG.moveTo(0, i * spacing);
            ctxG.lineTo(1024, i * spacing);
            ctxG.stroke();
        }
        gridTexture.update();

        groundMat.emissiveTexture = gridTexture;
        groundMat.emissiveColor = new BABYLON.Color3(1, 1, 1);
        groundMat.opacityTexture = gridTexture;
        ground.material = groundMat;
        ground.isPickable = true;

        this.scene.onBeforeRenderObservable.add(() => {
            const pulse = 0.1 + Math.sin(Date.now() * 0.001) * 0.05;
            groundMat.emissiveIntensity = pulse * 10;
        });

        this.board3D.push(ground);
    }

    updateGameState(gameState) {
        this.createSpecialCells(gameState);
        this.updateTokens(gameState);
        this.checkMysteryLandings(gameState);
        this.updateSpecialCellColors(gameState);
        this.checkCrystalEffectTrigger(gameState);
    }

    startRenderLoop() {
        this.engine.runRenderLoop(() => {
            if (this.scene) {
                this.animationTime += 0.016;
                this.updateAnimations();
                if (this._cameraUpdateCallback) {
                    this._cameraUpdateCallback();
                }
                this.scene.render();
            }
        });
    }

    setCameraUpdateCallback(callback) {
        this._cameraUpdateCallback = callback;
    }

    loadSounds() {
        this.audioManager.initAudioContext();
        this.audioManager.loadBackgroundMusic();
        this.audioManager.loadGeneratorHums();
        this.audioManager.loadSoundEffects();
    }

    playSound(soundName) {
        if (this.audioManager.soundEffects.has(soundName)) {
            this.audioManager.playSound(soundName);
        } else {
            this.audioManager.playSynthesizedSound(soundName);
        }
    }

    toggleMusic() {
        this.audioManager.toggleMusic();
    }

    updateGeneratorHums(generators) {
        this.audioManager.updateGeneratorHums(generators);
    }

    dispose() {
        if (this.audioManager) {
            this.audioManager.cleanup();
        }

        if (this.scene) this.scene.dispose();
        if (this.engine) this.engine.dispose();
    }
}

export { Renderer3D };
