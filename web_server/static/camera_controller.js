// ==========================================================================
// Camera Controller - Manages overview and first-person camera modes
// ==========================================================================

import { BOARD_CONFIG } from './game_client.constants.js';

// Eye level for the first-person camera: token center height, matching the
// TOKEN_CENTER_Y used by the renderer (tokens hang near the cage top).
const EYE_HEIGHT = Math.max(
    BOARD_CONFIG.TOKEN_HEIGHT / 2,
    BOARD_CONFIG.WALL_HEIGHT - BOARD_CONFIG.TOKEN_HEIGHT / 2,
);

const OVERVIEW_FOV = 0.7;
const FP_FOV = 0.9;
const FP_FOV_MIN = 0.5;
const FP_FOV_MAX = 1.2;
const FP_PITCH_MIN = -85;
const FP_PITCH_MAX = 60;
const FP_LOOK_DISTANCE = 200;
const FP_SMOOTHING = 14;          // exponential follow speed (1/s)
const TRANSITION_DURATION = 0.45; // seconds for overview ↔ FP camera moves

/**
 * Camera Controller - Manages overview and first-person camera modes.
 * A single ArcRotateCamera serves both modes: built-in controls drive it in
 * overview, and per-frame alpha/beta/radius/target updates drive it in
 * first-person (which keeps the render pipeline attached to one camera).
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

        this._cameraMode = "overview";
        this.controlledTokenId = null;
        this.tokenRotation = 0;
        this.cameraPitch = -15;
        this.mouseLookSensitivity = 0.3;
        this._transition = null;
        this._lastUpdateTime = null;

        this._initCameras();
    }

    /**
     * Initialize the overview camera.
     * @private
     */
    _initCameras() {
        const pose = this._overviewPose();

        this.camera = new BABYLON.ArcRotateCamera(
            "gameCamera",
            pose.alpha,
            pose.beta,
            pose.radius,
            pose.target.clone(),
            this.scene,
        );

        this.camera.minZ = 2;
        this.camera.maxZ = pose.radius * 10;
        this.camera.fov = OVERVIEW_FOV;

        this.camera.attachControl(this.canvas, true);
        this.camera.lowerRadiusLimit = 60;
        this.camera.upperRadiusLimit = pose.radius * 1.5;
        this.camera.wheelPrecision = this.deviceCapabilities ?
            this.deviceCapabilities.getCameraConfig().wheelPrecision : 5;

        // Disable BabylonJS built-in mouse button orbit/pan so left-click is
        // free for game interactions and drag-pan is handled by InputHandler.
        // Wheel zoom still works; rotation is via Q/E in first-person.
        if (this.camera.inputs.attached.pointers) {
            this.camera.inputs.attached.pointers.buttons = [];
        }
        // Remove built-in keyboard orbit too — arrow keys pan via InputHandler
        // (otherwise arrows both orbit alpha/beta and pan the target).
        if (this.camera.inputs.attached.keyboard) {
            this.camera.inputs.remove(this.camera.inputs.attached.keyboard);
        }
        this.camera.panningSensibility = 0;

        this.camera.inertia = this.deviceCapabilities ?
            this.deviceCapabilities.getCameraConfig().inertia : 0.9;

        // Overview beta limits keep the camera above the ground plane.
        this._applyOverviewBetaLimits();

        // Enable multi-touch pinch/pan on touch devices (ArcRotate built-ins).
        if (this.deviceCapabilities && this.deviceCapabilities.hasTouch()) {
            const pointers = this.camera.inputs.attached.pointers;
            if (pointers) {
                pointers.multiTouchPanning = true;
                pointers.multiTouchPanAndZoom = true;
            }
        }
    }

    _applyOverviewBetaLimits() {
        this.camera.lowerBetaLimit = 0.1;
        this.camera.upperBetaLimit = (Math.PI / 2) - 0.1;
    }

    _applyFPBetaLimits() {
        // First-person needs to look up and down freely, past both poles.
        this.camera.lowerBetaLimit = 0.01;
        this.camera.upperBetaLimit = Math.PI - 0.01;
    }

    /**
     * Standard overview pose (spherical position + target).
     * @private
     * @returns {Object} { position, target, alpha, beta, radius }
     */
    _overviewPose() {
        const boardRealWidth = this.boardWidth * this.cellSize;
        const boardRealHeight = this.boardHeight * this.cellSize;
        const target = new BABYLON.Vector3(
            boardRealWidth / 2,
            0,
            boardRealHeight / 2,
        );
        const boardDiagonal = Math.sqrt(boardRealWidth * boardRealWidth + boardRealHeight * boardRealHeight);
        const alpha = Math.PI / 4;
        const beta = Math.PI / 3;
        const radius = boardDiagonal * 0.8;
        const position = new BABYLON.Vector3(
            target.x + radius * Math.sin(alpha) * Math.sin(beta),
            radius * Math.cos(beta),
            target.z + radius * Math.cos(alpha) * Math.sin(beta),
        );
        return { position, target, alpha, beta, radius };
    }

    /**
     * Drive the camera from a cartesian pose (position + target) by
     * converting to the ArcRotate's alpha/beta/radius/target representation.
     * @private
     */
    _setCameraPose(position, target) {
        const delta = position.subtract(target);
        const radius = Math.max(delta.length(), 1);
        this.camera.radius = radius;
        this.camera.beta = Math.acos(Math.max(-1, Math.min(1, delta.y / radius)));
        this.camera.alpha = Math.atan2(delta.x, delta.z);
        this.camera.target.copyFrom(target);
    }

    /**
     * Toggle between overview and first-person camera modes.
     * @returns {BABYLON.ArcRotateCamera} The (single) game camera
     */
    toggleCameraMode() {
        if (this.cameraMode === "overview") {
            this.cameraMode = "firstperson";
            this.camera.detachControl();
            this._applyFPBetaLimits();
            this.camera.fov = FP_FOV;
            // Position is applied by update() once a token is controlled.
        } else {
            this.cameraMode = "overview";
            this._beginTransitionToOverview();
            this.camera.attachControl(this.canvas, true);
        }
        return this.camera;
    }

    /**
     * Start a smooth flight from the current pose back to the overview pose.
     * @private
     */
    _beginTransitionToOverview() {
        const pose = this._overviewPose();
        this._transition = {
            elapsed: 0,
            duration: TRANSITION_DURATION,
            fromPos: this.camera.position.clone(),
            fromTarget: this.camera.target.clone(),
            toPos: pose.position,
            toTarget: pose.target,
            finalPose: pose,
        };
    }

    /**
     * Per-frame camera update. Called from the render loop callback.
     * @param {Object|null} token - Controlled token in first-person mode
     */
    update(token) {
        const now = performance.now();
        const dt = this._lastUpdateTime === null ?
            0.016 : Math.min((now - this._lastUpdateTime) / 1000, 0.1);
        this._lastUpdateTime = now;

        if (this.cameraMode === "firstperson") {
            if (token) {
                this._updateFirstPersonCamera(token, dt);
            }
            return;
        }

        if (this._transition) {
            this._transition.elapsed += dt;
            const t = Math.min(this._transition.elapsed / this._transition.duration, 1);
            const s = t * t * (3 - 2 * t); // smoothstep easing
            const pos = BABYLON.Vector3.Lerp(this._transition.fromPos, this._transition.toPos, s);
            const target = BABYLON.Vector3.Lerp(this._transition.fromTarget, this._transition.toTarget, s);
            this._setCameraPose(pos, target);
            if (t >= 1) {
                const pose = this._transition.finalPose;
                this.camera.alpha = pose.alpha;
                this.camera.beta = pose.beta;
                this.camera.radius = pose.radius;
                this.camera.target.copyFrom(pose.target);
                this.camera.fov = OVERVIEW_FOV;
                this._applyOverviewBetaLimits();
                this._transition = null;
            }
        }
    }

    /**
     * Compute the first-person pose for a token: camera at the token's eye,
     * looking in the yaw (tokenRotation) / pitch (cameraPitch) direction.
     * @private
     */
    _firstPersonPose(token) {
        const worldX = token.position[0] * this.cellSize + this.cellSize / 2;
        const worldZ = token.position[1] * this.cellSize + this.cellSize / 2;

        const angle = this.tokenRotation * (Math.PI / 180);
        const pitchRad = this.cameraPitch * (Math.PI / 180);
        const dirX = Math.sin(angle) * Math.cos(pitchRad);
        const dirY = Math.sin(pitchRad);
        const dirZ = Math.cos(angle) * Math.cos(pitchRad);

        const eye = new BABYLON.Vector3(worldX, EYE_HEIGHT, worldZ);
        const target = new BABYLON.Vector3(
            eye.x + dirX * FP_LOOK_DISTANCE,
            eye.y + dirY * FP_LOOK_DISTANCE,
            eye.z + dirZ * FP_LOOK_DISTANCE,
        );
        return { position: eye, target };
    }

    /**
     * Smoothly move the camera to the token's eye-level first-person pose.
     * @param {Object} token - Token object with position property
     * @param {number} dt - Delta time in seconds
     * @private
     */
    _updateFirstPersonCamera(token, dt) {
        const pose = this._firstPersonPose(token);
        const s = 1 - Math.exp(-dt * FP_SMOOTHING);
        const pos = BABYLON.Vector3.Lerp(this.camera.position, pose.position, s);
        const target = BABYLON.Vector3.Lerp(this.camera.target, pose.target, s);
        this._setCameraPose(pos, target);
    }

    /**
     * Snap the camera to the token's first-person pose (no smoothing).
     * Used when entering FP mode or switching tokens so the view starts clean.
     * @param {Object} token - Token object with position property
     */
    snapToToken(token) {
        if (this.cameraMode !== "firstperson" || !token) return;
        const pose = this._firstPersonPose(token);
        this._setCameraPose(pose.position, pose.target);
    }

    /**
     * Reset camera to overview mode with a smooth transition.
     */
    resetView() {
        this.cameraMode = "overview";
        this.controlledTokenId = null;
        this.tokenRotation = 0;
        this.cameraPitch = -15;
        this._beginTransitionToOverview();
        this.camera.attachControl(this.canvas, true);
    }

    /**
     * Rotate camera left by 15 degrees (first-person only).
     */
    rotateCameraLeft() {
        if (this.cameraMode !== "firstperson") return;
        this.tokenRotation -= 15;
    }

    /**
     * Rotate camera right by 15 degrees (first-person only).
     */
    rotateCameraRight() {
        if (this.cameraMode !== "firstperson") return;
        this.tokenRotation += 15;
    }

    /**
     * Tilt camera up (first-person only).
     */
    lookUp() {
        if (this.cameraMode !== "firstperson") return;
        this.cameraPitch = Math.min(FP_PITCH_MAX, this.cameraPitch + 5);
    }

    /**
     * Tilt camera down (first-person only).
     */
    lookDown() {
        if (this.cameraMode !== "firstperson") return;
        this.cameraPitch = Math.max(FP_PITCH_MIN, this.cameraPitch - 5);
    }

    /**
     * Apply mouse movement for FPS mouse look.
     * @param {number} deltaX - Horizontal mouse movement
     * @param {number} deltaY - Vertical mouse movement
     */
    applyMouseLook(deltaX, deltaY) {
        if (this.cameraMode !== "firstperson") return;

        this.tokenRotation += deltaX * this.mouseLookSensitivity;
        this.cameraPitch = Math.max(
            FP_PITCH_MIN,
            Math.min(FP_PITCH_MAX, this.cameraPitch - deltaY * this.mouseLookSensitivity),
        );
    }

    _panTarget(dx, dz) {
        const padding = this.cellSize * 2;
        const maxX = this.boardWidth * this.cellSize + padding;
        const maxZ = this.boardHeight * this.cellSize + padding;
        const target = this.camera.target;
        target.x = Math.max(-padding, Math.min(maxX, target.x + dx));
        target.z = Math.max(-padding, Math.min(maxZ, target.z + dz));
    }

    /**
     * Ground-projected camera forward vector (stable at all pitch angles).
     * @private
     * @returns {BABYLON.Vector3} Normalized forward, y = 0
     */
    _groundForward() {
        const forward = this.camera.getDirection(BABYLON.Vector3.Forward());
        forward.y = 0;
        if (forward.lengthSquared() < 1e-6) {
            forward.set(-Math.sin(this.camera.alpha), 0, -Math.cos(this.camera.alpha));
        }
        return forward.normalize();
    }

    /**
     * Ground-projected camera right vector.
     * @private
     * @returns {BABYLON.Vector3} Normalized right, y = 0
     */
    _groundRight() {
        const right = this.camera.getDirection(BABYLON.Vector3.Right());
        right.y = 0;
        return right.normalize();
    }

    /**
     * Pan camera forward along its ground-projected view direction.
     * @param {number} [amount] - World units; defaults to a radius-relative step
     */
    moveCameraForward(amount) {
        if (this.cameraMode !== "overview" || this._transition) return;
        const step = amount !== undefined ? amount : this.camera.radius * 0.08;
        const forward = this._groundForward();
        this._panTarget(forward.x * step, forward.z * step);
    }

    /**
     * Pan camera backward along its ground-projected view direction.
     * @param {number} [amount] - World units; defaults to a radius-relative step
     */
    moveCameraBackward(amount) {
        if (this.cameraMode !== "overview" || this._transition) return;
        const step = amount !== undefined ? amount : this.camera.radius * 0.08;
        const forward = this._groundForward();
        this._panTarget(-forward.x * step, -forward.z * step);
    }

    /**
     * Pan camera left along its ground-projected right vector.
     * @param {number} [amount] - World units; defaults to a radius-relative step
     */
    moveCameraLeft(amount) {
        if (this.cameraMode !== "overview" || this._transition) return;
        const step = amount !== undefined ? amount : this.camera.radius * 0.08;
        const right = this._groundRight();
        this._panTarget(-right.x * step, -right.z * step);
    }

    /**
     * Pan camera right along its ground-projected right vector.
     * @param {number} [amount] - World units; defaults to a radius-relative step
     */
    moveCameraRight(amount) {
        if (this.cameraMode !== "overview" || this._transition) return;
        const step = amount !== undefined ? amount : this.camera.radius * 0.08;
        const right = this._groundRight();
        this._panTarget(right.x * step, right.z * step);
    }

    /**
     * Zoom in/out. Dollies the camera radius in overview; adjusts field of
     * view in first-person (where dolly is meaningless at eye level).
     * @param {number} steps - Positive zooms in, negative zooms out
     */
    adjustZoom(steps) {
        if (this.cameraMode === "firstperson") {
            this.camera.fov = Math.max(FP_FOV_MIN, Math.min(FP_FOV_MAX, this.camera.fov - steps * 0.05));
            return;
        }
        if (this._transition) return;
        const zoomFactor = Math.pow(0.88, steps);
        this.camera.radius = Math.max(
            this.camera.lowerRadiusLimit,
            Math.min(this.camera.upperRadiusLimit, this.camera.radius * zoomFactor),
        );
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
