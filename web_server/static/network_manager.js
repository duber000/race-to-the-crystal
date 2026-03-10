// ==========================================================================
// Networking Module - Handles all WebSocket and network communication
// ==========================================================================

import { STATE } from './game_client.constants.js';

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
        this.ssePrimaryMode = false;
        this.usingSSEForState = false;
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
            console.error("WebSocket disconnected");
            this.emit("disconnect");
            this.connectionState = STATE.DISCONNECTED;
        };
    }

    async initMercure() {
        // Initialize Mercure client for SSE support
        if (typeof MercureClient !== 'undefined') {
            this.mercureClient = new MercureClient();
            this.useMercure = true;
            console.log("Mercure client initialized");
        }
    }

    send(message) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify(message));
        } else {
            console.error("Cannot send message: WebSocket not connected");
        }
    }

    handleMessage(data) {
        switch (data.type) {
            case "connected":
            case "CONNECT_ACK":
                this.playerId = data.player_id || data.playerId;
                this.connectionState = STATE.CONNECTED;
                this.emit("connected", data);
                break;
            case "error":
                this.emit("error", data);
                break;
            case "disconnect":
                this.emit("disconnect");
                break;
            case "game_list":
            case "GAME_LIST":
                this.availableGames = data.games;
                this.emit("game_list", data);
                break;
            case "lobby_joined":
            case "CREATE_GAME":
            case "JOIN_GAME":
                this.currentLobby = data.lobby || data;
                this.isHost = data.host_id === this.playerId || (data.lobby && data.lobby.host_id === this.playerId);
                this.emit("lobby_joined", { lobby: this.currentLobby, isHost: this.isHost });
                break;
            case "lobby_updated":
            case "PLAYER_JOINED":
            case "PLAYER_LEFT":
            case "PLAYER_DISCONNECTED":
            case "PLAYER_RECONNECTED":
                this.currentLobby = data.lobby || data;
                this.isHost = (this.currentLobby.host_id === this.playerId);
                this.emit("lobby_updated", { lobby: this.currentLobby, isHost: this.isHost });
                break;
            case "host_left":
                this.emit("host_left");
                break;
            case "lobby_left":
            case "LEAVE_GAME":
                this.currentLobby = null;
                this.emit("lobby_left");
                break;
            case "game_starting":
            case "START_GAME":
                this.emit("game_starting");
                break;
            case "full_state":
            case "FULL_STATE":
                this.connectionState = STATE.IN_GAME;
                this.emit("full_state", data);
                break;
            case "invalid_action":
            case "INVALID_ACTION":
                this.emit("invalid_action", data);
                break;
            case "ERROR":
                this.emit("error", data);
                break;
            default:
                console.warn(`Unknown message type: ${data.type}`);
        }
    }

    toggleReady() {
        this.isReady = !this.isReady;
        this.send({
            type: "READY",
            ready: this.isReady
        });
        return this.isReady;
    }

    requestGameList() {
        this.send({ type: "LIST_GAMES" });
    }

    createGame(gameName, playerCount) {
        this.send({
            type: "CREATE_GAME",
            game_name: gameName,
            max_players: parseInt(playerCount) || 4
        });
    }

    joinGame(gameId) {
        this.send({
            type: "JOIN_GAME",
            game_id: gameId
        });
    }

    leaveLobby() {
        this.send({
            type: "LEAVE_GAME"
        });
    }

    startGame() {
        this.send({
            type: "START_GAME"
        });
    }

    moveToken(tokenId, position) {
        this.send({
            type: "MOVE",
            token_id: tokenId,
            position: position
        });
    }

    attackToken(attackerId, defenderId) {
        this.send({
            type: "ATTACK",
            attacker_id: attackerId,
            defender_id: defenderId
        });
    }

    deployToken(health, position) {
        this.send({
            type: "DEPLOY",
            health: health,
            position: position
        });
    }

    endTurn() {
        this.send({
            type: "END_TURN"
        });
    }

    disconnect() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        this.connectionState = STATE.DISCONNECTED;
    }

    getConnectionState() {
        return this.connectionState;
    }

    isPlayerReady() {
        return this.isReady;
    }

    isPlayerHost() {
        return this.isHost;
    }
}

export { NetworkManager };
