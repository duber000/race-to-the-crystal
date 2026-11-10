/**
 * webgl2_camera.js - Overview and first-person camera for the WebGL2 renderer.
 *
 * A single spherical camera serves both modes, mirroring the Babylon
 * implementation: built-in-style pan/zoom drives it in overview (InputHandler
 * pans, the wheel handler zooms), and per-frame spherical updates drive it in
 * first person. Position is *derived* from (target, alpha, beta, radius), so
 * there is never a stale position to sync.
 */

import { Vec3, Vec3Lerp, mat4LookAt } from './glmath.js';
import { BOARD_CONFIG } from '../game_client.constants.js';

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

/**
 * Overview azimuth per seat — the camera sits behind the player's own
 * deployment corner so your tokens are always near-side (never hidden
 * behind the crystal silhouette, a HUD panel, or the board's far edge).
 * Seats: 0 = NW, 1 = NE, 2 = SW, 3 = SE (grid coords, y grows downward).
 * Matches the deployment corners in game/board.kuki (getStartingPosition).
 */
const SEAT_ALPHAS = [
    Math.PI * 5 / 4,  // player_0 — NW corner
    Math.PI * 3 / 4,  // player_1 — NE corner
    Math.PI * 7 / 4,  // player_2 — SW corner
    Math.PI / 4,      // player_3 — SE corner
];
const OVERVIEW_ALPHA_DEFAULT = Math.PI / 4;
const TRANSITION_DURATION = 0.45; // seconds for overview ↔ FP camera moves

const UP = new Vec3(0, 1, 0);

/**
 * Camera Controller - Manages overview and first-person camera modes.
 */
class CameraController {
    /**
     * @param {Object} scene - Vanilla scene facade (kept for interface parity)
     * @param {HTMLCanvasElement} canvas - Canvas element
     * @param {number} boardWidth - Board width in cells (24)
     * @param {number} boardHeight - Board height in cells (24)
     * @param {number} cellSize - Cell size in world units
     * @param {number} wallHeight - Wall height in world units
     * @param {Object} deviceCapabilities - Device capabilities object
     * @param {number|null} localPlayerSeat - Seat index 0-3 (player_N). The
     *   overview azimuth sits behind this seat's deployment corner; null
     *   (unknown/spectator without a followed seat) falls back to the SE pose.
     */
    constructor(scene, canvas, boardWidth, boardHeight, cellSize, wallHeight, deviceCapabilities, localPlayerSeat) {
        this.scene = scene;
        this.canvas = canvas;
        this.boardWidth = boardWidth;
        this.boardHeight = boardHeight;
        this.cellSize = cellSize;
        this.wallHeight = wallHeight;
        this.deviceCapabilities = deviceCapabilities;
        this._seat = Number.isInteger(localPlayerSeat)
            ? ((localPlayerSeat % SEAT_ALPHAS.length) + SEAT_ALPHAS.length) % SEAT_ALPHAS.length
            : null;

        this._cameraMode = "overview";
        this.controlledTokenId = null;
        this.tokenRotation = 0;
        this.cameraPitch = -15;
        this.mouseLookSensitivity = 0.3;
        this._transition = null;
        this._focusTransition = null;
        this._focusActive = false;
        this._lastUpdateTime = null;

        this._initCameras();
        this._bindZoomAndTouch();

        const cancel = () => this.cancelFocus();
        this.canvas.addEventListener('mousedown', cancel);
        this.canvas.addEventListener('wheel', cancel, { passive: true });
        this.canvas.addEventListener('touchstart', cancel, { passive: true });
    }

    /**
     * Initialize the overview camera.
     * @private
     */
    _initCameras() {
        const pose = this._overviewPose();

        // Position is derived from spherical state, never stored.
        const camera = {
            target: pose.target.clone(),
            alpha: pose.alpha,
            beta: pose.beta,
            radius: pose.radius,
            fov: OVERVIEW_FOV,
            minZ: 1,
            maxZ: 10000,
            lowerRadiusLimit: 60,
            upperRadiusLimit: pose.radius * 1.5,
            lowerBetaLimit: 0.1,
            upperBetaLimit: (Math.PI / 2) - 0.1,
        };
        Object.defineProperty(camera, 'position', {
            get: () => this._sphericalPosition(camera),
        });
        camera.getViewMatrix = () => mat4LookAt(camera.position, camera.target, UP);
        camera.getDirection = (direction) => {
            // Only the XZ-projected forward/right are used (panning).
            if (direction === 'forward') {
                const forward = camera.target.subtract(camera.position);
                forward.y = 0;
                return forward.normalize();
            }
            const forward = camera.target.subtract(camera.position).normalize();
            const right = forward.cross(UP);
            right.y = 0;
            return right.normalize();
        };
        this.camera = camera;

        this._applyOverviewBetaLimits();
    }

