/**
 * Race to the Crystal - Main Game Client (Facade)
 *
 * This is the main entry point that coordinates all modules:
 * - WebSocketClient: Network communication and lobby management
 * - UIManager: All UI screens and HUD
 * - CameraController: Overview and first-person camera modes
 * - InputHandler: Mouse and keyboard input
 * - Renderer3D: Babylon.js 3D rendering
 *
 * Architecture follows the delegation pattern - each module handles
 * its specific responsibility while the main client coordinates them.
 */

class GameClient {
    constructor() {
        this.canvas = document.getElementById("renderCanvas");

        // Modules
        this.ui = new UIManager();
        this.cameraController = null;
        this.inputHandler = null;
        this.renderer = null;
        this.wsClient = null;

        // Game state
        this.gameState = null;
        this.localPlayerId = null;
        this.selectedTokenId = null;
        this.validMoves = new Set();
        this.turnPhase = TurnPhase.MOVEMENT;

        // Animation and effects
        this.musicPlaying = true;

        this.init();
    }

    init() {
        this.setupUI();
        this.setupConnectionScreen();
        this.updateUIState(STATE.DISCONNECTED);
        console.log("Game client initialized");
    }

    setupUI() {
        this.ui.canvas = this.canvas;
    }

    setupConnectionScreen() {
        this.ui.setupConnectionScreen((name, host, port) => {
            this.connectToServer(host, port, name);
        });
    }

    connectToServer(host, port, playerName) {
        this.wsClient = new WebSocketClient();

        this.wsClient.on('connecting', () => {
            this.ui.showConnectionStatus("Connecting to server...");
            this.updateUIState(STATE.CONNECTING);
        });

        this.wsClient.on('connected', (data) => {
            this.ui.showConnectionStatus("Connected!");
            this.updateUIState(STATE.CONNECTED);
            this.wsClient.requestGameList();
        });

        this.wsClient.on('error', (data) => {
            this.ui.showConnectionError(data.message);
            this.updateUIState(STATE.DISCONNECTED);
        });

        this.wsClient.on('game_list', (data) => {
            this.ui.renderGameList(data.games);
        });

        this.wsClient.on('lobby_joined', (data) => {
            this.updateUIState(STATE.IN_LOBBY);
            this.ui.renderWaitingRoom(data.lobby, data.isHost, data.isHost);
            this.setupWaitingRoomHandlers();
        });

        this.wsClient.on('lobby_updated', (data) => {
            const lobby = data.lobby;
            const isHost = this.wsClient.isPlayerHost();
            const isReady = this.wsClient.isPlayerReady();
            this.ui.renderWaitingRoom(lobby, isHost, isReady);
            this.ui.updateStartButtonState(lobby, isHost, () => this.startGame());
        });

        this.wsClient.on('host_left', () => {
            alert("Host left the game. Returning to lobby.");
            this.leaveLobby();
        });

        this.wsClient.on('lobby_left', () => {
            this.updateUIState(STATE.CONNECTED);
            this.wsClient.requestGameList();
        });

        this.wsClient.on('game_starting', () => {
            this.updateUIState(STATE.GAME_STARTING);
        });

        this.wsClient.on('full_state', (data) => {
            this.handleFullState(data);
        });

        this.wsClient.on('invalid_action', (data) => {
            this.ui.showActionError(data.message);
        });

        this.wsClient.connect(host, port, playerName);
    }

    setupWaitingRoomHandlers() {
        this.ui.setupWaitingRoomHandlers(
            () => this.toggleReady(),
            () => this.startGame(),
            () => this.leaveLobby()
        );
    }

    updateUIState(state) {
        switch (state) {
            case STATE.DISCONNECTED:
                this.ui.showScreen('disconnected');
                break;
            case STATE.CONNECTING:
                this.ui.showScreen('connecting');
                break;
            case STATE.CONNECTED:
                this.ui.showScreen('connected');
                this.setupLobbyBrowserHandlers();
                break;
            case STATE.IN_LOBBY:
                this.ui.showScreen('lobby');
                break;
            case STATE.GAME_STARTING:
                this.ui.showScreen('game_starting');
                break;
            case STATE.IN_GAME:
                this.ui.showScreen('in_game');
                this.initGameModules();
                break;
        }
    }

    setupLobbyBrowserHandlers() {
        this.ui.setupLobbyBrowserHandlers(
            (gameName) => this.wsClient.createGame(gameName, 4),
            () => this.wsClient.requestGameList(),
            () => this.wsClient.disconnect()
        );
    }

    handleFullState(data) {
        if (this.wsClient.getConnectionState() !== STATE.IN_GAME) {
            this.updateUIState(STATE.IN_GAME);

            if (data.game_state && data.game_state.perspective_player_id) {
                this.localPlayerId = data.game_state.perspective_player_id;
                console.log(`Local player ID: ${this.localPlayerId}`);
            }
        }

        if (data.game_state) {
            this.updateGameState(data.game_state);
        }
    }

