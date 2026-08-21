// ==========================================================================
// Game Client Modules - Separated Concerns from GameClient
// ==========================================================================

import { NetworkManager } from './network_manager.js';
import { CameraController } from './camera_controller.js';
import { InputHandler } from './input_handler.js';
import { Renderer3D } from './game_client.renderer.js';
import { STATE, TurnPhase, BOARD_CONFIG, BOARD_WIDTH, BOARD_HEIGHT, CELL_SIZE, WALL_HEIGHT } from './game_client.constants.js';

/**
 * Connection Manager - Handles network connection and state synchronization
 */
class ConnectionManager {
    constructor(gameClient) {
        this.gameClient = gameClient;
        this.networkManager = null;
        this.stateManager = gameClient.stateManager;
    }

    init() {
        this.networkManager = new NetworkManager();
        this.setupNetworkHandlers();
    }

    setupNetworkHandlers() {
        // Connection handlers
        this.networkManager.on("connecting", () => {
            this.gameClient.uiManager.showConnectionStatus("Connecting to server...");
            this.gameClient.updateUIState(STATE.CONNECTING);
        });

        this.networkManager.on("connected", (data) => {
            this.gameClient.uiManager.showConnectionStatus("Connected!");
            this.gameClient.uiManager.playerId = data.player_id || data.playerId;
            this.gameClient.updateUIState(STATE.CONNECTED);
            this.networkManager.requestGameList();
        });

        this.networkManager.on("game_list", (data) => {
            this.gameClient.uiManager.renderGameList(data.games || []);
        });

        this.networkManager.on("lobby_joined", (data) => {
            this.gameClient.updateUIState(STATE.IN_LOBBY);
            this.gameClient.uiManager.setupWaitingRoomHandlers(
                () => this.gameClient.uiController.toggleReady(),
                () => this.gameClient.uiController.startGame(),
                () => this.gameClient.uiController.leaveLobby(),
            );
            this.refreshLobbyUI(data.lobby, !!data.isHost);
        });

        this.networkManager.on("lobby_updated", (data) => {
            this.refreshLobbyUI(data.lobby, this.networkManager.isPlayerHost());
        });

        this.networkManager.on("game_starting", () => {
            this.gameClient.updateUIState(STATE.GAME_STARTING);
        });

        this.networkManager.on("lobby_left", () => {
            this.gameClient.updateUIState(STATE.CONNECTED);
            this.networkManager.requestGameList();
        });

        this.networkManager.on("error", (data) => {
            this.gameClient.uiManager.showConnectionError(data.message);
            this.gameClient.updateUIState(STATE.DISCONNECTED);
        });

        this.networkManager.on("disconnect", () => {
            this.gameClient.uiManager.playerId = null;
            this.gameClient.updateUIState(STATE.DISCONNECTED);
        });

        // Game state handlers
        this.networkManager.on("full_state", (data) => {
            this.handleFullState(data);
        });

        this.networkManager.on("state_update", (data) => {
            this.handleStateUpdate(data);
        });

        // Fine-grained events
        this.setupFineGrainedHandlers();
    }

    setupFineGrainedHandlers() {
        this.networkManager.on("token_moved", (data) => {            this.handleTokenMoved(data);
        });

        this.networkManager.on("combat_result", (data) => {
            this.handleCombatResult(data);
        });

        this.networkManager.on("token_deployed", (data) => {
            this.handleTokenDeployed(data);
        });

        this.networkManager.on("generator_update", (data) => {
            this.handleGeneratorUpdate(data);
        });

        this.networkManager.on("crystal_update", (data) => {
            this.handleCrystalUpdate(data);
        });

        this.networkManager.on("mystery_event", (data) => {
            this.handleMysteryEvent(data);
        });

        this.networkManager.on("turn_change", (data) => {
            this.handleTurnChange(data);
        });

        this.networkManager.on("game_won", (data) => {
            this.handleGameWon(data);
        });

        this.networkManager.on("invalid_action", (data) => {
            this.gameClient.uiManager.showActionError(data.message);
        });
    }

    refreshLobbyUI(lobby, isHost) {
        if (!lobby) return;
        this.gameClient.uiManager.renderWaitingRoom(
            lobby,
            isHost,
            this.networkManager.isPlayerReady(),
        );
        this.gameClient.uiManager.updateReadyButton(this.networkManager.isPlayerReady());
        this.gameClient.uiManager.updateStartButtonState(
            lobby,
            isHost,
            () => this.gameClient.uiController.startGame(),
        );
    }

