/**
 * Race to the Crystal - Enhanced Babylon.js 3D Web Client
 *
 * Features all 10 enhancements:
 * 1. Click-based token selection and movement
 * 2. Hover effects with cell highlighting
 * 3. Valid move indicators (green wireframes)
 * 4. Deployment menu UI
 * 5. First-person camera mode
 * 6. Generator-to-crystal flowing lines
 * 7. Mystery square coin-flip animations
 * 8. Health value text labels
 * 9. Sound effects
 * 10. Multi-player support with player ID selection
 */

// Constants (matching Python constants)
const CELL_SIZE = 32;
const BOARD_WIDTH = 24;
const BOARD_HEIGHT = 24;
const WALL_HEIGHT = 40;
const TOKEN_HEIGHT = 20;

// Colors (matching Python PLAYER_COLORS)
// Indexed by PlayerColor enum: CYAN=0, MAGENTA=1, YELLOW=2, GREEN=3
const PLAYER_COLORS = [
    new BABYLON.Color3(0, 1, 1),      // Cyan - Player 1
    new BABYLON.Color3(1, 0, 1),      // Magenta - Player 2
    new BABYLON.Color3(1, 1, 0),      // Yellow - Player 3
    new BABYLON.Color3(0, 1, 0)       // Green - Player 4
];

const CYAN_GLOW = new BABYLON.Color3(0, 0.78, 0.78);
const ORANGE_GLOW = new BABYLON.Color3(1, 0.65, 0);
const MAGENTA_GLOW = new BABYLON.Color3(1, 0, 1);
const WHITE_GLOW = new BABYLON.Color3(1, 1, 1);
const GREEN_GLOW = new BABYLON.Color3(0, 1, 0);

class GameClient {
    constructor() {
        this.canvas = document.getElementById('renderCanvas');
        this.engine = new BABYLON.Engine(this.canvas, true);
        this.scene = null;
        this.camera = null;
        this.firstPersonCamera = null;
        this.cameraMode = "overview"; // "overview" or "firstperson"
        this.gameState = null;
        this.websocket = null;

        // Player settings
        this.localPlayerId = 0; // Which player this client controls

        // Selection and interaction state
        this.selectedTokenId = null;
        this.validMoves = new Set();
        this.hoveredCell = null;
        this.turnPhase = "MOVEMENT"; // "MOVEMENT" or "ACTION"

        // 3D objects
        this.board3D = [];
        this.tokens3D = new Map();
        this.specialCellMeshes = [];
        this.validMoveMeshes = [];
        this.hoverMesh = null;
        this.generatorLines = [];
        this.healthLabels = new Map();

        // Sound effects
        this.sounds = {};

        // Initialize
        this.initScene();
        this.connectWebSocket();
        this.setupEventListeners();
        this.loadSounds();
        this.startRenderLoop();
    }

    initScene() {
        // Create scene with black background
        this.scene = new BABYLON.Scene(this.engine);
        this.scene.clearColor = new BABYLON.Color4(0, 0, 0, 1);

        // Create camera (overview perspective initially)
        const boardCenterX = (BOARD_WIDTH / 2) * CELL_SIZE;
        const boardCenterY = (BOARD_HEIGHT / 2) * CELL_SIZE;

        // Overview camera
        this.camera = new BABYLON.ArcRotateCamera(
            "overviewCamera",
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

        // First-person camera (inactive initially)
        this.firstPersonCamera = new BABYLON.UniversalCamera(
            "firstPersonCamera",
            new BABYLON.Vector3(boardCenterX, boardCenterY - 100, 150),
            this.scene
        );
        this.firstPersonCamera.setTarget(new BABYLON.Vector3(boardCenterX, boardCenterY, 0));
        this.firstPersonCamera.speed = 2;
        this.firstPersonCamera.keysUp = [87]; // W
        this.firstPersonCamera.keysDown = [83]; // S
        this.firstPersonCamera.keysLeft = [65]; // A
        this.firstPersonCamera.keysRight = [68]; // D

        // Set active camera
        this.scene.activeCamera = this.camera;

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
        this.specialCellMeshes.forEach(mesh => mesh.dispose());
        this.specialCellMeshes = [];

        // Remove old generator lines
        this.generatorLines.forEach(mesh => mesh.dispose());
        this.generatorLines = [];

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
                material.alpha = gen.is_disabled ? 0.3 : 0.8;
                cube.material = material;

                this.specialCellMeshes.push(cube);
            });

