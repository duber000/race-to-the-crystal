/**
 * Race to the Crystal - Babylon.js 3D Web Client
 *
 * This client connects to the FastAPI backend via WebSocket and renders
 * the game in 3D using Babylon.js 8 with Tron/Battlezone-style wireframe graphics.
 */

// Constants (matching Python constants)
const CELL_SIZE = 32;
const BOARD_WIDTH = 24;
const BOARD_HEIGHT = 24;
const WALL_HEIGHT = 40;
const TOKEN_HEIGHT = 20;

// Colors (matching Python PLAYER_COLORS)
const PLAYER_COLORS = {
    RED: new BABYLON.Color3(1, 0, 0),
    BLUE: new BABYLON.Color3(0, 0, 1),
    GREEN: new BABYLON.Color3(0, 1, 0),
    YELLOW: new BABYLON.Color3(1, 1, 0)
};

const CYAN_GLOW = new BABYLON.Color3(0, 0.78, 0.78);
const ORANGE_GLOW = new BABYLON.Color3(1, 0.65, 0);
const MAGENTA_GLOW = new BABYLON.Color3(1, 0, 1);
const WHITE_GLOW = new BABYLON.Color3(1, 1, 1);

class GameClient {
    constructor() {
        this.canvas = document.getElementById('renderCanvas');
        this.engine = new BABYLON.Engine(this.canvas, true);
        this.scene = null;
        this.camera = null;
        this.gameState = null;
        this.websocket = null;
        this.selectedTokenId = null;
        this.validMoves = new Set();

        // 3D objects
        this.board3D = null;
        this.tokens3D = new Map();

        // Initialize
        this.initScene();
        this.connectWebSocket();
        this.setupEventListeners();
        this.startRenderLoop();
    }

    initScene() {
        // Create scene with black background
        this.scene = new BABYLON.Scene(this.engine);
        this.scene.clearColor = new BABYLON.Color4(0, 0, 0, 1);

        // Create camera (overview perspective initially)
        const boardCenterX = (BOARD_WIDTH / 2) * CELL_SIZE;
        const boardCenterY = (BOARD_HEIGHT / 2) * CELL_SIZE;

        this.camera = new BABYLON.ArcRotateCamera(
            "camera",
            -Math.PI / 2,  // Alpha (rotation around Y axis)
            Math.PI / 4,   // Beta (angle from vertical)
            800,           // Radius (distance from target)
            new BABYLON.Vector3(boardCenterX, boardCenterY, 0),
            this.scene
        );

        this.camera.attachControl(this.canvas, true);
        this.camera.lowerRadiusLimit = 200;
        this.camera.upperRadiusLimit = 1500;
        this.camera.wheelPrecision = 50;

        // Ambient light for visibility
        const ambientLight = new BABYLON.HemisphericLight(
            "ambientLight",
            new BABYLON.Vector3(0, 0, 1),
            this.scene
        );
        ambientLight.intensity = 0.3;

        // Create glow layer for wireframe glow effect
        this.glowLayer = new BABYLON.GlowLayer("glow", this.scene);
        this.glowLayer.intensity = 1.5;

        // Create board
        this.createBoard();

        console.log("Scene initialized");
    }

    createBoard() {
        // Create board mesh group
        const boardMeshes = [];

        // Create grid lines (vertical pillars and horizontal connectors)
        const gridMaterial = new BABYLON.StandardMaterial("gridMaterial", this.scene);
        gridMaterial.emissiveColor = CYAN_GLOW;
        gridMaterial.wireframe = true;
        gridMaterial.alpha = 0.7;

        // Vertical pillars at grid intersections
        for (let x = 0; x <= BOARD_WIDTH; x++) {
            for (let y = 0; y <= BOARD_HEIGHT; y++) {
                const worldX = x * CELL_SIZE;
                const worldY = y * CELL_SIZE;

                const line = BABYLON.MeshBuilder.CreateLines(
                    `gridLine_${x}_${y}`,
                    {
                        points: [
                            new BABYLON.Vector3(worldX, worldY, 0),
                            new BABYLON.Vector3(worldX, worldY, WALL_HEIGHT)
                        ]
                    },
                    this.scene
                );
                line.color = CYAN_GLOW;
                line.enableEdgesRendering();
                boardMeshes.push(line);
            }
        }

        // Horizontal lines at top connecting pillars (parallel to X axis)
        for (let y = 0; y <= BOARD_HEIGHT; y++) {
            for (let x = 0; x < BOARD_WIDTH; x++) {
                const worldY = y * CELL_SIZE;
                const x1 = x * CELL_SIZE;
                const x2 = (x + 1) * CELL_SIZE;

                const line = BABYLON.MeshBuilder.CreateLines(
                    `hLineX_${x}_${y}`,
                    {
                        points: [
                            new BABYLON.Vector3(x1, worldY, WALL_HEIGHT),
                            new BABYLON.Vector3(x2, worldY, WALL_HEIGHT)
                        ]
                    },
                    this.scene
                );
                line.color = CYAN_GLOW;
                boardMeshes.push(line);
            }
        }

        // Horizontal lines parallel to Y axis
        for (let x = 0; x <= BOARD_WIDTH; x++) {
            for (let y = 0; y < BOARD_HEIGHT; y++) {
                const worldX = x * CELL_SIZE;
                const y1 = y * CELL_SIZE;
                const y2 = (y + 1) * CELL_SIZE;

                const line = BABYLON.MeshBuilder.CreateLines(
                    `hLineY_${x}_${y}`,
                    {
                        points: [
                            new BABYLON.Vector3(worldX, y1, WALL_HEIGHT),
                            new BABYLON.Vector3(worldX, y2, WALL_HEIGHT)
                        ]
                    },
                    this.scene
                );
                line.color = CYAN_GLOW;
                boardMeshes.push(line);
            }
        }

        this.board3D = boardMeshes;
        console.log("Board created with", boardMeshes.length, "meshes");
    }

