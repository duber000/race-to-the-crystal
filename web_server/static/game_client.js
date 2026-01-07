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
        this.localPlayerId = "player_0"; // Which player this client controls

        // Selection and interaction state
        this.selectedTokenId = null;
        this.validMoves = new Set();
        this.hoveredCell = null;
        this.turnPhase = "MOVEMENT"; // "MOVEMENT" or "ACTION"

        // 3D camera control state
        this.controlledTokenId = null; // Token camera follows in 3D mode
        this.tokenRotation = 0; // Camera rotation around token (in degrees)
        this.cameraPitch = -15; // Camera pitch angle
        this.mouseLookActive = false;
        this.lastMousePosition = { x: 0, y: 0 };
        this.isPanning = false; // Right-click drag panning state
        this.lastPanPosition = { x: 0, y: 0 };

        // Deployment menu state
        this.deploymentMenuOpen = false;
        this.selectedDeployHealth = null;

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
        this.musicPlaying = true;

        // Initialize
        this.initScene();
        this.connectWebSocket();
        this.setupEventListeners();
        this.loadSounds();
        this.startRenderLoop();
    }

    initScene() {
        console.log("Initializing scene...");
        // Create scene with black background
        this.scene = new BABYLON.Scene(this.engine);
        this.scene.clearColor = new BABYLON.Color4(0, 0, 0, 1);

        // Create camera (overview perspective initially)
        const boardCenterX = (BOARD_WIDTH / 2) * CELL_SIZE;
        const boardCenterY = (BOARD_HEIGHT / 2) * CELL_SIZE;

        // Overview camera (looking down at board from above)
        // In Babylon.js: X and Z are horizontal, Y is vertical (up)
        // Board is in XZ plane at Y=0, camera positioned above looking down
        this.camera = new BABYLON.ArcRotateCamera(
            "overviewCamera",
            Math.PI / 4,      // Alpha (rotation around Y axis, 45 degrees for diagonal view)
            Math.PI / 3,      // Beta (angle from vertical, ~60 degrees for overhead view)
            500,              // Radius (distance from target)
            new BABYLON.Vector3(boardCenterX, 0, boardCenterY),  // Look at board center at ground level (Y=0)
            this.scene
        );
        this.camera.attachControl(this.canvas, true);
        this.camera.lowerRadiusLimit = 300;
        this.camera.upperRadiusLimit = 1500;
        this.camera.wheelPrecision = 5; // Very fast zoom (10x faster)
        // Lock camera rotation to keep board stationary (prevent spinning)
        this.camera.lowerAlphaLimit = 0;
        this.camera.upperAlphaLimit = 0;
        this.camera.lowerBetaLimit = Math.PI / 3;
        this.camera.upperBetaLimit = Math.PI / 3;

        // First-person camera (inactive initially, token-locked)
        this.firstPersonCamera = new BABYLON.UniversalCamera(
            "firstPersonCamera",
            // In Babylon.js: Y is up, so (x, y, z) means (horizontal, vertical, horizontal)
            new BABYLON.Vector3(boardCenterX, boardCenterY + 150, boardCenterX - 100),
            this.scene
        );
        this.firstPersonCamera.setTarget(new BABYLON.Vector3(boardCenterX, 0, boardCenterY));
        // Disable keyboard controls (camera is token-locked)
        this.firstPersonCamera.keysUp = [];
        this.firstPersonCamera.keysDown = [];
        this.firstPersonCamera.keysLeft = [];
        this.firstPersonCamera.keysRight = [];
        this.firstPersonCamera.angularSensibility = 2000; // Mouse look sensitivity

        // Set active camera
        this.scene.activeCamera = this.camera;

        // Ambient light for visibility
        const ambientLight = new BABYLON.HemisphericLight(
            "ambientLight",
            new BABYLON.Vector3(0, 1, 0),  // Pointing up (Y is vertical in Babylon.js)
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
                const worldZ = y * CELL_SIZE;  // Use Z for horizontal Y (depth)

                // In Babylon.js: X and Z are horizontal, Y is vertical (up)
                // Swap Python's (x, y, z) to Babylon's (x, z, y)
                const line = BABYLON.MeshBuilder.CreateLines(
                    `gridLine_${x}_${y}`,
                    {
                        points: [
                            new BABYLON.Vector3(worldX, 0, worldZ),           // Bottom (Y=0)
                            new BABYLON.Vector3(worldX, WALL_HEIGHT, worldZ)  // Top (Y=height)
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
                const worldZ = y * CELL_SIZE;
                const x1 = x * CELL_SIZE;
                const x2 = (x + 1) * CELL_SIZE;

                const line = BABYLON.MeshBuilder.CreateLines(
                    `hLineX_${x}_${y}`,
                    {
                        points: [
                            new BABYLON.Vector3(x1, WALL_HEIGHT, worldZ),
                            new BABYLON.Vector3(x2, WALL_HEIGHT, worldZ)
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
                const z1 = y * CELL_SIZE;
                const z2 = (y + 1) * CELL_SIZE;

                const line = BABYLON.MeshBuilder.CreateLines(
                    `hLineY_${x}_${y}`,
                    {
                        points: [
                            new BABYLON.Vector3(worldX, WALL_HEIGHT, z1),
                            new BABYLON.Vector3(worldX, WALL_HEIGHT, z2)
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
                 const centerZ = gen.position[1] * CELL_SIZE + CELL_SIZE / 2;

                 const cube = BABYLON.MeshBuilder.CreateBox(
                     `generator_${gen.position[0]}_${gen.position[1]}`,
                     { size: CELL_SIZE * 0.6, height: WALL_HEIGHT * 0.6 },
                     this.scene
                 );
                 // In Babylon.js: Y is up, so position is (x, y, z)
                 cube.position = new BABYLON.Vector3(centerX, WALL_HEIGHT * 0.3, centerZ);

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
             const centerZ = gameState.crystal.position[1] * CELL_SIZE + CELL_SIZE / 2;

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
             // In Babylon.js: Y is up, so position is (x, y, z)
             pyramid.position = new BABYLON.Vector3(centerX, WALL_HEIGHT * 0.4, centerZ);

             const material = new BABYLON.StandardMaterial("crystalMat", this.scene);
             material.emissiveColor = MAGENTA_GLOW;
             material.wireframe = true;
             material.alpha = 0.9;
             pyramid.material = material;

             this.specialCellMeshes.push(pyramid);
         }

         // Create mystery squares (cyan rings)
         // Cell types: NORMAL=1, GENERATOR=2, CRYSTAL=3, MYSTERY=4, START=5
         if (gameState.board && gameState.board.grid) {
             for (let y = 0; y < gameState.board.grid.length; y++) {
                 for (let x = 0; x < gameState.board.grid[y].length; x++) {
                     const cell = gameState.board.grid[y][x];
                     if (cell.cell_type === 4) {  // MYSTERY = 4
                         const centerX = x * CELL_SIZE + CELL_SIZE / 2;
                         const centerZ = y * CELL_SIZE + CELL_SIZE / 2;

                         // Create a wireframe torus to represent mystery square
                         const ring = BABYLON.MeshBuilder.CreateTorus(
                             `mystery_${x}_${y}`,
                             {
                                 diameter: CELL_SIZE * 0.7,
                                 thickness: 3,
                                 tessellation: 16
                             },
                             this.scene
                         );
                         // In Babylon.js: Y is up, so position is (x, y, z)
                         ring.position = new BABYLON.Vector3(centerX, WALL_HEIGHT * 0.5, centerZ);
                         // Rotate to lay flat on ground (rotate around X axis)
                         ring.rotation.z = Math.PI / 2;

                         const material = new BABYLON.StandardMaterial("mysteryMat", this.scene);
                         material.emissiveColor = CYAN_GLOW;
                         material.wireframe = true;
                         material.alpha = 0.6;
                         ring.material = material;

                         this.glowLayer.addIncludedOnlyMesh(ring);
                         this.specialCellMeshes.push(ring);
                     }
                 }
             }
         }
     }

     // Enhancement #6: Generator-to-crystal flowing lines
    createGeneratorLines(gameState) {
        if (!gameState.generators || !gameState.crystal) return;

        const crystalX = gameState.crystal.position[0] * CELL_SIZE + CELL_SIZE / 2;
        const crystalZ = gameState.crystal.position[1] * CELL_SIZE + CELL_SIZE / 2;
        const crystalY = WALL_HEIGHT * 0.8;

        gameState.generators.forEach(gen => {
            if (gen.is_disabled) return; // Don't draw lines for disabled generators

            const genX = gen.position[0] * CELL_SIZE + CELL_SIZE / 2;
            const genZ = gen.position[1] * CELL_SIZE + CELL_SIZE / 2;
            const genY = WALL_HEIGHT * 0.6;

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
        const worldZ = token.position[1] * CELL_SIZE + CELL_SIZE / 2;

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
        // In Babylon.js: Y is up, so position is (x, y, z)
        hexagon.position = new BABYLON.Vector3(worldX, TOKEN_HEIGHT / 2, worldZ);

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
                        const worldZ = token.position[1] * CELL_SIZE + CELL_SIZE / 2;

                        // Animate movement
                        BABYLON.Animation.CreateAndStartAnimation(
                            "tokenMove",
                            tokenData.mesh,
                            "position",
                            30,
                            10,
                            tokenData.mesh.position,
                            new BABYLON.Vector3(worldX, TOKEN_HEIGHT / 2, worldZ),
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
                                new BABYLON.Vector3(worldX, TOKEN_HEIGHT + 10, worldZ),
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
        const centerZ = gridY * CELL_SIZE + CELL_SIZE / 2;
        const height = 2.0;
        const size = CELL_SIZE * 0.9;

        const square = BABYLON.MeshBuilder.CreateGround(
            "hoverSquare",
            { width: size, height: size },
            this.scene
        );
        // In Babylon.js: Y is up, so position is (x, y, z)
        square.position = new BABYLON.Vector3(centerX, height, centerZ);

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
            const centerZ = gridY * CELL_SIZE + CELL_SIZE / 2;

            const square = BABYLON.MeshBuilder.CreateGround(
                `validMove_${gridX}_${gridY}`,
                { width: size, height: size },
                this.scene
            );
            // In Babylon.js: Y is up, so position is (x, y, z)
            square.position = new BABYLON.Vector3(centerX, height, centerZ);

            const material = new BABYLON.StandardMaterial("validMoveMat", this.scene);
            material.emissiveColor = GREEN_GLOW;
            material.wireframe = true;
            material.alpha = 0.7;
            square.material = material;

            this.validMoveMeshes.push(square);
        });
    }

    // Enhancement #5: First-person camera mode (token-locked)
    toggleCameraMode() {
        if (this.cameraMode === "overview") {
            // Switch to first-person
            this.cameraMode = "firstperson";
            this.camera.detachControl(this.canvas);
            this.scene.activeCamera = this.firstPersonCamera;

            // Attach control but disable all default inputs (we handle everything manually)
            this.firstPersonCamera.attachControl(this.canvas, true);

            // Remove all default input handlers (keyboard/mouse)
            if (this.firstPersonCamera.inputs) {
                this.firstPersonCamera.inputs.clear();
                console.log("  ✓ Cleared camera default inputs");
            } else {
                console.log("  ✗ Warning: camera.inputs not available");
            }

            // Ensure canvas has focus for keyboard input
            this.canvas.focus();
            this.canvas.setAttribute('tabindex', '1');

            // Auto-select first token when entering first-person mode
            if (this.controlledTokenId === null || this.controlledTokenId === undefined) {
                this.cycleControlledToken();
            } else {
                // Update camera immediately
                this.updateFirstPersonCamera();
            }

            console.log("==============================================");
            console.log("✓ FIRST-PERSON MODE (Token-Locked Camera)");
            console.log("  TAB - Cycle through your tokens");
            console.log("  Q/E - Rotate camera left/right");
            console.log("  Right-click + drag - Mouse look");
            console.log("==============================================");
        } else {
            // Switch to overview
            this.cameraMode = "overview";
            this.firstPersonCamera.detachControl(this.canvas);
            this.scene.activeCamera = this.camera;
            this.camera.attachControl(this.canvas, true);

            // Ensure canvas has focus
            this.canvas.focus();

            console.log("==============================================");
            console.log("✓ OVERVIEW MODE (Bird's Eye View)");
            console.log("  Right-click + drag - Pan around board");
            console.log("  Scroll - Zoom in/out");
            console.log("==============================================");
        }
    }

    // Cycle to next controlled token (TAB key)
    cycleControlledToken() {
        console.log("TAB pressed - Cycling to next token (mode:", this.cameraMode, ")");

        if (!this.gameState) {
            console.log("  ✗ No game state");
            return;
        }

        const player = this.gameState.players[this.localPlayerId];
        if (!player) {
            console.log("  ✗ No player found for", this.localPlayerId);
            console.log("    Available players:", Object.keys(this.gameState.players));
            return;
        }

        // Get all alive deployed tokens for the player
        const aliveTokens = player.token_ids
            .map(id => this.gameState.tokens[id])
            .filter(token => token && token.is_alive && token.is_deployed)
            .map(token => token.id);
        
        console.log("  Player token IDs:", player.token_ids.length, "→", aliveTokens.length, "alive/deployed");

        if (aliveTokens.length === 0) {
            console.log("  ✗ No alive tokens to control");
            return;
        }

        // Find next token
        let nextIndex = 0;
        if (this.controlledTokenId !== null && this.controlledTokenId !== undefined && aliveTokens.includes(this.controlledTokenId)) {
            const currentIndex = aliveTokens.indexOf(this.controlledTokenId);
            nextIndex = (currentIndex + 1) % aliveTokens.length;
        }

        this.controlledTokenId = aliveTokens[nextIndex];
        this.cameraPitch = -15; // Reset pitch when switching tokens

        const token = this.gameState.tokens[this.controlledTokenId];
        if (token) {
            console.log(`  ✓ Now following token ${this.controlledTokenId} at (${token.position[0]}, ${token.position[1]})`);
            this.updateFirstPersonCamera();
        }
    }

    // Rotate camera left (Q key)
    rotateCameraLeft() {
        console.log("Q pressed - Rotating left (mode:", this.cameraMode, ")");
        if (this.cameraMode !== "firstperson") {
            console.log("  ✗ Not in first-person mode, ignoring");
            return;
        }
        const oldRot = this.tokenRotation;
        this.tokenRotation -= 15; // 15 degree increments
        console.log("  ✓ Rotation:", oldRot, "→", this.tokenRotation);
        console.log("  Camera before:", this.firstPersonCamera.rotation.y);
        this.updateFirstPersonCamera();
        console.log("  Camera after:", this.firstPersonCamera.rotation.y);
    }

    // Rotate camera right (E key)
    rotateCameraRight() {
        console.log("E pressed - Rotating right (mode:", this.cameraMode, ")");
        if (this.cameraMode !== "firstperson") {
            console.log("  ✗ Not in first-person mode, ignoring");
            return;
        }
        const oldRot = this.tokenRotation;
        this.tokenRotation += 15; // 15 degree increments
        console.log("  ✓ Rotation:", oldRot, "→", this.tokenRotation);
        console.log("  Camera before:", this.firstPersonCamera.rotation.y);
        this.updateFirstPersonCamera();
        console.log("  Camera after:", this.firstPersonCamera.rotation.y);
    }

    // Update first-person camera to follow controlled token
    updateFirstPersonCamera() {
        if (this.cameraMode !== "firstperson") {
            console.log("❌ Not in firstperson mode, returning");
            return;
        }
        if (this.controlledTokenId === null || this.controlledTokenId === undefined) {
            console.log("❌ No controlled token ID, returning");
            return;
        }
        if (!this.gameState) {
            console.log("❌ No game state, returning");
            return;
        }

        const token = this.gameState.tokens[this.controlledTokenId];
        if (!token) {
            console.log("❌ Token not found:", this.controlledTokenId);
            return;
        }
        if (!token.is_alive) {
            console.log("❌ Token dead:", this.controlledTokenId);
            return;
        }

        // Token position in world coordinates
        const tokenX = token.position[0] * CELL_SIZE + CELL_SIZE / 2;
        const tokenZ = token.position[1] * CELL_SIZE + CELL_SIZE / 2;
        const tokenY = TOKEN_HEIGHT / 2;

        // Camera offset from token (behind and above)
        const offset = 100; // Distance behind token
        const height = 30; // Height above token

        // Convert rotation to radians (note: tokenRotation is in degrees)
        const yawRad = (this.tokenRotation * Math.PI) / 180;
        const pitchRad = (this.cameraPitch * Math.PI) / 180;

        // Calculate camera position (behind and above token)
        // In Babylon.js: Forward is -Z, so we adjust the offsets
        const camX = tokenX + Math.sin(yawRad) * offset * Math.cos(pitchRad);
        const camZ = tokenZ + Math.cos(yawRad) * offset * Math.cos(pitchRad);
        const camY = tokenY + height + Math.sin(pitchRad) * offset;

        // Update camera position
        this.firstPersonCamera.position.x = camX;
        this.firstPersonCamera.position.y = camY;
        this.firstPersonCamera.position.z = camZ;

        // Point camera at token (more reliable than manual rotation)
        this.firstPersonCamera.setTarget(new BABYLON.Vector3(tokenX, tokenY + 10, tokenZ));

        // Debug output (only occasionally to avoid spam)
        if (Math.random() < 0.01) { // 1% of the time
            console.log("Camera update:", {
                tokenPos: [token.position[0], token.position[1]],
                yawDeg: this.tokenRotation,
                pitchDeg: this.cameraPitch,
                camPos: [camX.toFixed(1), camY.toFixed(1), camZ.toFixed(1)],
                camRot: [(this.firstPersonCamera.rotation.x * 180 / Math.PI).toFixed(1),
                         (this.firstPersonCamera.rotation.y * 180 / Math.PI).toFixed(1)]
            });
        }
    }

    // Activate mouse-look (right-click)
    activateMouseLook(x, y) {
        if (this.cameraMode !== "firstperson") return;
        this.mouseLookActive = true;
        this.lastMousePosition = { x, y };
        this.canvas.style.cursor = 'none';
        console.log("Mouse-look activated (right-click + drag to look around)");
    }

    // Deactivate mouse-look (release right-click)
    deactivateMouseLook() {
        this.mouseLookActive = false;
        this.canvas.style.cursor = 'default';
        console.log("Mouse-look deactivated");
    }

    // Handle right-click drag panning in overview mode
    handlePan(dx, dy) {
        if (this.cameraMode !== "overview") return;

        const panSpeed = 0.5; // Adjust pan speed

        // Get camera right and forward vectors (ignoring Y component)
        const right = this.camera.getDirection(BABYLON.Vector3.Right());
        right.y = 0;
        right.normalize();

        const forward = this.camera.getDirection(BABYLON.Vector3.Forward());
        forward.y = 0;
        forward.normalize();

        // Move camera target based on mouse movement
        // dx moves left/right, dy moves up/down on screen
        this.camera.target.addInPlace(right.scale(-dx * panSpeed));
        this.camera.target.addInPlace(forward.scale(dy * panSpeed));
    }

    // Handle mouse motion for mouse-look
    handleMouseMotion(dx, dy) {
        if (!this.mouseLookActive || this.cameraMode !== "firstperson") {
            return false;
        }

        // Update rotation based on mouse movement
        const sensitivity = 0.3;
        this.tokenRotation += dx * sensitivity;
        this.cameraPitch -= dy * sensitivity;

        // Clamp pitch to prevent flipping
        this.cameraPitch = Math.max(-89, Math.min(89, this.cameraPitch));

        this.updateFirstPersonCamera();
        return true;
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
        console.log("==================================================");
        console.log("✓ Updating game state");
        console.log("  - Current turn:", gameState.current_turn_player_id);
        console.log("  - Your player:", this.localPlayerId);
        console.log("  - Generators:", gameState.generators?.length || 0);
        console.log("  - Crystal:", gameState.crystal ? 'YES' : 'NO');
        console.log("  - Tokens:", Object.keys(gameState.tokens || {}).length);
        console.log("  - Players:", Object.keys(gameState.players || {}).length);
        console.log("==================================================");

        this.gameState = gameState;
        this.turnPhase = gameState.turn_phase || "MOVEMENT";

        // Update 3D scene
        console.log("Creating special cells (generators & crystal)...");
        this.createSpecialCells(gameState);
        console.log("Creating/updating tokens...");
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
        const port = window.location.port || '8888';
        const wsUrl = `${protocol}//${window.location.hostname}:${port}/ws`;

        console.log("==================================================");
        console.log("Connecting to WebSocket:", wsUrl);
        console.log("==================================================");
        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
            console.log("✓ WebSocket connected successfully");
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
            console.log("Sending action:", action.type, "for", action.player_id);
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
        // Mouse movement for hover effect and mouse-look
        this.scene.onPointerObservable.add((pointerInfo) => {
            if (pointerInfo.type === BABYLON.PointerEventTypes.POINTERMOVE) {
                // Handle mouse-look if active
                if (this.mouseLookActive) {
                    const dx = pointerInfo.event.movementX || 0;
                    const dy = pointerInfo.event.movementY || 0;
                    this.handleMouseMotion(dx, dy);
                }

                // Update hover indicator (skip if mouse-look active)
                if (!this.mouseLookActive) {
                    const pickResult = this.scene.pick(
                        this.scene.pointerX,
                        this.scene.pointerY
                    );

                    if (pickResult.hit && pickResult.pickedPoint) {
                        const x = pickResult.pickedPoint.x;
                        const z = pickResult.pickedPoint.z;  // In Babylon.js: z is the horizontal depth coordinate

                        const gridX = Math.floor(x / CELL_SIZE);
                        const gridY = Math.floor(z / CELL_SIZE);  // Use z instead of y

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
            }
        });

        // Mouse click for selection/movement
        this.scene.onPointerObservable.add((pointerInfo) => {
            if (pointerInfo.type === BABYLON.PointerEventTypes.POINTERDOWN) {
                if (pointerInfo.event.button === 0) { // Left click
                    if (this.hoveredCell) {
                        this.handleClick(this.hoveredCell[0], this.hoveredCell[1]);
                    }
                } else if (pointerInfo.event.button === 2) { // Right click
                    // In overview mode: start panning
                    if (this.cameraMode === "overview") {
                        this.isPanning = true;
                        this.lastPanPosition = { x: pointerInfo.event.clientX, y: pointerInfo.event.clientY };
                        this.canvas.style.cursor = 'grabbing';
                    } else {
                        // In first-person mode: activate mouse-look
                        this.activateMouseLook(pointerInfo.event.clientX, pointerInfo.event.clientY);
                    }
                }
            } else if (pointerInfo.type === BABYLON.PointerEventTypes.POINTERUP) {
                if (pointerInfo.event.button === 2) { // Right click release
                    if (this.cameraMode === "overview") {
                        // Stop panning
                        this.isPanning = false;
                        this.canvas.style.cursor = 'default';
                    } else {
                        // Deactivate mouse-look
                        this.deactivateMouseLook();
                    }
                }
            } else if (pointerInfo.type === BABYLON.PointerEventTypes.POINTERMOVE) {
                // Handle panning in overview mode
                if (this.isPanning && this.cameraMode === "overview") {
                    const dx = pointerInfo.event.movementX || 0;
                    const dy = pointerInfo.event.movementY || 0;
                    this.handlePan(dx, dy);
                }
            }
        });

        // Keyboard controls
        window.addEventListener('keydown', (event) => {
            const key = event.key.toLowerCase();
            console.log("Key pressed:", event.key, "->", key, "| Camera mode:", this.cameraMode);

            switch(key) {
                case ' ':
                    // End turn
                    event.preventDefault();
                    this.sendAction({ type: 'end_turn' });
                    this.selectedTokenId = null;
                    this.validMoves = new Set();
                    this.updateValidMoveIndicators(null);
                    break;
                case 'enter':
                    // End turn (alternative to Space)
                    event.preventDefault();
                    this.sendAction({ type: 'end_turn' });
                    this.selectedTokenId = null;
                    this.validMoves = new Set();
                    this.updateValidMoveIndicators(null);
                    break;
                case 'escape':
                    // Cancel action or close menu
                    event.preventDefault();
                    if (this.deploymentMenuOpen) {
                        this.toggleDeploymentMenu();
                    } else {
                        this.cancelAction();
                    }
                    break;
                case 'r':
                    // Toggle deployment menu
                    event.preventDefault();
                    this.toggleDeploymentMenu();
                    break;
                case 'v':
                    // Toggle camera mode
                    event.preventDefault();
                    this.toggleCameraMode();
                    break;
                case 'tab':
                    // Cycle controlled token in first-person mode
                    event.preventDefault();
                    if (this.cameraMode === "firstperson") {
                        this.cycleControlledToken();
                    }
                    break;
                case 'q':
                    // Rotate camera left
                    event.preventDefault();
                    this.rotateCameraLeft();
                    break;
                case 'e':
                    // Rotate camera right
                    event.preventDefault();
                    this.rotateCameraRight();
                    break;
                case 'm':
                    // Toggle music
                    event.preventDefault();
                    this.toggleMusic();
                    break;
                case '1':
                case '2':
                case '3':
                case '4':
                    // Switch local player ID
                    const playerIndex = parseInt(event.key) - 1;
                    this.localPlayerId = `player_${playerIndex}`;
                    console.log("Switched to player", this.localPlayerId);
                    break;
                case 'w':
                case 'arrowup':
                    // Move camera forward
                    event.preventDefault();
                    this.moveCameraForward();
                    break;
                case 's':
                case 'arrowdown':
                    // Move camera backward
                    event.preventDefault();
                    this.moveCameraBackward();
                    break;
                case 'a':
                case 'arrowleft':
                    // Move camera left
                    event.preventDefault();
                    this.moveCameraLeft();
                    break;
                case 'd':
                case 'arrowright':
                    // Move camera right
                    event.preventDefault();
                    this.moveCameraRight();
                    break;
                case '+':
                case '=':
                    // Increase FOV (zoom out)
                    event.preventDefault();
                    this.adjustFOV(15); // Increased from 5 to 15 for faster FOV adjustment
                    break;
                case '-':
                case '_':
                    // Decrease FOV (zoom in)
                    event.preventDefault();
                    this.adjustFOV(-15); // Increased from 5 to 15 for faster FOV adjustment
                    break;
            }
        });

        // Handle Ctrl+Q for quit
        window.addEventListener('keydown', (event) => {
            if (event.ctrlKey && event.key.toLowerCase() === 'q') {
                event.preventDefault();
                this.quitGame();
            }
        });

        // Prevent context menu on right-click
        this.canvas.addEventListener('contextmenu', (e) => {
            e.preventDefault();
        });

        // Handle window resize
        window.addEventListener('resize', () => {
            this.engine.resize();
        });
    }

    startRenderLoop() {
        this.engine.runRenderLoop(() => {
            if (this.scene) {
                // Update first-person camera to follow token
                this.updateFirstPersonCamera();
                this.scene.render();
            }
        });
    }

    // Toggle music (M key)
    toggleMusic() {
        this.musicPlaying = !this.musicPlaying;
        if (this.musicPlaying) {
            console.log("Music enabled");
            // Resume sounds if we had actual audio
        } else {
            console.log("Music muted");
            // Pause sounds if we had actual audio
        }
    }

    // Move camera forward (W/ArrowUp)
    moveCameraForward() {
        if (this.cameraMode === "overview") {
            const moveAmount = 50;
            const forward = this.camera.getDirection(BABYLON.Vector3.Forward());
            forward.y = 0; // Keep movement horizontal
            forward.normalize();
            forward.scaleInPlace(moveAmount);
            this.camera.target.addInPlace(forward);
        } else if (this.cameraMode === "firstperson") {
            const moveAmount = 20;
            const forward = this.firstPersonCamera.getDirection(BABYLON.Vector3.Forward());
            forward.y = 0; // Keep movement horizontal
            forward.normalize();
            forward.scaleInPlace(moveAmount);
            this.firstPersonCamera.position.addInPlace(forward);
            this.firstPersonCamera.setTarget(this.firstPersonCamera.position.clone().add(this.firstPersonCamera.getDirection(BABYLON.Vector3.Forward())));
        }
    }

    // Move camera backward (S/ArrowDown)
    moveCameraBackward() {
        if (this.cameraMode === "overview") {
            const moveAmount = 50;
            const forward = this.camera.getDirection(BABYLON.Vector3.Forward());
            forward.y = 0; // Keep movement horizontal
            forward.normalize();
            forward.scaleInPlace(-moveAmount);
            this.camera.target.addInPlace(forward);
        } else if (this.cameraMode === "firstperson") {
            const moveAmount = 20;
            const forward = this.firstPersonCamera.getDirection(BABYLON.Vector3.Forward());
            forward.y = 0; // Keep movement horizontal
            forward.normalize();
            forward.scaleInPlace(-moveAmount);
            this.firstPersonCamera.position.addInPlace(forward);
            this.firstPersonCamera.setTarget(this.firstPersonCamera.position.clone().add(this.firstPersonCamera.getDirection(BABYLON.Vector3.Forward())));
        }
    }

    // Move camera left (A/ArrowLeft)
    moveCameraLeft() {
        if (this.cameraMode === "overview") {
            const moveAmount = 50;
            const right = this.camera.getDirection(BABYLON.Vector3.Right());
            right.y = 0; // Keep movement horizontal
            right.normalize();
            right.scaleInPlace(-moveAmount);
            this.camera.target.addInPlace(right);
        } else if (this.cameraMode === "firstperson") {
            const moveAmount = 20;
            const right = this.firstPersonCamera.getDirection(BABYLON.Vector3.Right());
            right.y = 0; // Keep movement horizontal
            right.normalize();
            right.scaleInPlace(-moveAmount);
            this.firstPersonCamera.position.addInPlace(right);
            this.firstPersonCamera.setTarget(this.firstPersonCamera.position.clone().add(this.firstPersonCamera.getDirection(BABYLON.Vector3.Forward())));
        }
    }

    // Move camera right (D/ArrowRight)
    moveCameraRight() {
        if (this.cameraMode === "overview") {
            const moveAmount = 50;
            const right = this.camera.getDirection(BABYLON.Vector3.Right());
            right.y = 0; // Keep movement horizontal
            right.normalize();
            right.scaleInPlace(moveAmount);
            this.camera.target.addInPlace(right);
        } else if (this.cameraMode === "firstperson") {
            const moveAmount = 20;
            const right = this.firstPersonCamera.getDirection(BABYLON.Vector3.Right());
            right.y = 0; // Keep movement horizontal
            right.normalize();
            right.scaleInPlace(moveAmount);
            this.firstPersonCamera.position.addInPlace(right);
            this.firstPersonCamera.setTarget(this.firstPersonCamera.position.clone().add(this.firstPersonCamera.getDirection(BABYLON.Vector3.Forward())));
        }
    }

    // Adjust FOV (+/- keys)
    adjustFOV(change) {
        if (this.cameraMode === "overview") {
            this.camera.fov += change * 0.01;
            this.camera.fov = Math.max(0.1, Math.min(1.5, this.camera.fov));
            console.log("FOV adjusted to:", this.camera.fov);
        } else if (this.cameraMode === "firstperson") {
            this.firstPersonCamera.fov += change * 0.01;
            this.firstPersonCamera.fov = Math.max(0.1, Math.min(1.5, this.firstPersonCamera.fov));
            console.log("FOV adjusted to:", this.firstPersonCamera.fov);
        }
    }

    // Quit game (Ctrl+Q)
    quitGame() {
        console.log("Quitting game...");
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.close();
        }
        alert("Game quit. You can close this window.");
    }

    // Cancel current action/selection (ESC key)
    cancelAction() {
        if (this.selectedTokenId) {
            console.log("Cancelled token selection");
            this.selectedTokenId = null;
            this.validMoves = new Set();
            this.updateValidMoveIndicators(null);
        } else if (this.selectedDeployHealth) {
            console.log("Cancelled deployment selection");
            this.selectedDeployHealth = null;
            this.deploymentMenuOpen = false;
        } else if (this.deploymentMenuOpen) {
            console.log("Closed deployment menu");
            this.deploymentMenuOpen = false;
        }
    }

    // Toggle deployment menu (R key)
    toggleDeploymentMenu() {
        if (!this.gameState) {
            console.log("No game state");
            return;
        }
        if (this.gameState.current_turn_player_id !== this.localPlayerId) {
            console.log(`Not your turn. Current turn: ${this.gameState.current_turn_player_id}, You are: ${this.localPlayerId}`);
            console.log("Press 1-4 to switch which player you control");
            return;
        }

        if (this.turnPhase !== "MOVEMENT") {
            console.log("Can only deploy during MOVEMENT phase");
            return;
        }

        this.deploymentMenuOpen = !this.deploymentMenuOpen;
        if (this.deploymentMenuOpen) {
            this.showDeploymentUI();
        } else {
            this.hideDeploymentUI();
            this.selectedDeployHealth = null;
        }
    }

    showDeploymentUI() {
        // Remove any existing menu
        const existing = document.getElementById('deployment-menu');
        if (existing) existing.remove();

        // Create deployment menu
        const menu = document.createElement('div');
        menu.id = 'deployment-menu';
        menu.style.position = 'fixed';
        menu.style.top = '50%';
        menu.style.left = '50%';
        menu.style.transform = 'translate(-50%, -50%)';
        menu.style.backgroundColor = '#000080';
        menu.style.border = '2px solid #00FFFF';
        menu.style.padding = '20px';
        menu.style.zIndex = '1000';
        menu.style.fontFamily = 'monospace';
        menu.style.color = '#00FFFF';
        menu.style.textAlign = 'center';

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

        // Add button listeners
        menu.querySelectorAll('.deploy-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.selectedDeployHealth = parseInt(e.target.getAttribute('data-health'));
                console.log(`Selected ${this.selectedDeployHealth} HP token for deployment`);
                // Highlight the selected button
                menu.querySelectorAll('.deploy-btn').forEach(b => b.style.backgroundColor = '#000080');
                e.target.style.backgroundColor = '#008080';
            });
        });
    }

    hideDeploymentUI() {
        const menu = document.getElementById('deployment-menu');
        if (menu) menu.remove();
    }
}

// Initialize game client when page loads
window.addEventListener('DOMContentLoaded', () => {
    console.log("Initializing Race to the Crystal 3D Web Client with all enhancements");
    const client = new GameClient();

    // Make client available globally for debugging
    window.gameClient = client;
});