    handleFullState(data) {
        // Initialize game modules on first FULL_STATE
        if (!this.gameClient.gameInitialized) {
            this.gameClient.gameInitialized = true;
            this.networkManager.connectionState = STATE.IN_GAME;
            this.gameClient.updateUIState(STATE.IN_GAME);
        }

        this.stateManager.setFullState(data);

        if (data.last_action && this.gameClient.renderer) {
            this.gameClient.renderer.playSound(data.last_action);
        }
    }

    handleStateUpdate(delta) {
        this.stateManager.applyDelta(delta);
    }

    handleTokenMoved(data) {
        if (!this.gameClient.gameState || !this.gameClient.gameState.tokens[data.token_id]) return;
        
        // Update local state for immediate feedback
        this.gameClient.gameState.tokens[data.token_id].position = data.new_position;
        
        // Trigger animation in renderer
        if (this.gameClient.renderer) {
            this.gameClient.renderer.animateTokenMove(data.token_id, data.old_position, data.new_position);
        }
        
        // Refresh basic state info
        this.updateGameState(this.gameClient.gameState);
    }

    handleCombatResult(data) {
        if (!this.gameClient.gameState) return;
        
        // Update local state (health, destruction)
        const defender = this.gameClient.gameState.tokens[data.defender_id];
        if (defender) {
            defender.health = Math.max(0, defender.health - data.damage);
            if (data.defender_destroyed) {
                defender.is_alive = false;
            }
        }
        
        // Trigger animation in renderer
        if (this.gameClient.renderer) {
            this.gameClient.renderer.animateCombat(data);
        }
        
        this.updateGameState(this.gameClient.gameState);
    }

    handleTokenDeployed(data) {
        if (!this.gameClient.gameState) return;
        // (Actual synchronization usually happens via the next state update, 
        // but we can trigger a spawn animation here)
        if (this.gameClient.renderer) {
            this.gameClient.renderer.animateTokenDeploy(data);
        }
    }

    handleGeneratorUpdate(data) {
        if (this.gameClient.renderer) {
            this.gameClient.renderer.animateGeneratorUpdate(data);
        }
    }

    handleCrystalUpdate(data) {
        if (this.gameClient.renderer) {
            this.gameClient.renderer.animateCrystalUpdate(data);
        }
    }

    handleMysteryEvent(data) {
        if (this.gameClient.renderer) {
            this.gameClient.renderer.animateMysteryEvent(data);
        }
    }

    handleTurnChange(data) {
        if (!this.gameClient.gameState) return;
        this.gameClient.gameState.current_turn_player_id = data.current_player_id;
        this.gameClient.gameState.turn_number = data.turn_number;
        this.gameClient.gameState.turn_phase = data.turn_phase;
        
        this.updateGameState(this.gameClient.gameState);
    }

    handleGameWon(data) {
        if (this.gameClient.renderer) {
            this.gameClient.renderer.triggerVictoryEffect();
        }
        alert(`GAME OVER! ${data.winner_name} has won the race to the crystal!`);
    }

    updateGameState(gameState) {
        if (this.networkManager.getConnectionState() !== STATE.IN_GAME) {
            return;
        }

        this.gameClient.gameState = gameState;
        this.gameClient.turnPhase = gameState.turn_phase || TurnPhase.MOVEMENT;

        if (this.gameClient.renderer) {
            this.gameClient.renderer.updateGameState(gameState);
        }
        this.gameClient.uiManager.updateHUD(gameState, this.gameClient.localPlayerId);

        if (gameState.current_turn_player_id !== this.gameClient.localPlayerId) {
            this.gameClient.selectedTokenId = null;
            this.gameClient.validMoves = new Set();
            if (this.gameClient.renderer) {
                this.gameClient.renderer.updateValidMoveIndicators(null);
                this.gameClient.renderer.updateTokenSelectionGlow(null);
            }
            if (this.gameClient.uiManager.isDeploymentMenuOpen()) {
                this.gameClient.uiManager.toggleDeploymentMenu(false);
            }
            this.gameClient.uiManager.clearSelection();
        }

        // Keep first-person highlights in sync with turn/phase/token changes
        this.gameClient.inputController?.refreshFPIndicators();
    }

