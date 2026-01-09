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
    }

    // ==========================================================================
    // Screen Management
    // ==========================================================================

    showScreen(screenName) {
        document.getElementById("connection-screen").style.display = "none";
        document.getElementById("lobby-browser-screen").style.display = "none";
        document.getElementById("waiting-room-screen").style.display = "none";
        this.canvas.style.display = "none";

        const hud = document.getElementById("hud");
        const controls = document.getElementById("controls");
        const connectionStatus = document.getElementById("connectionStatus");

        if (hud) hud.style.display = "none";
        if (controls) controls.style.display = "none";
        if (connectionStatus) connectionStatus.style.display = "none";

        switch (screenName) {
            case 'disconnected':
            case 'connecting':
                document.getElementById("connection-screen").style.display = "block";
                break;
            case 'connected':
                document.getElementById("lobby-browser-screen").style.display = "block";
                break;
            case 'lobby':
                document.getElementById("waiting-room-screen").style.display = "block";
                break;
            case 'game':
            case 'game_starting':
                document.getElementById("waiting-room-screen").style.display = "block";
                break;
            case 'in_game':
                this.canvas.style.display = "block";
                if (hud) hud.style.display = "block";
                if (controls) controls.style.display = "block";
                if (connectionStatus) connectionStatus.style.display = "block";
                break;
        }
    }

    showConnectionStatus(message) {
        const statusMsg = document.getElementById("connection-status-msg");
        if (statusMsg) {
            statusMsg.textContent = message;
            statusMsg.style.color = "#0ff";
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
        errorDiv.style.position = "fixed";
        errorDiv.style.top = "50%";
        errorDiv.style.left = "50%";
        errorDiv.style.transform = "translate(-50%, -50%)";
        errorDiv.style.backgroundColor = "rgba(255, 0, 0, 0.8)";
        errorDiv.style.color = "#fff";
        errorDiv.style.padding = "20px";
        errorDiv.style.borderRadius = "10px";
        errorDiv.style.fontFamily = "monospace";
        errorDiv.style.fontSize = "16px";
        errorDiv.style.zIndex = "9999";
        errorDiv.style.textAlign = "center";
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
            noGamesMsg.style.display = "block";
            return;
        }

        noGamesMsg.style.display = "none";

        games.forEach((game) => {
            const gameDiv = document.createElement("div");
            gameDiv.className = "game-item";

            const gameInfo = document.createElement("div");
            gameInfo.className = "game-info";
            gameInfo.innerHTML = `
                <strong>${game.game_name || game.name}</strong>
                <span>Players: ${game.num_players || 0}/${game.max_players || 4}</span>
                <span>Status: ${game.status || "waiting"}</span>
            `;

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
        document.getElementById("create-game-btn").addEventListener("click", () => {
            const gameName = prompt("Enter game name:", "My Game");
            if (gameName && gameName.trim()) {
                createGame(gameName.trim(), 4);
            }
        });

        document.getElementById("refresh-games-btn").addEventListener("click", () => {
            refreshGames();
        });

        document.getElementById("disconnect-btn").addEventListener("click", () => {
            disconnect();
        });
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
        this.renderLobbyPlayerList(lobby, isHost);

        const startBtn = document.getElementById("start-game-btn");
        startBtn.style.display = isHost ? "block" : "none";

        this.updateReadyButton(isReady);
    }

    renderLobbyPlayerList(lobby, isHost) {
        const container = document.getElementById("lobby-players");
        container.innerHTML = "<h3>Players:</h3>";

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
            let readyIndicator = "";

            if (player.is_ready) {
                readyIndicator = '<span style="color: #0f0; font-weight: bold;"> ✓ READY</span>';
            } else {
                readyIndicator = '<span style="color: #f80; font-weight: bold;"> ✗ NOT READY</span>';
            }

            playerDiv.innerHTML = `
                <span style="color: ${color};">${player.player_name}${hostLabel}${youLabel}</span>${readyIndicator}
            `;

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
        readyBtn.style.backgroundColor = isReady ? "#080" : "#000";
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
            startBtn.style.opacity = "1";
            startBtn.style.cursor = "pointer";
            startBtn.title = "All players ready - click to start!";
        } else {
            startBtn.disabled = true;
            startBtn.style.opacity = "0.5";
            startBtn.style.cursor = "not-allowed";
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

        if (gameState.current_turn_player_id !== null && gameState.players[gameState.current_turn_player_id]) {
            const currentPlayer = gameState.players[gameState.current_turn_player_id];
            document.getElementById("currentPlayer").textContent = currentPlayer.name || "Unknown";
        }

        const playersList = document.getElementById("playersList");
        playersList.innerHTML = "";

        for (const player of Object.values(gameState.players)) {
            const playerDiv = document.createElement("div");
            playerDiv.className = "player-info";
            const isLocal = player.id === localPlayerId ? " (YOU)" : "";
            playerDiv.innerHTML = `
                <strong>${player.name}${isLocal}</strong>
                <div>Tokens: ${player.token_ids.length}</div>
            `;
            playersList.appendChild(playerDiv);
        }
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
        menu.style.position = "fixed";
        menu.style.top = "50%";
        menu.style.left = "50%";
        menu.style.transform = "translate(-50%, -50%)";
        menu.style.backgroundColor = "#000080";
        menu.style.border = "2px solid #00FFFF";
        menu.style.padding = "20px";
        menu.style.zIndex = "1000";
        menu.style.fontFamily = "monospace";
        menu.style.color = "#00FFFF";
        menu.style.textAlign = "center";

        menu.innerHTML = `
            <div style="margin-bottom: 20px; font-size: 16px; font-weight: bold;">
                SELECT TOKEN TO DEPLOY
            </div>
            <div style="display: grid; grid-template-columns: 1fr; gap: 10px;">
                <button class="deploy-btn" data-health="10" style="padding: 10px; background: #000080; border: 1px solid #00FFFF; color: #00FFFF; cursor: pointer; font-size: 14px;">10 HP</button>
                <button class="deploy-btn" data-health="8" style="padding: 10px; background: #000080; border: 1px solid #00FFFF; color: #00FFFF; cursor: pointer; font-size: 14px;">8 HP</button>
                <button class="deploy-btn" data-health="6" style="padding: 10px; background: #000080; border: 1px solid #00FFFF; color: #00FFFF; cursor: pointer; font-size: 14px;">6 HP</button>
                <button class="deploy-btn" data-health="4" style="padding: 10px; background: #000080; border: 1px solid #00FFFF; color: #00FFFF; cursor: pointer; font-size: 14px;">4 HP</button>
            </div>
            <div style="margin-top: 20px; font-size: 12px;">
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
        indicator.style.position = "fixed";
        indicator.style.top = "50%";
        indicator.style.left = "50%";
        indicator.style.transform = "translate(-50%, -50%)";
        indicator.style.backgroundColor = "rgba(0, 128, 128, 0.9)";
        indicator.style.border = "2px solid #00FFFF";
        indicator.style.padding = "15px 30px";
        indicator.style.zIndex = "1000";
        indicator.style.fontFamily = "monospace";
        indicator.style.color = "#00FFFF";
        indicator.style.fontSize = "18px";
        indicator.style.fontWeight = "bold";
        indicator.style.textAlign = "center";
        indicator.style.pointerEvents = "none";
        indicator.innerHTML = `
            <div style="font-size: 14px; margin-bottom: 5px;">DEPLOY TOKEN</div>
            <div style="font-size: 24px;">${health} HP</div>
            <div style="font-size: 12px; margin-top: 10px;">Click a corner cell</div>
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