    initGameModules() {
        console.log("Initializing game modules...");

        this.renderer = new Renderer3D(this.canvas);
        this.renderer.initScene();
        this.renderer.loadSounds();

        this.cameraController = new CameraController(
            this.renderer.scene,
            this.canvas,
            BOARD_WIDTH,
            BOARD_HEIGHT,
            CELL_SIZE,
            WALL_HEIGHT
        );

        this.inputHandler = new InputHandler(
            this.renderer.scene,
            this.canvas,
            this.cameraController,
            () => this.gameState,
            () => this.wsClient.getConnectionState()
        );

        this.setupInputHandlers();
        this.renderer.startRenderLoop();

        console.log("Game modules initialized");
    }

    setupInputHandlers() {
        this.inputHandler.on('click', ({ gridX, gridY }) => {
            this.handleClick(gridX, gridY);
        });

        this.inputHandler.on('hover', ({ gridX, gridY }) => {
            this.renderer.updateHoverIndicator(gridX, gridY);
        });

        this.inputHandler.on('keydown', (data) => {
            this.handleKeyDown(data.key);
        });
    }

    updateGameState(gameState) {
        if (this.wsClient.getConnectionState() !== STATE.IN_GAME) {
            console.log("Not in game state, ignoring game state update");
            return;
        }

        console.log("Updating game state...");
        this.gameState = gameState;
        this.turnPhase = gameState.turn_phase || TurnPhase.MOVEMENT;

        this.renderer.updateGameState(gameState);
        this.ui.updateHUD(gameState, this.localPlayerId);

        if (gameState.current_turn_player_id !== this.localPlayerId) {
            this.selectedTokenId = null;
            this.validMoves = new Set();
            this.renderer.updateValidMoveIndicators(null);
            this.renderer.updateTokenSelectionGlow(null);
        }
    }

    handleClick(gridX, gridY) {
        if (this.wsClient.getConnectionState() !== STATE.IN_GAME) return;
        if (!this.gameState || this.gameState.current_turn_player_id !== this.localPlayerId) return;

        if (this.ui.getSelectedDeployHealth() !== null) {
            const health = this.ui.getSelectedDeployHealth();
            this.wsClient.deployToken(health, [gridX, gridY]);
            this.renderer.playSound("deploy");
            this.ui.clearSelection();
            console.log(`Deployed ${health}HP token at (${gridX}, ${gridY})`);
            return;
        }

        const tokenAtCell = this.getTokenAt(gridX, gridY);

        if (this.selectedTokenId === null) {
            if (tokenAtCell && this.isOurToken(tokenAtCell.id)) {
                this.selectedTokenId = tokenAtCell.id;
                this.updateValidMoves(tokenAtCell);
                this.renderer.updateTokenSelectionGlow(this.selectedTokenId);
                this.renderer.playSound("deploy");
                console.log("Selected token:", tokenAtCell.id);
            }
        } else {
            const selectedToken = this.gameState.tokens[this.selectedTokenId];

            if (tokenAtCell && tokenAtCell.id === this.selectedTokenId) {
                this.selectedTokenId = null;
                this.validMoves = new Set();
                this.renderer.updateValidMoveIndicators(null);
                this.renderer.updateTokenSelectionGlow(null);
                console.log("Deselected token");
                return;
            }

            if (tokenAtCell && !this.isOurToken(tokenAtCell.id)) {
                if (this.turnPhase === TurnPhase.ACTION) {
                    this.wsClient.attackToken(this.selectedTokenId, tokenAtCell.id);
                    this.renderer.playSound("attack");
                    this.selectedTokenId = null;
                    this.validMoves = new Set();
                    this.renderer.updateValidMoveIndicators(null);
                    this.renderer.updateTokenSelectionGlow(null);
                }
                return;
            }

            const moveKey = `${gridX},${gridY}`;
            if (this.validMoves.has(moveKey)) {
                this.wsClient.moveToken(this.selectedTokenId, [gridX, gridY]);
                this.renderer.playSound("move");
                this.selectedTokenId = null;
                this.validMoves = new Set();
                this.renderer.updateValidMoveIndicators(null);
                this.renderer.updateTokenSelectionGlow(null);
                return;
            }
        }
    }