    _sphericalPosition(camera) {
        const sinBeta = Math.sin(camera.beta);
        return new Vec3(
            camera.target.x + camera.radius * Math.sin(camera.alpha) * sinBeta,
            camera.target.y + camera.radius * Math.cos(camera.beta),
            camera.target.z + camera.radius * Math.cos(camera.alpha) * sinBeta,
        );
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

    /** Overview azimuth for the local seat (falls back to the SE pose). */
    _seatAlpha() {
        return this._seat === null ? OVERVIEW_ALPHA_DEFAULT : SEAT_ALPHAS[this._seat];
    }

    /**
     * Standard overview pose (spherical position + target).
     * @private
     * @returns {Object} { position, target, alpha, beta, radius }
     *
     * Framed for the 18x18 board at a 40-degree vertical FOV: radius
     * 1.1x the board diagonal keeps every seat's deployment corner
     * inside the frame with margin above and below the HUD columns.
     */
    _overviewPose() {
        const boardRealWidth = this.boardWidth * this.cellSize;
        const boardRealHeight = this.boardHeight * this.cellSize;
        const target = new Vec3(boardRealWidth / 2, 0, boardRealHeight / 2);
        const boardDiagonal = Math.sqrt(boardRealWidth * boardRealWidth + boardRealHeight * boardRealHeight);
        const alpha = this._seatAlpha();
        const beta = Math.PI / 3;
        const radius = boardDiagonal * 1.1;
        const position = new Vec3(
            target.x + radius * Math.sin(alpha) * Math.sin(beta),
            radius * Math.cos(beta),
            target.z + radius * Math.cos(alpha) * Math.sin(beta),
        );
        return { position, target, alpha, beta, radius };
    }

    /**
     * Drive the camera from a cartesian pose (position + target) by
     * converting to the spherical representation.
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
     * Wheel zoom in overview (dolly) / field-of-view zoom in first person,
     * plus two-finger pinch and pan for touch devices.
     * @private
     */
    _bindZoomAndTouch() {
        this._boundWheel = (event) => {
            event.preventDefault();
            this.adjustZoom(event.deltaY < 0 ? 1 : -1);
        };
        this.canvas.addEventListener('wheel', this._boundWheel, { passive: false });

        // Two-finger pinch zoom / pan. Single-finger gestures stay reserved
        // for tap detection in InputHandler.
        this._pinchStart = null;
        this._boundTouchStart = (event) => {
            if (event.touches.length === 2) {
                const [a, b] = [event.touches[0], event.touches[1]];
                this._pinchStart = {
                    distance: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY),
                    midX: (a.clientX + b.clientX) / 2,
                    midY: (a.clientY + b.clientY) / 2,
                    radius: this.camera.radius,
                    fov: this.camera.fov,
                };
            }
        };
        this._boundTouchMove = (event) => {
            if (event.touches.length !== 2 || !this._pinchStart) return;
            event.preventDefault();
            const [a, b] = [event.touches[0], event.touches[1]];
            const distance = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
            const midX = (a.clientX + b.clientX) / 2;
            const midY = (a.clientY + b.clientY) / 2;
            const pinch = this._pinchStart;

            const scale = pinch.distance / Math.max(distance, 1);
            if (this.cameraMode === 'firstperson') {
                this.camera.fov = Math.max(FP_FOV_MIN, Math.min(FP_FOV_MAX, pinch.fov * scale));
            } else {
                this.camera.radius = Math.max(
                    this.camera.lowerRadiusLimit,
                    Math.min(this.camera.upperRadiusLimit, pinch.radius * scale),
                );
            }

            // Two-finger drag pans the target across the ground plane.
            const dx = midX - pinch.midX;
            const dy = midY - pinch.midY;
            this.moveCameraRight(-dx * 0.5);
            this.moveCameraForward(dy * 0.5);
            this._pinchStart.midX = midX;
            this._pinchStart.midY = midY;
        };
        this._boundTouchEnd = (event) => {
            if (event.touches.length < 2) this._pinchStart = null;
        };
        this.canvas.addEventListener('touchstart', this._boundTouchStart, { passive: true });
        this.canvas.addEventListener('touchmove', this._boundTouchMove, { passive: false });
        this.canvas.addEventListener('touchend', this._boundTouchEnd, { passive: true });
    }

