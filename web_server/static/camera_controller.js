// ==========================================================================
// Camera Controller - Manages overview and first-person camera modes
// ==========================================================================

class CameraController {
    constructor(scene, canvas, boardWidth, boardHeight, cellSize, wallHeight, deviceCapabilities) {
        this.scene = scene;
        this.canvas = canvas;
        this.boardWidth = boardWidth;
        this.boardHeight = boardHeight;
        this.cellSize = cellSize;
        this.wallHeight = wallHeight;
        this.deviceCapabilities = deviceCapabilities;

        this.cameraMode = "overview";
        this.controlledTokenId = null;
        this.tokenRotation = 0;
        this.cameraPitch = -15;
        this.mouseLookActive = false;
        this.mouseLookSensitivity = 0.3;
        this.isPanning = false;
        this.lastMousePosition = { x: 0, y: 0 };

        this._initCameras();
    }

    _initCameras() {
        // Calculate real world dimensions
        const boardRealWidth = this.boardWidth * this.cellSize;
        const boardRealHeight = this.boardHeight * this.cellSize;
        const boardCenterX = boardRealWidth / 2;
        const boardCenterY = boardRealHeight / 2;

        // Calculate the diagonal size of the board to determine safe limits
        const boardDiagonal = Math.sqrt(Math.pow(boardRealWidth, 2) + Math.pow(boardRealHeight, 2));

        // Get device-specific camera configuration
        const config = this.deviceCapabilities ? this.deviceCapabilities.getCameraConfig() : {
            panningSensibility: 50,
            wheelPrecision: 5,
            pinchPrecision: 0,
            inertia: 0.9,
            angularSensibility: 2000
        };

        console.log('[CameraController] Initializing cameras with config:', config);

        // Overview camera (ArcRotate) - works great with both mouse and touch
        this.camera = new BABYLON.ArcRotateCamera(
            "overviewCamera",
            Math.PI / 4,
            Math.PI / 3,
            boardDiagonal * 0.8, // Start at a zoom level relative to board size
            new BABYLON.Vector3(boardCenterX, 0, boardCenterY),
            this.scene,
        );

        this.camera.minZ = 5;  // Near clipping plane - prevent clipping through tokens

        // FIX: Set maxZ dynamically so edges of large boards don't get clipped
        this.camera.maxZ = boardDiagonal * 5;

        this.camera.attachControl(this.canvas, true);
        this.camera.lowerRadiusLimit = 200; // Allow getting closer

        // FIX: Allow zooming out far enough to see the corners, but not infinite
        this.camera.upperRadiusLimit = boardDiagonal * 1.5;

        this.camera.wheelPrecision = config.wheelPrecision;
        this.camera.fov = 0.7;  // Wider FOV to see edges of board (default ~0.8-1.0)

        // Disable built-in RMB panning - we handle panning via LMB through handlePan()
        // RMB is used only for rotation (alpha) in our custom input handler
        this.camera.panningSensibility = 0;

        this.camera.inertia = config.inertia;
        this.camera.lowerAlphaLimit = -Math.PI;  // Allow full rotation
        this.camera.upperAlphaLimit = Math.PI;   // Allow full rotation

        // FIX: Adjusted Beta limits to allow seeing the board from higher up if needed
        this.camera.lowerBetaLimit = 0.1;
        this.camera.upperBetaLimit = (Math.PI / 2) - 0.1; // Don't hit ground level

        // Enable multi-touch on mobile devices (keep mouse support for hybrid devices)
        if (this.deviceCapabilities && this.deviceCapabilities.hasTouch()) {
            console.log('[CameraController] Enabling multi-touch support (keeping mouse for hybrid devices)');
            if (this.camera.inputs && this.camera.inputs.attached && this.camera.inputs.attached.pointers) {
                // Enable multi-touch but DON'T disable mouse buttons (for hybrid devices like Surface)
                this.camera.inputs.attached.pointers.multiTouchPanning = true;
            }
        }
    }

    toggleCameraMode() {
        this.cameraMode = this.cameraMode === "overview" ? "firstperson" : "overview";
        
        if (this.cameraMode === "firstperson") {
            this._setupFirstPersonCamera();
        } else {
            this._setupOverviewCamera();
        }
        
        return this.camera;
    }

    _setupFirstPersonCamera() {
        // Detach built-in camera controls so they don't fight with manual FPS positioning
        this.camera.detachControl();

        // Get the controlled token and position camera behind it
        if (this.controlledTokenId && this.scene) {
            const token = this.scene.tokens[this.controlledTokenId];
            if (token) {
                this.updateFirstPersonCamera(token);
            }
        }
    }

    _setupOverviewCamera() {
        // Re-attach built-in camera controls for overview mode
        this.camera.attachControl(this.canvas, true);
        // Reset to default overview position
        const boardRealWidth = this.boardWidth * this.cellSize;
        const boardRealHeight = this.boardHeight * this.cellSize;
        const boardCenterX = boardRealWidth / 2;
        const boardCenterY = boardRealHeight / 2;

        this.camera.setPosition(new BABYLON.Vector3(boardCenterX, 0, boardCenterY));
        this.camera.setTarget(new BABYLON.Vector3(boardCenterX, 0, boardCenterY));
        this.camera.radius = Math.sqrt(Math.pow(boardRealWidth, 2) + Math.pow(boardRealHeight, 2)) * 0.8;
    }