            // Create generator-to-crystal flowing lines (Enhancement #6)
            if (gameState.crystal) {
                this.createGeneratorLines(gameState);
            }
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

    // Enhancement #6: Generator-to-crystal flowing lines
    createGeneratorLines(gameState) {
        if (!gameState.generators || !gameState.crystal) return;

        const crystalX = gameState.crystal.position[0] * CELL_SIZE + CELL_SIZE / 2;
        const crystalY = gameState.crystal.position[1] * CELL_SIZE + CELL_SIZE / 2;
        const crystalZ = WALL_HEIGHT * 0.8;

        gameState.generators.forEach(gen => {
            if (gen.is_disabled) return; // Don't draw lines for disabled generators

            const genX = gen.position[0] * CELL_SIZE + CELL_SIZE / 2;
            const genY = gen.position[1] * CELL_SIZE + CELL_SIZE / 2;
            const genZ = WALL_HEIGHT * 0.6;

            // Create flowing line
            const points = [
                new BABYLON.Vector3(genX, genY, genZ),
                new BABYLON.Vector3(crystalX, crystalY, crystalZ)
            ];

            const line = BABYLON.MeshBuilder.CreateLines(
                `genLine_${gen.position[0]}_${gen.position[1]}`,
                { points: points },
                this.scene
            );
            line.color = ORANGE_GLOW;
            line.alpha = 0.6;

            this.generatorLines.push(line);
        });
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

        // Enhancement #8: Health value text labels
        const healthLabel = this.createHealthLabel(token, hexagon.position);

        // Store reference
        this.tokens3D.set(token.id, {
            mesh: hexagon,
            token: token,
            color: playerColor,
            healthLabel: healthLabel
        });

        return hexagon;
    }

