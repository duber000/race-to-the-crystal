// ==========================================================================
// UI Manager - Handles all UI screens, HUD, and user interface
// ==========================================================================

import { TurnPhase } from './game_client.constants.js';

class UIManager {
    constructor() {
        this.deploymentMenuOpen = false;
        this.selectedDeployHealth = null;
        this.lobbyHandlersSetup = false;
        this.playerId = null;
        this.onJoinGame = null;
        this.onLeaveLobby = null;
        this.onStartGame = null;
        this.onToggleReady = null;
        this.onCreateGame = null;
    }

    // ==========================================================================
    // Screen Management
    // ==========================================================================

    showScreen(screenName) {
        this._setHiddenById("connection-screen", true);
        this._setHiddenById("lobby-browser-screen", true);
        this._setHiddenById("waiting-room-screen", true);

        if (this.canvas) {
            this.canvas.classList.add("hidden");
        }

        this._setHiddenById("hud", true);
        this._setHiddenById("controls", true);
        this._setHiddenById("connectionStatus", true);

        switch (screenName) {
            case 'disconnected':
            case 'connecting':
                this._setHiddenById("connection-screen", false);
                break;
            case 'connected':
                this._setHiddenById("lobby-browser-screen", false);
                break;
            case 'lobby':
                this._setHiddenById("waiting-room-screen", false);
                break;
            case 'game':
            case 'game_starting':
                this._setHiddenById("waiting-room-screen", false);
                break;
            case 'in_game':
                if (this.canvas) {
                    this.canvas.classList.remove("hidden");
                    this.canvas.setAttribute("tabindex", "1");
                    this.canvas.focus();
                }
                this._setHiddenById("hud", false);
                this._setHiddenById("controls", false);
                this._setHiddenById("connectionStatus", false);
                break;
            default:
                console.warn(`[UI] Unknown screen: ${screenName}`);
        }
    }

    _setHiddenById(elementId, hidden) {
        const element = document.getElementById(elementId);
        if (!element) {
            return;
        }
        element.classList.toggle("hidden", hidden);
    }