    connectToServer(host, port, playerName) {
        // Clear any existing handlers to prevent accumulation on reconnect
        this.networkManager.eventHandlers.clear();
        this.setupNetworkHandlers(); // Re-setup handlers

        this.networkManager.connect(host, port, playerName);
    }

    disconnect() {
        if (this.networkManager) {
            this.networkManager.disconnect();
        }
    }

    // Game action delegates
    endTurn() {
        this.networkManager.endTurn();
    }

    deployToken(healthValue, position) {
        this.networkManager.deployToken(healthValue, position);
    }

    moveToken(tokenId, destination) {
        this.networkManager.moveToken(tokenId, destination);
    }

    attackToken(attackerId, targetId) {
        this.networkManager.attackToken(attackerId, targetId);
    }

    getConnectionState() {
        return this.networkManager ? this.networkManager.getConnectionState() : STATE.DISCONNECTED;
    }
}

/**
 * Input Controller - Handles user input and translates to game actions
 */
class InputController {
    constructor(gameClient) {
        this.gameClient = gameClient;
        this.inputHandler = null;
    }

    init() {
        // Input handler will be initialized in initGameModules
    }

    setupInputHandlers() {
        if (!this.gameClient.inputHandler) return;

        this.gameClient.inputHandler.on("click", ({ gridX, gridY }) => {
            this.handleClick(gridX, gridY);
        });

        this.gameClient.inputHandler.on("hover", ({ gridX, gridY }) => {
            if (this.gameClient.renderer) {
                this.gameClient.renderer.updateHoverIndicator(gridX, gridY);
            }
        });

        this.gameClient.inputHandler.on("keydown", (data) => {
            this.handleKeyDown(data);
        });
    }

    handleClick(gridX, gridY) {
        // Early return checks
        if (this.getConnectionState() !== STATE.IN_GAME) return;
        if (!this.gameClient.gameState || 
            this.gameClient.gameState.current_turn_player_id !== this.gameClient.localPlayerId) {
            return;
        }

        // Handle deployment
        const deployHealth = this.gameClient.uiManager.getSelectedDeployHealth();
        if (deployHealth !== null) {
            this.handleDeployment(gridX, gridY, deployHealth);
            return;
        }

        // Handle token interaction
        this.handleTokenInteraction(gridX, gridY);
    }

    handleDeployment(gridX, gridY, health) {
        this.networkManager.deployToken(health, [gridX, gridY]);
        if (this.gameClient.renderer) {
            this.gameClient.renderer.playSound("deploy");
        }
        this.gameClient.uiManager.clearSelection();
    }

    handleTokenInteraction(gridX, gridY) {
        const tokenAtCell = this.getTokenAt(gridX, gridY);

        if (this.gameClient.selectedTokenId === null) {
            this.handleTokenSelection(tokenAtCell);
        } else {
            this.handleTokenAction(gridX, gridY, tokenAtCell);
        }
    }

    handleTokenSelection(tokenAtCell) {
        if (!tokenAtCell || !this.isOurToken(tokenAtCell.id)) {
            return;
        }

        // Show valid targets based on phase
        const validTargets = this.calculateValidTargets(tokenAtCell);
        this.gameClient.stateManager.setSelectedToken(tokenAtCell.id, validTargets);

        if (this.gameClient.renderer) {
            if (this.gameClient.turnPhase === TurnPhase.MOVEMENT) {
                this.gameClient.renderer.updateValidMoveIndicators(validTargets);
            } else {
                this.gameClient.renderer.updateValidAttackIndicators(validTargets);
            }
            this.gameClient.renderer.updateTokenSelectionGlow(this.gameClient.selectedTokenId);
        }
        if (this.gameClient.renderer) {
            this.gameClient.renderer.playSound("whoosh");
        }
    }

    handleTokenAction(gridX, gridY, tokenAtCell) {
        const selectedToken = this.gameClient.gameState.tokens[this.gameClient.selectedTokenId];

        // Clicking same token - deselect
        if (tokenAtCell && tokenAtCell.id === this.gameClient.selectedTokenId) {
            this.clearSelection();
            return;
        }

        // Attack enemy token
        if (tokenAtCell && !this.isOurToken(tokenAtCell.id)) {
            if (this.gameClient.turnPhase === TurnPhase.ACTION) {
                this.attemptAttack(tokenAtCell);
            } else {
                console.log(`Cannot attack: Wrong phase (currently ${this.gameClient.turnPhase}, need ACTION)`);
            }
            return;
        }

        // Move to the clicked cell (empty cells have no token to read a
        // position from, so the move key must come from the click coords)
        const moveKey = `${gridX},${gridY}`;
        if (this.gameClient.validMoves.has(moveKey)) {
            this.attemptMove([gridX, gridY]);
        }
    }