    updateFirstPersonCamera(token) {
        if (!token || !token.position) return;

        const [x, z] = token.position;
        const worldX = x * this.cellSize + this.cellSize / 2;
        const worldZ = z * this.cellSize + this.cellSize / 2;

        // Calculate camera position based on token rotation and pitch
        const angle = this.tokenRotation * (Math.PI / 180);
        const pitchRad = this.cameraPitch * (Math.PI / 180);
        const cameraDistance = 60;
        const cameraHeight = 40 - Math.sin(pitchRad) * cameraDistance;

        const offsetX = Math.sin(angle) * cameraDistance * Math.cos(pitchRad);
        const offsetZ = Math.cos(angle) * cameraDistance * Math.cos(pitchRad);

        this.camera.setPosition(new BABYLON.Vector3(
            worldX - offsetX,
            cameraHeight,
            worldZ - offsetZ
        ));

        // Look ahead of the token in the direction it faces
        const lookAheadDist = 30;
        this.camera.setTarget(new BABYLON.Vector3(
            worldX + Math.sin(angle) * lookAheadDist,
            10,
            worldZ + Math.cos(angle) * lookAheadDist
        ));
    }

    resetView() {
        this.cameraMode = "overview";
        this._setupOverviewCamera();
    }

    rotateCameraLeft() {
        this.tokenRotation -= 15;
        if (this.controlledTokenId && this.cameraMode === "firstperson") {
            const token = this.scene.tokens[this.controlledTokenId];
            if (token) {
                this.updateFirstPersonCamera(token);
            }
        }
    }

    rotateCameraRight() {
        this.tokenRotation += 15;
        if (this.controlledTokenId && this.cameraMode === "firstperson") {
            const token = this.scene.tokens[this.controlledTokenId];
            if (token) {
                this.updateFirstPersonCamera(token);
            }
        }
    }

    lookUp() {
        this.cameraPitch = Math.min(10, this.cameraPitch + 5);
        if (this.controlledTokenId && this.cameraMode === "firstperson") {
            const token = this.scene.tokens[this.controlledTokenId];
            if (token) {
                this.updateFirstPersonCamera(token);
            }
        }
    }

    applyMouseLook(deltaX, deltaY) {
        if (this.cameraMode !== "firstperson") return;

        this.tokenRotation += deltaX * this.mouseLookSensitivity;
        this.cameraPitch = Math.max(-60, Math.min(10, this.cameraPitch - deltaY * this.mouseLookSensitivity));

        if (this.controlledTokenId) {
            const token = this.scene.tokens ? this.scene.tokens[this.controlledTokenId] : null;
            if (token) {
                this.updateFirstPersonCamera(token);
            }
        }
    }

    lookDown() {
        this.cameraPitch = Math.max(-60, this.cameraPitch - 5);
        if (this.controlledTokenId && this.cameraMode === "firstperson") {
            const token = this.scene.tokens[this.controlledTokenId];
            if (token) {
                this.updateFirstPersonCamera(token);
            }
        }
    }

    moveCameraForward() {
        if (this.cameraMode !== "overview") return;
        
        const direction = new BABYLON.Vector3(
            Math.sin(this.camera.alpha) * this.camera.radius,
            0,
            Math.cos(this.camera.alpha) * this.camera.radius
        );
        
        this.camera.target.addInPlace(direction.scale(-0.1));
        this.camera.setPosition(this.camera.target.clone().addInPlace(new BABYLON.Vector3(0, this.camera.radius, 0)));
    }

    moveCameraBackward() {
        if (this.cameraMode !== "overview") return;
        
        const direction = new BABYLON.Vector3(
            Math.sin(this.camera.alpha) * this.camera.radius,
            0,
            Math.cos(this.camera.alpha) * this.camera.radius
        );
        
        this.camera.target.addInPlace(direction.scale(0.1));
        this.camera.setPosition(this.camera.target.clone().addInPlace(new BABYLON.Vector3(0, this.camera.radius, 0)));
    }

    moveCameraLeft() {
        if (this.cameraMode !== "overview") return;
        
        const direction = new BABYLON.Vector3(
            Math.cos(this.camera.alpha) * this.camera.radius,
            0,
            -Math.sin(this.camera.alpha) * this.camera.radius
        );
        
        this.camera.target.addInPlace(direction.scale(0.1));
        this.camera.setPosition(this.camera.target.clone().addInPlace(new BABYLON.Vector3(0, this.camera.radius, 0)));
    }

    moveCameraRight() {
        if (this.cameraMode !== "overview") return;
        
        const direction = new BABYLON.Vector3(
            Math.cos(this.camera.alpha) * this.camera.radius,
            0,
            -Math.sin(this.camera.alpha) * this.camera.radius
        );
        
        this.camera.target.addInPlace(direction.scale(-0.1));
        this.camera.setPosition(this.camera.target.clone().addInPlace(new BABYLON.Vector3(0, this.camera.radius, 0)));
    }

    adjustFOV(delta) {
        this.camera.fov = Math.max(0.5, Math.min(1.5, this.camera.fov + delta * 0.01));
    }

    cycleControlledToken(aliveTokens) {
        if (aliveTokens.length === 0) return null;

        if (this.controlledTokenId === null) {
            this.controlledTokenId = aliveTokens[0].id;
        } else {
            const currentIndex = aliveTokens.findIndex(token => token.id === this.controlledTokenId);
            const nextIndex = (currentIndex + 1) % aliveTokens.length;
            this.controlledTokenId = aliveTokens[nextIndex].id;
        }

        return this.controlledTokenId;
    }

    get cameraMode() {
        return this._cameraMode;
    }

    set cameraMode(value) {
        this._cameraMode = value;
    }

    dispose() {
        if (this.camera) {
            this.camera.dispose();
            this.camera = null;
        }
    }
}

export { CameraController };
