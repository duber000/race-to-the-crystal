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
        this.networkManager.on("token_moved", (data) => {
            this.handleTokenMoved(data);
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
            this.handleTokenAction(tokenAtCell);
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

    handleTokenAction(tokenAtCell) {
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

        // Move to empty cell
        const moveKey = `${tokenAtCell ? tokenAtCell.position[0] : 'none'},${tokenAtCell ? tokenAtCell.position[1] : 'none'}`;
        if (this.gameClient.validMoves.has(moveKey)) {
            this.attemptMove(tokenAtCell);
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

    attemptMove(tokenAtCell) {
        const destination = tokenAtCell ? [tokenAtCell.position[0], tokenAtCell.position[1]] : null;
        if (destination) {
            this.networkManager.moveToken(this.gameClient.selectedTokenId, destination);
            if (this.gameClient.renderer) {
                this.gameClient.renderer.playSound("move");
            }
        }
        this.clearSelection();
        if (this.gameClient.renderer) {
            this.gameClient.renderer.updateValidMoveIndicators(null);
            this.gameClient.renderer.updateTokenSelectionGlow(null);
        }
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
                this.moveControlledToken('forward');
                break;
            case "move_token_backward":
                this.moveControlledToken('backward');
                break;
            case "move_token_left":
                this.moveControlledToken('left');
                break;
            case "move_token_right":
                this.moveControlledToken('right');
                break;
            case "toggle_music":
                if (this.gameClient.renderer) {
                    this.gameClient.renderer.toggleMusic();
                }
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
            case "zoom_out":
                this.gameClient.cameraController.adjustFOV(15);
                break;
            case "zoom_in":
                this.gameClient.cameraController.adjustFOV(-15);
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
        this.gameClient.renderer.camera = this.gameClient.cameraController.toggleCameraMode();
        // Re-attach pipeline to the new active camera
        if (this.gameClient.renderer.pipeline) {
            this.gameClient.renderer.pipeline.addCamera(this.gameClient.renderer.camera);
        }
        if (this.gameClient.cameraController.cameraMode === "firstperson") {
            this.initializeFirstPersonMode();
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
                this.gameClient.cameraController.updateFirstPersonCamera(token);
            }
        }
    }

    moveControlledToken(direction) {
        // Only works in first-person mode
        if (this.gameClient.cameraController.cameraMode !== 'firstperson') {
            return;
        }

        // Must have a controlled token
        if (this.gameClient.controlledTokenId === null) {
            this.gameClient.uiManager.showActionError("No token selected!");
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

        // Calculate destination based on camera orientation
        const destination = this.calculateDestinationFromCameraRotation(token.position, direction);
        const [destX, destY] = destination;

        // Check if destination is on the board
        if (destX < 0 || destX >= BOARD_WIDTH || destY < 0 || destY >= BOARD_HEIGHT) {
            this.gameClient.uiManager.showActionError("Cannot move off the board!");
            return;
        }

        // Check if it's a valid move by calculating valid moves for this token
        const validMoves = this.calculateValidMoves(token);
        const moveKey = `${destX},${destY}`;

        if (validMoves.has(moveKey)) {
            this.networkManager.moveToken(this.gameClient.controlledTokenId, destination);
            if (this.gameClient.renderer) {
                this.gameClient.renderer.playSound("move");
            }
            this.gameClient.validMoves = new Set();
            if (this.gameClient.renderer) {
                this.gameClient.renderer.updateValidMoveIndicators(null);
            }
        } else {
            this.gameClient.uiManager.showActionError("Invalid move!");
        }
    }

    calculateDestinationFromCameraRotation(currentPos, direction) {
        // Get camera rotation in degrees
        // 0° = facing north (-Z), 90° = facing west (-X), 180° = facing south (+Z), 270° = facing east (+X)
        const rotation = this.gameClient.cameraController.tokenRotation;

        // Normalize rotation to 0-360
        const normalizedRotation = ((rotation % 360) + 360) % 360;

        // Determine cardinal direction based on rotation
        // Quantize to nearest 90 degrees
        const cardinalIndex = Math.round(normalizedRotation / 90) % 4;

        // Cardinal directions in grid space:
        // 0: North (-Y), 1: West (-X), 2: South (+Y), 3: East (+X)
        const cardinals = [
            [0, -1],  // North: -Y (toward 0,0)
            [-1, 0],  // West: -X (toward 0,0)
            [0, 1],   // South: +Y (toward 23,23)
            [1, 0]    // East: +X (toward 23,23)
        ];

        let directionIndex = cardinalIndex;

        // Adjust based on movement direction
        switch (direction) {
            case 'forward':
                // Keep current facing direction
                break;
            case 'backward':
                directionIndex = (directionIndex + 2) % 4;
                break;
            case 'left':
                directionIndex = (directionIndex + 3) % 4;
                break;
            case 'right':
                directionIndex = (directionIndex + 1) % 4;
                break;
        }

        const [dx, dy] = cardinals[directionIndex];
        return [currentPos[0] + dx, currentPos[1] + dy];
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
        const aliveTokens = this.getAliveTokens();
        if (aliveTokens.length > 0) {
            this.gameClient.controlledTokenId = aliveTokens[0].id;
            const token = this.gameClient.gameState?.tokens?.[this.gameClient.controlledTokenId];
            if (token) {
                this.gameClient.cameraController.updateFirstPersonCamera(token);
            }
        }
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
                this.gameClient.localPlayerId = playerIds[playerIndex];
                if (this.gameClient.renderer) {
                    this.gameClient.renderer.localPlayerId = this.gameClient.localPlayerId;
                }
                this.clearSelection();
                if (this.gameClient.renderer) {
                    this.gameClient.renderer.updateValidMoveIndicators(null);
                    this.gameClient.renderer.updateTokenSelectionGlow(null);
                }
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
            if (
                this.gameClient.cameraController.cameraMode === "firstperson" &&
                this.gameClient.gameState &&
                this.gameClient.controlledTokenId !== null
            ) {
                const token = this.gameClient.gameState.tokens[this.gameClient.controlledTokenId];
                if (token) {
                    this.gameClient.cameraController.updateFirstPersonCamera(token);
                }
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