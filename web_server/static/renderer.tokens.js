/**
 * TokenRenderer - Token and Phantom Token 3D Rendering
 * 
 * Handles:
 * - Creating and updating 3D token meshes
 * - Phantom token rendering with flicker effects
 * - Health label creation and updates
 * - Token position animations
 * - Token selection glow effects
 */

import { BOARD_CONFIG, CELL_SIZE, PLAYER_COLORS, CRYSTAL_EFFECT } from './game_client.constants.js';

const WALL_HEIGHT = BOARD_CONFIG.WALL_HEIGHT;
const TOKEN_HEIGHT = BOARD_CONFIG.TOKEN_HEIGHT;
const BOARD_CAGE_TOP_Y = WALL_HEIGHT;
const TOKEN_CENTER_Y = Math.max(TOKEN_HEIGHT / 2, BOARD_CAGE_TOP_Y - (TOKEN_HEIGHT / 2));

class TokenRenderer {
    constructor(scene) {
        this.scene = scene;
        this.tokens3D = new Map();
        this.phantomTokens3D = new Map();
        this.localPlayerId = null;

        // Caches for materials and textures to prevent memory leaks and reduce draw calls
        this.sharedMaterials = new Map();
        this.sharedPhantomMaterials = new Map();
        this.sharedHealthMaterials = new Map();
        this.sharedPhantomHealthMaterials = new Map();
        this.highlightMaterial = null;
    }

    updateTokens(gameState) {
        const allTokens = [];
        for (const player of Object.values(gameState.players)) {
            for (const tokenId of player.token_ids) {
                const token = gameState.tokens[tokenId];
                if (token && token.is_alive && token.is_deployed) {
                    allTokens.push(token);
                }
            }
        }

        const visibleTokens = this.filterVisibleTokens(gameState, allTokens);
        const visibleTokenIds = new Set(visibleTokens.map((t) => t.id));

        for (const [tokenId, tokenData] of this.tokens3D) {
            if (!visibleTokenIds.has(tokenId)) {
                tokenData.mesh.dispose();
                if (tokenData.healthLabel) {
                    tokenData.healthLabel.dispose();
                }
                this.tokens3D.delete(tokenId);
            }
        }

        for (const token of visibleTokens) {
            const player = Object.values(gameState.players).find((p) =>
                p.token_ids.includes(token.id)
            );
            const colorIndex = player ? (player.color_index ?? player.color ?? 0) : 0;
            const playerColor = PLAYER_COLORS[colorIndex] || PLAYER_COLORS[0];

            if (this.tokens3D.has(token.id)) {
                this.updateTokenPosition(token.id, token);
            } else {
                this.createToken3D(token, playerColor);
            }
        }

        this.updatePhantomTokens(gameState);
    }

    filterVisibleTokens(gameState, allTokens) {
        if (!gameState.crystal?.active_effect) {
            return allTokens;
        }

        const effect = gameState.crystal.active_effect;
        const localPlayerId = this.localPlayerId;

        if (effect.type === CRYSTAL_EFFECT.FOG_OF_WAR) {
            return allTokens.filter((token) => token.player_id === localPlayerId);
        }

        if (effect.type === CRYSTAL_EFFECT.PHANTOM_ENEMIES) {
            return allTokens;
        }

        return allTokens;
    }

    updatePhantomTokens(gameState) {
        const phantoms = this.getPhantomTokens(gameState);
        const phantomIds = new Set(phantoms.map((p) => p.phantom_id));

        for (const [phantomId, phantomData] of this.phantomTokens3D) {
            if (!phantomIds.has(phantomId)) {
                phantomData.mesh.dispose();
                if (phantomData.healthLabel) {
                    phantomData.healthLabel.dispose();
                }
                this.phantomTokens3D.delete(phantomId);
            }
        }

        for (const phantom of phantoms) {
            if (this.phantomTokens3D.has(phantom.phantom_id)) {
                const phantomData = this.phantomTokens3D.get(phantom.phantom_id);
                const worldX = phantom.position[0] * CELL_SIZE + CELL_SIZE / 2;
                const worldZ = phantom.position[1] * CELL_SIZE + CELL_SIZE / 2;
                phantomData.mesh.position.x = worldX;
                phantomData.mesh.position.z = worldZ;
            } else {
                const player = gameState.players[phantom.apparent_player_id];
                const colorIndex = player ? (player.color_index ?? player.color ?? 0) : 0;
            const playerColor = PLAYER_COLORS[colorIndex] || PLAYER_COLORS[0];
                this.createPhantomToken3D(phantom, playerColor);
            }
        }
    }