    createSpecialCells(gameState) {
        // Remove old special cell meshes
        if (this.specialCellMeshes) {
            this.specialCellMeshes.forEach(mesh => mesh.dispose());
        }
        this.specialCellMeshes = [];

        // Create generators (orange cubes)
        if (gameState.generators) {
            gameState.generators.forEach(gen => {
                const centerX = gen.position[0] * CELL_SIZE + CELL_SIZE / 2;
                const centerY = gen.position[1] * CELL_SIZE + CELL_SIZE / 2;

                const cube = BABYLON.MeshBuilder.CreateBox(
                    `generator_${gen.position[0]}_${gen.position[1]}`,
                    { size: CELL_SIZE * 0.6, height: WALL_HEIGHT * 0.6 },
                    this.scene
                );
                cube.position = new BABYLON.Vector3(centerX, centerY, WALL_HEIGHT * 0.3);

                const material = new BABYLON.StandardMaterial("generatorMat", this.scene);
                material.emissiveColor = ORANGE_GLOW;
                material.wireframe = true;
                material.alpha = 0.8;
                cube.material = material;

                this.specialCellMeshes.push(cube);
            });
        }

        // Create crystal (magenta diamond/pyramid)
        if (gameState.crystal) {
            const centerX = gameState.crystal.position[0] * CELL_SIZE + CELL_SIZE / 2;
            const centerY = gameState.crystal.position[1] * CELL_SIZE + CELL_SIZE / 2;

            const pyramid = BABYLON.MeshBuilder.CreateCylinder(
                "crystal",
                {
                    diameterTop: 0,
                    diameterBottom: CELL_SIZE,
                    height: WALL_HEIGHT * 0.8,
                    tessellation: 4
                },
                this.scene
            );
            pyramid.position = new BABYLON.Vector3(centerX, centerY, WALL_HEIGHT * 0.4);

            const material = new BABYLON.StandardMaterial("crystalMat", this.scene);
            material.emissiveColor = MAGENTA_GLOW;
            material.wireframe = true;
            material.alpha = 0.9;
            pyramid.material = material;

            this.specialCellMeshes.push(pyramid);
        }
    }

    createToken3D(token, playerColor) {
        // Create hexagonal prism token
        const worldX = token.position[0] * CELL_SIZE + CELL_SIZE / 2;
        const worldY = token.position[1] * CELL_SIZE + CELL_SIZE / 2;

        // Create hexagonal prism
        const hexagon = BABYLON.MeshBuilder.CreateCylinder(
            `token_${token.id}`,
            {
                diameter: CELL_SIZE * 0.9,
                height: TOKEN_HEIGHT,
                tessellation: 6
            },
            this.scene
        );
        hexagon.position = new BABYLON.Vector3(worldX, worldY, TOKEN_HEIGHT / 2);

        // Apply player color material
        const material = new BABYLON.StandardMaterial(`tokenMat_${token.id}`, this.scene);
        material.emissiveColor = playerColor;
        material.wireframe = true;
        material.alpha = 0.9;
        hexagon.material = material;

        // Store reference
        this.tokens3D.set(token.id, {
            mesh: hexagon,
            token: token,
            color: playerColor
        });

        return hexagon;
    }