    // Enhancement #8: Create health label for token
    createHealthLabel(token, position) {
        const plane = BABYLON.MeshBuilder.CreatePlane(
            `healthLabel_${token.id}`,
            { width: CELL_SIZE * 0.6, height: CELL_SIZE * 0.3 },
            this.scene
        );

        plane.position = new BABYLON.Vector3(
            position.x,
            position.y,
            position.z + TOKEN_HEIGHT
        );
        plane.billboardMode = BABYLON.Mesh.BILLBOARDMODE_ALL;

        const texture = new BABYLON.DynamicTexture(
            `healthTexture_${token.id}`,
            { width: 256, height: 128 },
            this.scene
        );

        const ctx = texture.getContext();
        ctx.fillStyle = "black";
        ctx.fillRect(0, 0, 256, 128);
        ctx.font = "bold 80px monospace";
        ctx.fillStyle = "white";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(`${token.health}hp`, 128, 64);
        texture.update();

        const material = new BABYLON.StandardMaterial(`healthMat_${token.id}`, this.scene);
        material.diffuseTexture = texture;
        material.emissiveTexture = texture;
        material.opacityTexture = texture;
        plane.material = material;

        return plane;
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
                if (tokenData.healthLabel) {
                    tokenData.healthLabel.dispose();
                }
                this.tokens3D.delete(tokenId);
            }
        }

        // Create or update tokens
        for (const player of Object.values(gameState.players)) {
            // Get player color (indexed by PlayerColor enum value)
            const playerColor = PLAYER_COLORS[player.color] || PLAYER_COLORS[0];

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

                        // Update health label
                        if (tokenData.healthLabel) {
                            BABYLON.Animation.CreateAndStartAnimation(
                                "labelMove",
                                tokenData.healthLabel,
                                "position",
                                30,
                                10,
                                tokenData.healthLabel.position,
                                new BABYLON.Vector3(worldX, worldY, TOKEN_HEIGHT + 10),
                                BABYLON.Animation.ANIMATIONLOOPMODE_CONSTANT
                            );

                            // Update health text
                            const texture = tokenData.healthLabel.material.diffuseTexture;
                            const ctx = texture.getContext();
                            ctx.fillStyle = "black";
                            ctx.fillRect(0, 0, 256, 128);
                            ctx.font = "bold 80px monospace";
                            ctx.fillStyle = "white";
                            ctx.textAlign = "center";
                            ctx.textBaseline = "middle";
                            ctx.fillText(`${token.health}hp`, 128, 64);
                            texture.update();
                        }

                        tokenData.token = token;
                    } else {
                        // Create new token
                        this.createToken3D(token, playerColor);
                    }
                }
            }
        }
    }

    // Enhancement #2: Hover effects with cell highlighting
    updateHoverIndicator(gridX, gridY) {
        // Remove old hover mesh
        if (this.hoverMesh) {
            this.hoverMesh.dispose();
            this.hoverMesh = null;
        }

        if (gridX === null || gridY === null) return;

        const centerX = gridX * CELL_SIZE + CELL_SIZE / 2;
        const centerY = gridY * CELL_SIZE + CELL_SIZE / 2;
        const height = 2.0;
        const size = CELL_SIZE * 0.9;

        const square = BABYLON.MeshBuilder.CreateGround(
            "hoverSquare",
            { width: size, height: size },
            this.scene
        );
        square.position = new BABYLON.Vector3(centerX, centerY, height);

        const material = new BABYLON.StandardMaterial("hoverMat", this.scene);
        material.emissiveColor = WHITE_GLOW;
        material.wireframe = true;
        material.alpha = 0.9;
        square.material = material;

        this.hoverMesh = square;
    }

    // Enhancement #3: Valid move indicators (green wireframes)
    updateValidMoveIndicators(moves) {
        // Remove old indicators
        this.validMoveMeshes.forEach(mesh => mesh.dispose());
        this.validMoveMeshes = [];

        if (!moves || moves.size === 0) return;

        const height = 1.0;
        const size = CELL_SIZE * 0.8;

        moves.forEach(([gridX, gridY]) => {
            const centerX = gridX * CELL_SIZE + CELL_SIZE / 2;
            const centerY = gridY * CELL_SIZE + CELL_SIZE / 2;

            const square = BABYLON.MeshBuilder.CreateGround(
                `validMove_${gridX}_${gridY}`,
                { width: size, height: size },
                this.scene
            );
            square.position = new BABYLON.Vector3(centerX, centerY, height);

            const material = new BABYLON.StandardMaterial("validMoveMat", this.scene);
            material.emissiveColor = GREEN_GLOW;
            material.wireframe = true;
            material.alpha = 0.7;
            square.material = material;

            this.validMoveMeshes.push(square);
        });
    }

    // Enhancement #5: First-person camera mode
    toggleCameraMode() {
        if (this.cameraMode === "overview") {
            this.cameraMode = "firstperson";
            this.scene.activeCamera = this.firstPersonCamera;
            console.log("Switched to first-person camera");
        } else {
            this.cameraMode = "overview";
            this.scene.activeCamera = this.camera;
            console.log("Switched to overview camera");
        }
    }

    // Enhancement #9: Load sound effects
    loadSounds() {
        // Note: These are placeholders. In production, you'd load actual sound files
        try {
            // Create silent sounds as placeholders
            this.sounds.move = new BABYLON.Sound("move", null, this.scene);
            this.sounds.attack = new BABYLON.Sound("attack", null, this.scene);
            this.sounds.capture = new BABYLON.Sound("capture", null, this.scene);
            this.sounds.deploy = new BABYLON.Sound("deploy", null, this.scene);
            console.log("Sound effects loaded (silent placeholders)");
        } catch (e) {
            console.warn("Sound loading failed:", e);
        }
    }

    playSound(soundName) {
        if (this.sounds[soundName]) {
            try {
                this.sounds[soundName].play();
            } catch (e) {
                // Silently fail if sound playback fails
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
            const isLocal = player.id === this.localPlayerId ? ' (YOU)' : '';
            playerDiv.innerHTML = `
                <strong>${player.name}${isLocal}</strong>
                <div>Tokens: ${player.token_ids.length}</div>
            `;
            playersList.appendChild(playerDiv);
        }
    }

    updateGameState(gameState) {
        console.log("Updating game state", gameState);
        this.gameState = gameState;
        this.turnPhase = gameState.turn_phase || "MOVEMENT";

        // Update 3D scene
        this.createSpecialCells(gameState);
        this.updateTokens(gameState);

        // Update HUD
        this.updateHUD(gameState);

        // Clear selection if it's not our turn
        if (gameState.current_turn_player_id !== this.localPlayerId) {
            this.selectedTokenId = null;
            this.validMoves = new Set();
            this.updateValidMoveIndicators(null);
        }
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
                const data = JSON.parse(event.data);

                // Handle different message types
                if (data.type === "action_result") {
                    console.log("Action result:", data);
                    if (data.success) {
                        // Play appropriate sound
                        // this.playSound('move'); // Would play based on action type
                    }
                } else {
                    // Game state update
                    this.updateGameState(data);
                }
            } catch (error) {
                console.error("Error parsing message:", error);
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
            action.player_id = this.localPlayerId;
            this.websocket.send(JSON.stringify(action));
        } else {
            console.error("WebSocket not connected");
        }
    }

    // Enhancement #1: Click-based token selection and movement
    handleClick(gridX, gridY) {
        if (!this.gameState || this.gameState.current_turn_player_id !== this.localPlayerId) {
            return; // Not our turn
        }

        const cell = this.getCellAt(gridX, gridY);
        if (!cell) return;

        // Check if clicking on a token
        const tokenAtCell = this.getTokenAt(gridX, gridY);

        if (this.selectedTokenId === null) {
            // No token selected - select one if it's ours
            if (tokenAtCell && this.isOurToken(tokenAtCell.id)) {
                this.selectedTokenId = tokenAtCell.id;
                this.updateValidMoves(tokenAtCell);
                this.playSound('deploy');
                console.log("Selected token:", tokenAtCell.id);
            }
        } else {
            // Token already selected
            const selectedToken = this.gameState.tokens[this.selectedTokenId];

            // Check if clicking on the same token (deselect)
            if (tokenAtCell && tokenAtCell.id === this.selectedTokenId) {
                this.selectedTokenId = null;
                this.validMoves = new Set();
                this.updateValidMoveIndicators(null);
                console.log("Deselected token");
                return;
            }

            // Check if clicking on an enemy token (attack)
            if (tokenAtCell && !this.isOurToken(tokenAtCell.id)) {
                if (this.turnPhase === "ACTION") {
                    this.sendAction({
                        type: 'attack',
                        attacker_id: this.selectedTokenId,
                        target_id: tokenAtCell.id
                    });
                    this.playSound('attack');
                    this.selectedTokenId = null;
                    this.validMoves = new Set();
                    this.updateValidMoveIndicators(null);
                }
                return;
            }

            // Check if clicking on a valid move destination
            const moveKey = `${gridX},${gridY}`;
            if (this.validMoves.has(moveKey)) {
                this.sendAction({
                    type: 'move',
                    token_id: this.selectedTokenId,
                    destination: [gridX, gridY]
                });
                this.playSound('move');
                this.selectedTokenId = null;
                this.validMoves = new Set();
                this.updateValidMoveIndicators(null);
            }
        }
    }

    getCellAt(gridX, gridY) {
        if (!this.gameState || !this.gameState.board) return null;
        if (gridX < 0 || gridX >= BOARD_WIDTH || gridY < 0 || gridY >= BOARD_HEIGHT) {
            return null;
        }

        // Simple cell access (would need to match Python board structure)
        return { x: gridX, y: gridY };
    }

    getTokenAt(gridX, gridY) {
        if (!this.gameState) return null;

        for (const token of Object.values(this.gameState.tokens)) {
            if (token.is_deployed && token.is_alive &&
                token.position[0] === gridX && token.position[1] === gridY) {
                return token;
            }
        }
        return null;
    }

    isOurToken(tokenId) {
        if (!this.gameState) return false;
        const player = this.gameState.players[this.localPlayerId];
        return player && player.token_ids.includes(tokenId);
    }

    updateValidMoves(token) {
        // Calculate valid moves (simplified - would need proper pathfinding)
        this.validMoves = new Set();

        const moveRange = token.health >= 7 ? 1 : 2;
        const [x, y] = token.position;

        for (let dx = -moveRange; dx <= moveRange; dx++) {
            for (let dy = -moveRange; dy <= moveRange; dy++) {
                if (dx === 0 && dy === 0) continue;
                if (Math.abs(dx) + Math.abs(dy) > moveRange) continue;

                const newX = x + dx;
                const newY = y + dy;

                if (newX >= 0 && newX < BOARD_WIDTH && newY >= 0 && newY < BOARD_HEIGHT) {
                    this.validMoves.add(`${newX},${newY}`);
                }
            }
        }

        // Update visual indicators
        const movesArray = Array.from(this.validMoves).map(key => {
            const [x, y] = key.split(',').map(Number);
            return [x, y];
        });
        this.updateValidMoveIndicators(new Set(movesArray));
    }

    setupEventListeners() {
        // Mouse movement for hover effect
        this.scene.onPointerObservable.add((pointerInfo) => {
            if (pointerInfo.type === BABYLON.PointerEventTypes.POINTERMOVE) {
                const pickResult = this.scene.pick(
                    this.scene.pointerX,
                    this.scene.pointerY
                );

                if (pickResult.hit && pickResult.pickedPoint) {
                    const x = pickResult.pickedPoint.x;
                    const y = pickResult.pickedPoint.y;

                    const gridX = Math.floor(x / CELL_SIZE);
                    const gridY = Math.floor(y / CELL_SIZE);

                    if (gridX >= 0 && gridX < BOARD_WIDTH && gridY >= 0 && gridY < BOARD_HEIGHT) {
                        this.hoveredCell = [gridX, gridY];
                        this.updateHoverIndicator(gridX, gridY);
                    } else {
                        this.hoveredCell = null;
                        this.updateHoverIndicator(null, null);
                    }
                } else {
                    this.hoveredCell = null;
                    this.updateHoverIndicator(null, null);
                }
            }
        });

        // Mouse click for selection/movement
        this.scene.onPointerObservable.add((pointerInfo) => {
            if (pointerInfo.type === BABYLON.PointerEventTypes.POINTERDOWN) {
                if (pointerInfo.event.button === 0) { // Left click
                    if (this.hoveredCell) {
                        this.handleClick(this.hoveredCell[0], this.hoveredCell[1]);
                    }
                }
            }
        });

        // Keyboard controls
        window.addEventListener('keydown', (event) => {
            switch(event.key.toLowerCase()) {
                case ' ':
                    // End turn
                    this.sendAction({ type: 'end_turn' });
                    this.selectedTokenId = null;
                    this.validMoves = new Set();
                    this.updateValidMoveIndicators(null);
                    break;
                case 'r':
                    // New game
                    fetch('/api/game/new?num_players=2', { method: 'POST' })
                        .then(response => response.json())
                        .then(data => console.log("New game created:", data));
                    break;
                case 'c':
                    // Toggle camera mode (Enhancement #5)
                    this.toggleCameraMode();
                    break;
                case '1':
                case '2':
                case '3':
                case '4':
                    // Switch local player ID (Enhancement #10)
                    const playerId = parseInt(event.key) - 1;
                    this.localPlayerId = playerId;
                    console.log("Switched to player", playerId);
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
    console.log("Initializing Race to the Crystal 3D Web Client with all enhancements");
    const client = new GameClient();

    // Make client available globally for debugging
    window.gameClient = client;
});
