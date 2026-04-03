/**
 * NetworkManager - Network communication, lobby, and message handling
 * 
 * Refactored version with extracted message handlers to reduce complexity
 * 
 * Consolidated module handling both WebSocket and SSE (Mercure) communications.
 * Features:
 * - Robust state synchronization with version tracking
 * - Parallel state update queue (preventing race conditions)
 * - Automatic SSE-to-WebSocket fallback
 * - Lobby and game action management
 */

import { STATE } from './game_client.constants.js';
import { mergeDelta } from './state_manager.js';

class NetworkManager {
  constructor() {
    this.websocket = null;
    this.playerName = null;
    this.playerId = null;
    this.currentGameId = null;
    this.currentLobby = null;
    this.isHost = false;
    this.isReady = false;
    this.availableGames = [];
    this.connectionState = STATE.DISCONNECTED;

    this.eventHandlers = new Map();

    // SSE-primary mode support
    this.useMercure = false;
    this.mercureClient = null;
    this.ssePrimaryMode = false; // Set from server config
    this.usingSSEForState = false; // True if actively using SSE for state updates
    
    // State update tracking for race condition prevention
    this.lastStateVersion = null; // Track last processed state version
    this.stateUpdateLock = false; // Prevent concurrent state processing
    this.stateUpdateQueue = [];
  }

  /**
   * Handle FULL_STATE message with idempotent processing and queue management.
   * @param {Object} data - Full state data from server
   * @private
   */
  _handleFullState(data) {
    // In SSE-primary mode, only process FULL_STATE via WebSocket if SSE is not active
    if (this.usingSSEForState && this.mercureClient && this.mercureClient.isConnected()) {
      console.log("⚠ Ignoring FULL_STATE from WebSocket (using SSE)");
      return;
    }
    
    console.log("✓ Processing FULL_STATE from WebSocket");
    
    // Check for duplicate state (idempotent processing)
    const stateVersion = data.version || data.timestamp || null;
    if (stateVersion && this.lastStateVersion && stateVersion === this.lastStateVersion) {
      console.log("⚠ Duplicate FULL_STATE detected, skipping (idempotent)");
      return;
    }
    
    // Set lock to prevent concurrent processing
    if (this.stateUpdateLock) {
      console.log("⚠ State update already processing, queuing");
      this.stateUpdateQueue.push({ source: "websocket", data });
      return;
    }
    
    this.stateUpdateLock = true;
    this.emit("full_state", data);
    
    // Update last processed version
    if (stateVersion) {
      this.lastStateVersion = stateVersion;
    }
    
    // If we were in GAME_STARTING state, transition to IN_GAME
    if (this.connectionState === STATE.GAME_STARTING) {
      this.connectionState = STATE.IN_GAME;
      console.log("✓ Transitioned to IN_GAME state - game actions now enabled");
    }
    
    this.stateUpdateLock = false;
    
    // Process queued updates
    this._processStateQueue();
  }

  /**
   * Handle STATE_UPDATE message by merging delta into local state.
   * @param {Object} data - Delta update data from server
   * @private
   */
  _handleStateUpdate(data) {
    console.log("✓ Processing STATE_UPDATE");
    this.emit("state_update", data);
  }

  /**
   * Recursively merge a delta into a base object.
   * Delegates to the shared mergeDelta utility from state_manager.js.
   * @param {Object} base - The object to update
   * @param {Object} delta - The changes to apply
   * @returns {Object} The updated object
   * @private
   */
  _mergeDelta(base, delta) {
    return mergeDelta(base || {}, delta || {});
  }

  /**
   * Process queued state updates sequentially.
   * @private
   */
  _processStateQueue() {
    if (this.stateUpdateQueue.length === 0) return;
    
    const next = this.stateUpdateQueue.shift();
    console.log(`Processing queued state update from ${next.source}`);
    
    if (next.source === "websocket") {
      this._handleFullState(next.data);
    } else if (next.source === "sse") {
      const update = next.data.game_state;
      this.emit("full_state", next.data);
      if (this.connectionState === STATE.GAME_STARTING) {
        this.connectionState = STATE.IN_GAME;
      }
    }
    
    // Recursively process remaining queue
    if (this.stateUpdateQueue.length > 0) {
      this._processStateQueue();
    }
  }

