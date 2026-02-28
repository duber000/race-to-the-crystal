/**
 * Renderer3D - Indicators Module
 * Hover, valid move, and valid attack indicators
 */

import { Renderer3D } from './renderer.base.js';

Renderer3D.prototype.updateHoverIndicator = function(gridX, gridY) {
    if (this.hoverMesh) {
        this.hoverMesh.dispose();
        this.hoverMesh = null;
    }

    if (gridX === null || gridY === null) return;

    const centerX = gridX * CELL_SIZE + CELL_SIZE / 2;
    const centerZ = gridY * CELL_SIZE + CELL_SIZE / 2;

    const square = BABYLON.MeshBuilder.CreateGround(
        "hoverSquare",
        { width: CELL_SIZE * 0.7, height: CELL_SIZE * 0.7 },
        this.scene,
    );
    square.position = new BABYLON.Vector3(centerX, 2.0, centerZ);

    const material = new BABYLON.StandardMaterial("hoverMat", this.scene);
    material.emissiveColor = WHITE_GLOW;
    material.wireframe = true;
    material.alpha = 0.9;
    square.material = material;

    this.hoverMesh = square;
};

Renderer3D.prototype.updateValidMoveIndicators = function(moves) {
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
};

Renderer3D.prototype.updateValidAttackIndicators = function(attacks) {
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
        material.emissiveColor = RED_GLOW;
        material.wireframe = true;
        material.alpha = 0.7;
        square.material = material;

        this.validAttackMeshes.push(square);
    });
};
