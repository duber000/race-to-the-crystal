/**
 * WebSocketClient - Network communication, lobby, and message handling
 *
 * Responsibilities:
 * - WebSocket connection management
 * - Lobby browser (create, join, list games)
 * - Waiting room (ready, start, leave)
 * - Message routing and handling
 *
 * Usage:
 *   const wsClient = new WebSocketClient();
 *   wsClient.connect(host, port, playerName);
 *   wsClient.on('message', (data) => { ... });
 *   wsClient.on('state_update', (gameState) => { ... });
 */

class WebSocketClient {
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

    switch (data.type) {
      case "CONNECT_ACK":
        this.playerId = data.player_id;
        console.log(`✓ Connected as ${this.playerName} (ID: ${this.playerId})`);
        this.connectionState = STATE.CONNECTED;
        this.emit("connected", { playerId: this.playerId });
        break;

      case "GAME_LIST":
        this.availableGames = data.games || [];
        console.log(`Received ${this.availableGames.length} games`);
        this.emit("game_list", { games: this.availableGames });
        break;

      case "CREATE_GAME":
        console.log("Game created:", data.game_id);
        this.currentGameId = data.game_id;
        this.currentLobby = {
          game_id: data.game_id,
          game_name: data.game_name,
          host_player_id: data.host_player_id,
          players: data.players || [],
          max_players: data.max_players,
          status: data.status,
        };
        this.isHost = true;

        // Sync local ready state with server
        const myPlayerInCreate = this.currentLobby.players.find(
          (p) => p.player_id === this.playerId,
        );
        if (myPlayerInCreate) {
          this.isReady = myPlayerInCreate.is_ready;
        }

        this.connectionState = STATE.IN_LOBBY;
        this.emit("lobby_joined", { lobby: this.currentLobby, isHost: true });
        break;

      case "JOIN_GAME":
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

        // Sync local ready state with server
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
        break;

      case "PLAYER_JOINED":
        console.log(`Player joined: ${data.player_name}`);
        if (data.lobby) {
          this.currentLobby.players = data.lobby.players;
          this.emit("lobby_updated", { lobby: this.currentLobby });
        }
        break;

      case "PLAYER_LEFT":
        console.log(`Player left: ${data.player_id}`);
        if (this.currentLobby) {
          this.currentLobby.players = this.currentLobby.players.filter(
            (p) => p.player_id !== data.player_id,
          );
          this.emit("lobby_updated", { lobby: this.currentLobby });

          if (data.player_id === this.currentLobby.host_player_id) {
            this.emit("host_left");
          }
        }
        break;

      case "READY":
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

          this.emit("lobby_updated", { lobby: this.currentLobby });
        }
        break;

      case "START_GAME":
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
        break;

      case "FULL_STATE":
        // In SSE-primary mode, only process FULL_STATE via WebSocket if SSE is not active
        if (this.usingSSEForState) {
          console.log("⚠ Ignoring FULL_STATE from WebSocket (using SSE)");
        } else {
          this.emit("full_state", data);
        }
        break;

      case "ERROR":
        console.error("Server error:", data.error || data.message);
        this.emit("error", { message: data.error || data.message });
        break;

      case "INVALID_ACTION":
        const message = data.reason || data.message || data.error || "Invalid action";
        console.warn("Invalid action:", message);
        this.emit("invalid_action", { message });
        break;

      default:
        console.warn("Unknown message type:", data.type);
        this.emit("unknown_message", data);
    }
  }

  async initMercure() {
    try {
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
        console.log("⚠ Mercure disabled - using WebSocket for all updates");
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
    const fallbackToWebSocket = () => {
      console.warn("⚠ Using WebSocket for state updates (fallback)");
      this.usingSSEForState = false;
    };

    this.mercureClient.subscribe(
      (update) => {
        console.log("✓ Mercure update received");

        // Mark that we're successfully using SSE for state updates
        if (!this.usingSSEForState) {
          this.usingSSEForState = true;
          console.log("✓ Using SSE for state updates");
        }

        // SSE publishes the game state directly, not wrapped in a 'state' property
        this.emit("full_state", {
          game_state: update,
        });
      },
      fallbackToWebSocket
    );

    // Optimistically set usingSSEForState to true if in SSE-primary mode
    // Will be set back to false if SSE fails
    if (this.ssePrimaryMode) {
      this.usingSSEForState = true;
    }
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
      max_players: maxPlayers,
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

    this.currentGameId = null;
    this.currentLobby = null;
    this.isHost = false;
    this.isReady = false;
    this.connectionState = STATE.CONNECTED;
    this.emit("lobby_left");
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