  on(event, handler) {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, []);
    }
    this.eventHandlers.get(event).push(handler);
  }

  off(event, handler) {
    if (this.eventHandlers.has(event)) {
      const handlers = this.eventHandlers.get(event);
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    if (this.eventHandlers.has(event)) {
      this.eventHandlers.get(event).forEach((handler) => handler(data));
    }
  }

  async connect(host, port, playerName) {
    this.playerName = playerName;
    this.emit("connecting");

    // Initialize Mercure support
    await this.initMercure();

    // Use wss:// for HTTPS pages, ws:// for HTTP
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${host}:${port}/ws`;
    console.log(`Connecting to ${wsUrl}...`);

    this.websocket = new WebSocket(wsUrl);

    this.websocket.onopen = () => {
      console.log("✓ WebSocket connected");
      this.connectionState = STATE.CONNECTING;
      this.send({
        type: "CONNECT",
        player_name: this.playerName,
        client_type: "WEB_BROWSER",
      });
    };

    this.websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (error) {
        console.error("Error parsing message:", error);
      }
    };

    this.websocket.onerror = (error) => {
      console.error("WebSocket error:", error);
      this.emit("error", { message: "Connection failed" });
      this.connectionState = STATE.DISCONNECTED;
    };

    this.websocket.onclose = () => {
      console.log("WebSocket disconnected");
      this.handleDisconnect();
    };
  }

  handleDisconnect() {
    this.unsubscribeMercure();
    this.playerId = null;
    this.currentGameId = null;
    this.currentLobby = null;
    this.isHost = false;
    this.isReady = false;
    this.availableGames = [];
    this.connectionState = STATE.DISCONNECTED;
    // Reset state sync fields so a fresh connection starts clean
    this.lastStateVersion = null;
    this.stateUpdateLock = false;
    this.stateUpdateQueue = [];
    this.usingSSEForState = false;
    this.emit("disconnect");
  }

  disconnect() {
    if (this.websocket) {
      this.websocket.close();
    }
  }

  send(message) {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      this.websocket.send(JSON.stringify(message));
      console.log("Sent:", message.type);
    } else {
      const state = this.websocket ? this.websocket.readyState : "null";
      const stateNames = ["CONNECTING", "OPEN", "CLOSING", "CLOSED"];
      const stateName = this.websocket
        ? stateNames[this.websocket.readyState]
        : "null";
      console.error(
        `WebSocket not connected! Current state: ${state} (${stateName})`,
      );
      console.error(`Connection state: ${this.connectionState}`);
    }
  }

  handleMessage(data) {
    console.log("Received message:", data.type);
    
    // Extract message handling to separate methods
    switch (data.type) {
      case "connected":
      case "CONNECT_ACK":
        this.handleConnected(data);
        break;
      
      case "game_list":
      case "GAME_LIST":
        this.handleGameList(data);
        break;
      
      case "CREATE_GAME":
      case "lobby_joined":
        this.handleLobbyJoined(data);
        break;
      
      case "JOIN_GAME":
        this.handleJoinGame(data);
        break;
      
      case "PLAYER_JOINED":
      case "PLAYER_LEFT":
      case "PLAYER_DISCONNECTED":
      case "PLAYER_RECONNECTED":
      case "lobby_updated":
        this.handleLobbyUpdated(data);
        break;
      
      case "READY":
        this.handleReadyStatus(data);
        break;
      
      case "START_GAME":
      case "game_starting":
        this.handleGameStarting(data);
        break;
      
      case "FULL_STATE":
      case "full_state":
        this._handleFullState(data);
        break;
      
      case "STATE_UPDATE":
      case "state_update":
        this._handleStateUpdate(data.data || data);
        break;
      
      case "ERROR":
      case "error":
        this.handleServerError(data);
        break;
      
      case "INVALID_ACTION":
      case "invalid_action":
        this.handleInvalidAction(data);
        break;
      
      case "LEAVE_GAME":
      case "lobby_left":
        this.handleLeaveGame(data);
        break;
      
      default:
        this.handleUnknownMessage(data);
    }
  }

  // Extracted message handler methods
  handleConnected(data) {
    this.playerId = data.player_id || data.playerId;
    console.log(`✓ Connected as ${this.playerName} (ID: ${this.playerId})`);
    this.connectionState = STATE.CONNECTED;
    this.emit("connected", { playerId: this.playerId });
  }

  handleGameList(data) {
    this.availableGames = data.games || [];
    console.log(`Received ${this.availableGames.length} games`);
    this.emit("game_list", { games: this.availableGames });
  }

  handleLobbyJoined(data) {
    console.log("Game created/joined:", data.game_id);
    this.currentGameId = data.game_id;
    const rawLobby = data.lobby || data;
    this.currentLobby = {
      game_id: rawLobby.game_id,
      game_name: rawLobby.game_name,
      host_player_id: rawLobby.host_player_id || rawLobby.host_id,
      players: rawLobby.players || [],
      max_players: rawLobby.max_players || 4,
      status: rawLobby.status,
    };
    this.isHost = this.playerId === this.currentLobby.host_player_id;

    // Sync local ready state with server
    const myPlayerInLobby = this.currentLobby.players.find(
      (p) => p.player_id === this.playerId,
    );
    if (myPlayerInLobby) {
      this.isReady = myPlayerInLobby.is_ready;
    }

    this.connectionState = STATE.IN_LOBBY;
    this.emit("lobby_joined", { lobby: this.currentLobby, isHost: this.isHost });
  }

  handleJoinGame(data) {
    console.log("Joined game:", data.game_id);
    this.currentGameId = data.game_id;
    this.currentLobby = {
      game_id: data.game_id,
      game_name: data.game_name,
      host_player_id: data.host_player_id,
      players: data.players || [],
      max_players: data.max_players,
      status: data.status,
    };
    this.isHost = this.playerId === data.host_player_id;

    const myPlayerInJoin = this.currentLobby.players.find(
      (p) => p.player_id === this.playerId,
    );
    if (myPlayerInJoin) {
      this.isReady = myPlayerInJoin.is_ready;
    }

    this.connectionState = STATE.IN_LOBBY;
    this.emit("lobby_joined", {
      lobby: this.currentLobby,
      isHost: this.isHost,
    });
  }

  handleLobbyUpdated(data) {
    console.log(`Lobby update: ${data.type}`);
    if (data.lobby) {
      this.currentLobby = {
        game_id: data.lobby.game_id,
        game_name: data.lobby.game_name,
        host_player_id: data.lobby.host_player_id || data.lobby.host_id,
        players: data.lobby.players || [],
        max_players: data.lobby.max_players || 4,
        status: data.lobby.status,
      };
      this.isHost = this.playerId === this.currentLobby.host_player_id;
      this.emit("lobby_updated", { lobby: this.currentLobby, isHost: this.isHost });

      if (data.type === "PLAYER_LEFT" && data.player_id === this.currentLobby.host_player_id) {
        this.emit("host_left");
      }
    }
  }

  handleReadyStatus(data) {
    console.log("Ready status updated:", data);
    if (data.lobby && data.lobby.players) {
      this.currentLobby.players = data.lobby.players;

      // Sync local ready state with server
      const myPlayer = data.lobby.players.find(
        (p) => p.player_id === this.playerId,
      );
      if (myPlayer) {
        this.isReady = myPlayer.is_ready;
      }

      this.emit("lobby_updated", { lobby: this.currentLobby, isHost: this.isHost });
    }
  }

  handleGameStarting(data) {
    console.log("Game starting!");
    this.subscribeMercure();
    // Only update state if not already in game (FULL_STATE may have already arrived)
    if (this.connectionState !== STATE.IN_GAME) {
      this.connectionState = STATE.GAME_STARTING;
      this.emit("game_starting");
      console.log("State set to GAME_STARTING");
    } else {
      console.log("Already IN_GAME, ignoring START_GAME state change");
    }
  }

  handleServerError(data) {
    console.error("Server error:", data.error || data.message);
    this.emit("error", { message: data.error || data.message });
  }

  handleInvalidAction(data) {
    const message = data.reason || data.message || data.error || "Invalid action";
    console.warn("Invalid action:", message);
    this.emit("invalid_action", { message });
  }

  handleLeaveGame(data) {
    this.currentLobby = null;
    this.currentGameId = null;
    this.connectionState = STATE.CONNECTED;
    this.emit("lobby_left");
  }

  handleUnknownMessage(data) {
    console.warn("Unknown message type:", data.type);
    this.emit("unknown_message", data);
  }

  async initMercure() {
    try {
      if (typeof MercureClient === 'undefined') {
        console.log("⚠ MercureClient not found - SSE support disabled");
        return false;
      }

      this.mercureClient = new MercureClient();
      const mercureReady = await this.mercureClient.init();

      if (mercureReady) {
        this.useMercure = true;

        // Check if SSE-primary mode is enabled from server config
        if (this.mercureClient.config && this.mercureClient.config.sse_primary_mode) {
          this.ssePrimaryMode = true;
          console.log("✓ SSE-primary mode enabled - state updates via SSE only");
        } else {
          this.ssePrimaryMode = false;
          console.log("✓ Dual-channel mode - state updates via both SSE and WebSocket");
        }

        console.log(
          "✓ Mercure client initialized - will use SSE for state updates",
        );
      } else {
        console.log("⚠ Mercure initialization failed - using WebSocket for all updates");
        this.useMercure = false;
        this.ssePrimaryMode = false;
      }
      return mercureReady;
    } catch (error) {
      console.error("Failed to initialize Mercure:", error);
      this.useMercure = false;
      this.ssePrimaryMode = false;
      return false;
    }
  }

  subscribeMercure() {
    if (!this.useMercure || !this.mercureClient || !this.currentGameId) {
      return;
    }

    console.log(`Subscribing to Mercure for game ${this.currentGameId}...`);

    // Update the topic to include the game_id
    this.mercureClient.setTopic(`${this.mercureClient.config.mercure_topic}/${this.currentGameId}`);

    // Fallback function: switch back to WebSocket if SSE fails
    const fallbackToWebSocket = async () => {
      console.warn("⚠ SSE failed - requesting WebSocket fallback");
      
      // Immediately set usingSSEForState to false to ensure we accept FULL_STATE messages
      this.usingSSEForState = false;

      // If we were waiting for the game to start, ensure we can receive FULL_STATE via WebSocket
      if (this.connectionState === STATE.GAME_STARTING) {
        console.log("⚠ Game was starting but SSE failed - will accept FULL_STATE via WebSocket");
      }

      // Request the server to send FULL_STATE via WebSocket
      this.send({
        type: "SSE_FALLBACK_REQUEST",
        game_id: this.currentGameId,
        player_id: this.playerId,
      });
    };

    this.mercureClient.subscribe(
      (update) => {
        console.log("✓ Mercure update received");

        // Mark that we're successfully using SSE for state updates
        if (!this.usingSSEForState) {
          this.usingSSEForState = true;
          console.log("✓ Using SSE for state updates");
        }

        // Check for duplicate state (idempotent processing)
        const stateVersion = update.version || update.timestamp || null;
        if (stateVersion && this.lastStateVersion && stateVersion === this.lastStateVersion) {
          console.log("⚠ Duplicate SSE state detected, skipping (idempotent)");
          return;
        }
        
        // Set lock to prevent concurrent processing
        if (this.stateUpdateLock) {
          console.log("⚠ State update already processing, queuing SSE update");
          this.stateUpdateQueue.push({ source: "sse", data: { game_state: update } });
          return;
        }
        
        this.stateUpdateLock = true;

        // Transition to IN_GAME state if needed (critical for enabling game actions)
        if (this.connectionState === STATE.GAME_STARTING) {
          this.connectionState = STATE.IN_GAME;
          console.log("✓ Transitioned to IN_GAME state via SSE - game actions now enabled");
        }

        // Dispatch based on message type
        const type = update.type;
        if (type === "STATE_UPDATE" || type === "state_update") {
          this._handleStateUpdate(update);
        } else if (type === "FULL_STATE" || type === "full_state") {
          this.emit("full_state", {
            game_state: update,
          });
        } else if (type) {
          // It's a fine-grained event (TOKEN_MOVED, COMBAT_RESULT, etc.)
          console.log(`✓ SSE Event received: ${type}`);
          this.emit(type.toLowerCase(), update);
        } else {
          // Default to full state for legacy/raw updates
          this.emit("full_state", {
            game_state: update,
          });
        }
        
        // Update last processed version
        if (stateVersion) {
          this.lastStateVersion = stateVersion;
        }
        
        this.stateUpdateLock = false;
        
        // Process queued updates
        this._processStateQueue();
      },
      fallbackToWebSocket
    );
  }

  unsubscribeMercure() {
    if (this.mercureClient && this.mercureClient.isConnected()) {
      this.mercureClient.disconnect();
    }
  }

  // ==========================================================================
  // Lobby Browser Methods
  // ==========================================================================

  requestGameList() {
    this.send({
      type: "LIST_GAMES",
      player_id: this.playerId,
    });
  }

  createGame(gameName, maxPlayers) {
    console.log(`Creating game: ${gameName}`);
    this.send({
      type: "CREATE_GAME",
      player_id: this.playerId,
      game_name: gameName,
      max_players: parseInt(maxPlayers) || 4,
    });
  }

  joinGame(gameId) {
    console.log(`Joining game: ${gameId}`);
    this.send({
      type: "JOIN_GAME",
      player_id: this.playerId,
      game_id: gameId,
    });
  }

  leaveLobby() {
    console.log("Leaving lobby...");
    this.send({
      type: "LEAVE_GAME",
      player_id: this.playerId,
      game_id: this.currentGameId,
    });
    // State transition and lobby_left event are driven by the server's LEAVE_GAME response
  }

  toggleReady() {
    this.isReady = !this.isReady;
    console.log(`Setting ready status to: ${this.isReady}`);
    this.send({
      type: "READY",
      player_id: this.playerId,
      game_id: this.currentGameId,
      ready: this.isReady,
    });
    return this.isReady;
  }

  startGame() {
    if (!this.isHost) {
      throw new Error("Only the host can start the game");
    }

    if (!this.currentLobby) return;

    const allReady = this.currentLobby.players.every((p) => p.is_ready);
    if (!allReady) {
      const notReadyPlayers = this.currentLobby.players
        .filter((p) => !p.is_ready)
        .map((p) => p.player_name)
        .join(", ");
      throw new Error(`Cannot start game! Waiting for: ${notReadyPlayers}`);
    }

    console.log("Starting game...");
    this.send({
      type: "START_GAME",
      player_id: this.playerId,
      game_id: this.currentGameId,
    });
  }

  // ==========================================================================
  // Game Actions
  // ==========================================================================

  sendAction(action) {
    if (this.connectionState !== STATE.IN_GAME) {
      console.warn("Not in game, ignoring action");
      return;
    }

    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      action.player_id = this.playerId;
      console.log("Sending action:", action.type);
      this.websocket.send(JSON.stringify(action));
    } else {
      console.error("WebSocket not connected");
    }
  }

  endTurn() {
    this.sendAction({ type: "END_TURN" });
  }

  deployToken(healthValue, position) {
    this.sendAction({
      type: "DEPLOY",
      health_value: healthValue,
      position: position,
    });
  }

  moveToken(tokenId, destination) {
    this.sendAction({
      type: "MOVE",
      token_id: tokenId,
      destination: destination,
    });
  }

  attackToken(attackerId, targetId) {
    this.sendAction({
      type: "ATTACK",
      attacker_id: attackerId,
      defender_id: targetId,
    });
  }

  // ==========================================================================
  // Getters
  // ==========================================================================

  getConnectionState() {
    return this.connectionState;
  }

  getCurrentLobby() {
    return this.currentLobby;
  }

  getAvailableGames() {
    return this.availableGames;
  }

  isPlayerHost() {
    return this.isHost;
  }

  isPlayerReady() {
    return this.isReady;
  }
}

export { NetworkManager };