    handleKeyDown(key) {
        switch (key) {
            case 'end_turn':
                this.wsClient.endTurn();
                this.selectedTokenId = null;
                this.validMoves = new Set();
                this.renderer.updateValidMoveIndicators(null);
                this.renderer.updateTokenSelectionGlow(null);
                break;
            case 'cancel':
                this.cancelAction();
                break;
            case 'deploy':
                this.toggleDeploymentMenu();
                break;
            case 'camera_toggle':
                this.renderer.camera = this.cameraController.toggleCameraMode();
                break;
            case 'cycle_token':
                this.cameraController.cycleControlledToken(this.getAliveTokens());
                break;
            case 'rotate_left':
                this.cameraController.rotateCameraLeft();
                break;
            case 'rotate_right':
                this.cameraController.rotateCameraRight();
                break;
            case 'toggle_music':
                this.musicPlaying = !this.musicPlaying;
                console.log(this.musicPlaying ? "Music enabled" : "Music muted");
                break;
            case 'camera_forward':
                this.cameraController.moveCameraForward();
                break;
            case 'camera_backward':
                this.cameraController.moveCameraBackward();
                break;
            case 'camera_left':
                this.cameraController.moveCameraLeft();
                break;
            case 'camera_right':
                this.cameraController.moveCameraRight();
                break;
            case 'zoom_out':
                this.cameraController.adjustFOV(15);
                break;
            case 'zoom_in':
                this.cameraController.adjustFOV(-15);
                break;
            case 'quit':
                this.quitGame();
                break;
            case 'switch_player':
                if (key.playerIndex !== undefined) {
                    this.localPlayerId = `player_${key.playerIndex}`;
                    console.log("Switched to player", this.localPlayerId);
                }
                break;
        }
    }

    getTokenAt(gridX, gridY) {
        if (!this.gameState) return null;

        for (const token of Object.values(this.gameState.tokens)) {
            if (token.is_deployed && token.is_alive &&
                token.position[0] === gridX && token.position[1] === gridY) {
                return token;
            }
        }
        return null;
    }

    isOurToken(tokenId) {
        if (!this.gameState) return false;
        const player = this.gameState.players[this.localPlayerId];
        return player && player.token_ids.includes(tokenId);
    }

    getAliveTokens() {
        if (!this.gameState) return [];
        const player = this.gameState.players[this.localPlayerId];
        if (!player) return [];
        return player.token_ids
            .map((id) => this.gameState.tokens[id])
            .filter((token) => token && token.is_alive && token.is_deployed);
    }

    updateValidMoves(token) {
        this.validMoves = new Set();

        const moveRange = token.health >= 7 ? 1 : 2;
        const start = token.position;
        const visited = new Set();
        visited.add(`${start[0]},${start[1]}`);

        const queue = [[start, 0]];
        const directions = [
            [-1, -1], [-1, 0], [-1, 1],
            [0, -1], [0, 1],
            [1, -1], [1, 0], [1, 1],
        ];

        while (queue.length > 0) {
            const [[x, y], distance] = queue.shift();

            if (distance >= moveRange) continue;

            for (const [dx, dy] of directions) {
                const nx = x + dx;
                const ny = y + dy;
                const posKey = `${nx},${ny}`;

                if (visited.has(posKey)) continue;
                if (nx < 0 || nx >= BOARD_WIDTH || ny < 0 || ny >= BOARD_HEIGHT) continue;

                const tokenAtCell = this.getTokenAt(nx, ny);
                if (tokenAtCell && !this.isOurToken(tokenAtCell.id)) continue;

                if (tokenAtCell && this.isOurToken(tokenAtCell.id)) {
                    const cell = this.gameState?.board?.grid?.[ny]?.[nx];
                    const isGeneratorOrCrystal = cell?.cell_type === 2 || cell?.cell_type === 3;
                    if (!isGeneratorOrCrystal) continue;
                }

                visited.add(posKey);

                if (nx !== start[0] || ny !== start[1]) {
                    this.validMoves.add(posKey);
                }

                queue.push([[nx, ny], distance + 1]);
            }
        }

        const movesArray = Array.from(this.validMoves).map((key) => {
            const [x, y] = key.split(",").map(Number);
            return [x, y];
        });
        this.renderer.updateValidMoveIndicators(new Set(movesArray));
    }

    toggleDeploymentMenu() {
        if (!this.gameState) return;
        if (this.gameState.current_turn_player_id !== this.localPlayerId) return;
        if (this.turnPhase !== TurnPhase.MOVEMENT) return;

        this.ui.toggleDeploymentMenu(!this.ui.isDeploymentMenuOpen());
    }

    cancelAction() {
        if (this.selectedTokenId) {
            this.selectedTokenId = null;
            this.validMoves = new Set();
            this.renderer.updateValidMoveIndicators(null);
            this.renderer.updateTokenSelectionGlow(null);
        } else if (this.ui.getSelectedDeployHealth() !== null) {
            this.ui.clearSelection();
        } else if (this.ui.isDeploymentMenuOpen()) {
            this.ui.toggleDeploymentMenu(false);
        }
    }

    toggleReady() {
        const isReady = this.wsClient.toggleReady();
        this.ui.updateReadyButton(isReady);
    }

    startGame() {
        try {
            this.wsClient.startGame();
        } catch (error) {
            alert(error.message);
        }
    }

    leaveLobby() {
        this.wsClient.leaveLobby();
    }

    quitGame() {
        console.log("Quitting game...");
        if (this.wsClient) {
            this.wsClient.disconnect();
        }
        if (this.renderer) {
            this.renderer.dispose();
        }
        alert("Game quit. You can close this window.");
    }
}

// Initialize game when page loads
window.addEventListener('DOMContentLoaded', () => {
    window.gameClient = new GameClient();
});
