// ==========================================================================
// Race to the Crystal - Main Game Client (Facade)
// ==========================================================================

// Import modules
import { NetworkManager } from './network_manager.js';
import { StateManager } from './state_manager.js';
import { UIManager } from './ui_manager.js';
import { CameraController } from './camera_controller.js';
import { InputHandler } from './input_handler.js';
import { DeviceCapabilities } from './game_client.device.js';
import { BOARD_CONFIG, GAME_PHASE, UI_STATE, INPUT_CONFIG, TurnPhase, STATE, CELL_SIZE, BOARD_WIDTH, BOARD_HEIGHT, WALL_HEIGHT } from './game_client.constants.js';
import { Renderer3D } from './game_client.renderer.js';

/**
 * Race to the Crystal - Main Game Client (Facade)
 *
 * This is the main entry point that coordinates all modules:
 * - NetworkManager: Network communication and lobby management
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

    // Device capabilities detection
    this.deviceCapabilities = new DeviceCapabilities();
    this.deviceCapabilities.logCapabilities();

    // Initialize modules
    this.networkManager = new NetworkManager();
    this.uiManager = new UIManager();
    this.cameraController = null;
    this.inputHandler = null;
    this.renderer = null;

    // Game state (managed by StateManager)
    this.stateManager = new StateManager();
    this.gameInitialized = false;
    this.turnPhase = GAME_PHASE.MOVEMENT;

    // Direct access for convenience (optional)
    Object.defineProperty(this, 'gameState', { get: () => this.stateManager.gameState });
    Object.defineProperty(this, 'localPlayerId', { get: () => this.stateManager.localPlayerId });
    Object.defineProperty(this, 'selectedTokenId', { get: () => this.stateManager.selectedTokenId });
    Object.defineProperty(this, 'controlledTokenId', { get: () => this.stateManager.controlledTokenId });
    Object.defineProperty(this, 'validMoves', { get: () => this.stateManager.validMoves });

    // Setup state change callback
    this.stateManager.setChangeCallback((state) => this.handleStateChanged(state));

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
    this.uiManager.setCanvas(this.canvas);
  }

  setupConnectionScreen() {
    this.uiManager.setupConnectionScreen((name, host, port) => {
      this.connectToServer(host, port, name);
    });
  }

  connectToServer(host, port, playerName) {
    this.networkManager.on("connecting", () => {
      this.uiManager.showConnectionStatus("Connecting to server...");
      this.updateUIState(STATE.CONNECTING);
    });

    this.networkManager.on("connected", (data) => {
      this.uiManager.showConnectionStatus("Connected!");
      this.uiManager.playerId = data.player_id || data.playerId;
      this.updateUIState(STATE.CONNECTED);
      this.networkManager.requestGameList();
    });

    this.networkManager.on("error", (data) => {
      this.uiManager.showConnectionError(data.message);
      this.updateUIState(STATE.DISCONNECTED);
    });

    this.networkManager.on("disconnect", () => {
      this.uiManager.playerId = null;
      this.updateUIState(STATE.DISCONNECTED);
    });

    this.networkManager.on("game_list", (data) => {
      this.uiManager.onJoinGame = (gameId) => this.networkManager.joinGame(gameId);
      this.uiManager.setupLobbyBrowserHandlers(
        (gameName, playerCount) => this.networkManager.createGame(gameName, playerCount),
        () => this.networkManager.requestGameList(),
        () => this.networkManager.disconnect()
      );
      this.uiManager.renderGameList(data.games);
    });

    this.networkManager.on("lobby_joined", (data) => {
      this.updateUIState(STATE.IN_LOBBY);
      const isReady = this.networkManager.isPlayerReady();
      this.uiManager.renderWaitingRoom(data.lobby, data.isHost, isReady);
      this.setupWaitingRoomHandlers();
    });

    this.networkManager.on("lobby_updated", (data) => {
      const lobby = data.lobby;
      const isHost = this.networkManager.isPlayerHost();
      const isReady = this.networkManager.isPlayerReady();
      this.uiManager.renderWaitingRoom(lobby, isHost, isReady);
      this.uiManager.updateStartButtonState(lobby, isHost, () => this.startGame());
    });

    this.networkManager.on("host_left", () => {
      alert("Host left the game. Returning to lobby.");
      this.leaveLobby();
    });

    this.networkManager.on("lobby_left", () => {
      this.updateUIState(STATE.CONNECTED);
      this.networkManager.requestGameList();
    });

    this.networkManager.on("game_starting", () => {
      // Only transition to game_starting if not already in game
      if (this.networkManager.getConnectionState() !== STATE.IN_GAME) {
        this.updateUIState(STATE.GAME_STARTING);
      }
    });

    this.networkManager.on("full_state", (data) => {
      this.handleFullState(data);
    });

    this.networkManager.on("state_update", (data) => {
      this.handleStateUpdate(data);
    });

    // Fine-grained SSE Events for animations
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
      this.uiManager.showActionError(data.message);
    });

    this.networkManager.connect(host, port, playerName);
  }

  setupWaitingRoomHandlers() {
    this.uiManager.setupWaitingRoomHandlers(
      () => this.toggleReady(),
      () => this.startGame(),
      () => this.leaveLobby(),
    );
  }

  updateUIState(state) {
    switch (state) {
      case STATE.DISCONNECTED:
        this.uiManager.showScreen("disconnected");
        break;
      case STATE.CONNECTING:
        this.uiManager.showScreen("connecting");
        break;
      case STATE.CONNECTED:
        this.uiManager.showScreen("connected");
        this.setupLobbyBrowserHandlers();
        break;
      case STATE.IN_LOBBY:
        this.uiManager.showScreen("lobby");
        break;
      case STATE.GAME_STARTING:
        this.uiManager.showScreen("game_starting");
        break;
      case STATE.IN_GAME:
        this.uiManager.showScreen("in_game");
        this.initGameModules();
        break;
      default:
        console.warn(`[GameClient] Unknown state: ${state}`);
    }
  }

  setupLobbyBrowserHandlers() {
    this.uiManager.setupLobbyBrowserHandlers(
      (gameName, playerCount) => {
        if (!this.networkManager) {
          alert(
            "Connection error: Network manager not found. Please reconnect.",
          );
          return;
        }
        this.networkManager.createGame(gameName, playerCount || 4);
      },
      () => {
        if (!this.networkManager) {
          return;
        }
        this.networkManager.requestGameList();
      },
      () => {
        if (!this.networkManager) {
          return;
        }
        this.networkManager.disconnect();
      },
    );
  }

  handleFullState(data) {
    // Initialize game modules on first FULL_STATE
    if (!this.gameInitialized) {
      this.gameInitialized = true;
      this.networkManager.connectionState = STATE.IN_GAME;
      this.updateUIState(STATE.IN_GAME);
    }

    this.stateManager.setFullState(data);

    if (data.last_action && this.renderer) {
      this.renderer.playSound(data.last_action);
    }
  }

  handleStateUpdate(delta) {
    this.stateManager.applyDelta(delta);
  }

  handleStateChanged(state) {
    if (this.networkManager.getConnectionState() !== STATE.IN_GAME) {
      return;
    }

    this.turnPhase = state.turn_phase || TurnPhase.MOVEMENT;

    if (this.renderer) {
      this.renderer.localPlayerId = this.stateManager.localPlayerId;
      this.renderer.updateGameState(state);
      this.renderer.updateValidMoveIndicators(this.stateManager.selectedTokenId);
      this.renderer.updateTokenSelectionGlow(this.stateManager.selectedTokenId);
    }
    
    this.uiManager.updateHUD(state, this.stateManager.localPlayerId);

    // Auto-clear selection if it's not our turn
    if (state.current_turn_player_id !== this.stateManager.localPlayerId) {
      this.stateManager.clearSelection();
      if (this.renderer) {
        this.renderer.updateValidMoveIndicators(null);
        this.renderer.updateTokenSelectionGlow(null);
      }
      if (this.uiManager.isDeploymentMenuOpen()) {
        this.uiManager.toggleDeploymentMenu(false);
      }
      this.uiManager.clearSelection();
    }
  }

  handleTokenMoved(data) {
    if (!this.gameState || !this.gameState.tokens[data.token_id]) return;
    
    // Update local state for immediate feedback
    this.gameState.tokens[data.token_id].position = data.new_position;
    
    // Trigger animation in renderer
    if (this.renderer) {
      this.renderer.animateTokenMove(data.token_id, data.old_position, data.new_position);
    }
    
    // Refresh basic state info
    this.updateGameState(this.gameState);
  }

  handleCombatResult(data) {
    if (!this.gameState) return;
    
    // Update local state (health, destruction)
    const defender = this.gameState.tokens[data.defender_id];
    if (defender) {
      defender.health -= data.damage;
      if (data.defender_destroyed) {
        defender.is_alive = false;
      }
    }
    
    // Trigger animation in renderer
    if (this.renderer) {
      this.renderer.animateCombat(data);
    }
    
    this.updateGameState(this.gameState);
  }

  handleTokenDeployed(data) {
    if (!this.gameState) return;
    // (Actual synchronization usually happens via the next state update, 
    // but we can trigger a spawn animation here)
    if (this.renderer) {
      this.renderer.animateTokenDeploy(data);
    }
  }

  handleGeneratorUpdate(data) {
    if (this.renderer) {
      this.renderer.animateGeneratorUpdate(data);
    }
  }

  handleCrystalUpdate(data) {
    if (this.renderer) {
      this.renderer.animateCrystalUpdate(data);
    }
  }

  handleMysteryEvent(data) {
    if (this.renderer) {
        this.renderer.animateMysteryEvent(data);
    }
  }

  handleTurnChange(data) {
    if (!this.gameState) return;
    this.gameState.current_turn_player_id = data.current_player_id;
    this.gameState.turn_number = data.turn_number;
    this.gameState.turn_phase = data.turn_phase;
    
    this.updateGameState(this.gameState);
  }

  handleGameWon(data) {
    if (this.renderer) {
      this.renderer.triggerVictoryEffect();
    }
    alert(`GAME OVER! ${data.winner_name} has won the race to the crystal!`);
  }

  initGameModules() {
    // Initialize renderer with device capabilities
    this.renderer = new Renderer3D(this.canvas, this.deviceCapabilities);
    this.renderer.initScene();
    this.renderer.loadSounds();

    // Initialize camera controller with device capabilities
    this.cameraController = new CameraController(
      this.renderer.scene,
      this.canvas,
      BOARD_WIDTH,
      BOARD_HEIGHT,
      CELL_SIZE,
      WALL_HEIGHT,
      this.deviceCapabilities,
    );

    // Initialize the post-processing pipeline now that we have a camera
    if (this.renderer && this.cameraController.camera) {
      this.renderer.initPipeline(this.cameraController.camera);
    }

    // Initialize input handler with device capabilities
    this.inputHandler = new InputHandler(
      this.renderer.scene,
      this.canvas,
      this.cameraController,
      () => this.gameState,
      () => this.networkManager.getConnectionState(),
      this.renderer.engine,
      this.deviceCapabilities,
    );


    this.renderer.setCameraUpdateCallback(() => {
      if (
        this.cameraController.cameraMode === "firstperson" &&
        this.gameState &&
        this.controlledTokenId !== null
      ) {
        const token = this.gameState.tokens[this.controlledTokenId];
        if (token) {
          this.cameraController.updateFirstPersonCamera(token);
        }
      }
    });

    this.renderer.startRenderLoop();

    requestAnimationFrame(() => {
      this.inputHandler.setupEventListeners();
      this.setupInputHandlers();
    });
  }

  setupInputHandlers() {
    this.inputHandler.on("click", ({ gridX, gridY }) => {
      this.handleClick(gridX, gridY);
    });

    this.inputHandler.on("hover", ({ gridX, gridY }) => {
      this.renderer.updateHoverIndicator(gridX, gridY);
    });

    this.inputHandler.on("keydown", (data) => {
      this.handleKeyDown(data);
    });
  }


  updateGameState(gameState) {
    if (this.networkManager.getConnectionState() !== STATE.IN_GAME) {
      return;
    }

    this.gameState = gameState;
    this.turnPhase = gameState.turn_phase || TurnPhase.MOVEMENT;

    if (this.renderer) {
      this.renderer.updateGameState(gameState);
    }
    this.uiManager.updateHUD(gameState, this.localPlayerId);

    if (gameState.current_turn_player_id !== this.localPlayerId) {
      this.selectedTokenId = null;
      this.validMoves = new Set();
      if (this.renderer) {
        this.renderer.updateValidMoveIndicators(null);
        this.renderer.updateTokenSelectionGlow(null);
      }
      if (this.uiManager.isDeploymentMenuOpen()) {
        this.uiManager.toggleDeploymentMenu(false);
      }
      this.uiManager.clearSelection();
    }
  }

  handleClick(gridX, gridY) {
    if (this.networkManager.getConnectionState() !== STATE.IN_GAME) return;
    if (
      !this.gameState ||
      this.gameState.current_turn_player_id !== this.localPlayerId
    )
      return;

    if (this.uiManager.getSelectedDeployHealth() !== null) {
      const health = this.uiManager.getSelectedDeployHealth();
      this.networkManager.deployToken(health, [gridX, gridY]);
      this.renderer.playSound("deploy");
      this.uiManager.clearSelection();
      return;
    }

    const tokenAtCell = this.getTokenAt(gridX, gridY);

    if (this.selectedTokenId === null) {
      if (tokenAtCell && this.isOurToken(tokenAtCell.id)) {
        // Show valid moves in MOVEMENT phase, attack targets in ACTION phase
        let validMoves = new Set();
        if (this.turnPhase === TurnPhase.MOVEMENT) {
          validMoves = this.calculateValidMoves(tokenAtCell);
        } else if (this.turnPhase === TurnPhase.ACTION) {
          validMoves = this.calculateValidAttackTargets(tokenAtCell);
        }
        
        this.stateManager.setSelectedToken(tokenAtCell.id, validMoves);
        
        if (this.renderer) {
          if (this.turnPhase === TurnPhase.MOVEMENT) {
            this.renderer.updateValidMoveIndicators(validMoves);
          } else {
            this.renderer.updateValidAttackIndicators(validMoves);
          }
          this.renderer.updateTokenSelectionGlow(this.selectedTokenId);
        }
        this.renderer.playSound("deploy");
      }
    } else {
      const selectedToken = this.gameState.tokens[this.selectedTokenId];

      if (tokenAtCell && tokenAtCell.id === this.selectedTokenId) {
        this.stateManager.clearSelection();
        if (this.renderer) {
          this.renderer.updateValidMoveIndicators(null);
          this.renderer.updateTokenSelectionGlow(null);
        }
        return;
      }

      if (tokenAtCell && !this.isOurToken(tokenAtCell.id)) {
        if (this.turnPhase === TurnPhase.ACTION) {
          console.log(`Attempting attack: ${this.selectedTokenId} > ${tokenAtCell.id}`);
          this.networkManager.attackToken(this.selectedTokenId, tokenAtCell.id);
          this.renderer.playSound("attack");
          this.stateManager.clearSelection();
          if (this.renderer) {
            this.renderer.updateValidMoveIndicators(null);
            this.renderer.updateTokenSelectionGlow(null);
          }
        } else {
          console.log(`Cannot attack: Wrong phase (currently ${this.turnPhase}, need ACTION)`);
        }
        return;
      }

      const moveKey = `${gridX},${gridY}`;
      if (this.validMoves.has(moveKey)) {
        this.networkManager.moveToken(this.selectedTokenId, [gridX, gridY]);
        this.renderer.playSound("move");
        this.stateManager.clearSelection();
        if (this.renderer) {
          this.renderer.updateValidMoveIndicators(null);
          this.renderer.updateTokenSelectionGlow(null);
        }
        return;
      }
    }
  }

  handleKeyDown(data) {
    const key = data.key;
    switch (key) {
      case "end_turn":
        this.networkManager.endTurn();
        this.selectedTokenId = null;
        this.validMoves = new Set();
        this.renderer.updateValidMoveIndicators(null);
        this.renderer.updateTokenSelectionGlow(null);
        break;
      case "cancel":
        this.cancelAction();
        break;
      case "deploy":
        this.toggleDeploymentMenu();
        break;
      case "camera_toggle":
        this.renderer.camera = this.cameraController.toggleCameraMode();
        // Re-attach pipeline to the new active camera
        if (this.renderer.pipeline) {
          this.renderer.pipeline.addCamera(this.renderer.camera);
        }
        if (this.cameraController.cameraMode === "firstperson") {
          const aliveTokens = this.getAliveTokens();
          if (aliveTokens.length > 0) {
            this.controlledTokenId = aliveTokens[0].id;
            const token = this.gameState?.tokens?.[this.controlledTokenId];
            if (token) {
              this.cameraController.updateFirstPersonCamera(token);
            }
          }
        }
        break;
      case "cycle_token":
        const newTokenId = this.cameraController.cycleControlledToken(
          this.getAliveTokens(),
        );
        if (newTokenId) {
          this.controlledTokenId = newTokenId;
          const token = this.gameState?.tokens?.[this.controlledTokenId];
          if (token) {
            this.cameraController.updateFirstPersonCamera(token);
          }
        }
        break;
      case "rotate_left":
        this.cameraController.rotateCameraLeft();
        break;
      case "rotate_right":
        this.cameraController.rotateCameraRight();
        break;
      case "look_up":
        this.cameraController.lookUp();
        break;
      case "look_down":
        this.cameraController.lookDown();
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
        if (this.renderer) {
          this.renderer.toggleMusic();
        }
        break;
      case "camera_forward":
        this.cameraController.moveCameraForward();
        break;
      case "camera_backward":
        this.cameraController.moveCameraBackward();
        break;
      case "camera_left":
        this.cameraController.moveCameraLeft();
        break;
      case "camera_right":
        this.cameraController.moveCameraRight();
        break;
      case "zoom_out":
        this.cameraController.adjustFOV(15);
        break;
      case "zoom_in":
        this.cameraController.adjustFOV(-15);
        break;
      case "quit":
        this.quitGame();
        break;
      case "switch_player":
        if (data.playerIndex !== undefined && this.gameState) {
          const playerIds = Object.keys(this.gameState.players);
          if (data.playerIndex < playerIds.length) {
            this.localPlayerId = playerIds[data.playerIndex];
            if (this.renderer) {
              this.renderer.localPlayerId = this.localPlayerId;
            }
            this.selectedTokenId = null;
            this.validMoves = new Set();
            if (this.renderer) {
              this.renderer.updateValidMoveIndicators(null);
              this.renderer.updateTokenSelectionGlow(null);
            }
          }
        }
        break;
    }
  }

  getTokenAt(gridX, gridY) {
    if (!this.gameState) return null;

    for (const token of Object.values(this.gameState.tokens)) {
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

  calculateDestinationFromCameraRotation(currentPos, direction) {
    // Get camera rotation in degrees
    // 0° = facing north (-Z), 90° = facing west (-X), 180° = facing south (+Z), 270° = facing east (+X)
    const rotation = this.cameraController.tokenRotation;

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

  moveControlledToken(direction) {
    // Only works in first-person mode
    if (this.cameraController.cameraMode !== 'firstperson') {
      return;
    }

    // Must have a controlled token
    if (this.controlledTokenId === null) {
      this.uiManager.showActionError("No token selected!");
      return;
    }

    // Must be our turn
    if (!this.gameState || this.gameState.current_turn_player_id !== this.localPlayerId) {
      this.uiManager.showActionError("Not your turn!");
      return;
    }

    // Must be in movement phase
    if (this.turnPhase !== TurnPhase.MOVEMENT) {
      this.uiManager.showActionError("Can only move during movement phase!");
      return;
    }

    const token = this.gameState.tokens[this.controlledTokenId];
    if (!token || !token.is_alive || !token.is_deployed) {
      this.uiManager.showActionError("Invalid token!");
      return;
    }

    // Calculate destination based on camera orientation
    const destination = this.calculateDestinationFromCameraRotation(token.position, direction);
    const [destX, destY] = destination;

    // Check if destination is on the board
    if (destX < 0 || destX >= BOARD_WIDTH || destY < 0 || destY >= BOARD_HEIGHT) {
      this.uiManager.showActionError("Cannot move off the board!");
      return;
    }

    // Check if it's a valid move by calculating valid moves for this token
    this.updateValidMoves(token);
    const moveKey = `${destX},${destY}`;

    if (this.validMoves.has(moveKey)) {
      this.networkManager.moveToken(this.controlledTokenId, destination);
      this.renderer.playSound("move");
      this.validMoves = new Set();
      this.renderer.updateValidMoveIndicators(null);
    } else {
      this.uiManager.showActionError("Invalid move!");
    }
  }

  toggleDeploymentMenu() {
    if (!this.gameState) return;
    if (this.gameState.current_turn_player_id !== this.localPlayerId) {
      this.uiManager.showActionError("Not your turn!");
      return;
    }
    if (this.turnPhase !== TurnPhase.MOVEMENT) {
      this.uiManager.showActionError("Can only deploy during movement phase!");
      return;
    }

    this.uiManager.toggleDeploymentMenu(!this.uiManager.isDeploymentMenuOpen());
  }

  cancelAction() {
    if (this.selectedTokenId) {
      this.stateManager.clearSelection();
      if (this.renderer) {
        this.renderer.updateValidMoveIndicators(null);
        this.renderer.updateTokenSelectionGlow(null);
      }
    } else if (this.uiManager.getSelectedDeployHealth() !== null) {
      this.uiManager.clearSelection();
    } else if (this.uiManager.isDeploymentMenuOpen()) {
      this.uiManager.toggleDeploymentMenu(false);
    }
  }

  toggleReady() {
    const isReady = this.networkManager.toggleReady();
    this.uiManager.updateReadyButton(isReady);
  }

  startGame() {
    try {
      this.networkManager.startGame();
    } catch (error) {
      alert(error.message);
    }
  }

  leaveLobby() {
    this.networkManager.leaveLobby();
  }

  quitGame() {
    // Clean up all resources
    if (this.networkManager) {
      this.networkManager.disconnect();
    }
    if (this.inputHandler) {
      this.inputHandler.dispose();
    }
    if (this.renderer) {
      this.renderer.dispose();
    }
    alert("Game quit. You can close this window.");
  }
}

// ==========================================================================
// Main entry point
// ==========================================================================

// Initialize game when page loads
window.addEventListener("DOMContentLoaded", () => {
  window.gameClient = new GameClient();
});
