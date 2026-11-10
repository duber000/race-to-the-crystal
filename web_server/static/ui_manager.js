// ==========================================================================
// UI Manager - Handles all UI screens, HUD, and user interface
// ==========================================================================

import { CRYSTAL_EFFECT, GAME_STATE_PHASE, TurnPhase } from './game_client.constants.js';
import { UIUtils } from './ui.utils.js';

class UIManager {
    constructor() {
        this.deploymentMenuOpen = false;
        this.selectedDeployHealth = null;
        this.lobbyHandlersSetup = false;
        this.playerId = null;
        this.onJoinGame = null;
        this.onSpectateGame = null;
        this.onLeaveLobby = null;
        this.onStartGame = null;
        this.onToggleReady = null;
        this.onCreateGame = null;
    }

    // ==========================================================================
    // Screen Management
    // ==========================================================================

    showScreen(screenName) {
        UIUtils.setHiddenById("connection-screen", true);
        UIUtils.setHiddenById("lobby-browser-screen", true);
        UIUtils.setHiddenById("waiting-room-screen", true);

        if (this.canvas) {
            this.canvas.classList.add("hidden");
        }

        UIUtils.setHiddenById("hud", true);
        UIUtils.setHiddenById("controls", true);
        UIUtils.setHiddenById("connectionStatus", true);

        switch (screenName) {
            case 'disconnected':
            case 'connecting':
                UIUtils.setHiddenById("connection-screen", false);
                break;
            case 'connected':
                UIUtils.setHiddenById("lobby-browser-screen", false);
                break;
            case 'lobby':
                UIUtils.setHiddenById("waiting-room-screen", false);
                break;
            case 'game':
            case 'game_starting':
                UIUtils.setHiddenById("waiting-room-screen", false);
                break;
            case 'in_game':
                if (this.canvas) {
                    this.canvas.classList.remove("hidden");
                    this.canvas.setAttribute("tabindex", "1");
                    this.canvas.focus();
                }
                UIUtils.setHiddenById("hud", false);
                UIUtils.setHiddenById("controls", false);
                UIUtils.setHiddenById("connectionStatus", false);
                break;
            default:
                console.warn(`[UI] Unknown screen: ${screenName}`);
        }
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
            setTimeout(() => { errorMsg.textContent = ""; }, 3000);
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
        errorDiv.setAttribute("role", "alert");

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
            indicator.classList.remove("hidden");
            const value = document.getElementById("deployment-indicator-value");
            if (value) {
                value.textContent = `${health} HP`;
            }
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

    setupDeploymentMenu() {
        const menu = document.getElementById("deployment-menu");
        if (!menu || this.deploymentMenuSetup) return;
        this.deploymentMenuSetup = true;
        menu.querySelectorAll(".deploy-btn").forEach((btn) => {
            btn.onclick = () => {
                const health = parseInt(btn.dataset.health, 10) || 4;
                this.selectedDeployHealth = health;
                this.toggleDeploymentMenu(false);
                this.showDeploymentIndicator(health);
            };
        });
    }

    toggleDeploymentMenu(open) {
        this.deploymentMenuOpen = open;
        const menu = document.getElementById("deployment-menu");
        if (menu) {
            if (open) {
                this.setupDeploymentMenu();
            }
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

    setupLobbyBrowserHandlers(onCreateGame, onJoinGame, onRefreshGames, onDisconnect, onSpectateGame) {
        this.onCreateGame = onCreateGame;
        this.onJoinGame = onJoinGame;
        this.onRefreshGames = onRefreshGames;
        this.onDisconnect = onDisconnect;
        this.onSpectateGame = onSpectateGame || null;

        // Setup join by game ID
        const joinIdBtn = document.getElementById("join-by-id-btn");
        const joinIdInput = document.getElementById("join-game-id-input");
        const joinById = () => {
            if (!joinIdInput) return;
            const gameId = joinIdInput.value.trim();
            if (!gameId) {
                this.showLobbyError("Please enter a game ID");
                return;
            }
            if (this.onJoinGame) {
                this.onJoinGame(gameId);
            }
        };
        if (joinIdBtn) {
            joinIdBtn.onclick = joinById;
        }
        if (joinIdInput) {
            joinIdInput.addEventListener("keypress", (e) => {
                if (e.key === "Enter") {
                    joinById();
                }
            });
        }

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
        const gameList = document.getElementById("game-list-container");
        const noGamesMsg = document.getElementById("no-games-msg");
        if (!gameList) return;

        // Clear existing games
        gameList.innerHTML = "";

        if (!games || games.length === 0) {
            if (noGamesMsg) noGamesMsg.classList.remove("hidden");
            return;
        }

        if (noGamesMsg) noGamesMsg.classList.add("hidden");

        // Render game items
        games.forEach(game => {
            const name = game.game_name || game.name;
            const id = game.game_id || game.id;
            const playerCount = game.current_players ?? (game.players ? game.players.length : 0);
            const maxPlayers = game.max_players || 4;
            const status = (game.status || game.game_status || 'WAITING').toUpperCase();
            const item = document.createElement("div");
            item.className = "game-item";

            const info = document.createElement("div");
            info.className = "game-info";

            const strong = document.createElement("strong");
            strong.textContent = name;

            const span = document.createElement("span");
            span.textContent = `${playerCount}/${maxPlayers} players • ${status}`;

            info.appendChild(strong);
            info.appendChild(span);
            item.appendChild(info);

            if (status === 'IN_PROGRESS') {
                const btn = document.createElement('button');
                btn.textContent = 'Spectate';
                btn.className = 'spectate-btn';
                btn.onclick = (e) => {
                    e.stopPropagation();
                    this.showSpectateSeatChooser(game, (follow) => {
                        if (this.onSpectateGame) this.onSpectateGame(id, follow);
                    });
                };
                item.appendChild(btn);
                item.onclick = () => {
                    this.showSpectateSeatChooser(game, (follow) => {
                        if (this.onSpectateGame) this.onSpectateGame(id, follow);
                    });
                };
            } else {
                item.onclick = () => {
                    if (this.onJoinGame) {
                        this.onJoinGame(id);
                    }
                };
            }
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

        // Show the game ID so others can join by ID (the lobby browser only
        // lists WAITING lobbies, and a private game is joined by ID).
        this._renderGameId(lobby.game_id);

        // Clear and rebuild players list (keep heading)
        playersList.innerHTML = "<h3>Players:</h3>";

        // Render player items
        if (lobby.players) {
            lobby.players.forEach(player => {
                const name = player.player_name || player.name;
                const ready = player.is_ready || player.ready;
                const item = document.createElement("div");
                item.className = "player-item";

                const nameSpan = document.createElement("span");
                nameSpan.className = "player-name";
                nameSpan.textContent = name;

                const statusSpan = document.createElement("span");
                statusSpan.className = `player-status ${ready ? 'is-ready' : 'is-not-ready'}`;
                statusSpan.textContent = ready ? "Ready!" : "Not ready";

                item.appendChild(nameSpan);
                item.appendChild(statusSpan);
                playersList.appendChild(item);
            });
        }
    }

    /**
     * Render the joinable game ID with a click-to-copy affordance.
     */
    _renderGameId(gameId) {
        const container = document.getElementById("lobby-game-id");
        if (!container) return;

        if (!gameId) {
            container.innerHTML = "";
            return;
        }

        container.innerHTML = "";
        const display = document.createElement("div");
        display.className = "game-id-display";
        display.textContent = `Game ID: ${gameId}`;
        display.title = "Click to copy the game ID";

        display.onclick = () => {
            const copy = () => {
                display.classList.add("game-id-copy-success");
                display.textContent = "✓ Copied to clipboard!";
                setTimeout(() => {
                    display.classList.remove("game-id-copy-success");
                    display.textContent = `Game ID: ${gameId}`;
                }, 1500);
            };

            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(gameId).then(copy).catch(() => {
                    console.warn("Clipboard write failed for game ID");
                });
            } else {
                copy();
            }
        };

        container.appendChild(display);
    }

    // ==========================================================================
    // In-Game HUD
    // ==========================================================================

    /**
     * Update the in-game HUD.
     *
     * The DOM ids here must match web_server/templates/index.html:
     *   #turnNumber #gamePhase #turnPhase #currentPlayer #playersList
     *   #crystalStatus #crystal-effects-indicator
     */
    updateHUD(gameState, localPlayerId) {
        if (!gameState) return;

        // --- turn / phase counters -------------------------------------------
        this._setText("turnNumber", gameState.turn_number ?? 0);
        this._setText("gamePhase", gameState.phase || GAME_STATE_PHASE.SETUP);
        this._setText("turnPhase", gameState.turn_phase || TurnPhase.MOVEMENT);

        // --- current player --------------------------------------------------
        const currentPlayer = gameState.current_turn_player_id
            ? gameState.players?.[gameState.current_turn_player_id]
            : null;
        const currentPlayerEl = document.getElementById("currentPlayer");
        if (currentPlayerEl) {
            currentPlayerEl.textContent = currentPlayer ? (currentPlayer.name || "Unknown") : "-";
            currentPlayerEl.className = "";
            if (currentPlayer) {
                currentPlayerEl.classList.add("player-color", `player-color-${this._colorIndex(currentPlayer)}`);
            }
        }

        // --- player roster ---------------------------------------------------
        const playersList = document.getElementById("playersList");
        if (playersList) {
            playersList.innerHTML = "";
            const players = Object.values(gameState.players || {});
            for (const player of players) {
                const playerDiv = document.createElement("div");
                playerDiv.className = "player-info";

                const isLocal = player.id === localPlayerId ? " (YOU)" : "";
                const name = document.createElement("strong");
                name.className = `player-color player-color-${this._colorIndex(player)}`;
                name.textContent = `${player.name || player.player_name || player.id}${isLocal}`;

                const tokenCount = document.createElement("div");
                const tokenIds = player.token_ids || [];
                const visible = tokenIds.filter((id) => {
                    const t = gameState.tokens?.[id];
                    if (!t || !t.is_alive || !t.is_deployed) return false;
                    // With fog of war on, only count the tokens this player
                    // can actually see — otherwise the roster would leak
                    // where the enemy has pieces on the board.
                    return player.id === localPlayerId || t.is_visible !== false;
                }).length;
                tokenCount.textContent = `Tokens: ${visible}/${tokenIds.length}`;

                playerDiv.appendChild(name);
                playerDiv.appendChild(tokenCount);
                playersList.appendChild(playerDiv);
            }
        }

        // --- crystal capture progress ----------------------------------------
        this._updateCrystalStatus(gameState);

        // --- active crystal effects -----------------------------------------
        this.updateCrystalEffectsIndicator(gameState, localPlayerId);
    }

    /**
     * Colour index for a player, tolerating either `color_index` or `color`.
     */
    _colorIndex(player) {
        if (typeof player.color_index === "number") return player.color_index;
        if (typeof player.color === "number") return player.color;
        return 0;
    }

    /**
     * Set an element's text content if the element exists.
     */
    _setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    /**
     * Show crystal ownership / capture progress.
     */
    _updateCrystalStatus(gameState) {
        const el = document.getElementById("crystalStatus");
        if (!el) return;

        const crystal = gameState.crystal;
        if (!crystal) {
            el.textContent = "Crystal unclaimed";
            return;
        }

        const holderId = crystal.controlling_player_id || crystal.holding_player_id;
        const holder = holderId ? gameState.players?.[holderId] : null;
        const required = crystal.base_tokens_required ?? 0;
        const held = (crystal.holding_token_ids || []).length;

        if (!holder) {
            el.textContent = `Crystal unclaimed (needs ${required} tokens)`;
            return;
        }

        el.textContent = `${holder.name || holderId} controls crystal (${held}/${required} tokens, ${crystal.turns_held} turn${crystal.turns_held === 1 ? "" : "s"})`;
    }

    /**
     * Update the crystal effects indicator showing active debuffs/buffs.
     */
    updateCrystalEffectsIndicator(gameState, localPlayerId) {
        const indicator = document.getElementById("crystal-effects-indicator");
        if (!indicator) return;

        const playerEffects = gameState.crystal_effects?.player_effects?.[localPlayerId];
        const activeEffects = (playerEffects?.active_effects || []).filter(
            (e) => e.turns_remaining > 0,
        );

        if (activeEffects.length === 0) {
            indicator.innerHTML = "";
            indicator.classList.add("hidden");
            return;
        }

        indicator.classList.remove("hidden");
        indicator.textContent = "";

        const panel = document.createElement("div");
        panel.className = "effects-panel";

        for (const effect of activeEffects) {
            let effectName, icon, cssClass;
            switch (effect.effect_type) {
                case CRYSTAL_EFFECT.FOG_OF_WAR:
                    effectName = "Fog of War";
                    icon = "🌫️";
                    cssClass = "fog-of-war";
                    break;
                case CRYSTAL_EFFECT.PHANTOM_ENEMIES:
                    effectName = "Phantom Enemies";
                    icon = "👻";
                    cssClass = "phantom-enemies";
                    break;
                case CRYSTAL_EFFECT.DAMAGE_BOOST:
                    effectName = "Damage Boost";
                    icon = "⚡";
                    cssClass = "damage-boost";
                    break;
                case CRYSTAL_EFFECT.SPEED_BOOST:
                    effectName = "Speed Boost";
                    icon = "💨";
                    cssClass = "speed-boost";
                    break;
                default:
                    effectName = "Unknown Effect";
                    icon = "❓";
                    cssClass = "";
            }

            const badge = document.createElement("div");
            badge.className = `effect-badge ${cssClass}`.trim();

            const iconSpan = document.createElement("span");
            iconSpan.className = "effect-icon";
            iconSpan.textContent = icon;

            const nameSpan = document.createElement("span");
            nameSpan.className = "effect-name";
            nameSpan.textContent = effectName;

            const duration = document.createElement("span");
            duration.className = "effect-duration";
            duration.textContent = `${effect.turns_remaining} turn${effect.turns_remaining !== 1 ? "s" : ""}`;

            badge.appendChild(iconSpan);
            badge.appendChild(nameSpan);
            badge.appendChild(duration);
            panel.appendChild(badge);
        }

        indicator.appendChild(panel);
    }

    /**
     * Show a countdown for the current turn.
     *
     * The server sends the timeout in the TURN_CHANGED event; the countdown
     * runs locally from there, so it does not need a message per second.
     *
     * @param {number} seconds - Seconds allowed for the turn
     * @param {string} playerId - The player whose turn it is
     */
    startTurnCountdown(seconds, playerId) {
        this.stopTurnCountdown();
        if (!seconds || seconds <= 0) {
            return;
        }

        this.turnCountdown = {
            playerId: playerId,
            remaining: seconds,
            deadline: Date.now() + seconds * 1000,
        };

        const tick = () => {
            if (!this.turnCountdown) return;
            const left = Math.max(
                0,
                Math.round((this.turnCountdown.deadline - Date.now()) / 1000),
            );
            this.turnCountdown.remaining = left;
            this._renderTurnCountdown(left, seconds);

            if (left <= 0) {
                this.stopTurnCountdown();
                return;
            }
            this.turnCountdownTimer = setTimeout(tick, 250);
        };

        this._renderTurnCountdown(seconds, seconds);
        this.turnCountdownTimer = setTimeout(tick, 250);
    }

    /**
     * Stop the turn countdown.
     */
    stopTurnCountdown() {
        if (this.turnCountdownTimer) {
            clearTimeout(this.turnCountdownTimer);
            this.turnCountdownTimer = null;
        }
        this.turnCountdown = null;
        const el = document.getElementById("turn-timer");
        if (el) {
            el.textContent = "";
            el.classList.add("hidden");
        }
    }

    /**
     * Render the countdown, warning as it runs down.
     */
    _renderTurnCountdown(remaining, total) {
        const el = document.getElementById("turn-timer");
        if (!el) return;

        el.classList.remove("hidden");
        el.textContent = `${remaining}s`;
        el.classList.toggle("turn-timer-urgent", remaining <= 10 && total > 0);
    }

    /**
     * Seat-cam picker for spectators. The spectator chooses which seat to
     * follow; they will see exactly what that player can see (fog-filtered
     * by the server). With no picker data (e.g. a malformed game list),
     * falls back to a random seat.
     */
    showSpectateSeatChooser(game, onPick) {
        const gameName = (game && (game.game_name || game.name)) || 'this game';
        const players = (game && Array.isArray(game.players)) ? game.players : [];

        if (players.length === 0) {
            onPick("");
            return;
        }

        const overlay = document.createElement('div');
        overlay.className = 'spectate-overlay';

        const card = document.createElement('div');
        card.className = 'spectate-card';

        const title = document.createElement('h3');
        title.textContent = `Spectate ${gameName}`;
        card.appendChild(title);

        const blurb = document.createElement('p');
        blurb.textContent = 'Choose your view. You see exactly what they see — hidden units stay hidden.';
        card.appendChild(blurb);

        const seats = document.createElement('div');
        seats.className = 'spectate-seats';

        players.forEach((player, idx) => {
            // Seats are player_{color_index} — the server assigns seats in
            // join (colour index) order, matching getPlayerList ordering.
            // Trust color_index over the array position when present.
            const seatIdx = Number.isInteger(player.color_index) ? player.color_index : idx;
            const seat = `player_${seatIdx}`;
            const btn = document.createElement('button');
            btn.className = 'spectate-seat';
            const name = player.player_name || player.name || `Seat ${idx + 1}`;
            const label = document.createElement('span');
            label.textContent = name;
            const kind = document.createElement('small');
            kind.textContent = player.client_type || '';
            btn.appendChild(label);
            btn.appendChild(kind);
            btn.onclick = () => {
                overlay.remove();
                onPick(seat);
            };
            seats.appendChild(btn);
        });

        card.appendChild(seats);

        const random = document.createElement('button');
        random.className = 'spectate-random';
        random.textContent = 'Random seat';
        random.onclick = () => {
            overlay.remove();
            onPick("");
        };
        card.appendChild(random);

        const cancel = document.createElement('button');
        cancel.className = 'spectate-cancel';
        cancel.textContent = 'Cancel';
        cancel.onclick = () => overlay.remove();
        card.appendChild(cancel);

        overlay.appendChild(card);
        overlay.onclick = (e) => {
            if (e.target === overlay) overlay.remove();
        };
        document.body.appendChild(overlay);
    }

    /**
     * Persistent banner for spectators: shows which seat they are
     * following.
     */
    showSpectateBanner(followName) {
        this.hideSpectateBanner();
        const banner = document.createElement('div');
        banner.id = 'spectate-banner';
        banner.className = 'spectate-banner';
        banner.textContent = `SPECTATING — following ${followName}`;
        document.body.appendChild(banner);
    }

    hideSpectateBanner() {
        const existing = document.getElementById('spectate-banner');
        if (existing) existing.remove();
    }

    setCanvas(canvas) {
        this.canvas = canvas;
    }
}

export { UIManager };