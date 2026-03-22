// ==========================================================================
// Camera Controller - Manages overview and first-person camera modes
// ==========================================================================

/**
 * Camera Controller - Manages overview and first-person camera modes.
 * Handles camera initialization, mode switching, and FPS camera positioning.
 */
class CameraController {
    /**
     * Create a camera controller.
     * @param {BABYLON.Scene} scene - Babylon.js scene
     * @param {HTMLCanvasElement} canvas - Canvas element
     * @param {number} boardWidth - Board width in cells (24)
     * @param {number} boardHeight - Board height in cells (24)
     * @param {number} cellSize - Cell size in world units
     * @param {number} wallHeight - Wall height in world units
     * @param {Object} deviceCapabilities - Device capabilities object
     */
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

    /**
     * Initialize overview and first-person cameras.
     * @private
     */
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

        // Disable BabylonJS built-in mouse button orbit/pan so left-click is free
        // for game interactions and right-click is free for custom panning.
        // Camera rotation is handled via keyboard (Q/E) and scroll zoom still works.
        if (this.camera.inputs.attached.pointers) {
            this.camera.inputs.attached.pointers.buttons = [];
        }
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

    /**
     * Toggle between overview and first-person camera modes.
     * @returns {BABYLON.ArcRotateCamera} The configured camera
     */
    toggleCameraMode() {
        this.cameraMode = this.cameraMode === "overview" ? "firstperson" : "overview";
        
        if (this.cameraMode === "firstperson") {
            this._setupFirstPersonCamera();
        } else {
            this._setupOverviewCamera();
        }
        
        return this.camera;
    }

    /**
     * Setup first-person camera mode.
     * Detaches built-in controls and positions camera behind controlled token.
     * @private
     */
    _setupFirstPersonCamera() {
        // Detach built-in camera controls so they don't fight with manual FPS positioning
        this.camera.detachControl();
        // Camera position is updated by the render loop callback in GameClient
    }

    /**
     * Setup overview camera mode.
     * Re-attaches built-in controls and resets to default overview position.
     * @private
     */
    _setupOverviewCamera() {
        // Re-attach built-in camera controls for overview mode
        this.camera.attachControl(this.canvas, true);
        // Reset ArcRotateCamera to default overview: set target to board center and radius
        const boardRealWidth = this.boardWidth * this.cellSize;
        const boardRealHeight = this.boardHeight * this.cellSize;
        const boardCenterX = boardRealWidth / 2;
        const boardCenterY = boardRealHeight / 2;
        const boardDiagonal = Math.sqrt(boardRealWidth * boardRealWidth + boardRealHeight * boardRealHeight);

        this.camera.target = new BABYLON.Vector3(boardCenterX, 0, boardCenterY);
        this.camera.radius = boardDiagonal * 0.8;
        this.camera.alpha = Math.PI / 4;
        this.camera.beta = Math.PI / 3;
    }

    /**
     * Update first-person camera position behind the controlled token.
     * @param {Object} token - Token object with position property
     */
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

    /**
     * Reset camera to overview mode.
     */
    resetView() {
        this.cameraMode = "overview";
        this._setupOverviewCamera();
    }

    /**
     * Rotate camera left by 15 degrees.
     */
    rotateCameraLeft() {
        this.tokenRotation -= 15;
        // Camera position update is handled by the render loop callback in GameClient
    }

    /**
     * Rotate camera right by 15 degrees.
     */
    rotateCameraRight() {
        this.tokenRotation += 15;
        // Camera position update is handled by the render loop callback in GameClient
    }

    /**
     * Tilt camera up by 5 degrees.
     */
    lookUp() {
        this.cameraPitch = Math.min(10, this.cameraPitch + 5);
        // Camera position update is handled by the render loop callback in GameClient
    }

    /**
     * Apply mouse movement for FPS camera look.
     * @param {number} deltaX - Horizontal mouse movement
     * @param {number} deltaY - Vertical mouse movement
     */
    applyMouseLook(deltaX, deltaY) {
        if (this.cameraMode !== "firstperson") return;

        this.tokenRotation += deltaX * this.mouseLookSensitivity;
        this.cameraPitch = Math.max(-60, Math.min(10, this.cameraPitch - deltaY * this.mouseLookSensitivity));
        // Camera position update is handled by the render loop callback in GameClient
    }

    /**
     * Tilt camera down by 5 degrees.
     */
    lookDown() {
        this.cameraPitch = Math.max(-60, this.cameraPitch - 5);
        // Camera position update is handled by the render loop callback in GameClient
    }

    /**
     * Move camera forward in overview mode.
     */
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

    /**
     * Move camera backward in overview mode.
     */
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

    /**
     * Move camera left in overview mode.
     */
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

    /**
     * Move camera right in overview mode.
     */
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

    /**
     * Adjust camera field of view.
     * @param {number} delta - FOV change amount
     */
    adjustFOV(delta) {
        this.camera.fov = Math.max(0.5, Math.min(1.5, this.camera.fov + delta * 0.01));
    }

    /**
     * Cycle to next controlled token for FPS camera.
     * @param {Array} aliveTokens - Array of alive token objects
     * @returns {number|null} New controlled token ID or null
     */
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

    /**
     * Get camera mode.
     * @returns {string} Current camera mode
     */
    get cameraMode() {
        return this._cameraMode;
    }

    /**
     * Set camera mode.
     * @param {string} value - New camera mode
     */
    set cameraMode(value) {
        this._cameraMode = value;
    }

    /**
     * Dispose camera resources.
     */
    dispose() {
        if (this.camera) {
            this.camera.detachControl();
            this.camera.dispose();
            this.camera = null;
        }
    }
}

export { CameraController };
