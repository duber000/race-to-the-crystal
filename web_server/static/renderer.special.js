/**
 * Renderer3D - Special Cells Module
 * Generators, crystal, mystery squares, and generator lines
 */

import { Renderer3D, GENERATOR_HEIGHT, GENERATOR_CENTER_Y, CYAN_GLOW, ORANGE_GLOW } from './renderer.base.js';
import { BOARD_CONFIG, CELL_SIZE } from './game_client.constants.js';

const WALL_HEIGHT = BOARD_CONFIG.WALL_HEIGHT;

Renderer3D.prototype.createSpecialCells = function(gameState) {
    this.cleanupCallbacks.forEach(cb => cb());
    this.cleanupCallbacks = [];

    if (this.vls) {
        this.vls.mesh = null;
    }

    this.specialCellMeshes.forEach((mesh) => mesh.dispose());
    this.specialCellMeshes = [];
    this.crystalFrames = [];
    this.generatorMeshes.clear();
    this.crystalMesh = null;

    this.generatorLineMeshes.forEach((lineData) => {
        if (lineData.beams) {
            lineData.beams.forEach(beam => beam.dispose());
        }
    });
    this.generatorLineMeshes = [];

    if (!gameState.crystal) return;

    const centerX = gameState.crystal.position[0] * CELL_SIZE + CELL_SIZE / 2;
    const centerZ = gameState.crystal.position[1] * CELL_SIZE + CELL_SIZE / 2;
    const hubY = 60;

    const hub = BABYLON.MeshBuilder.CreateIcoSphere("nlo_hub", { radius: 40, subdivisions: 2 }, this.scene);
    hub.position = new BABYLON.Vector3(centerX, hubY, centerZ);
    hub.scaling.y = 2.2;

    const hubMat = new BABYLON.PBRMaterial("nloHubMat", this.scene);
    hubMat.albedoColor = new BABYLON.Color3(0, 0.2, 0.8);
    hubMat.emissiveColor = new BABYLON.Color3(0, 0.8, 1.0);
    hubMat.emissiveIntensity = 2.0;
    hubMat.subSurface.isTranslucencyEnabled = true;
    hubMat.subSurface.translucencyIntensity = 1.0;
    hub.material = hubMat;

    this.crystalMesh = { mesh: hub, position: gameState.crystal.position, tokenCounts: {} };
    this.specialCellMeshes.push(hub);

    const hubCore = BABYLON.MeshBuilder.CreateIcoSphere("nlo_core", { radius: 25, subdivisions: 1 }, this.scene);
    hubCore.position = hub.position;
    hubCore.parent = hub;
    const coreMat = hubMat.clone("coreMat");
    coreMat.emissiveIntensity = 5.0;
    hubCore.material = coreMat;
    this.specialCellMeshes.push(hubCore);

    const frame = BABYLON.MeshBuilder.CreateIcoSphere("gold_frame", { radius: 60, subdivisions: 1 }, this.scene);
    frame.position = hub.position;
    frame.scaling.y = 2.2;
    const frameMat = new BABYLON.PBRMaterial("goldFrameMat", this.scene);
    frameMat.albedoColor = new BABYLON.Color3(1.0, 0.766, 0.336);
    frameMat.metallic = 1.0;
    frameMat.roughness = 0.2;

    if (!this.scene.environmentTexture) {
        this.scene.environmentTexture = BABYLON.CubeTexture.CreateFromPrefilteredData(
            "https://playground.babylonjs.com/textures/environment.env",
            this.scene
        );
    }

    frame.material = frameMat;
    frame.material.wireframe = true;
    this.specialCellMeshes.push(frame);
    this.crystalFrames.push(frame);

    const innerFrame = frame.clone("inner_frame");
    innerFrame.scaling = new BABYLON.Vector3(0.6, 1.3, 0.6);
    this.specialCellMeshes.push(innerFrame);
    this.crystalFrames.push(innerFrame);

    const outerFrame = frame.clone("outer_frame");
    outerFrame.scaling = new BABYLON.Vector3(1.2, 0.8, 1.2);
    this.specialCellMeshes.push(outerFrame);
    this.crystalFrames.push(outerFrame);

    if (this.vls) {
        this.vls.mesh = hub;
    } else if (this.scene.activeCamera) {
        this.initGodRays(hub);
    }

    const shardMat = new BABYLON.PBRMaterial("shardMat", this.scene);
    shardMat.albedoColor = new BABYLON.Color3(1, 1, 1);
    shardMat.alpha = 0.2;
    shardMat.metallic = 0;
    shardMat.roughness = 0.1;
    shardMat.subSurface.isRefractionEnabled = true;
    shardMat.subSurface.indexOfRefraction = 1.458;
    shardMat.transparencyMode = BABYLON.PBRMaterial.PBRMATERIAL_ALPHABLEND;

    if (gameState.generators) {
        gameState.generators.forEach((gen, index) => {
            const worldX = gen.position[0] * CELL_SIZE + CELL_SIZE / 2;
            const worldZ = gen.position[1] * CELL_SIZE + CELL_SIZE / 2;

            const pillar = BABYLON.MeshBuilder.CreateCylinder(`shard_assembly_${index}`, {
                height: GENERATOR_HEIGHT,
                diameter: 24,
                subdivisions: 32
            }, this.scene);
            pillar.position = new BABYLON.Vector3(worldX, GENERATOR_CENTER_Y, worldZ);

            pillar.material = shardMat.clone(`shardMat_${index}`);

            const positions = pillar.getVerticesData(BABYLON.VertexBuffer.PositionKind);
            for (let i = 0; i < positions.length; i++) {
                positions[i] += (Math.random() - 0.5) * 1.0;
            }
            pillar.setVerticesData(BABYLON.VertexBuffer.PositionKind, positions);

            const hitParticles = new BABYLON.ParticleSystem(`hitParticles_${index}`, 200, this.scene);
            hitParticles.particleTexture = new BABYLON.Texture(
                "https://playground.babylonjs.com/textures/flare.png",
                this.scene
            );
            hitParticles.emitter = pillar.position.clone();
            hitParticles.minEmitBox = new BABYLON.Vector3(-1, 0, -1);
            hitParticles.maxEmitBox = new BABYLON.Vector3(1, 2, 1);
            hitParticles.color1 = new BABYLON.Color4(1, 1, 1, 1);
            hitParticles.color2 = new BABYLON.Color4(0.5, 0.8, 1, 1);
            hitParticles.minSize = 0.1;
            hitParticles.maxSize = 0.5;
            hitParticles.minLifeTime = 0.1;
            hitParticles.maxLifeTime = 0.5;
            hitParticles.emitRate = 0;
            hitParticles.blendMode = BABYLON.ParticleSystem.BLENDMODE_ADD;
            hitParticles.start();

            this.specialCellMeshes.push(pillar);
            this.generatorMeshes.set(`${gen.position[0]},${gen.position[1]}`, {
                mesh: pillar,
                hitParticles: hitParticles,
                position: gen.position,
                isDisabled: gen.is_disabled,
                lastOwner: null,
            });
        });
    }

    this.createGeneratorLines(gameState);

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
};

