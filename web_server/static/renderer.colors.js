/**
 * Renderer3D - Special Cell Colors Module
 * Generator and crystal color updates based on token ownership
 */

import { Renderer3D, ORANGE_GLOW } from './renderer.base.js';

Renderer3D.prototype.updateSpecialCellColors = function(gameState) {
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

        if (gen.is_disabled && !genMeshData.isDisabled) {
            this.triggerExplosion(gen.position, ORANGE_GLOW);
            this.playSound("capture");
        }

        if (dominantPlayer && playerCounts[dominantPlayer] >= 2 && !gen.is_disabled) {
            const color = playerColors[dominantPlayer] || ORANGE_GLOW;
            genMeshData.mesh.material.emissiveColor = color;
            genMeshData.mesh.material.alpha = 1.0;
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
            if (token.position[0] === gameState.crystal.position[0] && 
                token.position[1] === gameState.crystal.position[1]) {
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
            const color = playerColors[dominantPlayer] || new BABYLON.Color3(0, 0.8, 1.0);
            this.crystalMesh.mesh.material.emissiveColor = color;
            this.crystalMesh.mesh.material.emissiveIntensity = 3.0;
        } else {
            this.crystalMesh.mesh.material.emissiveColor = new BABYLON.Color3(0, 0.8, 1.0);
            this.crystalMesh.mesh.material.emissiveIntensity = 2.0;
        }

        this.crystalMesh.tokenCounts = crystalCounts;
    }
};

Renderer3D.prototype.getPlayerColors = function(gameState) {
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
};