    attemptAttack(tokenAtCell) {
        console.log(`Attempting attack: ${this.gameClient.selectedTokenId} > ${tokenAtCell.id}`);
        this.networkManager.attackToken(this.gameClient.selectedTokenId, tokenAtCell.id);
        if (this.gameClient.renderer) {
            this.gameClient.renderer.playSound("attack");
        }
        this.clearSelection();
        if (this.gameClient.renderer) {
            this.gameClient.renderer.updateValidMoveIndicators(null);
            this.gameClient.renderer.updateTokenSelectionGlow(null);
        }
    }

    attemptMove(destination) {
        if (!destination) {
            return;
        }
        this.networkManager.moveToken(this.gameClient.selectedTokenId, destination);
        if (this.gameClient.renderer) {
            this.gameClient.renderer.playSound("move");
        }
        this.clearSelection();
    }

    clearSelection() {
        this.gameClient.stateManager.clearSelection();
        if (this.gameClient.renderer) {
            this.gameClient.renderer.updateValidMoveIndicators(null);
            this.gameClient.renderer.updateTokenSelectionGlow(null);
        }
    }

    handleKeyDown(data) {
        const key = data.key;
        switch (key) {
            case "end_turn":
                this.networkManager.endTurn();
                this.clearSelection();
                break;
            case "cancel":
                this.cancelAction();
                break;
            case "deploy":
                this.toggleDeploymentMenu();
                break;
            case "camera_toggle":
                this.toggleCameraMode();
                break;
            case "cycle_token":
                this.cycleControlledToken();
                break;
            case "rotate_left":
                this.gameClient.cameraController.rotateCameraLeft();
                break;
            case "rotate_right":
                this.gameClient.cameraController.rotateCameraRight();
                break;
            case "look_up":
                this.gameClient.cameraController.lookUp();
                break;
            case "look_down":
                this.gameClient.cameraController.lookDown();
                break;
            case "move_token_forward":
                this.moveControlledOrCamera('forward');
                break;
            case "move_token_backward":
                this.moveControlledOrCamera('backward');
                break;
            case "move_token_left":
                this.moveControlledOrCamera('left');
                break;
            case "move_token_right":
                this.moveControlledOrCamera('right');
                break;
            case "toggle_music":
                if (this.gameClient.renderer) {
                    this.gameClient.renderer.toggleMusic();
                }
                break;
            case "zoom_in":
                this.gameClient.cameraController.adjustZoom(1);
                break;
            case "zoom_out":
                this.gameClient.cameraController.adjustZoom(-1);
                break;
            case "camera_forward":
                this.gameClient.cameraController.moveCameraForward();
                break;
            case "camera_backward":
                this.gameClient.cameraController.moveCameraBackward();
                break;
            case "camera_left":
                this.gameClient.cameraController.moveCameraLeft();
                break;
            case "camera_right":
                this.gameClient.cameraController.moveCameraRight();
                break;
            case "quit":
                this.quitGame();
                break;
            case "switch_player":
                this.switchPlayer(data.playerIndex);
                break;
        }
    }

    cancelAction() {
        if (this.gameClient.selectedTokenId) {
            this.clearSelection();
        } else if (this.gameClient.uiManager.getSelectedDeployHealth() !== null) {
            this.gameClient.uiManager.clearSelection();
        } else if (this.gameClient.uiManager.isDeploymentMenuOpen()) {
            this.gameClient.uiManager.toggleDeploymentMenu(false);
        }
    }

    toggleDeploymentMenu() {
        if (!this.gameClient.gameState) return;
        if (this.gameClient.gameState.current_turn_player_id !== this.gameClient.localPlayerId) {
            this.gameClient.uiManager.showActionError("Not your turn!");
            return;
        }
        if (this.gameClient.turnPhase !== TurnPhase.MOVEMENT) {
            this.gameClient.uiManager.showActionError("Can only deploy during movement phase!");
            return;
        }

        this.gameClient.uiManager.toggleDeploymentMenu(!this.gameClient.uiManager.isDeploymentMenuOpen());
    }

