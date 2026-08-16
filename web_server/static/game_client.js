// ==========================================================================
// Race to the Crystal - Main Game Client (Facade)
// ==========================================================================

// Import modules
import { StateManager } from './state_manager.js';
import { UIManager } from './ui_manager.js';
import { CameraController } from './camera_controller.js';
import { DeviceCapabilities } from './game_client.device.js';
import { BOARD_CONFIG, GAME_PHASE, UI_STATE, INPUT_CONFIG, TurnPhase, STATE, CELL_SIZE, BOARD_WIDTH, BOARD_HEIGHT, WALL_HEIGHT } from './game_client.constants.js';
import { Renderer3D } from './game_client.renderer.js';
import { ConnectionManager, InputController, UIController } from './game_client.modules.js';

/**
 * Race to the Crystal - Main Game Client (Facade)
 *
 * This is the main entry point that coordinates all modules:
 * - ConnectionManager: Network communication and lobby management
 * - UIManager: All UI screens and HUD
 * - CameraController: Overview and first-person camera modes
 * - InputController: Mouse and keyboard input (refactored from InputHandler)
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

    // Initialize managers
    this.stateManager = new StateManager();
    this.uiManager = new UIManager();
    this.connectionManager = new ConnectionManager(this);
    this.uiController = new UIController(this);

    // Module instances (initialized later)
    this.cameraController = null;
    // InputController will be initialized later in initGameModules with proper parameters
    this.inputController = null;
    this.inputHandler = null; // For backward compatibility
    this.renderer = null;

    // Game state
    this.gameInitialized = false;
    this.turnPhase = GAME_PHASE.MOVEMENT;
    this.musicPlaying = true;

    // Direct access for convenience (optional)
    Object.defineProperty(this, 'gameState', {
      get: () => this.stateManager.gameState,
      set: (v) => { this.stateManager.gameState = v; }
    });
    Object.defineProperty(this, 'localPlayerId', {
      get: () => this.stateManager.localPlayerId,
      set: (v) => { this.stateManager.localPlayerId = v; }
    });
    Object.defineProperty(this, 'selectedTokenId', {
      get: () => this.stateManager.selectedTokenId,
      set: (v) => { this.stateManager.selectedTokenId = v; }
    });
    Object.defineProperty(this, 'controlledTokenId', {
      get: () => this.stateManager.controlledTokenId,
      set: (v) => { this.stateManager.controlledTokenId = v; }
    });
    Object.defineProperty(this, 'validMoves', {
      get: () => this.stateManager.validMoves,
      set: (v) => { this.stateManager.validMoves = v; }
    });
    Object.defineProperty(this, 'networkManager', {
      get: () => (this.connectionManager ? this.connectionManager.networkManager : null)
    });

    // Setup state change callback
    this.stateManager.setChangeCallback((state) => this.handleStateChanged(state));

    this.init();
  }

  init() {
    // Initialize managers
    this.connectionManager.init();
    this.uiController.init();
    console.log("Game client initialized");
  }

  handleStateChanged(state) {
    if (this.connectionManager.getConnectionState() !== STATE.IN_GAME) {
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
        this.uiController.setupLobbyBrowserHandlers();
        break;
      case STATE.IN_LOBBY:
        this.uiManager.showScreen("lobby");
        break;
      case STATE.GAME_STARTING:
        this.uiManager.showScreen("game_starting");
        break;
      case STATE.IN_GAME:
        this.uiManager.showScreen("in_game");
        this.uiController.initGameModules();
        break;
      default:
        console.warn(`[GameClient] Unknown state: ${state}`);
    }
  }

  // handleClick is now handled by InputController

  handleKeyDown(data) {
    const key = data.key;
    switch (key) {
      case "end_turn":
        this.connectionManager.networkManager.endTurn();
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

  // These methods are now handled by the respective controllers
  // InputController handles: isOurToken, getAliveTokens, calculateValidAttackTargets, 
  // calculateValidMoves, calculateDestinationFromCameraRotation, moveControlledToken
  // UIController handles: toggleDeploymentMenu, cancelAction, toggleReady, startGame, leaveLobby
  // ConnectionManager handles: quitGame (network cleanup)

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

    // Initialize input controller with device capabilities
    this.inputController = new InputController(
      this.canvas,
      this.cameraController,
      () => this.gameState,
      () => this.connectionManager.getConnectionState(),
      this.renderer.engine,
      this.deviceCapabilities,
    );
    // Replace the old inputHandler reference for compatibility
    this.inputHandler = this.inputController;

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
    if (this.inputController) {
      this.inputController.setupInputHandlers();
    }
  }

  quitGame() {
    // Clean up all resources
    if (this.connectionManager.networkManager) {
      this.connectionManager.networkManager.disconnect();
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