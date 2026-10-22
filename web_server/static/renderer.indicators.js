/**
 * Renderer3D - Indicators Module
 * Hover, valid move, and valid attack indicators
 *
 * Also the tactical overlays of Phase 1.4: the threat map and the
 * objective capture progress. Both are projections of what the player
 * knows, and both are computed by the game package and sent in the state
 * -- nothing here re-implements a rule, the client draws numbers it is
 * given.
 */

import { Renderer3D, WHITE_GLOW, GREEN_GLOW, RED_GLOW, ORANGE_GLOW } from './renderer.base.js';
import { CELL_SIZE } from './game_client.constants.js';

// The colour of a pip that is not filled yet: dim, but visible enough that
// the ring reads as a ring and the player can see how many are still
// needed.
const OBJECTIVE_PIP_EMPTY = new BABYLON.Color3(0.45, 0.45, 0.45);
const OBJECTIVE_PIP_EMPTY_ALPHA = 0.55;

Renderer3D.prototype.updateHoverIndicator = function(gridX, gridY) {
    if (this.hoverMesh) {
        this.hoverMesh.dispose();
        this.hoverMesh = null;
    }

    this.hoveredCell = gridX === null || gridY === null ? null : { gridX, gridY };
    // The threat overlay is anchored to the cell under the pointer, so it
    // has to follow the hover.
    this.updateThreatIndicators();

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
    // Decoration — must not intercept a click meant for the cell below.
    square.isPickable = false;

    this.hoverMesh = square;
};

// Valid-move sets may contain "x,y" strings (from calculateValidMoves) or
// [x, y] arrays — accept both so callers never need to convert.
function toGridCoords(entry) {
    if (Array.isArray(entry)) return entry;
    return entry.split(',').map(Number);
}

Renderer3D.prototype.updateValidMoveIndicators = function(moves) {
    this.validMoveMeshes.forEach((mesh) => mesh.dispose());
    this.validMoveMeshes = [];

    if (!moves || moves.size === 0) return;

    moves.forEach((entry) => {
        const [gridX, gridY] = toGridCoords(entry);
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
        square.isPickable = false;

        this.validMoveMeshes.push(square);
    });
};

Renderer3D.prototype.updateValidAttackIndicators = function(attacks) {
    this.validAttackMeshes.forEach((mesh) => mesh.dispose());
    this.validAttackMeshes = [];

    if (!attacks || attacks.size === 0) return;

    attacks.forEach((entry) => {
        const [gridX, gridY] = toGridCoords(entry);
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
        square.isPickable = false;

        this.validAttackMeshes.push(square);
    });
};

// ==========================================================================
// Tactical overlays (Phase 1.4)
// ==========================================================================

// Dispose a list of decoration meshes, and their materials with them.
function disposeMeshes(meshes) {
    meshes.forEach((mesh) => {
        if (!mesh) return;
        if (mesh.material) {
            mesh.material.dispose();
            mesh.material = null;
        }
        mesh.dispose();
    });
}

// Mark the enemy tokens that could hit the cell under the pointer.
//
// The threat map is computed by the game package: it maps a cell to the
// enemy tokens that can attack it, counting only the ones the player can
// actually see. So this is a projection of what the player knows, not of
// the true board.
Renderer3D.prototype.updateThreatIndicators = function() {
    disposeMeshes(this.threatMeshes);
    this.threatMeshes = [];

    const state = this.lastGameState;
    if (!state || !state.threat_map) return;
    if (!this.hoveredCell) return;

    const key = `${this.hoveredCell.gridX},${this.hoveredCell.gridY}`;
    const tokenIds = state.threat_map[key];
    if (!tokenIds || tokenIds.length === 0) return;

    // The cell under the pointer is dangerous.
    this.threatMeshes.push(
        this.createThreatSquare(this.hoveredCell.gridX, this.hoveredCell.gridY),
    );

    // And every enemy token that could hit it is marked.
    tokenIds.forEach((tokenId) => {
        const mesh = this.getTokenMesh(tokenId);
        if (!mesh) return;

        const ring = BABYLON.MeshBuilder.CreateTorus(
            `threatRing_${tokenId}`,
            { diameter: CELL_SIZE * 0.8, thickness: 3, tessellation: 20 },
            this.scene,
        );
        ring.position = new BABYLON.Vector3(mesh.position.x, 2.0, mesh.position.z);

        const material = new BABYLON.StandardMaterial(`threatRingMat_${tokenId}`, this.scene);
        material.emissiveColor = RED_GLOW;
        material.diffuseColor = new BABYLON.Color3(0, 0, 0);
        material.alpha = 0.9;
        ring.material = material;
        // Decoration — must not intercept a click meant for the token.
        ring.isPickable = false;

        this.threatMeshes.push(ring);
    });
};

// The mesh of a token, if it has one. The token meshes belong to the
// token renderer, not to this one.
Renderer3D.prototype.getTokenMesh = function(tokenId) {
    if (this.tokenRenderer && this.tokenRenderer.tokens3D) {
        const entry = this.tokenRenderer.tokens3D.get(tokenId);
        if (entry && entry.mesh) return entry.mesh;
    }
    if (this.tokens3D) {
        const entry = this.tokens3D.get(tokenId);
        if (entry && entry.mesh) return entry.mesh;
    }
    return null;
};