    toggleCameraMode() {
        const enteringFP = this.gameClient.cameraController.cameraMode === "overview";
        this.gameClient.cameraController.toggleCameraMode();

        if (enteringFP) {
            // Selection is a pointer-driven overview concept; deselect so the
            // FP indicators reflect the controlled token instead.
            this.gameClient.stateManager.clearSelection();
            this.initializeFirstPersonMode();
        } else {
            this.gameClient.controlledTokenId = null;
            this.gameClient.cameraController.controlledTokenId = null;
            if (this.gameClient.renderer) {
                this.gameClient.renderer.updateControlledTokenVisibility(null);
                this.gameClient.renderer.updateValidMoveIndicators(null);
                this.gameClient.renderer.updateValidAttackIndicators(null);
            }
        }
    }

    cycleControlledToken() {
        const newTokenId = this.gameClient.cameraController.cycleControlledToken(
            this.getAliveTokens(),
        );
        if (newTokenId) {
            this.gameClient.controlledTokenId = newTokenId;
            const token = this.gameClient.gameState?.tokens?.[this.gameClient.controlledTokenId];
            if (token) {
                this.gameClient.cameraController.snapToToken(token);
            }
            this.refreshFPIndicators();
        }
    }

    /**
     * Refresh the valid-move/attack highlights for the controlled token in
     * first-person mode, so WASD movement never happens blind.
     */
    refreshFPIndicators() {
        if (this.gameClient.cameraController?.cameraMode !== "firstperson") return;
        if (!this.gameClient.gameState || !this.gameClient.renderer) return;

        if (this.gameClient.gameState.current_turn_player_id !== this.gameClient.localPlayerId) {
            this.gameClient.renderer.updateValidMoveIndicators(null);
            this.gameClient.renderer.updateValidAttackIndicators(null);
            return;
        }

        const token = this.gameClient.gameState.tokens[this.gameClient.controlledTokenId];
        if (!token || !token.is_alive || !token.is_deployed) return;

        if (this.gameClient.turnPhase === TurnPhase.MOVEMENT) {
            this.gameClient.renderer.updateValidMoveIndicators(this.calculateValidMoves(token));
            this.gameClient.renderer.updateValidAttackIndicators(null);
        } else if (this.gameClient.turnPhase === TurnPhase.ACTION) {
            this.gameClient.renderer.updateValidMoveIndicators(null);
            this.gameClient.renderer.updateValidAttackIndicators(this.calculateValidAttackTargets(token));
        }
    }

    moveControlledOrCamera(direction) {
        // WASD/arrows steer the controlled token in first-person mode,
        // and pan the camera in overview mode.
        if (this.gameClient.cameraController.cameraMode === "firstperson") {
            this.moveControlledToken(direction);
            return;
        }
        switch (direction) {
            case 'forward':
                this.gameClient.cameraController.moveCameraForward();
                break;
            case 'backward':
                this.gameClient.cameraController.moveCameraBackward();
                break;
            case 'left':
                this.gameClient.cameraController.moveCameraLeft();
                break;
            case 'right':
                this.gameClient.cameraController.moveCameraRight();
                break;
        }
    }

    moveControlledToken(direction) {
        // Only works in first-person mode
        if (this.gameClient.cameraController.cameraMode !== 'firstperson') {
            return;
        }

        // Must have a controlled token
        if (this.gameClient.controlledTokenId === null) {
            this.gameClient.uiManager.showActionError("No token controlled! Press TAB to cycle tokens.");
            return;
        }

        // Must be our turn
        if (!this.gameClient.gameState || this.gameClient.gameState.current_turn_player_id !== this.gameClient.localPlayerId) {
            this.gameClient.uiManager.showActionError("Not your turn!");
            return;
        }

        // Must be in movement phase
        if (this.gameClient.turnPhase !== TurnPhase.MOVEMENT) {
            this.gameClient.uiManager.showActionError("Can only move during movement phase!");
            return;
        }

        const token = this.gameClient.gameState.tokens[this.gameClient.controlledTokenId];
        if (!token || !token.is_alive || !token.is_deployed) {
            this.gameClient.uiManager.showActionError("Invalid token!");
            return;
        }

        // Pick the valid destination that best matches the camera-relative
        // input direction (8-way, so diagonals work and walls never dead-end)
        const destination = this.calculateCameraRelativeDestination(token, direction);
        if (!destination) {
            this.gameClient.uiManager.showActionError("No valid move in that direction!");
            return;
        }

        this.networkManager.moveToken(this.gameClient.controlledTokenId, destination);
        if (this.gameClient.renderer) {
            this.gameClient.renderer.playSound("move");
        }
        this.refreshFPIndicators();
    }