    /**
     * Toggle between overview and first-person camera modes.
     */
    toggleCameraMode() {
        if (this.cameraMode === "overview") {
            this.cameraMode = "firstperson";
            this._applyFPBetaLimits();
            this.camera.fov = FP_FOV;
            // Position is applied by update() once a token is controlled.
        } else {
            this.cameraMode = "overview";
            this._beginTransitionToOverview();
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
    focusOn(worldPos, options) {
        if (this.cameraMode !== "overview") return;
        const opts = options || {};
        const radius = opts.radius || 45;
        const duration = opts.duration || 0.6;
        let wx, wz;
        if (Array.isArray(worldPos)) {
            wx = worldPos[0] * this.cellSize + this.cellSize / 2;
            wz = worldPos[1] * this.cellSize + this.cellSize / 2;
        } else if (worldPos && typeof worldPos.x !== "undefined") {
            wx = worldPos.x;
            wz = worldPos.z;
        } else {
            return;
        }
        const target = new Vec3(wx, 0, wz);
        // Frame from the player's own side, matching the overview azimuth.
        const alpha = this._seatAlpha();
        const beta = Math.PI / 3;
        const position = new Vec3(
            target.x + radius * Math.sin(alpha) * Math.sin(beta),
            radius * Math.cos(beta),
            target.z + radius * Math.cos(alpha) * Math.sin(beta),
        );
        const pose = { position, target, alpha, beta, radius };
        this._focusTransition = {
            elapsed: 0,
            duration: duration,
            fromPos: this.camera.position.clone(),
            fromTarget: this.camera.target.clone(),
            toPos: pose.position,
            toTarget: pose.target,
            finalPose: pose,
        };
        this._focusActive = false;
    }

    releaseFocus() {
        if (this.cameraMode !== "overview") return;
        const pose = this._overviewPose();
        this._focusTransition = {
            elapsed: 0,
            duration: TRANSITION_DURATION,
            fromPos: this.camera.position.clone(),
            fromTarget: this.camera.target.clone(),
            toPos: pose.position,
            toTarget: pose.target,
            finalPose: pose,
        };
        this._focusActive = false;
    }

    cancelFocus() {
        this._focusTransition = null;
        this._focusActive = false;
    }

    followToken(tokenId) {
        this._followTokenId = tokenId;
    }

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

        if (this._focusTransition) {
            this._focusTransition.elapsed += dt;
            const t = Math.min(this._focusTransition.elapsed / this._focusTransition.duration, 1);
            const ease = t * t * (3 - 2 * t);
            const pos = Vec3Lerp(this._focusTransition.fromPos, this._focusTransition.toPos, ease);
            const tgt = Vec3Lerp(this._focusTransition.fromTarget, this._focusTransition.toTarget, ease);
            this._setCameraPose(pos, tgt);
            if (t >= 1) {
                const pose = this._focusTransition.finalPose;
                this.camera.alpha = pose.alpha;
                this.camera.beta = pose.beta;
                this.camera.radius = pose.radius;
                this.camera.target.copyFrom(pose.target);
                this.camera.fov = OVERVIEW_FOV;
                this._applyOverviewBetaLimits();
                this._focusTransition = null;
                this._focusActive = true;
            }
            return;
        }

        if (this._transition) {
            this._transition.elapsed += dt;
            const t = Math.min(this._transition.elapsed / this._transition.duration, 1);
            const s = t * t * (3 - 2 * t); // smoothstep easing
            const pos = Vec3Lerp(this._transition.fromPos, this._transition.toPos, s);
            const target = Vec3Lerp(this._transition.fromTarget, this._transition.toTarget, s);
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
        // A token hidden by fog of war has no position. The camera can
        // only follow one of the player's own tokens, so this should not
        // happen — but a null position must not throw.
        if (!token || !token.position) {
            return null;
        }

        const worldX = token.position[0] * this.cellSize + this.cellSize / 2;
        const worldZ = token.position[1] * this.cellSize + this.cellSize / 2;

        const angle = this.tokenRotation * (Math.PI / 180);
        const pitchRad = this.cameraPitch * (Math.PI / 180);
        const dirX = Math.sin(angle) * Math.cos(pitchRad);
        const dirY = Math.sin(pitchRad);
        const dirZ = Math.cos(angle) * Math.cos(pitchRad);

        const eye = new Vec3(worldX, EYE_HEIGHT, worldZ);
        const target = new Vec3(
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
        if (!pose) return;
        const s = 1 - Math.exp(-dt * FP_SMOOTHING);
        const pos = Vec3Lerp(this.camera.position, pose.position, s);
        const target = Vec3Lerp(this.camera.target, pose.target, s);
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
        if (!pose) return;
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
     * @returns {Vec3} Normalized forward, y = 0
     */
    _groundForward() {
        const forward = this.camera.getDirection('forward');
        if (forward.lengthSquared() < 1e-6) {
            forward.set(-Math.sin(this.camera.alpha), 0, -Math.cos(this.camera.alpha));
        }
        forward.y = 0;
        return forward.normalize();
    }

    /**
     * Ground-projected camera right vector.
     * @private
     * @returns {Vec3} Normalized right, y = 0
     */
    _groundRight() {
        const forward = this.camera.target.subtract(this.camera.position).normalize();
        const right = forward.cross(UP);
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
        this.canvas.removeEventListener('wheel', this._boundWheel);
        this.canvas.removeEventListener('touchstart', this._boundTouchStart);
        this.canvas.removeEventListener('touchmove', this._boundTouchMove);
        this.canvas.removeEventListener('touchend', this._boundTouchEnd);
        this.camera = null;
    }
}

export { CameraController };
