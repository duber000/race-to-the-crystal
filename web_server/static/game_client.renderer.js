/**
 * Renderer3D - Babylon.js scene, tokens, board, and special cells rendering
 *
 * Responsibilities:
 * - Scene initialization and render loop
 * - Board grid creation
 * - Token creation and updates
 * - Generator, crystal, and mystery square rendering
 * - Hover and valid move indicators
 * - Animations (mystery, particles, victory effects)
 * - Sound effects
 *
 * Usage:
 *   const renderer = new Renderer3D(canvas);
 *   renderer.initScene();
 *   renderer.updateGameState(gameState);
 *   renderer.startRenderLoop();
 */

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

        // Local player ID for crystal effects filtering
        this.localPlayerId = null;

        this.animationTime = 0;
        this.animationCallbacks = new Map();

        // Track last processed mystery event to avoid duplicates
        this.lastProcessedMysteryEvent = null;

        // Crystal effect animator
        this.crystalEffectAnimator = null;

        this.audioContext = null;
        this.soundsEnabled = true;

        // Background music and generator hums
        this.backgroundMusic = null;
        this.generatorHums = [];
        this.musicVolume = 0.3;
        this.humVolume = 0.2;
        this.musicEnabled = true;
    }

    // ==========================================================================
    // Scene Initialization
    // ==========================================================================

    initScene() {
        // Get device-specific rendering configuration
        const renderConfig = this.deviceCapabilities ?
            this.deviceCapabilities.getRenderingConfig() :
            { hardwareScaling: 1.0, antialiasing: true };

        console.log('[Renderer3D] Initializing scene with config:', renderConfig);

        // Create engine with adaptive antialiasing
        this.engine = new BABYLON.Engine(this.canvas, renderConfig.antialiasing);

        this.scene = new BABYLON.Scene(this.engine);
        this.scene.clearColor = new BABYLON.Color4(0, 0, 0, 1);

        // Apply performance optimizations for mobile
        this.applyPerformanceSettings(renderConfig);

        this.initLights();
        this.createBoard();

        // Initialize crystal effect animator
        this.crystalEffectAnimator = new CrystalEffectAnimator(this.scene);

        return this.scene;
    }

    /**
     * Apply performance optimizations based on device capabilities
     * @param {object} renderConfig - Rendering configuration from device capabilities
     */
    applyPerformanceSettings(renderConfig) {
        if (!this.deviceCapabilities || !this.deviceCapabilities.shouldOptimizePerformance()) {
            console.log('[Renderer3D] Using high-quality settings');
            return;
        }

        console.log('[Renderer3D] Applying mobile performance optimizations');

        // Lower hardware scaling for mobile (reduces resolution)
        this.engine.setHardwareScalingLevel(renderConfig.hardwareScaling);

        // Disable shadows (game doesn't use them currently, but good to be explicit)
        this.scene.shadowsEnabled = renderConfig.shadowsEnabled;

        // Skip frustum clipping for small scenes (performance boost)
        this.scene.skipFrustumClipping = true;

        // Disable fog if present
        this.scene.fogEnabled = false;

        // Reduce glow layer intensity on mobile for better performance
        if (this.glowLayer) {
            this.glowLayer.intensity = 1.0; // Reduced from 1.5
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

        // Main directional light for depth
        const dirLight = new BABYLON.DirectionalLight(
            "dirLight",
            new BABYLON.Vector3(-1, -2, -1),
            this.scene
        );
        dirLight.position = new BABYLON.Vector3(20, 40, 20);
        dirLight.intensity = 0.6;

        // Glow layer for emissive materials
        this.glowLayer = new BABYLON.GlowLayer("glow", this.scene);
        this.glowLayer.intensity = 1.0;

        // Post-processing pipeline setup (delayed until camera is available)
        this.pipeline = null;

        // Create a starry skybox
        this.createSkybox();

        // Create ambient particles
        this.createAmbientParticles();
    }

    /**
     * Complete the rendering pipeline setup once a camera is available
     * @param {BABYLON.Camera} camera - The camera to attach the pipeline to
     */
    initPipeline(camera) {
        if (!camera || this.pipeline) return;

        console.log('[Renderer3D] Initializing rendering pipeline with camera:', camera.name);

        this.pipeline = new BABYLON.DefaultRenderingPipeline(
            "defaultPipeline",
            true, // isHDR
            this.scene,
            [camera]
        );

        this.pipeline.bloomEnabled = true;
        this.pipeline.bloomThreshold = 0.8;
        this.pipeline.bloomWeight = 0.3;
        this.pipeline.bloomKernel = 64;
        this.pipeline.bloomScale = 0.5;

        this.pipeline.chromaticAberrationEnabled = true;
        this.pipeline.chromaticAberration.aberrationAmount = 30;

        this.pipeline.sharpenEnabled = true;
        this.pipeline.sharpen.edgeAmount = 0.2;

        this.pipeline.grainEnabled = true;
        this.pipeline.grain.intensity = 5;
        this.pipeline.grain.animated = true;
    }

    createSkybox() {
        // Create a large sphere for the skybox
        const skybox = BABYLON.MeshBuilder.CreateSphere("stars", { diameter: 5000, segments: 8 }, this.scene);
        const skyboxMaterial = new BABYLON.StandardMaterial("starsMate", this.scene);
        skyboxMaterial.backFaceCulling = false;
        skyboxMaterial.disableLighting = true;
        skybox.material = skyboxMaterial;
        skybox.infiniteDistance = true;

        // Create a procedural star texture
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

        // Apply a slow rotation to the skybox
        this.scene.onBeforeRenderObservable.add(() => {
            skybox.rotation.y += 0.0002;
            skybox.rotation.x += 0.0001;
        });
    }

    createAmbientParticles() {
        const particleSystem = new BABYLON.ParticleSystem("ambientParticles", 2000, this.scene);

        // Create a tiny white dot texture
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
        ground.position.x = (BOARD_WIDTH * CELL_SIZE) / 2 - CELL_SIZE / 2;
        ground.position.z = (BOARD_HEIGHT * CELL_SIZE) / 2 - CELL_SIZE / 2;
        ground.position.y = 0;

        const groundMat = new BABYLON.PBRMaterial("groundMat", this.scene);
        groundMat.albedoColor = new BABYLON.Color3(0.02, 0.02, 0.05);
        groundMat.metallic = 0.1;
        groundMat.roughness = 0.8;

        // Create procedural grid texture
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

        // Animate ground lines slowly
        this.scene.onBeforeRenderObservable.add(() => {
            const pulse = 0.1 + Math.sin(Date.now() * 0.001) * 0.05;
            groundMat.emissiveIntensity = pulse * 10;
        });

        this.board3D.push(ground);
    }

    // ==========================================================================
    // Game State Rendering
    // ==========================================================================

    updateGameState(gameState) {
        this.createSpecialCells(gameState);
        this.updateTokens(gameState);
        this.checkMysteryLandings(gameState);
        this.updateSpecialCellColors(gameState);
        this.checkCrystalEffectTrigger(gameState);
    }

    createSpecialCells(gameState) {
        this.specialCellMeshes.forEach((mesh) => mesh.dispose());
        this.specialCellMeshes = [];
        this.generatorMeshes.clear();
        this.crystalMesh = null;

        // Dispose old generator line segments
        this.generatorLineMeshes.forEach((lineData) => {
            if (lineData.segments) {
                lineData.segments.forEach(seg => {
                    if (seg) seg.dispose();
                });
            }
        });
        this.generatorLineMeshes = [];

        if (gameState.generators) {
            gameState.generators.forEach((gen) => {
                const centerX = gen.position[0] * CELL_SIZE + CELL_SIZE / 2;
                const centerZ = gen.position[1] * CELL_SIZE + CELL_SIZE / 2;

                const baseSize = CELL_SIZE * 0.6;
                const baseHeight = WALL_HEIGHT * 0.6;
                const cubes = [];

                // Create 10 glow layers (enhanced from original single box)
                for (let i = 10; i > 0; i--) {
                    const glowSize = baseSize + (i * 5); // Larger glow spread
                    const glowHeight = baseHeight + (i * 3);
                    const glowAlpha = (150 / (i + 0.5)) / 255; // Increased base alpha

                    const glowCube = BABYLON.MeshBuilder.CreateBox(
                        `generator_glow_${gen.position[0]}_${gen.position[1]}_${i}`,
                        { size: glowSize, height: glowHeight },
                        this.scene,
                    );
                    glowCube.position = new BABYLON.Vector3(
                        centerX,
                        WALL_HEIGHT * 0.3,
                        centerZ,
                    );

                    const glowMaterial = new BABYLON.StandardMaterial(`genGlowMat_${i}`, this.scene);
                    glowMaterial.emissiveColor = ORANGE_GLOW;
                    glowMaterial.wireframe = true;
                    glowMaterial.alpha = gen.is_disabled ? glowAlpha * 0.3 : glowAlpha * 0.8;
                    glowCube.material = glowMaterial;

                    this.specialCellMeshes.push(glowCube);
                    cubes.push(glowCube);
                }

                // Main bright cube
                const cube = BABYLON.MeshBuilder.CreateBox(
                    `generator_${gen.position[0]}_${gen.position[1]}`,
                    { size: baseSize, height: baseHeight },
                    this.scene,
                );
                cube.position = new BABYLON.Vector3(
                    centerX,
                    WALL_HEIGHT * 0.3,
                    centerZ,
                );

                const material = new BABYLON.PBRMaterial("generatorMat", this.scene);
                material.emissiveColor = ORANGE_GLOW;
                material.albedoColor = new BABYLON.Color3(0.1, 0.05, 0);
                material.metallic = 0.8;
                material.roughness = 0.2;
                material.emissiveIntensity = gen.is_disabled ? 0.3 : 1.5;
                material.alpha = gen.is_disabled ? 0.3 : 1.0;
                cube.material = material;

                // Rotational animation for active generators
                if (!gen.is_disabled) {
                    this.scene.onBeforeRenderObservable.add(() => {
                        cube.rotation.y += 0.02;
                        cube.rotation.x += 0.01;
                    });
                }

                this.specialCellMeshes.push(cube);
                cubes.push(cube);

                this.generatorMeshes.set(`${gen.position[0]},${gen.position[1]}`, {
                    mesh: cube,
                    glowMeshes: cubes,
                    position: gen.position,
                    isDisabled: gen.is_disabled,
                    lastOwner: null,
                });
            });

            if (gameState.crystal) {
                this.createGeneratorLines(gameState);
            }
        }

        if (gameState.crystal) {
            const centerX = gameState.crystal.position[0] * CELL_SIZE + CELL_SIZE / 2;
            const centerZ = gameState.crystal.position[1] * CELL_SIZE + CELL_SIZE / 2;

            // Make crystal MUCH taller and span 2x2 cells (4 squares)
            const crystalBase = CELL_SIZE * 2.5;  // Spans 2.5 cells diameter
            const crystalHeight = WALL_HEIGHT * 3.0;  // 3x taller than original

            // Create multiple glow layers for the crystal
            const glowLayers = 6;
            for (let i = glowLayers; i > 0; i--) {
                const glowBase = crystalBase + (i * 8);
                const glowHeight = crystalHeight + (i * 6);
                const glowAlpha = (120 / (i + 1)) / 255;

                const glowPyramid = BABYLON.MeshBuilder.CreateCylinder(
                    `crystal_glow_${i}`,
                    { diameterTop: 0, diameterBottom: glowBase, height: glowHeight, tessellation: 4 },
                    this.scene,
                );
                glowPyramid.position = new BABYLON.Vector3(centerX, glowHeight / 2, centerZ);

                const glowMaterial = new BABYLON.StandardMaterial(`crystalGlowMat_${i}`, this.scene);
                glowMaterial.emissiveColor = MAGENTA_GLOW;
                glowMaterial.wireframe = true;
                glowMaterial.alpha = glowAlpha;
                glowPyramid.material = glowMaterial;

                this.specialCellMeshes.push(glowPyramid);
            }

            // Main bright pyramid
            const pyramid = BABYLON.MeshBuilder.CreateCylinder(
                "crystal",
                { diameterTop: 0, diameterBottom: crystalBase, height: crystalHeight, tessellation: 4 },
                this.scene,
            );
            pyramid.position = new BABYLON.Vector3(centerX, crystalHeight / 2, centerZ);

            const material = new BABYLON.PBRMaterial("crystalPBR", this.scene);
            material.emissiveColor = MAGENTA_GLOW;
            material.albedoColor = new BABYLON.Color3(0, 0, 0);
            material.metallic = 0.9;
            material.roughness = 0.1;
            material.emissiveIntensity = 2.0;
            material.alpha = 0.8;
            material.transparencyMode = BABYLON.PBRMaterial.PBRMATERIAL_ALPHABLEND;
            pyramid.material = material;

            // Add a point light to the crystal
            const crystalLight = new BABYLON.PointLight("crystalLight", pyramid.position, this.scene);
            crystalLight.diffuse = MAGENTA_GLOW;
            crystalLight.intensity = 0.8;
            crystalLight.range = CELL_SIZE * 15;

            // Animate crystal light pulsing
            this.scene.onBeforeRenderObservable.add(() => {
                const pulse = 0.6 + Math.sin(Date.now() * 0.002) * 0.4;
                crystalLight.intensity = pulse;
                pyramid.rotation.y += 0.01;
            });

            this.specialCellMeshes.push(pyramid);
            this.specialCellMeshes.push(crystalLight);
            this.crystalMesh = { mesh: pyramid, position: gameState.crystal.position, tokenCounts: {} };
        }

        if (gameState.board && gameState.board.grid) {
            for (let y = 0; y < gameState.board.grid.length; y++) {
                for (let x = 0; x < gameState.board.grid[y].length; x++) {
                    const cell = gameState.board.grid[y][x];
                    if (cell.cell_type === 4) {
                        this.createMysteryRing(x, y);
                    }
                }
            }
        }
    }

    createMysteryRing(x, y) {
        const centerX = x * CELL_SIZE + CELL_SIZE / 2;
        const centerZ = y * CELL_SIZE + CELL_SIZE / 2;

        const ring = BABYLON.MeshBuilder.CreateTorus(
            `mystery_${x}_${y}`,
            { diameter: CELL_SIZE * 0.7, thickness: 3, tessellation: 16 },
            this.scene,
        );
        ring.position = new BABYLON.Vector3(centerX, WALL_HEIGHT * 0.5, centerZ);
        ring.rotation.z = Math.PI / 2;

        const material = new BABYLON.PBRMaterial("mysteryMat", this.scene);
        material.emissiveColor = CYAN_GLOW.clone();
        material.albedoColor = new BABYLON.Color3(0, 0, 0);
        material.metallic = 0.5;
        material.roughness = 0.2;
        material.emissiveIntensity = 2.0;
        material.alpha = 0.6;
        material.transparencyMode = BABYLON.PBRMaterial.PBRMATERIAL_ALPHABLEND;
        ring.material = material;

        // Animated rotation
        this.scene.onBeforeRenderObservable.add(() => {
            ring.rotation.x += 0.05;
            ring.rotation.y += 0.02;
        });

        this.glowLayer.addIncludedOnlyMesh(ring);
        this.specialCellMeshes.push(ring);
        this.mysteryRings.push(ring);
    }

    createGeneratorLines(gameState) {
        if (!gameState.generators || !gameState.crystal) return;

        const crystalX = gameState.crystal.position[0] * CELL_SIZE + CELL_SIZE / 2;
        const crystalZ = gameState.crystal.position[1] * CELL_SIZE + CELL_SIZE / 2;
        const crystalY = WALL_HEIGHT * 2.5;  // Connect to top of taller crystal

        gameState.generators.forEach((gen) => {
            if (gen.is_disabled) return;

            const genX = gen.position[0] * CELL_SIZE + CELL_SIZE / 2;
            const genZ = gen.position[1] * CELL_SIZE + CELL_SIZE / 2;
            const genY = WALL_HEIGHT * 0.6;

            // Create data structure for animated flowing segments
            this.generatorLineMeshes.push({
                genX, genY, genZ,
                crystalX, crystalY, crystalZ,
                genPosition: gen.position,
                segments: []
            });
        });
    }

    // ==========================================================================
    // Token Rendering
    // ==========================================================================

    /**
     * Check if local player has a specific crystal effect active
     */
    hasEffect(gameState, effectType) {
        if (!this.localPlayerId || !gameState.crystal_effects) {
            return false;
        }

        const playerEffects = gameState.crystal_effects.player_effects?.[this.localPlayerId];
        if (!playerEffects || !playerEffects.active_effects) {
            return false;
        }

        return playerEffects.active_effects.some(
            (effect) => effect.effect_type === effectType && effect.turns_remaining > 0
        );
    }

    /**
     * Filter tokens based on fog of war effect
     */
    filterVisibleTokens(gameState, allTokens) {
        const hasFog = this.hasEffect(gameState, CrystalEffect.FOG_OF_WAR);

        if (!hasFog) {
            return allTokens;
        }

        // With fog of war, only show own tokens
        return allTokens.filter((token) => token.player_id === this.localPlayerId);
    }

    /**
     * Get phantom tokens for local player
     */
    getPhantomTokens(gameState) {
        if (!this.localPlayerId || !gameState.crystal_effects) {
            return [];
        }

        const playerEffects = gameState.crystal_effects.player_effects?.[this.localPlayerId];
        return playerEffects?.phantom_tokens || [];
    }

    updateTokens(gameState) {
        // Collect all alive, deployed tokens
        const allTokens = [];
        for (const player of Object.values(gameState.players)) {
            for (const tokenId of player.token_ids) {
                const token = gameState.tokens[tokenId];
                if (token && token.is_alive && token.is_deployed) {
                    allTokens.push(token);
                }
            }
        }

        // Filter visible tokens based on crystal effects
        const visibleTokens = this.filterVisibleTokens(gameState, allTokens);
        const visibleTokenIds = new Set(visibleTokens.map((t) => t.id));

        // Remove tokens that are no longer visible
        for (const [tokenId, tokenData] of this.tokens3D) {
            if (!visibleTokenIds.has(tokenId)) {
                tokenData.mesh.dispose();
                if (tokenData.healthLabel) {
                    tokenData.healthLabel.dispose();
                }
                this.tokens3D.delete(tokenId);
            }
        }

        // Update or create visible tokens
        for (const token of visibleTokens) {
            const player = Object.values(gameState.players).find((p) =>
                p.token_ids.includes(token.id)
            );
            const playerColor = player ? PLAYER_COLORS[player.color] || PLAYER_COLORS[0] : PLAYER_COLORS[0];

            if (this.tokens3D.has(token.id)) {
                this.updateTokenPosition(token.id, token);
            } else {
                this.createToken3D(token, playerColor);
            }
        }

        // Update phantom tokens
        this.updatePhantomTokens(gameState);
    }

    /**
     * Update phantom tokens based on crystal effects
     */
    updatePhantomTokens(gameState) {
        const phantoms = this.getPhantomTokens(gameState);
        const phantomIds = new Set(phantoms.map((p) => p.phantom_id));

        // Remove old phantoms
        for (const [phantomId, phantomData] of this.phantomTokens3D) {
            if (!phantomIds.has(phantomId)) {
                phantomData.mesh.dispose();
                if (phantomData.healthLabel) {
                    phantomData.healthLabel.dispose();
                }
                this.phantomTokens3D.delete(phantomId);
            }
        }

        // Create or update phantoms
        for (const phantom of phantoms) {
            if (this.phantomTokens3D.has(phantom.phantom_id)) {
                // Update existing phantom position if needed
                const phantomData = this.phantomTokens3D.get(phantom.phantom_id);
                const worldX = phantom.position[0] * CELL_SIZE + CELL_SIZE / 2;
                const worldZ = phantom.position[1] * CELL_SIZE + CELL_SIZE / 2;
                phantomData.mesh.position.x = worldX;
                phantomData.mesh.position.z = worldZ;
            } else {
                // Create new phantom - look up player color from game state
                const player = gameState.players[phantom.apparent_player_id];
                const playerColor = player ? PLAYER_COLORS[player.color] || PLAYER_COLORS[0] : PLAYER_COLORS[0];
                this.createPhantomToken3D(phantom, playerColor);
            }
        }
    }

    createToken3D(token, playerColor) {
        const worldX = token.position[0] * CELL_SIZE + CELL_SIZE / 2;
        const worldZ = token.position[1] * CELL_SIZE + CELL_SIZE / 2;

        const hexagon = BABYLON.MeshBuilder.CreateCylinder(
            `token_${token.id}`,
            { diameter: CELL_SIZE * 0.9, height: TOKEN_HEIGHT, tessellation: 6 },
            this.scene,
        );
        hexagon.position = new BABYLON.Vector3(worldX, TOKEN_HEIGHT / 2, worldZ);

        const material = new BABYLON.PBRMaterial(`tokenMat_${token.id}`, this.scene);
        material.emissiveColor = playerColor;
        material.albedoColor = new BABYLON.Color3(0, 0, 0);
        material.metallic = 0.5;
        material.roughness = 0.4;
        material.emissiveIntensity = 1.0;
        material.alpha = 0.9;
        hexagon.material = material;

        // Add a small light beneath the token for a floor glow
        const tokenLight = new BABYLON.PointLight(`tokenLight_${token.id}`, hexagon.position, this.scene);
        tokenLight.diffuse = playerColor;
        tokenLight.intensity = 0.3;
        tokenLight.range = CELL_SIZE * 1.5;
        tokenLight.parent = hexagon;

        const healthLabel = this.createHealthLabel(token, hexagon.position);

        this.tokens3D.set(token.id, {
            mesh: hexagon,
            token: token,
            color: playerColor,
            healthLabel: healthLabel,
        });

        return hexagon;
    }

    /**
     * Create a phantom token with distinctive visual style
     */
    createPhantomToken3D(phantom, playerColor) {
        const worldX = phantom.position[0] * CELL_SIZE + CELL_SIZE / 2;
        const worldZ = phantom.position[1] * CELL_SIZE + CELL_SIZE / 2;

        const hexagon = BABYLON.MeshBuilder.CreateCylinder(
            `phantom_${phantom.phantom_id}`,
            { diameter: CELL_SIZE * 0.9, height: TOKEN_HEIGHT, tessellation: 6 },
            this.scene,
        );
        hexagon.position = new BABYLON.Vector3(worldX, TOKEN_HEIGHT / 2, worldZ);

        const material = new BABYLON.PBRMaterial(
            `phantomMat_${phantom.phantom_id}`,
            this.scene
        );
        material.emissiveColor = playerColor;
        material.albedoColor = new BABYLON.Color3(0, 0, 0);
        material.metallic = 0.2;
        material.roughness = 0.8;
        material.emissiveIntensity = 0.5;
        material.alpha = 0.4; // Semi-transparent for phantom effect
        material.transparencyMode = BABYLON.PBRMaterial.PBRMATERIAL_ALPHABLEND;

        hexagon.material = material;

        // Create health label for phantom
        const healthLabel = this.createPhantomHealthLabel(phantom, hexagon.position);

        // Add flickering animation to make it look illusory
        this.addPhantomFlickerAnimation(hexagon, material);

        this.phantomTokens3D.set(phantom.phantom_id, {
            mesh: hexagon,
            phantom: phantom,
            color: playerColor,
            healthLabel: healthLabel,
        });

        return hexagon;
    }

    /**
     * Create health label for phantom token
     */
    createPhantomHealthLabel(phantom, position) {
        const plane = BABYLON.MeshBuilder.CreatePlane(
            `phantomHealthLabel_${phantom.phantom_id}`,
            { width: CELL_SIZE * 0.6, height: CELL_SIZE * 0.3 },
            this.scene,
        );

        plane.position = new BABYLON.Vector3(position.x, position.y, position.z + TOKEN_HEIGHT);
        plane.billboardMode = BABYLON.Mesh.BILLBOARDMODE_ALL;

        const texture = new BABYLON.DynamicTexture(
            `phantomHealthTexture_${phantom.phantom_id}`,
            { width: 256, height: 128 },
            this.scene,
        );

        const ctx = texture.getContext();
        ctx.fillStyle = "black";
        ctx.fillRect(0, 0, 256, 128);
        ctx.font = "bold 80px monospace";
        ctx.fillStyle = "rgba(255, 255, 255, 0.7)"; // Semi-transparent text
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(`${phantom.apparent_health}hp`, 128, 64);
        texture.update();

        const material = new BABYLON.StandardMaterial(
            `phantomHealthMat_${phantom.phantom_id}`,
            this.scene
        );
        material.diffuseTexture = texture;
        material.emissiveTexture = texture;
        material.opacityTexture = texture;
        material.alpha = 0.7;
        plane.material = material;

        return plane;
    }

    /**
     * Add flickering animation to phantom token
     */
    addPhantomFlickerAnimation(mesh, material) {
        const flicker = new BABYLON.Animation(
            `phantomFlicker_${mesh.name}`,
            "material.alpha",
            30,
            BABYLON.Animation.ANIMATIONTYPE_FLOAT,
            BABYLON.Animation.ANIMATIONLOOPMODE_CYCLE
        );

        const keys = [
            { frame: 0, value: 0.5 },
            { frame: 15, value: 0.3 },
            { frame: 30, value: 0.5 },
        ];

        flicker.setKeys(keys);
        mesh.animations = [flicker];
        this.scene.beginAnimation(mesh, 0, 30, true);
    }

    createHealthLabel(token, position) {
        const plane = BABYLON.MeshBuilder.CreatePlane(
            `healthLabel_${token.id}`,
            { width: CELL_SIZE * 0.6, height: CELL_SIZE * 0.3 },
            this.scene,
        );

        plane.position = new BABYLON.Vector3(position.x, position.y, position.z + TOKEN_HEIGHT);
        plane.billboardMode = BABYLON.Mesh.BILLBOARDMODE_ALL;

        const texture = new BABYLON.DynamicTexture(
            `healthTexture_${token.id}`,
            { width: 256, height: 128 },
            this.scene,
        );

        const ctx = texture.getContext();
        ctx.fillStyle = "black";
        ctx.fillRect(0, 0, 256, 128);
        ctx.font = "bold 80px monospace";
        ctx.fillStyle = "white";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(`${token.health}hp`, 128, 64);
        texture.update();

        const material = new BABYLON.StandardMaterial(`healthMat_${token.id}`, this.scene);
        material.diffuseTexture = texture;
        material.emissiveTexture = texture;
        material.opacityTexture = texture;
        plane.material = material;

        return plane;
    }

    updateTokenPosition(tokenId, token) {
        const tokenData = this.tokens3D.get(tokenId);
        const worldX = token.position[0] * CELL_SIZE + CELL_SIZE / 2;
        const worldZ = token.position[1] * CELL_SIZE + CELL_SIZE / 2;

        BABYLON.Animation.CreateAndStartAnimation(
            "tokenMove",
            tokenData.mesh,
            "position",
            30,
            10,
            tokenData.mesh.position,
            new BABYLON.Vector3(worldX, TOKEN_HEIGHT / 2, worldZ),
            BABYLON.Animation.ANIMATIONLOOPMODE_CONSTANT,
        );

        if (tokenData.healthLabel) {
            BABYLON.Animation.CreateAndStartAnimation(
                "labelMove",
                tokenData.healthLabel,
                "position",
                30,
                10,
                tokenData.healthLabel.position,
                new BABYLON.Vector3(worldX, TOKEN_HEIGHT + 10, worldZ),
                BABYLON.Animation.ANIMATIONLOOPMODE_CONSTANT,
            );

            const texture = tokenData.healthLabel.material.diffuseTexture;
            const ctx = texture.getContext();
            ctx.fillStyle = "black";
            ctx.fillRect(0, 0, 256, 128);
            ctx.font = "bold 80px monospace";
            ctx.fillStyle = "white";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(`${token.health}hp`, 128, 64);
            texture.update();
        }

        tokenData.token = token;
    }

    updateTokenSelectionGlow(selectedTokenId) {
        this.tokens3D.forEach((tokenData, tokenId) => {
            if (tokenData.mesh && tokenData.mesh.material) {
                tokenData.mesh.material.emissiveColor = tokenData.color;
                tokenData.mesh.material.alpha = 0.9;
                tokenData.mesh.scaling = new BABYLON.Vector3(1, 1, 1);
            }
        });

        if (selectedTokenId !== null) {
            const selectedData = this.tokens3D.get(selectedTokenId);
            if (selectedData && selectedData.mesh && selectedData.mesh.material) {
                selectedData.mesh.material.emissiveColor = new BABYLON.Color3(1, 1, 1);
                selectedData.mesh.material.alpha = 1.0;
                selectedData.mesh.scaling = new BABYLON.Vector3(1.2, 1.2, 1.2);
            }
        }
    }

    // ==========================================================================
    // Indicators
    // ==========================================================================

    updateHoverIndicator(gridX, gridY) {
        if (this.hoverMesh) {
            this.hoverMesh.dispose();
            this.hoverMesh = null;
        }

        if (gridX === null || gridY === null) return;

        const centerX = gridX * CELL_SIZE + CELL_SIZE / 2;
        const centerZ = gridY * CELL_SIZE + CELL_SIZE / 2;

        const square = BABYLON.MeshBuilder.CreateGround(
            "hoverSquare",
            { width: CELL_SIZE * 0.9, height: CELL_SIZE * 0.9 },
            this.scene,
        );
        square.position = new BABYLON.Vector3(centerX, 2.0, centerZ);

        const material = new BABYLON.StandardMaterial("hoverMat", this.scene);
        material.emissiveColor = WHITE_GLOW;
        material.wireframe = true;
        material.alpha = 0.9;
        square.material = material;

        this.hoverMesh = square;
    }

    updateValidMoveIndicators(moves) {
        this.validMoveMeshes.forEach((mesh) => mesh.dispose());
        this.validMoveMeshes = [];

        if (!moves || moves.size === 0) return;

        moves.forEach(([gridX, gridY]) => {
            const centerX = gridX * CELL_SIZE + CELL_SIZE / 2;
            const centerZ = gridY * CELL_SIZE + CELL_SIZE / 2;

            const square = BABYLON.MeshBuilder.CreateGround(
                `validMove_${gridX}_${gridY}`,
                { width: CELL_SIZE * 0.8, height: CELL_SIZE * 0.8 },
                this.scene,
            );
            square.position = new BABYLON.Vector3(centerX, 1.0, centerZ);

            const material = new BABYLON.StandardMaterial("validMoveMat", this.scene);
            material.emissiveColor = GREEN_GLOW;
            material.wireframe = true;
            material.alpha = 0.7;
            square.material = material;

            this.validMoveMeshes.push(square);
        });
    }

    updateValidAttackIndicators(attacks) {
        this.validAttackMeshes.forEach((mesh) => mesh.dispose());
        this.validAttackMeshes = [];

        if (!attacks || attacks.size === 0) return;

        attacks.forEach((posKey) => {
            const [gridX, gridY] = posKey.split(',').map(Number);
            const centerX = gridX * CELL_SIZE + CELL_SIZE / 2;
            const centerZ = gridY * CELL_SIZE + CELL_SIZE / 2;

            const square = BABYLON.MeshBuilder.CreateGround(
                `validAttack_${gridX}_${gridY}`,
                { width: CELL_SIZE * 0.8, height: CELL_SIZE * 0.8 },
                this.scene,
            );
            square.position = new BABYLON.Vector3(centerX, 1.0, centerZ);

            const material = new BABYLON.StandardMaterial("validAttackMat", this.scene);
            material.emissiveColor = RED_GLOW; // Red for attacks
            material.wireframe = true;
            material.alpha = 0.7;
            square.material = material;

            this.validAttackMeshes.push(square);
        });
    }

    // ==========================================================================
    // Animations
    // ==========================================================================

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

    updateAnimations() {
        // Update flowing generator line segments
        this.generatorLineMeshes.forEach((lineData) => {
            if (!lineData.genX) return; // Skip if not initialized properly

            // Dispose old segments
            if (lineData.segments) {
                lineData.segments.forEach(seg => {
                    if (seg) seg.dispose();
                });
                lineData.segments = [];
            }

            // Create 12 flowing segments with pulsing glow
            const segments = 12;
            const flowOffset = (this.animationTime * 2.0) % 1.0; // Flow speed

            for (let i = 0; i < segments; i++) {
                // Calculate segment position along the line
                const t1 = (i / segments + flowOffset) % 1.0;
                const t2 = ((i + 1) / segments + flowOffset) % 1.0;

                // Linear interpolation along the line
                const x1 = lineData.genX + (lineData.crystalX - lineData.genX) * t1;
                const y1 = lineData.genY + (lineData.crystalY - lineData.genY) * t1;
                const z1 = lineData.genZ + (lineData.crystalZ - lineData.genZ) * t1;

                const x2 = lineData.genX + (lineData.crystalX - lineData.genX) * t2;
                const y2 = lineData.genY + (lineData.crystalY - lineData.genY) * t2;
                const z2 = lineData.genZ + (lineData.crystalZ - lineData.genZ) * t2;

                // Calculate brightness based on position (flowing effect)
                const brightness = Math.abs(Math.sin((t1 + flowOffset) * Math.PI)) * 0.8 + 0.2;

                // Create segment line
                const points = [
                    new BABYLON.Vector3(x1, y1, z1),
                    new BABYLON.Vector3(x2, y2, z2)
                ];

                const line = BABYLON.MeshBuilder.CreateLines(
                    `genSegment_${i}_${Date.now()}`,
                    { points: points },
                    this.scene
                );

                // Set color with brightness
                const color = ORANGE_GLOW.clone();
                color.r *= brightness;
                color.g *= brightness;
                color.b *= brightness;
                line.color = color;

                lineData.segments.push(line);
            }
        });

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
            const pulse = 1 + 0.15 * Math.sin(this.animationTime * 2); // Increased from 0.05 to 0.15 for more visible pulse
            crystal.scaling.x = pulse;
            crystal.scaling.z = pulse;
            crystal.rotation.y = this.animationTime * 0.5;

            // Apply same pulse and rotation to glow layers
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

        // Update crystal effect animator
        if (this.crystalEffectAnimator) {
            this.crystalEffectAnimator.update(0.016); // ~60fps
        }
    }

    updateMysteryAnimations() {
        this.mysteryAnimations.forEach((progress, posKey) => {
            const [x, y] = posKey.split(",").map(Number);
            const ring = this.scene.getMeshByName(`mystery_${x}_${y}`);

            if (ring) {
                // 3D coin-flip animation with perspective scaling (3 full spins)
                const rotationAngle = progress * 3 * 2 * Math.PI;

                // Horizontal perspective scaling (coin flip effect)
                const scaleX = Math.abs(Math.cos(rotationAngle));

                ring.rotation.y = rotationAngle;
                ring.scaling.x = scaleX; // Horizontal scale creates coin-flip perspective
                ring.scaling.z = 1;      // Keep vertical scale constant

                // Pulse brightness during animation
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
    }

    checkMysteryLandings(gameState) {
        if (!gameState.tokens || !gameState.board) return;

        // Check for new mystery event from server
        if (gameState.last_triggered_mystery_event) {
            const eventKey = JSON.stringify(gameState.last_triggered_mystery_event);

            // Only process if this is a new event (different from last processed)
            if (eventKey !== this.lastProcessedMysteryEvent) {
                const [tokenId, position, effect] = gameState.last_triggered_mystery_event;
                const posKey = `${position[0]},${position[1]}`;

                this.mysteryAnimations.set(posKey, 0.0);
                console.log(`Token ${tokenId} triggered mystery square at ${posKey} - Effect: ${effect}`);
                this.playSound("mystery");

                // Mark this event as processed
                this.lastProcessedMysteryEvent = eventKey;
            }
        }

        // Clean up completed animations
        for (const [posKey, progress] of this.mysteryAnimations) {
            if (progress >= 1.0) {
                this.mysteryAnimations.delete(posKey);
            }
        }
    }

    isMysterySquare(x, y, gameState) {
        if (!gameState.board || !gameState.board.grid) return false;
        if (y < 0 || y >= gameState.board.grid.length) return false;
        if (x < 0 || x >= gameState.board.grid[y].length) return false;
        return gameState.board.grid[y][x].cell_type === 4;
    }

    checkCrystalEffectTrigger(gameState) {
        // Check if a crystal effect was just triggered
        if (!gameState.last_triggered_crystal_effect || !this.crystalEffectAnimator) return;
        if (!gameState.crystal) return;

        const [affectedPlayerId, effectType] = gameState.last_triggered_crystal_effect;

        // Get affected tokens for lightning effect
        let affectedTokens = [];
        if (effectType === CrystalEffect.DAMAGE_BOOST) {
            affectedTokens = Object.values(gameState.tokens || {}).filter(
                t => t.player_id === affectedPlayerId && t.is_deployed && t.is_alive
            );
        }

        // Start animation
        this.crystalEffectAnimator.startEffect(
            effectType,
            gameState.crystal.position,
            affectedTokens
        );

        // Play sound effect
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
    }

    // ==========================================================================
    // Special Cell Colors
    // ==========================================================================

    updateSpecialCellColors(gameState) {
        if (!gameState.tokens || !gameState.generators) return;

        const playerColors = this.getPlayerColors(gameState);

        gameState.generators.forEach((gen) => {
            const posKey = `${gen.position[0]},${gen.position[1]}`;
            const genMeshData = this.generatorMeshes.get(posKey);
            if (!genMeshData) return;

            const tokensHere = [];
            for (const token of Object.values(gameState.tokens)) {
                if (!token.is_deployed || !token.is_alive) continue;
                if (token.position[0] === gen.position[0] && token.position[1] === gen.position[1]) {
                    tokensHere.push(token);
                }
            }

            let dominantPlayer = null;
            let maxCount = 0;
            const playerCounts = {};
            for (const token of tokensHere) {
                for (const [playerId, player] of Object.entries(gameState.players || {})) {
                    if (player.token_ids && player.token_ids.includes(token.id)) {
                        playerCounts[playerId] = (playerCounts[playerId] || 0) + 1;
                        if (playerCounts[playerId] > maxCount) {
                            maxCount = playerCounts[playerId];
                            dominantPlayer = playerId;
                        }
                        break;
                    }
                }
            }

            // Stop generator hum when captured
            if (gen.is_disabled && !genMeshData.isDisabled) {
                this.triggerExplosion(gen.position, ORANGE_GLOW);
                this.playSound("capture");

                const genIndex = gameState.generators.indexOf(gen);
                if (genIndex >= 0 && genIndex < this.generatorHums.length) {
                    const hum = this.generatorHums[genIndex];
                    if (hum && this.musicEnabled) {
                        hum.pause();
                        hum.currentTime = 0;
                        console.log(`Generator ${genIndex} disabled - hum stopped`);
                    }
                }
            }

            if (dominantPlayer && playerCounts[dominantPlayer] >= 2 && !gen.is_disabled) {
                const color = playerColors[dominantPlayer] || ORANGE_GLOW;
                genMeshData.mesh.material.emissiveColor = color;
                genMeshData.mesh.material.alpha = 1.0;
                // Update glow layers too
                if (genMeshData.glowMeshes) {
                    genMeshData.glowMeshes.forEach(glowMesh => {
                        if (glowMesh && glowMesh.material) {
                            glowMesh.material.emissiveColor = color;
                        }
                    });
                }
                genMeshData.lastOwner = dominantPlayer;
            } else if (gen.is_disabled) {
                genMeshData.mesh.material.emissiveColor = new BABYLON.Color3(0.3, 0.3, 0.3);
                genMeshData.mesh.material.alpha = 0.3;
                // Update glow layers too
                if (genMeshData.glowMeshes) {
                    genMeshData.glowMeshes.forEach(glowMesh => {
                        if (glowMesh && glowMesh.material) {
                            glowMesh.material.emissiveColor = new BABYLON.Color3(0.3, 0.3, 0.3);
                            glowMesh.material.alpha *= 0.3;
                        }
                    });
                }
                genMeshData.lastOwner = null;
            } else {
                genMeshData.mesh.material.emissiveColor = ORANGE_GLOW;
                genMeshData.mesh.material.alpha = 0.8;
                // Update glow layers too
                if (genMeshData.glowMeshes) {
                    genMeshData.glowMeshes.forEach(glowMesh => {
                        if (glowMesh && glowMesh.material) {
                            glowMesh.material.emissiveColor = ORANGE_GLOW;
                        }
                    });
                }
                genMeshData.lastOwner = null;
            }

            genMeshData.isDisabled = gen.is_disabled;
        });

        if (this.crystalMesh && gameState.crystal) {
            const tokensAtCrystal = [];
            for (const token of Object.values(gameState.tokens)) {
                if (!token.is_deployed || !token.is_alive) continue;
                if (token.position[0] === gameState.crystal.position[0] && token.position[1] === gameState.crystal.position[1]) {
                    tokensAtCrystal.push(token);
                }
            }

            const crystalCounts = {};
            let dominantPlayer = null;
            let maxCount = 0;
            for (const token of tokensAtCrystal) {
                for (const [playerId, player] of Object.entries(gameState.players || {})) {
                    if (player.token_ids && player.token_ids.includes(token.id)) {
                        crystalCounts[playerId] = (crystalCounts[playerId] || 0) + 1;
                        if (crystalCounts[playerId] > maxCount) {
                            maxCount = crystalCounts[playerId];
                            dominantPlayer = playerId;
                        }
                        break;
                    }
                }
            }

            if (dominantPlayer && crystalCounts[dominantPlayer] >= 2) {
                const color = playerColors[dominantPlayer] || MAGENTA_GLOW;
                this.crystalMesh.mesh.material.emissiveColor = color;
            } else {
                this.crystalMesh.mesh.material.emissiveColor = MAGENTA_GLOW;
            }

            this.crystalMesh.tokenCounts = crystalCounts;
        }
    }

    getPlayerColors(gameState) {
        const colors = {};
        const colorValues = [
            new BABYLON.Color3(1, 0, 0),
            new BABYLON.Color3(0, 0, 1),
            new BABYLON.Color3(0, 1, 0),
            new BABYLON.Color3(1, 1, 0),
        ];

        for (const [playerId, player] of Object.entries(gameState.players || {})) {
            const colorIndex = parseInt(playerId.split("_")[1]) || 0;
            colors[playerId] = colorValues[colorIndex % colorValues.length];
        }
        return colors;
    }

    // ==========================================================================
    // Effects
    // ==========================================================================

    triggerExplosion(position, color) {
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
    }

    updateExplosionParticles() {
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
    }

    triggerVictoryEffect() {
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
    }

    // ==========================================================================
    // Sound Effects
    // ==========================================================================

    loadSounds() {
        this.audioContext = null;
        this.soundsEnabled = true;

        // Load background music
        this.loadBackgroundMusic();

        // Load 4 generator hum tracks
        this.loadGeneratorHums();
    }

    loadBackgroundMusic() {
        try {
            this.backgroundMusic = new Audio('/static/assets/music/techno.mp3');
            this.backgroundMusic.loop = true;
            this.backgroundMusic.volume = this.musicVolume;

            // Try to play, but handle autoplay restrictions
            const playPromise = this.backgroundMusic.play();
            if (playPromise !== undefined) {
                playPromise.then(() => {
                    console.log("Background music playing");
                }).catch(e => {
                    console.log("Background music autoplay blocked, will start on user interaction");
                    // Add click listener to start music on first interaction
                    document.addEventListener('click', () => {
                        if (this.backgroundMusic && this.musicEnabled) {
                            this.backgroundMusic.play().catch(() => { });
                        }
                    }, { once: true });
                });
            }
        } catch (e) {
            console.error("Error loading background music:", e);
        }
    }

    loadGeneratorHums() {
        for (let i = 0; i < 4; i++) {
            try {
                const hum = new Audio(`/static/assets/music/generator_${i}_hum.wav`);
                hum.loop = true;
                hum.volume = this.humVolume;

                // Try to play immediately
                const playPromise = hum.play();
                if (playPromise !== undefined) {
                    playPromise.then(() => {
                        console.log(`Generator ${i} hum playing`);
                    }).catch(e => {
                        console.log(`Generator ${i} hum autoplay blocked`);
                        // Will be started by user interaction trigger
                        document.addEventListener('click', () => {
                            if (this.musicEnabled) {
                                hum.play().catch(() => { });
                            }
                        }, { once: true });
                    });
                }

                this.generatorHums.push(hum);
            } catch (e) {
                console.error(`Error loading generator ${i} hum:`, e);
                this.generatorHums.push(null);
            }
        }
    }

    toggleMusic() {
        this.musicEnabled = !this.musicEnabled;

        if (this.musicEnabled) {
            // Resume music
            if (this.backgroundMusic) {
                this.backgroundMusic.play().catch(e => console.log("Music play failed:", e));
            }
            // Resume active generator hums
            this.generatorHums.forEach((hum) => {
                if (hum && hum.paused) {
                    hum.play().catch(() => { });
                }
            });
        } else {
            // Pause all audio
            if (this.backgroundMusic) {
                this.backgroundMusic.pause();
            }
            this.generatorHums.forEach(hum => {
                if (hum) hum.pause();
            });
        }

        console.log(this.musicEnabled ? "Music enabled" : "Music disabled");
    }

    getAudioContext() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        return this.audioContext;
    }

    playSound(soundName) {
        if (!this.soundsEnabled) return;

        try {
            const ctx = this.getAudioContext();
            if (ctx.state === "suspended") {
                ctx.resume();
            }
            this.synthesizeSound(soundName, ctx);
        } catch (e) {
        }
    }

    synthesizeSound(soundName, ctx) {
        const now = ctx.currentTime;

        switch (soundName) {
            case "move": this.playSlidingSound(ctx, now); break;
            case "attack": this.playFlushingSound(ctx, now); break;
            case "capture": this.playGeneratorExplosionSound(ctx, now); break;
            case "crystal": this.playCrystalShatterSound(ctx, now); break;
            case "mystery": this.playMysteryBingSound(ctx, now); break;
            case "fog_horn": this.playFogHornSound(ctx, now); break;
            case "ghost": this.playGhostSound(ctx, now); break;
            case "lightning": this.playLightningSound(ctx, now); break;
            case "whoosh": this.playWhooshSound(ctx, now); break;
            default: this.playDeploySound(ctx, now); break;
        }
    }

    playSlidingSound(ctx, now) {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const filter = ctx.createBiquadFilter();

        osc.type = "sawtooth";
        osc.frequency.setValueAtTime(1000, now);
        osc.frequency.exponentialRampToValueAtTime(200, now + 0.5);

        filter.type = "lowpass";
        filter.frequency.setValueAtTime(2000, now);
        filter.frequency.exponentialRampToValueAtTime(500, now + 0.5);

        gain.gain.setValueAtTime(0.1, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.5);

        osc.connect(filter);
        filter.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        osc.stop(now + 0.5);
    }

    playFlushingSound(ctx, now) {
        const duration = 2.0;
        const noiseBuffer = ctx.createBuffer(1, ctx.sampleRate * duration, ctx.sampleRate);
        const noiseData = noiseBuffer.getChannelData(0);
        for (let i = 0; i < noiseData.length; i++) {
            noiseData[i] = Math.random() * 2 - 1;
        }

        const noise = ctx.createBufferSource();
        noise.buffer = noiseBuffer;

        const noiseFilter = ctx.createBiquadFilter();
        noiseFilter.type = "bandpass";
        noiseFilter.frequency.setValueAtTime(800, now);
        noiseFilter.frequency.exponentialRampToValueAtTime(100, now + duration);
        noiseFilter.Q.value = 1;

        const gain = ctx.createGain();
        gain.gain.setValueAtTime(0.2, now);
        gain.gain.setValueAtTime(0.2, now + duration * 0.7);
        gain.gain.exponentialRampToValueAtTime(0.01, now + duration);

        noise.connect(noiseFilter);
        noiseFilter.connect(gain);
        gain.connect(ctx.destination);

        noise.start(now);
        noise.stop(now + duration);
    }

    playGeneratorExplosionSound(ctx, now) {
        const duration = 1.2;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = "sawtooth";
        osc.frequency.setValueAtTime(150, now);
        osc.frequency.exponentialRampToValueAtTime(30, now + duration);

        gain.gain.setValueAtTime(0.3, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + duration);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        osc.stop(now + duration);

        const noiseBuffer = ctx.createBuffer(1, ctx.sampleRate * 0.3, ctx.sampleRate);
        const noiseData = noiseBuffer.getChannelData(0);
        for (let i = 0; i < noiseData.length; i++) {
            noiseData[i] = (Math.random() * 2 - 1) * Math.exp(-i / (ctx.sampleRate * 0.1));
        }

        const noise = ctx.createBufferSource();
        noise.buffer = noiseBuffer;
        const noiseGain = ctx.createGain();
        noiseGain.gain.setValueAtTime(0.4, now);
        noiseGain.gain.exponentialRampToValueAtTime(0.01, now + 0.3);

        noise.connect(noiseGain);
        noiseGain.connect(ctx.destination);
        noise.start(now);
    }

    playCrystalShatterSound(ctx, now) {
        const duration = 1.5;

        for (let i = 0; i < 10; i++) {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();

            const freq = 2000 + Math.random() * 6000;
            const decay = 0.5 + Math.random() * 2.0;

            osc.type = "sine";
            osc.frequency.setValueAtTime(freq, now);

            gain.gain.setValueAtTime(0.05, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + decay);

            osc.connect(gain);
            gain.connect(ctx.destination);

            osc.start(now);
            osc.stop(now + decay);
        }

        const noiseBuffer = ctx.createBuffer(1, ctx.sampleRate * 0.1, ctx.sampleRate);
        const noiseData = noiseBuffer.getChannelData(0);
        for (let i = 0; i < noiseData.length; i++) {
            noiseData[i] = Math.random() * 2 - 1;
        }

        const noise = ctx.createBufferSource();
        noise.buffer = noiseBuffer;
        const noiseGain = ctx.createGain();
        noiseGain.gain.setValueAtTime(0.2, now);
        noiseGain.gain.exponentialRampToValueAtTime(0.01, now + 0.1);

        noise.connect(noiseGain);
        noiseGain.connect(ctx.destination);
        noise.start(now);
    }

    playMysteryBingSound(ctx, now) {
        const duration = 0.3;
        const mainFreq = 1500;

        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = "sine";
        osc.frequency.setValueAtTime(mainFreq, now);

        gain.gain.setValueAtTime(0, now);
        gain.gain.linearRampToValueAtTime(0.3, now + 0.01);
        gain.gain.exponentialRampToValueAtTime(0.001, now + duration);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        osc.stop(now + duration);

        [1.8, 2.5, 3.2].forEach((mult, idx) => {
            const harm = ctx.createOscillator();
            const harmGain = ctx.createGain();
            harm.type = "sine";
            harm.frequency.setValueAtTime(mainFreq * mult, now);
            harmGain.gain.setValueAtTime((0.1 * (3 - idx)) / 3, now);
            harmGain.gain.exponentialRampToValueAtTime(0.001, now + duration);
            harm.connect(harmGain);
            harmGain.connect(ctx.destination);
            harm.start(now);
            harm.stop(now + duration);
        });
    }

    playDeploySound(ctx, now) {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = "sine";
        osc.frequency.setValueAtTime(800, now);
        osc.frequency.exponentialRampToValueAtTime(1200, now + 0.1);

        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.2);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        osc.stop(now + 0.2);
    }

    playFogHornSound(ctx, now) {
        // Deep fog horn - low frequency oscillator with slight vibrato
        const duration = 1.5;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const lfo = ctx.createOscillator();
        const lfoGain = ctx.createGain();

        // Main horn tone
        osc.type = "triangle";
        osc.frequency.setValueAtTime(80, now);
        osc.frequency.exponentialRampToValueAtTime(60, now + duration);

        // Vibrato
        lfo.type = "sine";
        lfo.frequency.value = 5;
        lfoGain.gain.value = 3;
        lfo.connect(lfoGain);
        lfoGain.connect(osc.frequency);

        gain.gain.setValueAtTime(0.3, now);
        gain.gain.setValueAtTime(0.3, now + duration * 0.7);
        gain.gain.exponentialRampToValueAtTime(0.01, now + duration);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        lfo.start(now);
        osc.stop(now + duration);
        lfo.stop(now + duration);
    }

    playGhostSound(ctx, now) {
        // Spooky ghost - ethereal wavy tone
        const duration = 1.2;

        // Main ghostly wail
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const filter = ctx.createBiquadFilter();

        osc.type = "sine";
        osc.frequency.setValueAtTime(400, now);
        osc.frequency.setValueAtTime(600, now + duration * 0.3);
        osc.frequency.setValueAtTime(350, now + duration * 0.6);
        osc.frequency.setValueAtTime(500, now + duration);

        filter.type = "lowpass";
        filter.frequency.value = 1000;
        filter.Q.value = 5;

        gain.gain.setValueAtTime(0.2, now);
        gain.gain.setValueAtTime(0.2, now + duration * 0.5);
        gain.gain.exponentialRampToValueAtTime(0.01, now + duration);

        osc.connect(filter);
        filter.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        osc.stop(now + duration);

        // Add ghostly harmonics
        for (let i = 0; i < 3; i++) {
            const harm = ctx.createOscillator();
            const harmGain = ctx.createGain();
            harm.type = "sine";
            harm.frequency.setValueAtTime(800 + i * 200, now);
            harmGain.gain.setValueAtTime(0.05 * (3 - i) / 3, now);
            harmGain.gain.exponentialRampToValueAtTime(0.001, now + duration);
            harm.connect(harmGain);
            harmGain.connect(ctx.destination);
            harm.start(now);
            harm.stop(now + duration);
        }
    }

    playLightningSound(ctx, now) {
        // Lightning strike - sharp crack with rumble
        const duration = 0.5;

        // Sharp crack (white noise burst)
        const noiseBuffer = ctx.createBuffer(1, ctx.sampleRate * 0.05, ctx.sampleRate);
        const noiseData = noiseBuffer.getChannelData(0);
        for (let i = 0; i < noiseData.length; i++) {
            noiseData[i] = (Math.random() * 2 - 1) * Math.exp(-i / (ctx.sampleRate * 0.01));
        }

        const noise = ctx.createBufferSource();
        noise.buffer = noiseBuffer;
        const noiseGain = ctx.createGain();
        noiseGain.gain.setValueAtTime(0.5, now);
        noiseGain.gain.exponentialRampToValueAtTime(0.01, now + 0.05);

        noise.connect(noiseGain);
        noiseGain.connect(ctx.destination);
        noise.start(now);

        // Thunder rumble
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const filter = ctx.createBiquadFilter();

        osc.type = "sawtooth";
        osc.frequency.setValueAtTime(100, now + 0.1);
        osc.frequency.exponentialRampToValueAtTime(40, now + duration);

        filter.type = "lowpass";
        filter.frequency.setValueAtTime(200, now);
        filter.Q.value = 2;

        gain.gain.setValueAtTime(0, now + 0.1);
        gain.gain.linearRampToValueAtTime(0.2, now + 0.15);
        gain.gain.exponentialRampToValueAtTime(0.01, now + duration);

        osc.connect(filter);
        filter.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now + 0.1);
        osc.stop(now + duration);
    }

    playWhooshSound(ctx, now) {
        // Whoosh - wind-like sweeping sound
        const duration = 1.0;

        // Wind noise
        const noiseBuffer = ctx.createBuffer(1, ctx.sampleRate * duration, ctx.sampleRate);
        const noiseData = noiseBuffer.getChannelData(0);
        for (let i = 0; i < noiseData.length; i++) {
            noiseData[i] = Math.random() * 2 - 1;
        }

        const noise = ctx.createBufferSource();
        noise.buffer = noiseBuffer;

        const filter = ctx.createBiquadFilter();
        filter.type = "bandpass";
        filter.frequency.setValueAtTime(200, now);
        filter.frequency.exponentialRampToValueAtTime(2000, now + duration * 0.5);
        filter.frequency.exponentialRampToValueAtTime(500, now + duration);
        filter.Q.value = 2;

        const gain = ctx.createGain();
        gain.gain.setValueAtTime(0.1, now);
        gain.gain.linearRampToValueAtTime(0.25, now + duration * 0.3);
        gain.gain.exponentialRampToValueAtTime(0.01, now + duration);

        noise.connect(filter);
        filter.connect(gain);
        gain.connect(ctx.destination);

        noise.start(now);
        noise.stop(now + duration);
    }

    // ==========================================================================
    // Cleanup
    // ==========================================================================

    dispose() {
        // Stop and cleanup audio
        if (this.backgroundMusic) {
            this.backgroundMusic.pause();
            this.backgroundMusic = null;
        }

        this.generatorHums.forEach(hum => {
            if (hum) {
                hum.pause();
            }
        });
        this.generatorHums = [];

        // Cleanup 3D resources
        this.tokens3D.forEach((tokenData) => {
            if (tokenData.mesh) tokenData.mesh.dispose();
            if (tokenData.healthLabel) tokenData.healthLabel.dispose();
        });
        this.tokens3D.clear();

        this.specialCellMeshes.forEach((mesh) => mesh.dispose());
        this.specialCellMeshes = [];

        this.validMoveMeshes.forEach((mesh) => mesh.dispose());
        this.validMoveMeshes = [];

        if (this.hoverMesh) this.hoverMesh.dispose();
        if (this.scene) this.scene.dispose();
        if (this.engine) this.engine.dispose();
    }
}