    /**
     * Compute the camera-relative desired world direction for a movement
     * input, then choose the reachable neighbor cell whose direction best
     * matches it. The camera's horizontal view direction is derived from the
     * same yaw (tokenRotation) that drives the first-person camera, so "W"
     * always moves toward what the player sees — including diagonals.
     * @param {Object} token - Controlled token with position [gridX, gridY]
     * @param {string} direction - 'forward' | 'backward' | 'left' | 'right'
     * @returns {Array|null} [gridX, gridY] destination, or null if no valid moves
     */
    calculateCameraRelativeDestination(token, direction) {
        const angle = this.gameClient.cameraController.tokenRotation * (Math.PI / 180);
        const forwardX = Math.sin(angle);
        const forwardZ = Math.cos(angle);
        const rightX = Math.cos(angle);
        const rightZ = -Math.sin(angle);

        let desiredX = 0;
        let desiredZ = 0;
        switch (direction) {
            case 'forward':
                desiredX = forwardX; desiredZ = forwardZ;
                break;
            case 'backward':
                desiredX = -forwardX; desiredZ = -forwardZ;
                break;
            case 'left':
                desiredX = -rightX; desiredZ = -rightZ;
                break;
            case 'right':
                desiredX = rightX; desiredZ = rightZ;
                break;
        }

        const [posX, posY] = token.position;
        const validMoves = this.calculateValidMoves(token);
        const offsets = [
            [-1, -1], [-1, 0], [-1, 1],
            [0, -1],           [0, 1],
            [1, -1],  [1, 0],  [1, 1],
        ];

        let best = null;
        let bestScore = -Infinity;
        for (const [ox, oy] of offsets) {
            const key = `${posX + ox},${posY + oy}`;
            if (!validMoves.has(key)) continue;
            const score = ox * desiredX + oy * desiredZ;
            if (score > bestScore) {
                bestScore = score;
                best = [posX + ox, posY + oy];
            }
        }
        return best;
    }

    calculateValidMoves(token) {
        const validMoves = new Set();
        const moveRange = token.health >= 7 ? 1 : 2;
        const start = token.position;
        const visited = new Set();
        const posKey = (x, y) => `${x},${y}`;
        
        visited.add(posKey(start[0], start[1]));
        const queue = [[start, 0]];
        const directions = [
            [-1, -1], [-1, 0], [-1, 1],
            [0, -1],           [0, 1],
            [1, -1],  [1, 0],  [1, 1],
        ];

        while (queue.length > 0) {
            const [[x, y], distance] = queue.shift();

            if (distance < moveRange) {
                for (const [dx, dy] of directions) {
                    const nx = x + dx;
                    const ny = y + dy;
                    const key = posKey(nx, ny);

                    if (
                        nx >= 0 && nx < BOARD_CONFIG.WIDTH &&
                        ny >= 0 && ny < BOARD_CONFIG.HEIGHT &&
                        !visited.has(key)
                    ) {
                        const tokenAt = this.getTokenAt(nx, ny);
                        if (!tokenAt) {
                            visited.add(key);
                            validMoves.add(key);
                            queue.push([[nx, ny], distance + 1]);
                        }
                    }
                }
            }
        }
        return validMoves;
    }

    calculateValidAttackTargets(token) {
        const validMoves = new Set();

        // Find adjacent enemy tokens
        const [x, y] = token.position;
        const directions = [
            [-1, -1],
            [-1, 0],
            [-1, 1],
            [0, -1],
            [0, 1],
            [1, -1],
            [1, 0],
            [1, 1],
        ];

        for (const [dx, dy] of directions) {
            const nx = x + dx;
            const ny = y + dy;

            if (nx < 0 || nx >= BOARD_CONFIG.WIDTH || ny < 0 || ny >= BOARD_CONFIG.HEIGHT)
                continue;

            const enemyToken = this.getTokenAt(nx, ny);
            if (enemyToken && !this.isOurToken(enemyToken.id)) {
                validMoves.add(`${nx},${ny}`);
            }
        }

        return validMoves;
    }

