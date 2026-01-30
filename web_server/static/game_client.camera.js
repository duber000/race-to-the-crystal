/**
 * CameraController - Camera management for overview and first-person modes
 *
 * Touch Controls (via Babylon.js built-in multi-touch):
 * - Pinch: Zoom in/out
 * - Two-finger drag: Pan camera
 * - Works on both touch and hybrid devices (mouse + touch)
 *
 * Mouse Controls:
 * - Right-click + drag: Pan camera
 * - Mouse wheel: Zoom in/out
 * - Q/E keys: Rotate in first-person mode
 *
 * Note: Touch gesture handling is done by Babylon.js ArcRotateCamera's
 * built-in pointer input system to avoid conflicts and support hybrid devices.
 */
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
                this.camera.inputs.attached.pointers.multiTouchPanAndZoom = true;
                this.camera.pinchPrecision = config.pinchPrecision;
            }
        }

        // First-person camera
        this.firstPersonCamera = new BABYLON.UniversalCamera(
            "firstPersonCamera",
            new BABYLON.Vector3(boardCenterX, boardCenterY + 150, boardCenterX - 100),
            this.scene,
        );
        this.firstPersonCamera.setTarget(new BABYLON.Vector3(boardCenterX, 0, boardCenterY));
        this.firstPersonCamera.minZ = 5;  // Near clipping plane - prevent clipping through tokens

        // FIX: Update maxZ here too
        this.firstPersonCamera.maxZ = boardDiagonal * 5;

        this.firstPersonCamera.keysUp = [];
        this.firstPersonCamera.keysDown = [];
        this.firstPersonCamera.keysLeft = [];
        this.firstPersonCamera.keysRight = [];
        this.firstPersonCamera.angularSensibility = config.angularSensibility;

        this.scene.activeCamera = this.camera;
    }

    toggleCameraMode() {
        if (this.cameraMode === "overview") {
            this.cameraMode = "firstperson";
            this.camera.detachControl(this.canvas);
            this.scene.activeCamera = this.firstPersonCamera;
            this.firstPersonCamera.attachControl(this.canvas, true);
            if (this.firstPersonCamera.inputs) {
                this.firstPersonCamera.inputs.clear();
            }
            this.canvas.focus();
            this.canvas.setAttribute("tabindex", "1");
            return this.firstPersonCamera;
        } else {
            this.cameraMode = "overview";
            this.firstPersonCamera.detachControl(this.canvas);
            this.scene.activeCamera = this.camera;
            this.camera.attachControl(this.canvas, true);
            this.canvas.focus();
            return this.camera;
        }
    }

    updateFirstPersonCamera(token) {
        if (this.cameraMode !== "firstperson" || !token) return;

        // Note: Assuming TOKEN_HEIGHT is defined globally or passed in context. 
        // If not, replace with a fixed value like 50.
        const tokenHeightVal = (typeof TOKEN_HEIGHT !== 'undefined') ? TOKEN_HEIGHT : 50;

        const tokenX = token.position[0] * this.cellSize + this.cellSize / 2;
        const tokenZ = token.position[1] * this.cellSize + this.cellSize / 2;
        const tokenY = tokenHeightVal / 2;

        const offset = 100;
        const height = 30;

        const yawRad = (this.tokenRotation * Math.PI) / 180;
        const pitchRad = (this.cameraPitch * Math.PI) / 180;

        const camX = tokenX + Math.sin(yawRad) * offset * Math.cos(pitchRad);
        const camZ = tokenZ + Math.cos(yawRad) * offset * Math.cos(pitchRad);
        const camY = tokenY + height + Math.sin(pitchRad) * offset;

        this.firstPersonCamera.position.x = camX;
        this.firstPersonCamera.position.y = camY;
        this.firstPersonCamera.position.z = camZ;

        this.firstPersonCamera.setTarget(new BABYLON.Vector3(tokenX, tokenY + 10, tokenZ));
    }

    cycleControlledToken(tokens) {
        const aliveTokens = tokens.filter(t => t.is_alive && t.is_deployed).map(t => t.id);
        if (aliveTokens.length === 0) return null;

        let nextIndex = 0;
        if (this.controlledTokenId !== null && aliveTokens.includes(this.controlledTokenId)) {
            const currentIndex = aliveTokens.indexOf(this.controlledTokenId);
            nextIndex = (currentIndex + 1) % aliveTokens.length;
        }

        this.controlledTokenId = aliveTokens[nextIndex];
        this.cameraPitch = -15;
        return this.controlledTokenId;
    }

    rotateCameraLeft() {
        if (this.cameraMode !== "firstperson") return false;
        this.tokenRotation -= 15;
        return true;
    }

    rotateCameraRight() {
        if (this.cameraMode !== "firstperson") return false;
        this.tokenRotation += 15;
        return true;
    }

    lookUp() {
        if (this.cameraMode !== "firstperson") return false;
        this.cameraPitch -= 15;
        this.cameraPitch = Math.max(-89, Math.min(89, this.cameraPitch));
        return true;
    }

    lookDown() {
        if (this.cameraMode !== "firstperson") return false;
        this.cameraPitch += 15;
        this.cameraPitch = Math.max(-89, Math.min(89, this.cameraPitch));
        return true;
    }

    activateMouseLook(x, y) {
        if (this.cameraMode !== "firstperson") {
            return;
        }
        this.mouseLookActive = true;
        this.lastMousePosition = { x, y };
        this.canvas.style.cursor = "none";
    }

    deactivateMouseLook() {
        this.mouseLookActive = false;
        this.canvas.style.cursor = "default";
    }

    handleMouseMotion(dx, dy) {
        if (!this.mouseLookActive || this.cameraMode !== "firstperson") return false;

        const sensitivity = 0.3;
        this.tokenRotation += dx * sensitivity;
        this.cameraPitch -= dy * sensitivity;
        this.cameraPitch = Math.max(-89, Math.min(89, this.cameraPitch));
        return true;
    }

    startPan(x, y) {
        if (this.cameraMode !== "overview") return;
        this.isPanning = true;
        this.lastMousePosition = { x, y };
        this.canvas.style.cursor = "grabbing";
    }

    stopPan() {
        this.isPanning = false;
        this.canvas.style.cursor = "default";
    }

    handlePan(dx, dy) {
        if (this.cameraMode !== "overview") return;

        const panSpeed = 0.5;

        const right = this.camera.getDirection(BABYLON.Vector3.Right());
        right.y = 0;
        right.normalize();

        const forward = this.camera.getDirection(BABYLON.Vector3.Forward());
        forward.y = 0;
        forward.normalize();

        // Calculate the proposed move
        const moveVector = right.scale(-dx * panSpeed).add(forward.scale(dy * panSpeed));
        const newTarget = this.camera.target.add(moveVector);

        // FIX: Define the bounds (World coordinates of board edges)
        // Adding a padding (2 cells) so you can see just past the edge
        const padding = this.cellSize * 2;
        const minX = -padding;
        const maxX = (this.boardWidth * this.cellSize) + padding;
        const minZ = -padding;
        const maxZ = (this.boardHeight * this.cellSize) + padding;

        // FIX: Apply clamping: Only move if within bounds
        if (newTarget.x >= minX && newTarget.x <= maxX) {
            this.camera.target.x = newTarget.x;
        }

        if (newTarget.z >= minZ && newTarget.z <= maxZ) {
            this.camera.target.z = newTarget.z;
        }
    }

    moveCameraForward(amount) {
        const moveAmount = amount !== undefined ? amount : (this.cameraMode === "overview" ? 50 : 20);
        const activeCamera = this.cameraMode === "overview" ? this.camera : this.firstPersonCamera;
        const forward = activeCamera.getDirection(BABYLON.Vector3.Forward());
        forward.y = 0;
        forward.normalize();
        forward.scaleInPlace(moveAmount);

        if (this.cameraMode === "overview") {
            this.camera.target.addInPlace(forward);
        } else {
            activeCamera.position.addInPlace(forward);
            activeCamera.setTarget(activeCamera.position.clone().add(activeCamera.getDirection(BABYLON.Vector3.Forward())));
        }
    }

    moveCameraBackward(amount) {
        const moveAmount = amount !== undefined ? amount : (this.cameraMode === "overview" ? 50 : 20);
        const activeCamera = this.cameraMode === "overview" ? this.camera : this.firstPersonCamera;
        const forward = activeCamera.getDirection(BABYLON.Vector3.Forward());
        forward.y = 0;
        forward.normalize();
        forward.scaleInPlace(-moveAmount);

        if (this.cameraMode === "overview") {
            this.camera.target.addInPlace(forward);
        } else {
            activeCamera.position.addInPlace(forward);
            activeCamera.setTarget(activeCamera.position.clone().add(activeCamera.getDirection(BABYLON.Vector3.Forward())));
        }
    }

    moveCameraLeft(amount) {
        const moveAmount = amount !== undefined ? amount : (this.cameraMode === "overview" ? 50 : 20);
        const activeCamera = this.cameraMode === "overview" ? this.camera : this.firstPersonCamera;
        const right = activeCamera.getDirection(BABYLON.Vector3.Right());
        right.y = 0;
        right.normalize();
        right.scaleInPlace(-moveAmount);

        if (this.cameraMode === "overview") {
            this.camera.target.addInPlace(right);
        } else {
            activeCamera.position.addInPlace(right);
            activeCamera.setTarget(activeCamera.position.clone().add(activeCamera.getDirection(BABYLON.Vector3.Forward())));
        }
    }

    moveCameraRight(amount) {
        const moveAmount = amount !== undefined ? amount : (this.cameraMode === "overview" ? 50 : 20);
        const activeCamera = this.cameraMode === "overview" ? this.camera : this.firstPersonCamera;
        const right = activeCamera.getDirection(BABYLON.Vector3.Right());
        right.y = 0;
        right.normalize();
        right.scaleInPlace(moveAmount);

        if (this.cameraMode === "overview") {
            this.camera.target.addInPlace(right);
        } else {
            activeCamera.position.addInPlace(right);
            activeCamera.setTarget(activeCamera.position.clone().add(activeCamera.getDirection(BABYLON.Vector3.Forward())));
        }
    }

    adjustFOV(change) {
        const activeCamera = this.cameraMode === "overview" ? this.camera : this.firstPersonCamera;
        activeCamera.fov += change * 0.01;
        activeCamera.fov = Math.max(0.1, Math.min(1.5, activeCamera.fov));
        return activeCamera.fov;
    }

    /**
     * Reset camera to initial overview position
     * Useful for mobile users who get lost while panning/zooming
     */
    resetView() {
        const boardCenterX = (this.boardWidth / 2) * this.cellSize;
        const boardCenterY = (this.boardHeight / 2) * this.cellSize;
        const boardRealWidth = this.boardWidth * this.cellSize;
        const boardRealHeight = this.boardHeight * this.cellSize;
        const boardDiagonal = Math.sqrt(Math.pow(boardRealWidth, 2) + Math.pow(boardRealHeight, 2));

        // Switch to overview mode if in first-person
        if (this.cameraMode === "firstperson") {
            this.toggleCameraMode();
        }

        // Reset overview camera to initial position
        this.camera.alpha = Math.PI / 4;
        this.camera.beta = Math.PI / 3;
        // FIX: Reset radius relative to diagonal
        this.camera.radius = boardDiagonal * 0.8;
        this.camera.target = new BABYLON.Vector3(boardCenterX, 0, boardCenterY);
        this.camera.fov = 0.8; // Default FOV

        // Reset first-person camera state
        this.tokenRotation = 0;
        this.cameraPitch = -15;
        this.controlledTokenId = null;

        console.log('[CameraController] View reset to initial position');
    }
}
