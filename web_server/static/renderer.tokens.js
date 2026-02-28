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

class TokenRenderer {
    constructor(scene) {
        this.scene = scene;
        this.tokens3D = new Map();
        this.phantomTokens3D = new Map();
        this.localPlayerId = null;
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
            const playerColor = player ? PLAYER_COLORS[player.color] || PLAYER_COLORS[0] : PLAYER_COLORS[0];

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

        if (effect.type === CrystalEffect.FOG_OF_WAR) {
            return allTokens.filter((token) => token.player_id === localPlayerId);
        }

        if (effect.type === CrystalEffect.PHANTOM_ENEMIES) {
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
                const playerColor = player ? PLAYER_COLORS[player.color] || PLAYER_COLORS[0] : PLAYER_COLORS[0];
                this.createPhantomToken3D(phantom, playerColor);
            }
        }
    }

    getPhantomTokens(gameState) {
        if (!gameState.crystal?.active_effect || gameState.crystal.active_effect.type !== CrystalEffect.PHANTOM_ENEMIES) {
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

        const material = new BABYLON.PBRMaterial(`tokenMat_${token.id}`, this.scene);
        material.emissiveColor = playerColor;
        material.albedoColor = new BABYLON.Color3(0, 0, 0);
        material.metallic = 0.5;
        material.roughness = 0.4;
        material.emissiveIntensity = 1.0;
        material.alpha = 0.9;
        material.backFaceCulling = false;
        hexagon.material = material;

        const tokenLight = new BABYLON.PointLight(
            `tokenLight_${token.id}`,
            hexagon.position,
            this.scene
        );
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

    createPhantomToken3D(phantom, playerColor) {
        const worldX = phantom.position[0] * CELL_SIZE + CELL_SIZE / 2;
        const worldZ = phantom.position[1] * CELL_SIZE + CELL_SIZE / 2;

        const hexagon = BABYLON.MeshBuilder.CreateCylinder(
            `phantom_${phantom.phantom_id}`,
            { diameter: CELL_SIZE * 0.7, height: TOKEN_HEIGHT, tessellation: 6 },
            this.scene,
        );
        hexagon.position = new BABYLON.Vector3(worldX, TOKEN_CENTER_Y, worldZ);

        const material = new BABYLON.PBRMaterial(
            `phantomMat_${phantom.phantom_id}`,
            this.scene
        );
        material.emissiveColor = playerColor;
        material.albedoColor = new BABYLON.Color3(0, 0, 0);
        material.metallic = 0.2;
        material.roughness = 0.8;
        material.emissiveIntensity = 0.5;
        material.alpha = 0.4;
        material.transparencyMode = BABYLON.PBRMaterial.PBRMATERIAL_ALPHABLEND;
        material.backFaceCulling = false;

        hexagon.material = material;

        const healthLabel = this.createPhantomHealthLabel(phantom, hexagon.position);

        this.addPhantomFlickerAnimation(hexagon, material);

        this.phantomTokens3D.set(phantom.phantom_id, {
            mesh: hexagon,
            phantom: phantom,
            color: playerColor,
            healthLabel: healthLabel,
        });

        return hexagon;
    }

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
        ctx.fillStyle = "rgba(255, 255, 255, 0.7)";
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
            new BABYLON.Vector3(worldX, TOKEN_CENTER_Y, worldZ),
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
                new BABYLON.Vector3(worldX, TOKEN_CENTER_Y + (TOKEN_HEIGHT / 2) + 10, worldZ),
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
    }
}

export { TokenRenderer };
