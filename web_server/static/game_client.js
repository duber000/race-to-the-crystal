// ==========================================================================
// Race to the Crystal - Main Game Client (Facade)
// ==========================================================================

// Import modules
import { StateManager } from './state_manager.js';
import { UIManager } from './ui_manager.js';
import { DeviceCapabilities } from './game_client.device.js';
import { GAME_PHASE, TurnPhase, STATE } from './game_client.constants.js';
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

    // Module instances (initialized later by UIController.initGameModules)
    this.cameraController = null;
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

  handleKeyDown(data) {
    if (this.inputController) {
      this.inputController.handleKeyDown(data);
    }
  }

  handleStateChanged(state) {
    if (this.connectionManager.getConnectionState() !== STATE.IN_GAME) {
      return;
    }

    this.turnPhase = state.turn_phase || TurnPhase.MOVEMENT;

    if (this.renderer) {
      this.renderer.localPlayerId = this.stateManager.localPlayerId;
      this.renderer.updateGameState(state);
      this.renderer.updateValidMoveIndicators(this.stateManager.validMoves);
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

    // Keep first-person highlights in sync with state updates
    this.inputController?.refreshFPIndicators();
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

  // Game actions are handled by the controllers in game_client.modules.js:
  // InputController (input → game actions, first-person movement),
  // UIController (module init, screens), ConnectionManager (network, quit).

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