Renderer3D.prototype.createMysteryRing = function(x, y) {
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

    this.scene.onBeforeRenderObservable.add(() => {
        ring.rotation.x += 0.05;
        ring.rotation.y += 0.02;
    });

    this.glowLayer.addIncludedOnlyMesh(ring);
    this.specialCellMeshes.push(ring);
    this.mysteryRings.push(ring);
};

Renderer3D.prototype.createGeneratorLines = function(gameState) {
    if (!gameState.generators || !gameState.crystal || !this.crystalMesh) return;

    const centerX = gameState.crystal.position[0] * CELL_SIZE + CELL_SIZE / 2;
    const centerZ = gameState.crystal.position[1] * CELL_SIZE + CELL_SIZE / 2;
    const hubY = 10;
    const hubPos = new BABYLON.Vector3(centerX, hubY, centerZ);

    gameState.generators.forEach((gen, index) => {
        if (gen.is_disabled) return;

        const genData = this.generatorMeshes.get(`${gen.position[0]},${gen.position[1]}`);
        if (!genData) return;

        const pillarPos = genData.mesh.position;
        const path = [pillarPos, hubPos];

        const blueMat = new BABYLON.PBRMaterial(`laserBlue_${index}`, this.scene);
        blueMat.emissiveColor = new BABYLON.Color3(0.1, 0.4, 1.0);
        blueMat.emissiveIntensity = 8.0;
        blueMat.albedoColor = new BABYLON.Color3(0, 0, 0);

        const greenMat = new BABYLON.PBRMaterial(`laserGreen_${index}`, this.scene);
        greenMat.emissiveColor = new BABYLON.Color3(0.1, 0.8, 0.2);
        greenMat.emissiveIntensity = 8.0;
        greenMat.albedoColor = new BABYLON.Color3(0, 0, 0);

        const redMat = new BABYLON.PBRMaterial(`laserRed_${index}`, this.scene);
        redMat.emissiveColor = new BABYLON.Color3(0.8, 0.1, 0.1);
        redMat.emissiveIntensity = 8.0;
        redMat.albedoColor = new BABYLON.Color3(0, 0, 0);

        const materials = [blueMat, greenMat, redMat];
        const beams = [];

        materials.forEach((mat, mIdx) => {
            const beam = BABYLON.MeshBuilder.CreateTube(`laserBeam_${index}_${mIdx}`, {
                path: path,
                radius: 0.5,
                instance: null
            }, this.scene);
            beam.material = mat;
            beam.position.x += (mIdx - 1) * 0.8;
            beam.position.z += (mIdx - 1) * 0.8;
            beams.push(beam);
            this.specialCellMeshes.push(beam);
        });

        this.generatorLineMeshes.push({
            genPosition: gen.position,
            beams: beams,
            pillarPos: pillarPos,
            hitParticles: genData.hitParticles
        });
    });
};
