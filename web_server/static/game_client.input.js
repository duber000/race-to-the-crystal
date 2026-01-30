/**
 * InputHandler - Mouse, keyboard, and touch input handling
 *
 * Responsibilities:
 * - Mouse movement, clicks, and hover detection
 * - Keyboard shortcuts
 * - Touch tap detection (single/double tap for game actions)
 * - Camera controls (pan, zoom, rotate) via Babylon.js built-in multi-touch
 * - Event listener setup and cleanup
 *
 * Note: Camera gesture controls (pinch, pan) are handled by Babylon.js ArcRotateCamera
 * to avoid conflicts and support hybrid devices. This class only handles taps for
 * game actions (selecting cells, canceling).
 *
 * Usage:
 *   const input = new InputHandler(scene, canvas, cameraController, gameState, connectionState, engine, deviceCapabilities);
 *   input.setupEventListeners();
 *   input.on('click', (gridX, gridY) => { ... });
 *   input.on('keydown', (key) => { ... });
 *   input.dispose(); // Clean up when done
 */

// Debounce delay for game actions (ms)
// Prevents accidental double-actions from key holds/rapid presses
const ACTION_DEBOUNCE_MS = 200;

class InputHandler {
    constructor(scene, canvas, cameraController, gameState, connectionState, engine, deviceCapabilities) {
        this.scene = scene;
        this.canvas = canvas;
        this.cameraController = cameraController;
        this.gameState = gameState;
        this.connectionState = connectionState;
        this.engine = engine;
        this.deviceCapabilities = deviceCapabilities;

        // Mouse state
        this.isPanning = false; // Right-click panning
        this.isLMBDown = false;
        this.lmbDownPosition = { x: 0, y: 0 };
        this.isLMBDragging = false;
        this.lastPanPosition = { x: 0, y: 0 };
        this.hoveredCell = null;

        // Touch state (for tap detection only)
        this.touches = new Map();
        this.lastTapTime = 0;
        this.lastTapPosition = null;

        // Action debouncing (prevents rapid key spam)
        this.lastActionTime = {};

        this.eventHandlers = new Map();
    }

    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
    }

    emit(event, data) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => handler(data));
        }
    }

    /**
     * Check if an action should be debounced (prevents rapid repeated actions).
     * Returns true if action is allowed, false if it should be ignored.
     */
    shouldAllowAction(actionKey) {
        const now = Date.now();
        const lastTime = this.lastActionTime[actionKey];

        if (!lastTime || (now - lastTime) > ACTION_DEBOUNCE_MS) {
            this.lastActionTime[actionKey] = now;
            return true;
        }

        return false;
    }

    setupEventListeners() {
        this.setupPointerListeners();
        this.setupKeyboardListeners();

        // Add touch-specific listeners only if touch is supported
        if (this.deviceCapabilities && this.deviceCapabilities.hasTouch()) {
            this.setupTouchGestures();
        }

        this.setupWindowListeners();
    }

    setupPointerListeners() {
        this.canvas.addEventListener("click", () => {
            this.canvas.focus();
        });

        this.scene.onPointerObservable.add((pointerInfo) => {
            switch (pointerInfo.type) {
                case BABYLON.PointerEventTypes.POINTERMOVE:
                    this.handlePointerMove(pointerInfo);
                    break;
                case BABYLON.PointerEventTypes.POINTERDOWN:
                    this.handlePointerDown(pointerInfo);
                    break;
                case BABYLON.PointerEventTypes.POINTERUP:
                    this.handlePointerUp(pointerInfo);
                    break;
            }
        });

        this.canvas.addEventListener("contextmenu", (e) => {
            e.preventDefault();
        });
    }

    handlePointerMove(pointerInfo) {
        const dx = pointerInfo.event.movementX || 0;
        const dy = pointerInfo.event.movementY || 0;

        // Handle mouse-look (RMB in first-person)
        if (this.cameraController.mouseLookActive) {
            this.cameraController.handleMouseMotion(dx, dy);
            return;
        }

        // Handle LMB dragging/moving (mouse only to avoid conflict with touch gestures)
        if (this.isLMBDown && pointerInfo.event.pointerType === 'mouse') {
            const dist = Math.sqrt(
                Math.pow(pointerInfo.event.clientX - this.lmbDownPosition.x, 2) +
                Math.pow(pointerInfo.event.clientY - this.lmbDownPosition.y, 2)
            );

            if (dist > 5) {
                this.isLMBDragging = true;
            }

            if (this.isLMBDragging) {
                if (this.cameraController.cameraMode === "firstperson") {
                    // Move around the board in FPS mode with LMB
                    this.cameraController.moveCameraForward(-dy * 0.5);
                    this.cameraController.moveCameraRight(dx * 0.5);
                }
                // LMB panning in overview mode is disabled - use RMB for rotation
                return;
            }
        }

        // Handle RMB circular panning (rotation) in overview mode
        if (this.isPanning && this.cameraController.cameraMode === "overview") {
            // Rotate camera around the board based on horizontal mouse movement
            const rotationAmount = dx * 0.005; // Sensitivity: adjust as needed
            if (this.cameraController.camera) {
                this.cameraController.camera.alpha = (this.cameraController.camera.alpha + rotationAmount) % (Math.PI * 2);
            }
            return;
        }

        const pickResult = this.scene.pick(
            this.scene.pointerX,
            this.scene.pointerY,
        );

        if (pickResult.hit && pickResult.pickedPoint) {
            const x = pickResult.pickedPoint.x;
            const z = pickResult.pickedPoint.z;

            const gridX = Math.floor(x / CELL_SIZE);
            const gridY = Math.floor(z / CELL_SIZE);

            if (gridX >= 0 && gridX < BOARD_WIDTH && gridY >= 0 && gridY < BOARD_HEIGHT) {
                this.hoveredCell = [gridX, gridY];
                this.emit('hover', { gridX, gridY });
            } else {
                this.hoveredCell = null;
                this.emit('hover', { gridX: null, gridY: null });
            }
        } else {
            this.hoveredCell = null;
            this.emit('hover', { gridX: null, gridY: null });
        }
    }

    handlePointerDown(pointerInfo) {
        if (pointerInfo.event.button === 0) {
            if (pointerInfo.event.pointerType === 'mouse') {
                this.isLMBDown = true;
                this.lmbDownPosition = {
                    x: pointerInfo.event.clientX,
                    y: pointerInfo.event.clientY,
                };
                this.isLMBDragging = false;
            } else {
                // Restore immediate click logic for touch/pen to maintain compatibility
                const pickResult = this.scene.pick(
                    pointerInfo.event.clientX,
                    pointerInfo.event.clientY,
                );

                if (pickResult.hit && pickResult.pickedPoint) {
                    const x = pickResult.pickedPoint.x;
                    const z = pickResult.pickedPoint.z;
                    const gridX = Math.floor(x / CELL_SIZE);
                    const gridY = Math.floor(z / CELL_SIZE);

                    if (gridX >= 0 && gridX < BOARD_WIDTH && gridY >= 0 && gridY < BOARD_HEIGHT) {
                        this.emit('click', { gridX, gridY });
                    }
                }
            }
        } else if (pointerInfo.event.button === 2) {
            if (this.cameraController.cameraMode === "overview") {
                this.isPanning = true;
                this.lastPanPosition = {
                    x: pointerInfo.event.clientX,
                    y: pointerInfo.event.clientY,
                };
                this.canvas.style.cursor = "grabbing";
            } else {
                this.cameraController.activateMouseLook(
                    pointerInfo.event.clientX,
                    pointerInfo.event.clientY,
                );
            }
        }
    }

    handlePointerUp(pointerInfo) {
        if (pointerInfo.event.button === 0 && pointerInfo.event.pointerType === 'mouse') {
            if (this.isLMBDown && !this.isLMBDragging) {
                // Perform click only if not dragging
                const pickResult = this.scene.pick(
                    pointerInfo.event.clientX,
                    pointerInfo.event.clientY,
                );

                if (pickResult.hit && pickResult.pickedPoint) {
                    const x = pickResult.pickedPoint.x;
                    const z = pickResult.pickedPoint.z;
                    const gridX = Math.floor(x / CELL_SIZE);
                    const gridY = Math.floor(z / CELL_SIZE);

                    if (gridX >= 0 && gridX < BOARD_WIDTH && gridY >= 0 && gridY < BOARD_HEIGHT) {
                        this.emit('click', { gridX, gridY });
                    }
                }
            }
            this.isLMBDown = false;
            this.isLMBDragging = false;
        } else if (pointerInfo.event.button === 2) {
            if (this.cameraController.cameraMode === "overview") {
                this.isPanning = false;
                this.canvas.style.cursor = "default";
            } else {
                this.cameraController.deactivateMouseLook();
            }
        }
    }

    setupKeyboardListeners() {
        window.addEventListener("keydown", (event) => {
            const key = event.key.toLowerCase();

            switch (key) {
                case " ":
                case "enter":
                    event.preventDefault();
                    // Debounce end_turn to prevent spacebar spam
                    if (this.shouldAllowAction('end_turn')) {
                        this.emit('keydown', { key: 'end_turn' });
                    }
                    break;
                case "escape":
                    event.preventDefault();
                    // Debounce cancel to prevent accidental double-cancel
                    if (this.shouldAllowAction('cancel')) {
                        this.emit('keydown', { key: 'cancel' });
                    }
                    break;
                case "r":
                    event.preventDefault();
                    // Debounce deploy to prevent accidental double-deploy
                    if (this.shouldAllowAction('deploy')) {
                        this.emit('keydown', { key: 'deploy' });
                    }
                    break;
                case "v":
                    event.preventDefault();
                    // Debounce camera toggle to prevent rapid switching
                    if (this.shouldAllowAction('camera_toggle')) {
                        this.emit('keydown', { key: 'camera_toggle' });
                    }
                    break;
                case "tab":
                    event.preventDefault();
                    if (this.cameraController.cameraMode === "firstperson") {
                        // Debounce token cycling to prevent skipping tokens
                        if (this.shouldAllowAction('cycle_token')) {
                            this.emit('keydown', { key: 'cycle_token' });
                        }
                    }
                    break;
                case "q":
                    event.preventDefault();
                    this.emit('keydown', { key: 'rotate_left' });
                    break;
                case "e":
                    event.preventDefault();
                    this.emit('keydown', { key: 'rotate_right' });
                    break;
                case "m":
                    event.preventDefault();
                    // Debounce music toggle to prevent rapid on/off switching
                    if (this.shouldAllowAction('toggle_music')) {
                        this.emit('keydown', { key: 'toggle_music' });
                    }
                    break;
                case "w":
                    event.preventDefault();
                    if (this.deviceCapabilities && !this.deviceCapabilities.isMobile()) {
                        this.emit('keydown', { key: 'move_token_forward' });
                    } else {
                        this.emit('keydown', { key: 'camera_forward' });
                    }
                    break;
                case "s":
                    event.preventDefault();
                    if (this.deviceCapabilities && !this.deviceCapabilities.isMobile()) {
                        this.emit('keydown', { key: 'move_token_backward' });
                    } else {
                        this.emit('keydown', { key: 'camera_backward' });
                    }
                    break;
                case "a":
                    event.preventDefault();
                    if (this.deviceCapabilities && !this.deviceCapabilities.isMobile()) {
                        this.emit('keydown', { key: 'move_token_left' });
                    } else {
                        this.emit('keydown', { key: 'camera_left' });
                    }
                    break;
                case "d":
                    event.preventDefault();
                    if (this.deviceCapabilities && !this.deviceCapabilities.isMobile()) {
                        this.emit('keydown', { key: 'move_token_right' });
                    } else {
                        this.emit('keydown', { key: 'camera_right' });
                    }
                    break;
                case "arrowup":
                    event.preventDefault();
                    if (this.deviceCapabilities && !this.deviceCapabilities.isMobile()) {
                        this.emit('keydown', { key: 'look_up' });
                    } else {
                        this.emit('keydown', { key: 'camera_forward' });
                    }
                    break;
                case "arrowdown":
                    event.preventDefault();
                    if (this.deviceCapabilities && !this.deviceCapabilities.isMobile()) {
                        this.emit('keydown', { key: 'look_down' });
                    } else {
                        this.emit('keydown', { key: 'camera_backward' });
                    }
                    break;
                case "arrowleft":
                    event.preventDefault();
                    if (this.deviceCapabilities && !this.deviceCapabilities.isMobile()) {
                        this.emit('keydown', { key: 'rotate_left' });
                    } else {
                        this.emit('keydown', { key: 'camera_left' });
                    }
                    break;
                case "arrowright":
                    event.preventDefault();
                    if (this.deviceCapabilities && !this.deviceCapabilities.isMobile()) {
                        this.emit('keydown', { key: 'rotate_right' });
                    } else {
                        this.emit('keydown', { key: 'camera_right' });
                    }
                    break;
                case "+":
                case "=":
                    event.preventDefault();
                    this.emit('keydown', { key: 'zoom_out' });
                    break;
                case "-":
                case "_":
                    event.preventDefault();
                    this.emit('keydown', { key: 'zoom_in' });
                    break;
                default:
                    if (key >= '1' && key <= '4') {
                        event.preventDefault();
                        this.emit('keydown', { key: 'switch_player', playerIndex: parseInt(key) - 1 });
                    }
            }
        });

        window.addEventListener("keydown", (event) => {
            if (event.ctrlKey && event.key.toLowerCase() === "q") {
                event.preventDefault();
                this.emit('keydown', { key: 'quit' });
            }
        });
    }

    setupWindowListeners() {
        window.addEventListener("resize", () => {
            if (this.engine) {
                this.engine.resize();
            }
        });
    }

    getHoveredCell() {
        return this.hoveredCell;
    }

    isPanningActive() {
        return this.isPanning;
    }

    // ==========================================================================
    // Touch Gesture Handling (Tap Detection Only)
    // Camera controls are handled by Babylon.js built-in multi-touch
    // ==========================================================================

    setupTouchGestures() {
        console.log('[InputHandler] Setting up tap detection (camera handled by Babylon.js)');

        // Bind methods to preserve 'this' context
        this.boundOnTouchStart = (e) => this.onTouchStart(e);
        this.boundOnTouchEnd = (e) => this.onTouchEnd(e);

        this.canvas.addEventListener('touchstart', this.boundOnTouchStart, { passive: false });
        this.canvas.addEventListener('touchend', this.boundOnTouchEnd, { passive: false });
    }

    onTouchStart(event) {
        // Track touches for tap detection only
        for (let touch of event.changedTouches) {
            this.touches.set(touch.identifier, {
                startTime: Date.now(),
                startX: touch.clientX,
                startY: touch.clientY
            });
        }
    }

    onTouchEnd(event) {
        // Only handle single-touch taps (ignore multi-touch gestures)
        if (event.changedTouches.length !== 1) {
            // Clear all touches on multi-touch end
            for (let touch of event.changedTouches) {
                this.touches.delete(touch.identifier);
            }
            return;
        }

        const touch = event.changedTouches[0];
        const startTouch = this.touches.get(touch.identifier);

        if (startTouch) {
            const duration = Date.now() - startTouch.startTime;
            const distance = Math.sqrt(
                Math.pow(touch.clientX - startTouch.startX, 2) +
                Math.pow(touch.clientY - startTouch.startY, 2)
            );

            // Detect tap (short duration, small movement)
            if (duration < 300 && distance < 20) {
                this.handleTap(touch.clientX, touch.clientY);
            }

            this.touches.delete(touch.identifier);
        }
    }

    handleTap(x, y) {
        const now = Date.now();
        const isDoubleTap =
            this.lastTapTime &&
            (now - this.lastTapTime) < 300 &&
            this.lastTapPosition &&
            Math.abs(x - this.lastTapPosition.x) < 30 &&
            Math.abs(y - this.lastTapPosition.y) < 30;

        if (isDoubleTap) {
            // Double-tap detected - cancel action (like ESC key)
            console.log('[InputHandler] Double-tap detected - cancel action');
            this.emit('keydown', { key: 'cancel' });

            // Add haptic feedback
            if (this.deviceCapabilities && this.deviceCapabilities.hasVibration()) {
                this.deviceCapabilities.vibrate(50);
            }

            this.lastTapTime = 0;
            this.lastTapPosition = null;
        } else {
            // Single tap - same as left-click
            const pickResult = this.scene.pick(x, y);

            if (pickResult.hit && pickResult.pickedPoint) {
                const gridX = Math.floor(pickResult.pickedPoint.x / CELL_SIZE);
                const gridY = Math.floor(pickResult.pickedPoint.z / CELL_SIZE);

                if (gridX >= 0 && gridX < BOARD_WIDTH && gridY >= 0 && gridY < BOARD_HEIGHT) {
                    console.log(`[InputHandler] Tap at grid: ${gridX}, ${gridY}`);
                    this.emit('click', { gridX, gridY });

                    // Add haptic feedback
                    if (this.deviceCapabilities && this.deviceCapabilities.hasVibration()) {
                        this.deviceCapabilities.vibrate(30);
                    }
                }
            }

            this.lastTapTime = now;
            this.lastTapPosition = { x, y };
        }
    }

    /**
     * Clean up event listeners
     */
    dispose() {
        // Remove touch listeners
        if (this.boundOnTouchStart) {
            this.canvas.removeEventListener('touchstart', this.boundOnTouchStart);
        }
        if (this.boundOnTouchEnd) {
            this.canvas.removeEventListener('touchend', this.boundOnTouchEnd);
        }

        // Clear touch tracking
        this.touches.clear();

        console.log('[InputHandler] Disposed and cleaned up event listeners');
    }
}