    getPhantomTokens(gameState) {
        if (!gameState.crystal?.active_effect || gameState.crystal.active_effect.type !== CRYSTAL_EFFECT.PHANTOM_ENEMIES) {
            return [];
        }

        const phantoms = [];
        const affectedPlayerId = gameState.crystal.active_effect.affected_player_id;
        const localPlayerId = this.localPlayerId;

        if (affectedPlayerId === localPlayerId) {
            const player = gameState.players[affectedPlayerId];
            if (!player) return [];

            for (const tokenId of player.token_ids) {
                const token = gameState.tokens[tokenId];
                if (token && token.is_alive && token.is_deployed) {
                    phantoms.push({
                        phantom_id: `phantom_${tokenId}`,
                        apparent_player_id: affectedPlayerId,
                        apparent_health: token.health,
                        position: token.position,
                    });
                }
            }
        }

        return phantoms;
    }

    createToken3D(token, playerColor) {
        const worldX = token.position[0] * CELL_SIZE + CELL_SIZE / 2;
        const worldZ = token.position[1] * CELL_SIZE + CELL_SIZE / 2;

        const hexagon = BABYLON.MeshBuilder.CreateCylinder(
            `token_${token.id}`,
            { diameter: CELL_SIZE * 0.7, height: TOKEN_HEIGHT, tessellation: 6 },
            this.scene,
        );
        hexagon.position = new BABYLON.Vector3(worldX, TOKEN_CENTER_Y, worldZ);

        const colorKey = playerColor.toHexString();
        if (!this.sharedMaterials.has(colorKey)) {
            const material = new BABYLON.PBRMaterial(`tokenMatShared_${colorKey}`, this.scene);
            material.emissiveColor = playerColor;
            material.albedoColor = new BABYLON.Color3(0, 0, 0);
            material.metallic = 0.5;
            material.roughness = 0.4;
            material.emissiveIntensity = 1.0;
            material.alpha = 0.9;
            material.backFaceCulling = false;
            this.sharedMaterials.set(colorKey, material);
        }
        hexagon.material = this.sharedMaterials.get(colorKey);

        const healthLabel = this.createHealthLabel(token, hexagon.position);

        this.tokens3D.set(token.id, {
            mesh: hexagon,
            token: token,
            color: playerColor,
            healthLabel: healthLabel,
        });

        return hexagon;
    }

    createPhantomToken3D(phantom, playerColor) {
        const worldX = phantom.position[0] * CELL_SIZE + CELL_SIZE / 2;
        const worldZ = phantom.position[1] * CELL_SIZE + CELL_SIZE / 2;

        const hexagon = BABYLON.MeshBuilder.CreateCylinder(
            `phantom_${phantom.phantom_id}`,
            { diameter: CELL_SIZE * 0.7, height: TOKEN_HEIGHT, tessellation: 6 },
            this.scene,
        );
        hexagon.position = new BABYLON.Vector3(worldX, TOKEN_CENTER_Y, worldZ);

        const colorKey = playerColor.toHexString();
        if (!this.sharedPhantomMaterials.has(colorKey)) {
            const material = new BABYLON.PBRMaterial(`phantomMatShared_${colorKey}`, this.scene);
            material.emissiveColor = playerColor;
            material.albedoColor = new BABYLON.Color3(0, 0, 0);
            material.metallic = 0.2;
            material.roughness = 0.8;
            material.emissiveIntensity = 0.5;
            material.alpha = 0.4;
            material.transparencyMode = BABYLON.PBRMaterial.PBRMATERIAL_ALPHABLEND;
            material.backFaceCulling = false;
            this.sharedPhantomMaterials.set(colorKey, material);
        }
        hexagon.material = this.sharedPhantomMaterials.get(colorKey);

        const healthLabel = this.createPhantomHealthLabel(phantom, hexagon.position);

        this.addPhantomFlickerAnimation(hexagon, hexagon.material);

        this.phantomTokens3D.set(phantom.phantom_id, {
            mesh: hexagon,
            phantom: phantom,
            color: playerColor,
            healthLabel: healthLabel,
        });

        return hexagon;
    }

    getSharedHealthMaterial(health, isPhantom = false) {
        const pool = isPhantom ? this.sharedPhantomHealthMaterials : this.sharedHealthMaterials;
        if (!pool.has(health)) {
            const texture = new BABYLON.DynamicTexture(
                `healthTex_${isPhantom ? 'phantom_' : ''}${health}`,
                { width: 256, height: 128 },
                this.scene,
                false
            );
            const ctx = texture.getContext();
            ctx.fillStyle = "black";
            ctx.fillRect(0, 0, 256, 128);
            ctx.font = "bold 80px monospace";
            ctx.fillStyle = isPhantom ? "rgba(255, 255, 255, 0.7)" : "white";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(`${health}hp`, 128, 64);
            texture.update();

            const material = new BABYLON.StandardMaterial(
                `healthMat_${isPhantom ? 'phantom_' : ''}${health}`, 
                this.scene
            );
            material.diffuseTexture = texture;
            material.emissiveTexture = texture;
            material.opacityTexture = texture;
            if (isPhantom) {
                material.alpha = 0.7;
            }
            pool.set(health, material);
        }
        return pool.get(health);
    }

