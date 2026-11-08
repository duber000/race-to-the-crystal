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
        // The end of a match arrives twice: as a GAME_ENDED event on the
        // event stream and as a GAME_WON message. The victory effect must
        // only fire once.
        this.victoryTriggered = false;
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
            if (this.pendingSpectateGameId) {
                const gid = this.pendingSpectateGameId;
                const follow = this.pendingSpectateFollow || "";
                this.pendingSpectateGameId = null;
                this.pendingSpectateFollow = null;
                this.networkManager.send({ type: 'SPECTATE', game_id: gid, follow });
                return;
            }
            this.gameClient.updateUIState(STATE.CONNECTED);
            this.networkManager.requestGameList();
        });

        this.networkManager.on("game_list", (data) => {
            this.gameClient.isSpectator = false;
            if (this.gameClient.uiManager.hideSpectateBanner) {
                this.gameClient.uiManager.hideSpectateBanner();
            }
            this.gameClient.uiManager.renderGameList(data.games || []);
        });
        this.networkManager.on("spectate_ack", (data) => {
            this.gameClient.isSpectator = true;
            this.gameClient.spectatingFollowing = data && data.follow_name ? data.follow_name : null;
            if (this.gameClient.uiManager.showSpectateBanner) {
                this.gameClient.uiManager.showSpectateBanner(this.gameClient.spectatingFollowing || 'seat');
            }
            this.gameClient.updateUIState(STATE.IN_GAME);
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
            this.victoryTriggered = false;
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
        // The server's event vocabulary (server/ws_endpoint.kuki) delivered
        // as EVENT frames. The names here are the lowercased wire types.
        this.networkManager.on("token_moved", (data) => {
            this.handleTokenMoved(data);
        });

        this.networkManager.on("combat_resolved", (data) => {
            this.handleCombatResolved(data);
        });

        this.networkManager.on("token_deployed", (data) => {
            this.handleTokenDeployed(data);
        });

        this.networkManager.on("generator_changed", (data) => {
            this.handleGeneratorChanged(data);
        });

        this.networkManager.on("crystal_changed", (data) => {
            this.handleCrystalChanged(data);
        });

        this.networkManager.on("mystery_triggered", (data) => {
            this.handleMysteryTriggered(data);
        });

        this.networkManager.on("turn_changed", (data) => {
            this.handleTurnChanged(data);
        });

        this.networkManager.on("turn_timed_out", (data) => {
            this.handleTurnTimedOut(data);
        });

        this.networkManager.on("radio_chatter", (data) => {
            this.handleRadioChatter(data);
        });

        this.networkManager.on("game_ended", (data) => {
            this.handleGameEnded(data);
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
        if (this.gameClient.replayMode) return;
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
        if (this.gameClient.replayMode) return;
        this.stateManager.applyDelta(delta);
    }

    handleTokenMoved(data) {
        const token = this.gameClient.gameState?.tokens?.[data.token_id];
        if (!token) return;

        // Update local state for immediate feedback. The authoritative state
        // follows as a FULL_STATE, which overwrites this. A token hidden by
        // fog of war has no position and is never sent a move.
        token.position = data.new_position;

        // Trigger animation in renderer
        if (this.gameClient.renderer) {
            this.gameClient.renderer.animateTokenMove(data.token_id, data.old_position, data.new_position);
        }

        // Refresh basic state info
        this.updateGameState(this.gameClient.gameState);
    }

    handleCombatResolved(data) {
        if (!this.gameClient.gameState) return;

        // Update local state (health, destruction) for immediate feedback.
        const defender = this.gameClient.gameState.tokens[data.defender_id];
        if (defender) {
            defender.health = Math.max(0, defender.health - data.damage);
            if (data.defender_killed) {
                defender.is_alive = false;
            }
        }

        // Trigger animation in renderer
        if (this.gameClient.renderer) {
            this.gameClient.renderer.animateCombat(data);
            if (this.gameClient.renderer.audioManager) {
                this.gameClient.renderer.audioManager.duck('music', 0.75, 0.6);
                this.gameClient.renderer.audioManager.duck('hum', 0.75, 0.6);
                this.gameClient.renderer.audioManager.playSynthesizedSound('bass_hit');
            }
        }

        // Camera choreography: briefly frame the defender on combat.
        if (data.defender_position && this.gameClient.cameraController) {
            const cc = this.gameClient.cameraController;
            cc.focusOn(data.defender_position, { radius: 38, duration: 0.45 });
            setTimeout(() => cc.releaseFocus(), 1100);
        }

        this.updateGameState(this.gameClient.gameState);
    }

    handleTokenDeployed(data) {
        // (State synchronisation happens via the next state update; the
        // event only drives the spawn animation.)
        if (this.gameClient.renderer) {
            this.gameClient.renderer.animateTokenDeploy(data);
        }
    }

    handleGeneratorChanged(data) {
        if (this.gameClient.renderer) {
            this.gameClient.renderer.animateGeneratorUpdate(data);
            if (data && data.is_disabled && this.gameClient.renderer.audioManager) {
                this.gameClient.renderer.audioManager.playSynthesizedSound('chord_rise');
            }
        }
        if (data && data.is_disabled && data.position && this.gameClient.cameraController) {
            const cc = this.gameClient.cameraController;
            cc.focusOn(data.position, { radius: 42, duration: 0.55 });
            setTimeout(() => cc.releaseFocus(), 1500);
        }
    }

    handleCrystalChanged(data) {
        if (this.gameClient.renderer) {
            this.gameClient.renderer.animateCrystalUpdate(data);
        }
        if (data && data.position && !data.is_contested && this.gameClient.cameraController) {
            const cc = this.gameClient.cameraController;
            cc.focusOn(data.position, { radius: 40, duration: 0.5 });
            setTimeout(() => cc.releaseFocus(), 1300);
        }
    }

    handleMysteryTriggered(data) {
        if (this.gameClient.renderer) {
            this.gameClient.renderer.animateMysteryEvent(data);
        }
    }

    handleTurnChanged(data) {
        // The countdown does not depend on the game state: the server sends
        // the event before the first FULL_STATE, so the state may still be
        // null here.
        this.gameClient.uiManager.startTurnCountdown(
            data.turn_timeout_seconds || 0,
            data.current_player_id,
        );

        if (!this.gameClient.gameState) return;
        this.gameClient.gameState.current_turn_player_id = data.current_player_id;
        this.gameClient.gameState.turn_number = data.turn_number;
        this.gameClient.gameState.turn_phase = data.turn_phase;

        this.updateGameState(this.gameClient.gameState);
    }

    handleTurnTimedOut(data) {
        // The server passed on a turn that ran out of time.
        this.gameClient.uiManager.showActionError(
            `${data.player_name} ran out of time — turn passed on.`,
        );
        this.gameClient.uiManager.stopTurnCountdown();
    }

    handleRadioChatter(data) {
        console.log(`📻 ${data.player_name}: ${data.text}`);
        if (this.gameClient.commsManager) {
            this.gameClient.commsManager.add(data);
        }
    }

    handleGameEnded(data) {
        this.triggerVictoryOnce();
    }

    handleGameWon(data) {
        this.triggerVictoryOnce();
        alert(`GAME OVER! ${data.winner_name} has won the race to the crystal!`);
    }

    /**
     * Play the victory effect, at most once per match.
     *
     * The end of a match is announced twice — a GAME_ENDED event on the
     * event stream and a GAME_WON message — so the effect has to be
     * idempotent or the confetti is spawned twice.
     */
    triggerVictoryOnce() {
        if (this.victoryTriggered) {
            return;
        }
        this.victoryTriggered = true;
        if (this.gameClient.renderer) {
            this.gameClient.renderer.triggerVictoryEffect();
        }
    }

    updateGameState(gameState) {
        if (this.networkManager.getConnectionState() !== STATE.IN_GAME) {
            return;
        }

        this.gameClient.gameState = gameState;

        // Delegate to the façade so there is a single implementation of the
        // state -> view sync (renderer, HUD, selection, first-person hints).
        this.gameClient.handleStateChanged(gameState);
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

    spectateGame(gameId, follow) {
        this.gameClient.isSpectator = true;
        this.pendingSpectateGameId = gameId;
        this.pendingSpectateFollow = follow || "";
        if (!this.networkManager) this.init();
        if (this.networkManager.connectionState === STATE.CONNECTED) {
            const followNow = this.pendingSpectateFollow;
            this.pendingSpectateGameId = null;
            this.pendingSpectateFollow = null;
            this.networkManager.send({ type: 'SPECTATE', game_id: gameId, follow: followNow });
        } else {
            // reuse default connection inputs
            const host = (document.getElementById('server-host-input')?.value || 'localhost').trim();
            const port = (document.getElementById('server-port-input')?.value || '8000').trim();
            const name = (document.getElementById('player-name-input')?.value || 'Spectator').trim();
            this.networkManager.connect(host, port, name);
        }
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
                        if (tokenAt) {
                            // An enemy token always blocks the cell. A
                            // friendly token blocks it too, *unless* the
                            // cell is a generator or the crystal: the
                            // server lets friendly tokens stack on those,
                            // and both the generator capture (two tokens)
                            // and the crystal capture (up to twelve) need
                            // several tokens on one cell. Without this the
                            // browser could never stack a second token and
                            // the match could never be won.
                            const isFriendly =
                                tokenAt.player_id === this.gameClient.localPlayerId;
                            if (!isFriendly || !this.isStackableCell(nx, ny)) {
                                continue;
                            }
                        }
                        visited.add(key);
                        validMoves.add(key);
                        queue.push([[nx, ny], distance + 1]);
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
                // A token hidden by fog of war has no position.
                token.position &&
                token.position[0] === gridX &&
                token.position[1] === gridY
            ) {
                return token;
            }
        }
        return null;
    }

    /**
     * Whether friendly tokens may share this cell.
     *
     * The server only lets two of your own tokens stand on the same cell
     * when that cell is a generator or the crystal — both captures need
     * several tokens on one cell. Cell types: 1 = generator, 2 = crystal.
     */
    isStackableCell(gridX, gridY) {
        const state = this.gameClient.gameState;
        if (!state || !state.board || !state.board.grid) return false;
        const row = state.board.grid[gridY];
        if (!row) return false;
        const cell = row[gridX];
        if (!cell) return false;
        return cell.cell_type === 1 || cell.cell_type === 2;
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
            (gameId, follow) => {
                if (!this.gameClient.connectionManager) {
                    return;
                }
                this.gameClient.connectionManager.spectateGame(gameId, follow);
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
        if (this.gameClient.renderer) {
            this.gameClient.renderer.cameraController = this.gameClient.cameraController;
        }

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