    calculateValidTargets(token) {
        if (this.gameClient.turnPhase === TurnPhase.MOVEMENT) {
            return this.calculateValidMoves(token);
        } else if (this.gameClient.turnPhase === TurnPhase.ACTION) {
            return this.calculateValidAttackTargets(token);
        }
        return new Set();
    }

    getTokenAt(gridX, gridY) {
        if (!this.gameClient.gameState) return null;

        for (const token of Object.values(this.gameClient.gameState.tokens)) {
            if (
                token.is_deployed &&
                token.is_alive &&
                token.position[0] === gridX &&
                token.position[1] === gridY
            ) {
                return token;
            }
        }
        return null;
    }

    isOurToken(tokenId) {
        if (!this.gameClient.gameState) return false;
        const player = this.gameClient.gameState.players[this.gameClient.localPlayerId];
        return player && player.token_ids.includes(tokenId);
    }

    getAliveTokens() {
        if (!this.gameClient.gameState) return [];
        const player = this.gameClient.gameState.players[this.gameClient.localPlayerId];
        if (!player) return [];
        return player.token_ids
            .map((id) => this.gameClient.gameState.tokens[id])
            .filter((token) => token && token.is_alive && token.is_deployed);
    }

    initializeFirstPersonMode() {
        const newTokenId = this.gameClient.cameraController.cycleControlledToken(
            this.getAliveTokens(),
        );
        if (!newTokenId) return;

        this.gameClient.controlledTokenId = newTokenId;
        const token = this.gameClient.gameState?.tokens?.[newTokenId];
        if (token) {
            this.gameClient.cameraController.snapToToken(token);
        }
        this.refreshFPIndicators();
    }

    /**
     * Mobile Reset action: leave first-person cleanly (restoring token
     * visibility and indicators), then fly the camera back to overview.
     */
    resetToOverview() {
        if (this.gameClient.cameraController?.cameraMode === "firstperson") {
            this.toggleCameraMode();
        }
        this.gameClient.cameraController?.resetView();
    }

    quitGame() {
        // Clean up all resources
        if (this.gameClient.networkManager) {
            this.gameClient.networkManager.disconnect();
        }
        if (this.gameClient.inputHandler) {
            this.gameClient.inputHandler.dispose();
        }
        if (this.gameClient.renderer) {
            this.gameClient.renderer.dispose();
        }
        alert("Game quit. You can close this window.");
    }

    switchPlayer(playerIndex) {
        if (playerIndex !== undefined && this.gameClient.gameState) {
            const playerIds = Object.keys(this.gameClient.gameState.players);
            if (playerIndex < playerIds.length) {
                // First-person control follows the local player; drop back to
                // overview when spectating someone else's perspective.
                if (this.gameClient.cameraController?.cameraMode === "firstperson") {
                    this.toggleCameraMode();
                }
                this.gameClient.localPlayerId = playerIds[playerIndex];
                if (this.gameClient.renderer) {
                    this.gameClient.renderer.localPlayerId = this.gameClient.localPlayerId;
                }
                this.clearSelection();
            }
        }
    }

    // Delegates
    get networkManager() {
        return this.gameClient.networkManager;
    }

    getConnectionState() {
        return this.networkManager ? this.networkManager.getConnectionState() : STATE.DISCONNECTED;
    }
}

/**
 * UI Controller - Manages UI state and screen transitions
 */
class UIController {
    constructor(gameClient) {
        this.gameClient = gameClient;
    }

    init() {
        this.setupUI();
        this.setupConnectionScreen();
        this.updateUIState(STATE.DISCONNECTED);
    }

    setupUI() {
        this.gameClient.uiManager.setCanvas(this.gameClient.canvas);
    }

    setupConnectionScreen() {
        this.gameClient.uiManager.setupConnectionScreen((name, host, port) => {
            this.gameClient.connectionManager.connectToServer(host, port, name);
        });
    }