// A red outline over a cell that is under attack.
Renderer3D.prototype.createThreatSquare = function(gridX, gridY) {
    const centerX = gridX * CELL_SIZE + CELL_SIZE / 2;
    const centerZ = gridY * CELL_SIZE + CELL_SIZE / 2;

    const square = BABYLON.MeshBuilder.CreateGround(
        `threatCell_${gridX}_${gridY}`,
        { width: CELL_SIZE * 0.8, height: CELL_SIZE * 0.8 },
        this.scene,
    );
    square.position = new BABYLON.Vector3(centerX, 2.5, centerZ);

    const material = new BABYLON.StandardMaterial(`threatCellMat_${gridX}_${gridY}`, this.scene);
    material.emissiveColor = RED_GLOW;
    material.wireframe = true;
    material.alpha = 0.95;
    square.material = material;
    square.isPickable = false;

    return square;
};

// Draw the capture progress of the generators and the crystal.
//
// Two rings of pips around each objective: the inner ring is the turns of
// the capture, the outer ring is the tokens it needs, one pip each. Rings
// rather than a filled arc, because the objective's own mesh stands on
// the cell and would hide anything drawn under it.
Renderer3D.prototype.updateObjectiveIndicators = function(gameState) {
    disposeMeshes(this.objectiveMeshes);
    this.objectiveMeshes = [];

    if (!gameState) return;
    const colors = this.getPlayerColors(gameState);

    (gameState.generators || []).forEach((gen) => {
        this.addObjectiveIndicator(
            `gen${gen.id}`,
            gen.position,
            gen.tokens_present || 0,
            gen.tokens_required || 0,
            gen.turns_held || 0,
            gen.turns_required || 0,
            gen.capturing_player_id ? colors[gen.capturing_player_id] : null,
            gen.is_disabled,
            // The generator's pillar is 24 wide, so its pips have to clear
            // a radius of 12 to be seen.
            12,
        );
    });

    const crystal = gameState.crystal;
    if (crystal) {
        this.addObjectiveIndicator(
            "crystal",
            crystal.position,
            crystal.tokens_present || 0,
            crystal.tokens_required || 0,
            crystal.turns_held || 0,
            crystal.turns_required || 0,
            crystal.holding_player_id ? colors[crystal.holding_player_id] : null,
            false,
            // The crystal's hub stands over the cell.
            30,
        );
    }
};

// One objective's capture indicator: a ring of pips for the turns of the
// capture and a ring for the tokens it needs.
Renderer3D.prototype.addObjectiveIndicator = function(
    key, position, tokensPresent, tokensRequired, turnsHeld, turnsRequired, color, isDisabled, footprint,
) {
    // A generator that has fallen needs no progress, and a disabled
    // generator is drawn grey by the cell colouring instead.
    if (isDisabled) return;
    if (!tokensRequired) return;
    if (!position) return;

    const centerX = position[0] * CELL_SIZE + CELL_SIZE / 2;
    const centerZ = position[1] * CELL_SIZE + CELL_SIZE / 2;
    const tint = color || ORANGE_GLOW;

    // The turns of the capture, on a tight ring just clear of the
    // objective's own mesh.
    if (turnsRequired > 0) {
        const ringRadius = footprint + 3;
        const spacing = (2 * Math.PI * ringRadius) / turnsRequired;
        const pipSize = Math.max(2.5, Math.min(5, spacing * 0.5));
        for (let i = 0; i < turnsRequired; i++) {
            const angle = (i / turnsRequired) * Math.PI * 2 - Math.PI / 2;
            this.objectiveMeshes.push(
                this.createObjectivePip(
                    `objectiveTurn_${key}_${i}`,
                    centerX + Math.cos(angle) * ringRadius,
                    centerZ + Math.sin(angle) * ringRadius,
                    pipSize,
                    i < turnsHeld ? tint : OBJECTIVE_PIP_EMPTY,
                    i < turnsHeld ? 0.95 : OBJECTIVE_PIP_EMPTY_ALPHA,
                ),
            );
        }
    }

    // The tokens the capture needs, on a wider ring, lit as they arrive.
    const ringRadius = footprint + 9;
    const spacing = (2 * Math.PI * ringRadius) / tokensRequired;
    const pipSize = Math.max(2.5, Math.min(7, spacing * 0.5));
    for (let i = 0; i < tokensRequired; i++) {
        const angle = (i / tokensRequired) * Math.PI * 2 - Math.PI / 2;
        const lit = i < tokensPresent;
        this.objectiveMeshes.push(
            this.createObjectivePip(
                `objectivePip_${key}_${i}`,
                centerX + Math.cos(angle) * ringRadius,
                centerZ + Math.sin(angle) * ringRadius,
                pipSize,
                lit ? tint : OBJECTIVE_PIP_EMPTY,
                lit ? 0.95 : OBJECTIVE_PIP_EMPTY_ALPHA,
            ),
        );
    }
};

// One pip of an objective's capture indicator.
Renderer3D.prototype.createObjectivePip = function(name, x, z, size, color, alpha) {
    const pip = BABYLON.MeshBuilder.CreateGround(
        name,
        { width: size, height: size },
        this.scene,
    );
    pip.position = new BABYLON.Vector3(x, 1.2, z);

    const material = new BABYLON.StandardMaterial(`${name}Mat`, this.scene);
    material.emissiveColor = color;
    material.diffuseColor = new BABYLON.Color3(0, 0, 0);
    material.alpha = alpha;
    pip.material = material;
    pip.isPickable = false;

    return pip;
};




