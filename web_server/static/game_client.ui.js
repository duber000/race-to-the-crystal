/**
 * UIManager - HUD, menus, and UI rendering
 *
 * Responsibilities:
 * - Connection screen
 * - Lobby browser UI
 * - Waiting room UI
 * - In-game HUD
 * - Deployment menu
 * - Action feedback (errors, etc.)
 *
 * Usage:
 *   const ui = new UIManager();
 *   ui.showScreen('lobby');
 *   ui.updateHUD(gameState);
 */

class UIManager {
    constructor() {
        this.deploymentMenuOpen = false;
        this.selectedDeployHealth = null;
        this.lobbyHandlersSetup = false;
        this.playerId = null;
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

    showActionError(message) {
        const errorDiv = document.createElement("div");
        errorDiv.className = "action-error";
        errorDiv.textContent = message;

        document.body.appendChild(errorDiv);

        setTimeout(() => {
            errorDiv.remove();
        }, 3000);
    }

    // ==========================================================================
    // Lobby Browser UI
    // ==========================================================================

    renderGameList(games) {
        const container = document.getElementById("game-list-container");
        const noGamesMsg = document.getElementById("no-games-msg");

        container.innerHTML = "";

        if (!games || games.length === 0) {
            noGamesMsg.classList.remove("hidden");
            return;
        }

        noGamesMsg.classList.add("hidden");

        games.forEach((game) => {
            const gameDiv = document.createElement("div");
            gameDiv.className = "game-item";

            const gameInfo = document.createElement("div");
            gameInfo.className = "game-info";
            const gameName = document.createElement("strong");
            gameName.textContent = game.game_name || game.name || "Unknown Game";

            const players = document.createElement("span");
            const currentPlayers =
                game.current_players ?? game.num_players ?? 0;
            players.textContent = `Players: ${currentPlayers}/${game.max_players || 4}`;

            const status = document.createElement("span");
            status.textContent = `Status: ${game.status || "waiting"}`;

            gameInfo.appendChild(gameName);
            gameInfo.appendChild(players);
            gameInfo.appendChild(status);

            const joinBtn = document.createElement("button");
            joinBtn.textContent = "Join";
            joinBtn.addEventListener("click", () => {
                if (this.onJoinGame) {
                    this.onJoinGame(game.game_id);
                }
            });

            gameDiv.appendChild(gameInfo);
            gameDiv.appendChild(joinBtn);
            container.appendChild(gameDiv);
        });
    }

    setupLobbyBrowserHandlers(createGame, refreshGames, disconnect) {
        if (this.lobbyHandlersSetup) {
            return;
        }
        this.lobbyHandlersSetup = true;
        document.getElementById("create-game-btn").addEventListener("click", () => {
            this.showCreateGameDialog(createGame);
        });

        document.getElementById("refresh-games-btn").addEventListener("click", () => {
            refreshGames();
        });

        document.getElementById("disconnect-btn").addEventListener("click", () => {
            disconnect();
        });

        // Join by game ID handler
        const joinByIdBtn = document.getElementById("join-by-id-btn");
        const joinByIdInput = document.getElementById("join-game-id-input");

        const handleJoinById = () => {
            const gameId = joinByIdInput.value.trim();
            if (gameId && this.onJoinGame) {
                this.onJoinGame(gameId);
                joinByIdInput.value = "";
            }
        };

        joinByIdBtn.addEventListener("click", handleJoinById);
        joinByIdInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                handleJoinById();
            }
        });
    }

    showCreateGameDialog(createGame) {
        // Create dialog overlay
        const overlay = document.createElement("div");
        overlay.id = "create-game-dialog-overlay";
        overlay.className = "dialog-overlay";

        const dialog = document.createElement("div");
        dialog.className = "dialog";

        dialog.innerHTML = `
            <h2 class="dialog-title">CREATE GAME</h2>
            <div class="dialog-field">
                <label class="dialog-label">Game Name:</label>
                <input type="text" id="dialog-game-name" value="My Game" maxlength="50"
                    class="dialog-input">
            </div>
            <div class="dialog-field">
                <label class="dialog-label">Number of Players:</label>
                <select id="dialog-player-count"
                    class="dialog-select">
                    <option value="2">2 Players</option>
                    <option value="3">3 Players</option>
                    <option value="4" selected>4 Players</option>
                </select>
            </div>
            <div class="dialog-note">
                AI players will fill empty slots when you start the game
            </div>
            <div class="dialog-actions">
                <button id="dialog-create-btn"
                    class="dialog-button">
                    Create
                </button>
                <button id="dialog-cancel-btn"
                    class="dialog-button">
                    Cancel
                </button>
            </div>
        `;

        overlay.appendChild(dialog);
        document.body.appendChild(overlay);

        // Handle create button
        dialog.querySelector("#dialog-create-btn").addEventListener("click", () => {
            const gameName = dialog.querySelector("#dialog-game-name").value.trim();
            const playerCount = parseInt(dialog.querySelector("#dialog-player-count").value);

            if (gameName) {
                createGame(gameName, playerCount);
                overlay.remove();
            }
        });

        // Handle cancel button
        dialog.querySelector("#dialog-cancel-btn").addEventListener("click", () => {
            overlay.remove();
        });

        // Handle escape key
        overlay.addEventListener("keydown", (e) => {
            if (e.key === "Escape") {
                overlay.remove();
            }
        });

        // Focus game name input
        dialog.querySelector("#dialog-game-name").focus();
        dialog.querySelector("#dialog-game-name").select();
    }

    // ==========================================================================
    // Waiting Room UI
    // ==========================================================================

    renderWaitingRoom(lobby, isHost, isReady) {
        if (!lobby) {
            console.warn("No lobby data to render");
            return;
        }

        document.getElementById("lobby-game-name").textContent = lobby.game_name;

        // Display game ID for sharing (add if not exists)
        let gameIdDisplay = document.getElementById("lobby-game-id");
        if (!gameIdDisplay) {
            gameIdDisplay = document.createElement("div");
            gameIdDisplay.id = "lobby-game-id";
            gameIdDisplay.className = "game-id-display";
            gameIdDisplay.title = "Click to copy game ID";

            const titleElement = document.getElementById("lobby-game-name");
            titleElement.after(gameIdDisplay);

            // Add click to copy functionality
            gameIdDisplay.addEventListener("click", () => {
                const gameId = gameIdDisplay.getAttribute("data-game-id");
                navigator.clipboard.writeText(gameId).then(() => {
                    gameIdDisplay.textContent = "✓ Copied to clipboard!";
                    gameIdDisplay.classList.add("game-id-copy-success");
                    setTimeout(() => {
                        const shortId = gameId.substring(0, 8);
                        gameIdDisplay.textContent = "";
                        const gameIdLabel = document.createTextNode("Game ID: ");
                        const strong = document.createElement("strong");
                        strong.textContent = shortId;
                        const suffix = document.createTextNode(" (click to copy full ID)");
                        gameIdDisplay.appendChild(gameIdLabel);
                        gameIdDisplay.appendChild(strong);
                        gameIdDisplay.appendChild(suffix);
                        gameIdDisplay.classList.remove("game-id-copy-success");
                    }, 2000);
                }).catch(() => {
                    console.error("Failed to copy game ID");
                });
            });
        }

        // Update game ID display
        const shortId = lobby.game_id.substring(0, 8);
        gameIdDisplay.textContent = "";
        const gameIdLabel = document.createTextNode("Game ID: ");
        const strong = document.createElement("strong");
        strong.textContent = shortId;
        const suffix = document.createTextNode(" (click to copy full ID)");
        gameIdDisplay.appendChild(gameIdLabel);
        gameIdDisplay.appendChild(strong);
        gameIdDisplay.appendChild(suffix);
        gameIdDisplay.setAttribute("data-game-id", lobby.game_id);

        this.renderLobbyPlayerList(lobby, isHost);

        const startBtn = document.getElementById("start-game-btn");
        if (isHost) {
            startBtn.classList.remove("hidden");
        } else {
            startBtn.classList.add("hidden");
        }

        this.updateReadyButton(isReady);
    }

    renderLobbyPlayerList(lobby, isHost) {
        const container = document.getElementById("lobby-players");
        const playerCount = lobby.players ? lobby.players.length : 0;
        const maxPlayers = lobby.max_players || 4;
        container.innerHTML = `<h3>Players (${playerCount}/${maxPlayers}):</h3>`;

        if (!lobby || !lobby.players) {
            return;
        }

        lobby.players.forEach((player) => {
            const playerDiv = document.createElement("div");
            playerDiv.className = "lobby-player";

            const playerIsHost = player.player_id === lobby.host_player_id;
            const isYou = player.player_id === this.playerId;
            const hostLabel = playerIsHost ? " (Host)" : "";
            const youLabel = isYou ? " (YOU)" : "";

            const color = this.getPlayerColor(player.color_index);
            const nameSpan = document.createElement("span");
            nameSpan.className = `player-color player-color-${player.color_index ?? 0}`;
            nameSpan.textContent = `${player.player_name}${hostLabel}${youLabel}`;

            const readySpan = document.createElement("span");
            readySpan.className = "ready-indicator";
            if (player.is_ready) {
                readySpan.classList.add("ready");
                readySpan.textContent = " ✓ READY";
            } else {
                readySpan.classList.add("not-ready");
                readySpan.textContent = " ✗ NOT READY";
            }

            playerDiv.appendChild(nameSpan);
            playerDiv.appendChild(readySpan);

            container.appendChild(playerDiv);
        });
    }

    getPlayerColor(colorIndex) {
        const colors = ["#0ff", "#f0f", "#ff0", "#0f0"];
        return colors[colorIndex] || "#fff";
    }

    updateReadyButton(isReady) {
        const readyBtn = document.getElementById("ready-btn");
        readyBtn.textContent = isReady ? "Unready" : "Ready";
        readyBtn.classList.toggle("ready-button--ready", isReady);
        readyBtn.classList.toggle("ready-button--not-ready", !isReady);
    }

    updateStartButtonState(lobby, isHost, startGameCallback) {
        if (!isHost) return;

        const startBtn = document.getElementById("start-game-btn");
        if (!startBtn || !lobby) return;

        const allReady = lobby.players.every((p) => p.is_ready);
        const minPlayers = lobby.players.length >= (lobby.min_players || 2);

        if (startGameCallback) {
            startBtn.onclick = startGameCallback;
        }

        if (allReady && minPlayers) {
            startBtn.disabled = false;
            startBtn.classList.add("start-button--enabled");
            startBtn.classList.remove("start-button--disabled");
            const emptySlots = (lobby.max_players || 4) - lobby.players.length;
            if (emptySlots > 0) {
                startBtn.title = `Start game (${emptySlots} AI player${emptySlots > 1 ? 's' : ''} will fill empty slots)`;
            } else {
                startBtn.title = "All players ready - click to start!";
            }
        } else {
            startBtn.disabled = true;
            startBtn.classList.add("start-button--disabled");
            startBtn.classList.remove("start-button--enabled");
            if (!allReady) {
                startBtn.title = "Waiting for all players to be ready...";
            } else {
                startBtn.title = `Need at least ${lobby.min_players || 2} players`;
            }
        }
    }

    setupWaitingRoomHandlers(toggleReady, startGame, leaveLobby) {
        const readyBtn = document.getElementById("ready-btn");
        const startBtn = document.getElementById("start-game-btn");
        const leaveBtn = document.getElementById("leave-lobby-btn");

        if (readyBtn) readyBtn.onclick = toggleReady;
        if (startBtn) startBtn.onclick = startGame;
        if (leaveBtn) leaveBtn.onclick = leaveLobby;
    }

    // ==========================================================================
    // In-Game HUD
    // ==========================================================================

    updateHUD(gameState, localPlayerId) {
        document.getElementById("turnNumber").textContent = gameState.turn_number || 0;
        document.getElementById("gamePhase").textContent = gameState.phase || "SETUP";

        // Display turn phase (MOVEMENT vs ACTION)
        const turnPhaseMap = {
            1: "MOVEMENT",
            2: "ACTION",
            3: "END_TURN"
        };
        const turnPhaseValue = gameState.turn_phase || 1;
        document.getElementById("turnPhase").textContent = turnPhaseMap[turnPhaseValue] || "MOVEMENT";

        if (gameState.current_turn_player_id !== null && gameState.players[gameState.current_turn_player_id]) {
            const currentPlayer = gameState.players[gameState.current_turn_player_id];
            const currentColorIndex = currentPlayer.color_index ?? currentPlayer.color ?? 0;
            const currentPlayerEl = document.getElementById("currentPlayer");
            currentPlayerEl.textContent = currentPlayer.name || "Unknown";
            currentPlayerEl.className = "";
            currentPlayerEl.classList.add(
                "player-color",
                `player-color-${currentColorIndex}`,
            );
        }

        const playersList = document.getElementById("playersList");
        playersList.innerHTML = "";

        for (const player of Object.values(gameState.players)) {
            const playerDiv = document.createElement("div");
            playerDiv.className = "player-info";
            const isLocal = player.id === localPlayerId ? " (YOU)" : "";
            const colorIndex = player.color_index ?? player.color ?? 0;
            const name = document.createElement("strong");
            name.className = `player-color player-color-${colorIndex}`;
            name.textContent = `${player.name}${isLocal}`;

            const tokenCount = document.createElement("div");
            tokenCount.textContent = `Tokens: ${player.token_ids.length}`;

            playerDiv.appendChild(name);
            playerDiv.appendChild(tokenCount);
            playersList.appendChild(playerDiv);
        }

        // Update crystal effects indicator
        this.updateCrystalEffectsIndicator(gameState, localPlayerId);
    }

    /**
     * Update the crystal effects indicator showing active debuffs
     */
    updateCrystalEffectsIndicator(gameState, localPlayerId) {
        const indicator = document.getElementById("crystal-effects-indicator");
        if (!indicator) return;

        const playerEffects = gameState.crystal_effects?.player_effects?.[localPlayerId];

        if (!playerEffects || !playerEffects.active_effects || playerEffects.active_effects.length === 0) {
            indicator.innerHTML = "";
            indicator.classList.add("hidden");
            return;
        }

        const activeEffects = playerEffects.active_effects.filter(e => e.turns_remaining > 0);

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
            // Get effect name, icon, and CSS class based on type
            let effectName, icon, cssClass;
            switch (effect.effect_type) {
                case CrystalEffect.FOG_OF_WAR:
                    effectName = "Fog of War";
                    icon = "🌫️";
                    cssClass = "fog-of-war";
                    break;
                case CrystalEffect.PHANTOM_ENEMIES:
                    effectName = "Phantom Enemies";
                    icon = "👻";
                    cssClass = "phantom-enemies";
                    break;
                case CrystalEffect.DAMAGE_BOOST:
                    effectName = "Damage Boost";
                    icon = "⚡";
                    cssClass = "damage-boost";
                    break;
                case CrystalEffect.SPEED_BOOST:
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
            badge.className = `effect-badge ${cssClass}`;

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

    // ==========================================================================
    // Deployment Menu
    // ==========================================================================

    toggleDeploymentMenu(isOpen) {
        this.deploymentMenuOpen = isOpen;
        if (isOpen) {
            this.showDeploymentUI();
        } else {
            this.hideDeploymentUI();
            this.selectedDeployHealth = null;
        }
    }

    showDeploymentUI() {
        const existing = document.getElementById("deployment-menu");
        if (existing) existing.remove();

        const menu = document.createElement("div");
        menu.id = "deployment-menu";
        menu.className = "deployment-menu";

        menu.innerHTML = `
            <div class="deployment-menu-title">
                SELECT TOKEN TO DEPLOY
            </div>
            <div class="deployment-menu-grid">
                <button class="deploy-btn" data-health="10">10 HP</button>
                <button class="deploy-btn" data-health="8">8 HP</button>
                <button class="deploy-btn" data-health="6">6 HP</button>
                <button class="deploy-btn" data-health="4">4 HP</button>
            </div>
            <div class="deployment-menu-hint">
                Click a button then click a corner cell to deploy
            </div>
        `;

        document.body.appendChild(menu);

        menu.querySelectorAll(".deploy-btn").forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                this.selectedDeployHealth = parseInt(e.target.getAttribute("data-health"));
                console.log(`Selected ${this.selectedDeployHealth} HP token for deployment`);
                this.hideDeploymentUI();
                this.showDeploymentIndicator(this.selectedDeployHealth);
                if (this.onDeploySelect) {
                    this.onDeploySelect(this.selectedDeployHealth);
                }
            });
        });
    }

    showDeploymentIndicator(health) {
        const existing = document.getElementById("deployment-indicator");
        if (existing) existing.remove();

        const indicator = document.createElement("div");
        indicator.id = "deployment-indicator";
        indicator.className = "deployment-indicator";
        indicator.innerHTML = `
            <div class="deployment-indicator-subtitle">DEPLOY TOKEN</div>
            <div class="deployment-indicator-value">${health} HP</div>
            <div class="deployment-indicator-hint">Click a corner cell</div>
        `;

        document.body.appendChild(indicator);
    }

    hideDeploymentUI() {
        const existing = document.getElementById("deployment-menu");
        if (existing) existing.remove();
        this.deploymentMenuOpen = false;
    }

    hideDeploymentIndicator() {
        const existing = document.getElementById("deployment-indicator");
        if (existing) existing.remove();
        this.selectedDeployHealth = null;
    }

    isDeploymentMenuOpen() {
        return this.deploymentMenuOpen;
    }

    getSelectedDeployHealth() {
        return this.selectedDeployHealth;
    }

    clearSelection() {
        this.selectedDeployHealth = null;
        this.hideDeploymentIndicator();
    }

    // ==========================================================================
    // Connection Screen
    // ==========================================================================

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
}