    createPhantomHealthLabel(phantom, position) {
        const plane = BABYLON.MeshBuilder.CreatePlane(
            `phantomHealthLabel_${phantom.phantom_id}`,
            { width: CELL_SIZE * 0.6, height: CELL_SIZE * 0.3 },
            this.scene,
        );
        plane.position = new BABYLON.Vector3(position.x, position.y, position.z + TOKEN_HEIGHT);
        plane.billboardMode = BABYLON.Mesh.BILLBOARDMODE_ALL;
        plane.material = this.getSharedHealthMaterial(phantom.apparent_health, true);
        return plane;
    }

    addPhantomFlickerAnimation(mesh, material) {
        const flicker = new BABYLON.Animation(
            `phantomFlicker_${mesh.name}`,
            "visibility",
            30,
            BABYLON.Animation.ANIMATIONTYPE_FLOAT,
            BABYLON.Animation.ANIMATIONLOOPMODE_CYCLE
        );

        const keys = [
            { frame: 0, value: 1.0 },
            { frame: 15, value: 0.5 },
            { frame: 30, value: 1.0 },
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
        plane.material = this.getSharedHealthMaterial(token.health, false);
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
            new BABYLON.Vector3(worldX, TOKEN_CENTER_Y, worldZ),
            BABYLON.Animation.ANIMATIONLOOPMODE_CONSTANT,
        );

        if (tokenData.healthLabel) {
            tokenData.healthLabel.material = this.getSharedHealthMaterial(token.health, false);
            BABYLON.Animation.CreateAndStartAnimation(
                "labelMove",
                tokenData.healthLabel,
                "position",
                30,
                10,
                tokenData.healthLabel.position,
                new BABYLON.Vector3(worldX, TOKEN_CENTER_Y + (TOKEN_HEIGHT / 2) + 10, worldZ),
                BABYLON.Animation.ANIMATIONLOOPMODE_CONSTANT,
            );
        }
    }

    /**
     * Hide the controlled token (mesh + health label) so it does not block
     * the first-person view; pass null to show all tokens again.
     */
    setControlledToken(controlledTokenId) {
        this.tokens3D.forEach((tokenData, tokenId) => {
            const visible = tokenId !== controlledTokenId;
            if (tokenData.mesh) {
                tokenData.mesh.setEnabled(visible);
            }
            if (tokenData.healthLabel) {
                tokenData.healthLabel.setEnabled(visible);
            }
        });
    }

    updateTokenSelectionGlow(selectedTokenId) {
        this.tokens3D.forEach((tokenData, tokenId) => {
            if (tokenData.mesh && tokenData.mesh.material) {
                const colorKey = tokenData.color.toHexString();
                tokenData.mesh.material = this.sharedMaterials.get(colorKey) || tokenData.mesh.material;
                tokenData.mesh.scaling = new BABYLON.Vector3(1, 1, 1);
            }
        });

        if (selectedTokenId !== null) {
            const selectedData = this.tokens3D.get(selectedTokenId);
            if (selectedData && selectedData.mesh) {
                if (!this.highlightMaterial) {
                    this.highlightMaterial = new BABYLON.PBRMaterial("highlightMat", this.scene);
                    this.highlightMaterial.emissiveColor = new BABYLON.Color3(1, 1, 1);
                    this.highlightMaterial.albedoColor = new BABYLON.Color3(0, 0, 0);
                    this.highlightMaterial.metallic = 0.5;
                    this.highlightMaterial.roughness = 0.4;
                    this.highlightMaterial.emissiveIntensity = 1.5;
                    this.highlightMaterial.alpha = 1.0;
                    this.highlightMaterial.backFaceCulling = false;
                }
                selectedData.mesh.material = this.highlightMaterial;
                selectedData.mesh.scaling = new BABYLON.Vector3(1.2, 1.2, 1.2);
            }
        }
    }

    cleanup() {
        this.tokens3D.forEach((tokenData) => {
            if (tokenData.mesh) tokenData.mesh.dispose();
            if (tokenData.healthLabel) tokenData.healthLabel.dispose();
        });
        this.tokens3D.clear();

        this.phantomTokens3D.forEach((phantomData) => {
            if (phantomData.mesh) phantomData.mesh.dispose();
            if (phantomData.healthLabel) phantomData.healthLabel.dispose();
        });
        this.phantomTokens3D.clear();

        this.sharedMaterials.forEach(m => m.dispose(false, true));
        this.sharedMaterials.clear();
        this.sharedPhantomMaterials.forEach(m => m.dispose(false, true));
        this.sharedPhantomMaterials.clear();
        this.sharedHealthMaterials.forEach(m => m.dispose(false, true));
        this.sharedHealthMaterials.clear();
        this.sharedPhantomHealthMaterials.forEach(m => m.dispose(false, true));
        this.sharedPhantomHealthMaterials.clear();
        if (this.highlightMaterial) {
            this.highlightMaterial.dispose(false, true);
            this.highlightMaterial = null;
        }
    }
}

export { TokenRenderer };