    setupConnectionScreen(connectCallback) {
        document.getElementById("connect-btn").addEventListener("click", () => {
            const name = document.getElementById("player-name-input").value.trim();
            const host = document.getElementById("server-host-input").value.trim();
            const port = document.getElementById("server-port-input").value.trim();

            if (!name) {
                this.showConnectionError("Please enter your name");
                return;
            }

            connectCallback(name, host, port);
        });

        document.getElementById("player-name-input").addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                document.getElementById("connect-btn").click();
            }
        });
    }

    showConnectionStatus(message) {
        const statusMsg = document.getElementById("connection-status-msg");
        if (statusMsg) {
            statusMsg.textContent = message;
        }
    }

    showConnectionError(message) {
        const errorMsg = document.getElementById("connection-error");
        if (errorMsg) {
            errorMsg.textContent = message;
        }
    }

    showLobbyError(message) {
        const errorMsg = document.getElementById("lobby-error");
        if (errorMsg) {
            errorMsg.textContent = message;
            setTimeout(() => { errorMsg.textContent = ""; }, 3000);
        }
    }

    showActionError(message) {
        const errorDiv = document.createElement("div");
        errorDiv.className = "action-error";
        errorDiv.textContent = message;

        document.body.appendChild(errorDiv);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 3000);
    }

    showDeploymentIndicator(health) {
        const indicator = document.getElementById("deployment-indicator");
        if (indicator) {
            indicator.textContent = `Deploy ${health} HP`;
            indicator.classList.remove("hidden");
        }
    }

    clearSelection() {
        this.selectedDeployHealth = null;
        const indicator = document.getElementById("deployment-indicator");
        if (indicator) {
            indicator.classList.add("hidden");
        }
    }

    getSelectedDeployHealth() {
        return this.selectedDeployHealth;
    }

    toggleDeploymentMenu(open) {
        this.deploymentMenuOpen = open;
        const menu = document.getElementById("deployment-menu");
        if (menu) {
            menu.classList.toggle("hidden", !open);
        }
    }

    isDeploymentMenuOpen() {
        return this.deploymentMenuOpen;
    }

    updateReadyButton(isReady) {
        const button = document.getElementById("ready-btn");
        if (button) {
            button.textContent = isReady ? "Ready!" : "Ready?";
            button.classList.toggle("ready", isReady);
        }
    }

    updateStartButtonState(lobby, isHost, callback) {
        const button = document.getElementById("start-game-btn");
        if (button) {
            button.classList.toggle("hidden", !isHost);
            button.disabled = !(isHost && lobby.players && lobby.players.length >= 2);
            button.onclick = callback;
        }
    }

    // ==========================================================================
    // Lobby Browser UI
    // ==========================================================================

    setupLobbyBrowserHandlers(onCreateGame, onRefreshGames, onDisconnect) {
        this.onCreateGame = onCreateGame;
        this.onRefreshGames = onRefreshGames;
        this.onDisconnect = onDisconnect;

        // Setup create game button - shows inline form
        const createBtn = document.getElementById("create-game-btn");
        const createSection = document.getElementById("create-game-section");
        if (createBtn && createSection) {
            createBtn.onclick = () => {
                createSection.classList.remove("hidden");
                createBtn.classList.add("hidden");
                const nameInput = document.getElementById("create-game-name-input");
                if (nameInput) nameInput.focus();
            };

            const confirmBtn = document.getElementById("create-game-confirm-btn");
            const cancelBtn = document.getElementById("create-game-cancel-btn");

            const hideCreateForm = () => {
                createSection.classList.add("hidden");
                createBtn.classList.remove("hidden");
            };

            if (confirmBtn) {
                confirmBtn.onclick = () => {
                    const gameName = document.getElementById("create-game-name-input").value.trim();
                    const playerCount = parseInt(document.getElementById("create-game-players-input").value) || 4;
                    if (!gameName) {
                        this.showLobbyError("Please enter a game name");
                        return;
                    }
                    if (playerCount < 2 || playerCount > 4) {
                        this.showLobbyError("Player count must be 2-4");
                        return;
                    }
                    hideCreateForm();
                    if (this.onCreateGame) {
                        this.onCreateGame(gameName, playerCount);
                    }
                };
            }

            if (cancelBtn) {
                cancelBtn.onclick = hideCreateForm;
            }

            // Allow Enter key in game name input to submit
            const nameInput = document.getElementById("create-game-name-input");
            if (nameInput) {
                nameInput.addEventListener("keypress", (e) => {
                    if (e.key === "Enter" && confirmBtn) {
                        confirmBtn.click();
                    }
                });
            }
        }

        // Setup refresh button
        const refreshBtn = document.getElementById("refresh-games-btn");
        if (refreshBtn) {
            refreshBtn.onclick = () => {
                if (this.onRefreshGames) {
                    this.onRefreshGames();
                }
            };
        }

        // Setup disconnect button
        const disconnectBtn = document.getElementById("disconnect-btn");
        if (disconnectBtn) {
            disconnectBtn.onclick = () => {
                if (this.onDisconnect) {
                    this.onDisconnect();
                }
            };
        }
    }

    renderGameList(games) {
        const gameList = document.getElementById("game-list");
        if (!gameList) return;

        // Clear existing games
        gameList.innerHTML = "";

        if (games.length === 0) {
            const empty = document.createElement("div");
            empty.className = "game-item empty";
            empty.textContent = "No games found. Create a new game!";
            gameList.appendChild(empty);
            return;
        }

        // Render game items
        games.forEach(game => {
            const item = document.createElement("div");
            item.className = "game-item";
            item.innerHTML = `
                <div class="game-name">${game.name}</div>
                <div class="game-info">
                    ${game.players.length}/${game.max_players} players
                </div>
            `;
            item.onclick = () => {
                if (this.onJoinGame) {
                    this.onJoinGame(game.id);
                }
            };
            gameList.appendChild(item);
        });
    }

    // ==========================================================================
    // Waiting Room UI
    // ==========================================================================

    setupWaitingRoomHandlers(onToggleReady, onStartGame, onLeaveLobby) {
        this.onToggleReady = onToggleReady;
        this.onStartGame = onStartGame;
        this.onLeaveLobby = onLeaveLobby;

        // Setup ready button
        const readyBtn = document.getElementById("ready-btn");
        if (readyBtn) {
            readyBtn.onclick = () => {
                if (this.onToggleReady) {
                    this.onToggleReady();
                }
            };
        }

        // Setup start game button
        const startBtn = document.getElementById("start-game-btn");
        if (startBtn) {
            startBtn.onclick = () => {
                if (this.onStartGame) {
                    this.onStartGame();
                }
            };
        }

        // Setup leave lobby button
        const leaveBtn = document.getElementById("leave-lobby-btn");
        if (leaveBtn) {
            leaveBtn.onclick = () => {
                if (this.onLeaveLobby) {
                    this.onLeaveLobby();
                }
            };
        }
    }

    renderWaitingRoom(lobby, isHost, isReady) {
        const playersList = document.getElementById("lobby-players");
        if (!playersList) return;

        // Update game name
        const gameName = document.getElementById("lobby-game-name");
        if (gameName) {
            gameName.textContent = `${lobby.game_name || "Game Lobby"}${isHost ? " (Host)" : ""}`;
        }

        // Clear and rebuild players list (keep heading)
        playersList.innerHTML = "<h3>Players:</h3>";

        // Render player items
        if (lobby.players) {
            lobby.players.forEach(player => {
                const name = player.player_name || player.name;
                const ready = player.is_ready || player.ready;
                const item = document.createElement("div");
                item.className = "player-item";
                item.innerHTML = `
                    <span class="player-name">${name}</span>
                    <span class="player-status" style="color: ${ready ? '#0f0' : '#f80'}">${ready ? "Ready!" : "Not ready"}</span>
                `;
                playersList.appendChild(item);
            });
        }
    }

    // ==========================================================================
    // In-Game HUD
    // ==========================================================================

    updateHUD(gameState, localPlayerId) {
        if (!gameState || !localPlayerId) return;

        const player = gameState.players[localPlayerId];
        if (!player) return;

        // Update player info
        const playerName = document.getElementById("player-name");
        const playerTokens = document.getElementById("player-tokens");
        const playerHealth = document.getElementById("player-health");

        if (playerName) playerName.textContent = player.name;
        if (playerTokens) playerTokens.textContent = player.token_ids.length;
        
        // Calculate total health
        let totalHealth = 0;
        player.token_ids.forEach(tokenId => {
            const token = gameState.tokens[tokenId];
            if (token && token.is_alive && token.is_deployed) {
                totalHealth += token.health;
            }
        });

        if (playerHealth) playerHealth.textContent = totalHealth;

        // Update turn info
        const turnPlayer = document.getElementById("turn-player");
        const turnPhase = document.getElementById("turn-phase");

        if (turnPlayer && gameState.current_turn_player_id) {
            const currentPlayer = gameState.players[gameState.current_turn_player_id];
            turnPlayer.textContent = currentPlayer ? currentPlayer.name : "Unknown";
        }

        if (turnPhase) {
            turnPhase.textContent = gameState.turn_phase === TurnPhase.MOVEMENT ? "Movement" : "Action";
        }

        // Update crystal status
        const crystalStatus = document.getElementById("crystal-status");
        if (crystalStatus && gameState.crystal) {
            const crystalPlayer = gameState.players[gameState.crystal.controlling_player_id];
            crystalStatus.textContent = crystalPlayer ? `${crystalPlayer.name} controls crystal` : "Crystal unclaimed";
        }
    }

    setCanvas(canvas) {
        this.canvas = canvas;
    }
}

export { UIManager };
