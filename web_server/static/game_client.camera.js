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
        const boardCenterX = (this.boardWidth / 2) * this.cellSize;
        const boardCenterY = (this.boardHeight / 2) * this.cellSize;

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
            500,
            new BABYLON.Vector3(boardCenterX, 0, boardCenterY),
            this.scene,
        );
        this.camera.attachControl(this.canvas, true);
        this.camera.lowerRadiusLimit = 300;
        this.camera.upperRadiusLimit = 1500;
        this.camera.wheelPrecision = config.wheelPrecision;
        this.camera.panningSensibility = config.panningSensibility;
        this.camera.inertia = config.inertia;
        this.camera.lowerAlphaLimit = 0;
        this.camera.upperAlphaLimit = 0;
        this.camera.lowerBetaLimit = Math.PI / 3;
        this.camera.upperBetaLimit = Math.PI / 3;

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

        const tokenX = token.position[0] * this.cellSize + this.cellSize / 2;
        const tokenZ = token.position[1] * this.cellSize + this.cellSize / 2;
        const tokenY = TOKEN_HEIGHT / 2;

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

        this.camera.target.addInPlace(right.scale(-dx * panSpeed));
        this.camera.target.addInPlace(forward.scale(dy * panSpeed));
    }

    moveCameraForward() {
        const moveAmount = this.cameraMode === "overview" ? 50 : 20;
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

    moveCameraBackward() {
        const moveAmount = this.cameraMode === "overview" ? 50 : 20;
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

    moveCameraLeft() {
        const moveAmount = this.cameraMode === "overview" ? 50 : 20;
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

    moveCameraRight() {
        const moveAmount = this.cameraMode === "overview" ? 50 : 20;
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

        // Switch to overview mode if in first-person
        if (this.cameraMode === "firstperson") {
            this.toggleCameraMode();
        }

        // Reset overview camera to initial position
        this.camera.alpha = Math.PI / 4;
        this.camera.beta = Math.PI / 3;
        this.camera.radius = 500;
        this.camera.target = new BABYLON.Vector3(boardCenterX, 0, boardCenterY);
        this.camera.fov = 0.8; // Default FOV

        // Reset first-person camera state
        this.tokenRotation = 0;
        this.cameraPitch = -15;
        this.controlledTokenId = null;

        console.log('[CameraController] View reset to initial position');
    }

}