    updateUIState(state) {
        switch (state) {
            case STATE.DISCONNECTED:
                this.gameClient.uiManager.showScreen("disconnected");
                break;
            case STATE.CONNECTING:
                this.gameClient.uiManager.showScreen("connecting");
                break;
            case STATE.CONNECTED:
                this.gameClient.uiManager.showScreen("connected");
                this.setupLobbyBrowserHandlers();
                break;
            case STATE.IN_LOBBY:
                this.gameClient.uiManager.showScreen("lobby");
                break;
            case STATE.GAME_STARTING:
                this.gameClient.uiManager.showScreen("game_starting");
                break;
            case STATE.IN_GAME:
                this.gameClient.uiManager.showScreen("in_game");
                this.initGameModules();
                break;
            default:
                console.warn(`[GameClient] Unknown state: ${state}`);
        }
    }

    setupLobbyBrowserHandlers() {
        this.gameClient.uiManager.setupLobbyBrowserHandlers(
            (gameName, playerCount) => {
                if (!this.gameClient.networkManager) {
                    alert(
                        "Connection error: Network manager not found. Please reconnect.",
                    );
                    return;
                }
                this.gameClient.networkManager.createGame(gameName, playerCount || 4);
            },
            (gameId) => {
                if (!this.gameClient.networkManager) {
                    return;
                }
                this.gameClient.networkManager.joinGame(gameId);
            },
            () => {
                if (!this.gameClient.networkManager) {
                    return;
                }
                this.gameClient.networkManager.requestGameList();
            },
            () => {
                if (!this.gameClient.networkManager) {
                    return;
                }
                this.gameClient.networkManager.disconnect();
            },
        );
    }

    setupWaitingRoomHandlers() {
        this.gameClient.uiManager.setupWaitingRoomHandlers(
            () => this.toggleReady(),
            () => this.startGame(),
            () => this.leaveLobby(),
        );
    }

    toggleReady() {
        const isReady = this.gameClient.networkManager.toggleReady();
        this.gameClient.uiManager.updateReadyButton(isReady);
    }

    startGame() {
        try {
            this.gameClient.networkManager.startGame();
        } catch (error) {
            alert(error.message);
        }
    }

    leaveLobby() {
        this.gameClient.networkManager.leaveLobby();
    }

    initGameModules() {
        // Initialize renderer with device capabilities
        this.gameClient.renderer = new Renderer3D(this.gameClient.canvas, this.gameClient.deviceCapabilities);
        this.gameClient.renderer.initScene();
        this.gameClient.renderer.loadSounds();

        // Initialize camera controller with device capabilities
        this.gameClient.cameraController = new CameraController(
            this.gameClient.renderer.scene,
            this.gameClient.canvas,
            BOARD_WIDTH,
            BOARD_HEIGHT,
            CELL_SIZE,
            WALL_HEIGHT,
            this.gameClient.deviceCapabilities,
        );

        // Initialize the post-processing pipeline now that we have a camera
        if (this.gameClient.renderer && this.gameClient.cameraController.camera) {
            this.gameClient.renderer.initPipeline(this.gameClient.cameraController.camera);
        }

        // Initialize input handler with device capabilities
        this.gameClient.inputHandler = new InputHandler(
            this.gameClient.renderer.scene,
            this.gameClient.canvas,
            this.gameClient.cameraController,
            () => this.gameClient.gameState,
            () => this.gameClient.networkManager.getConnectionState(),
            this.gameClient.renderer.engine,
            this.gameClient.deviceCapabilities,
        );

        this.gameClient.renderer.setCameraUpdateCallback(() => {
            const cameraController = this.gameClient.cameraController;
            let token = null;
            if (
                cameraController.cameraMode === "firstperson" &&
                this.gameClient.gameState &&
                this.gameClient.controlledTokenId !== null
            ) {
                token = this.gameClient.gameState.tokens[this.gameClient.controlledTokenId] || null;
            }
            cameraController.update(token);

            // Re-apply every frame so mesh recreation on state updates
            // cannot resurrect the token blocking the first-person view.
            if (this.gameClient.renderer) {
                this.gameClient.renderer.updateControlledTokenVisibility(
                    token ? token.id : null,
                );
            }
        });

        this.gameClient.renderer.startRenderLoop();

        requestAnimationFrame(() => {
            this.gameClient.inputHandler.setupEventListeners();
            this.setupInputHandlers();
        });
    }

    setupInputHandlers() {
        if (this.gameClient.inputController) {
            this.gameClient.inputController.setupInputHandlers();
        }
    }
}

// Export the modules for use in GameClient
export { ConnectionManager, InputController, UIController };