    updateTokens(gameState) {
        // Remove tokens that no longer exist
        const existingTokenIds = new Set();
        for (const player of Object.values(gameState.players)) {
            for (const tokenId of player.token_ids) {
                const token = gameState.tokens[tokenId];
                if (token && token.is_alive && token.is_deployed) {
                    existingTokenIds.add(tokenId);
                }
            }
        }

        // Remove dead/undeployed tokens
        for (const [tokenId, tokenData] of this.tokens3D) {
            if (!existingTokenIds.has(tokenId)) {
                tokenData.mesh.dispose();
                this.tokens3D.delete(tokenId);
            }
        }

        // Create or update tokens
        for (const player of Object.values(gameState.players)) {
            // Get player color
            const colorKey = Object.keys(PLAYER_COLORS)[player.color];
            const playerColor = PLAYER_COLORS[colorKey] || PLAYER_COLORS.RED;

            for (const tokenId of player.token_ids) {
                const token = gameState.tokens[tokenId];
                if (token && token.is_alive && token.is_deployed) {
                    if (this.tokens3D.has(tokenId)) {
                        // Update existing token position
                        const tokenData = this.tokens3D.get(tokenId);
                        const worldX = token.position[0] * CELL_SIZE + CELL_SIZE / 2;
                        const worldY = token.position[1] * CELL_SIZE + CELL_SIZE / 2;

                        // Animate movement
                        BABYLON.Animation.CreateAndStartAnimation(
                            "tokenMove",
                            tokenData.mesh,
                            "position",
                            30,
                            10,
                            tokenData.mesh.position,
                            new BABYLON.Vector3(worldX, worldY, TOKEN_HEIGHT / 2),
                            BABYLON.Animation.ANIMATIONLOOPMODE_CONSTANT
                        );

                        tokenData.token = token;
                    } else {
                        // Create new token
                        this.createToken3D(token, playerColor);
                    }
                }
            }
        }
    }

    updateHUD(gameState) {
        // Update turn info
        document.getElementById('turnNumber').textContent = gameState.turn_number || 0;
        document.getElementById('gamePhase').textContent = gameState.phase || 'SETUP';

        // Update current player
        if (gameState.current_turn_player_id !== null && gameState.players[gameState.current_turn_player_id]) {
            const currentPlayer = gameState.players[gameState.current_turn_player_id];
            document.getElementById('currentPlayer').textContent = currentPlayer.name || 'Unknown';
        }

        // Update players list
        const playersList = document.getElementById('playersList');
        playersList.innerHTML = '';
        for (const player of Object.values(gameState.players)) {
            const playerDiv = document.createElement('div');
            playerDiv.className = 'player-info';
            playerDiv.innerHTML = `
                <strong>${player.name}</strong>
                <div>Tokens: ${player.token_ids.length}</div>
            `;
            playersList.appendChild(playerDiv);
        }
    }

    updateGameState(gameState) {
        console.log("Updating game state", gameState);
        this.gameState = gameState;

        // Update 3D scene
        this.createSpecialCells(gameState);
        this.updateTokens(gameState);

        // Update HUD
        this.updateHUD(gameState);
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/game`;

        console.log("Connecting to WebSocket:", wsUrl);
        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
            console.log("WebSocket connected");
            document.getElementById('connectionStatus').textContent = 'Connected';
            document.getElementById('connectionStatus').classList.remove('disconnected');
        };

        this.websocket.onmessage = (event) => {
            try {
                const gameState = JSON.parse(event.data);
                this.updateGameState(gameState);
            } catch (error) {
                console.error("Error parsing game state:", error);
            }
        };

        this.websocket.onerror = (error) => {
            console.error("WebSocket error:", error);
            document.getElementById('connectionStatus').textContent = 'Error';
            document.getElementById('connectionStatus').classList.add('disconnected');
        };

        this.websocket.onclose = () => {
            console.log("WebSocket disconnected");
            document.getElementById('connectionStatus').textContent = 'Disconnected';
            document.getElementById('connectionStatus').classList.add('disconnected');

            // Attempt to reconnect after 3 seconds
            setTimeout(() => this.connectWebSocket(), 3000);
        };
    }

    sendAction(action) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify(action));
        } else {
            console.error("WebSocket not connected");
        }
    }

    setupEventListeners() {
        // Keyboard controls
        window.addEventListener('keydown', (event) => {
            switch(event.key.toLowerCase()) {
                case ' ':
                    // End turn
                    this.sendAction({
                        type: 'end_turn',
                        player_id: this.gameState?.current_turn_player_id || 0
                    });
                    break;
                case 'r':
                    // New game
                    fetch('/api/game/new?num_players=2', { method: 'POST' })
                        .then(response => response.json())
                        .then(data => console.log("New game created:", data));
                    break;
            }
        });

        // Handle window resize
        window.addEventListener('resize', () => {
            this.engine.resize();
        });
    }

    startRenderLoop() {
        this.engine.runRenderLoop(() => {
            if (this.scene) {
                this.scene.render();
            }
        });
    }
}

// Initialize game client when page loads
window.addEventListener('DOMContentLoaded', () => {
    console.log("Initializing Race to the Crystal 3D Web Client");
    const client = new GameClient();
});
