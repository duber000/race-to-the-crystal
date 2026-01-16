/**
 * InputHandler - Mouse, keyboard, and touch input handling
 *
 * Responsibilities:
 * - Mouse movement, clicks, and hover detection
 * - Keyboard shortcuts
 * - Touch gestures (tap, pinch, pan, rotate)
 * - Camera controls (pan, zoom, rotate)
 * - Event listener setup and cleanup
 *
 * Usage:
 *   const input = new InputHandler(scene, canvas, cameraController, gameState, connectionState, engine, deviceCapabilities);
 *   input.setupEventListeners();
 *   input.on('click', (gridX, gridY) => { ... });
 *   input.on('keydown', (key) => { ... });
 */

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
        this.isPanning = false;
        this.lastPanPosition = { x: 0, y: 0 };
        this.hoveredCell = null;

        // Touch state
        this.touches = new Map();
        this.gestureStartDistance = 0;
        this.gestureStartAngle = 0;
        this.lastTapTime = 0;
        this.lastTapPosition = null;
        this.isTouchPanning = false;

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

        if (this.cameraController.mouseLookActive) {
            this.cameraController.handleMouseMotion(dx, dy);
            return;
        }

        if (this.isPanning && this.cameraController.cameraMode === "overview") {
            this.cameraController.handlePan(dx, dy);
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
        if (pointerInfo.event.button === 2) {
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
                    this.emit('keydown', { key: 'end_turn' });
                    break;
                case "escape":
                    event.preventDefault();
                    this.emit('keydown', { key: 'cancel' });
                    break;
                case "r":
                    event.preventDefault();
                    this.emit('keydown', { key: 'deploy' });
                    break;
                case "v":
                    event.preventDefault();
                    this.emit('keydown', { key: 'camera_toggle' });
                    break;
                case "tab":
                    event.preventDefault();
                    if (this.cameraController.cameraMode === "firstperson") {
                        this.emit('keydown', { key: 'cycle_token' });
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
                    this.emit('keydown', { key: 'toggle_music' });
                    break;
                case "w":
                case "arrowup":
                    event.preventDefault();
                    this.emit('keydown', { key: 'camera_forward' });
                    break;
                case "s":
                case "arrowdown":
                    event.preventDefault();
                    this.emit('keydown', { key: 'camera_backward' });
                    break;
                case "a":
                case "arrowleft":
                    event.preventDefault();
                    this.emit('keydown', { key: 'camera_left' });
                    break;
                case "d":
                case "arrowright":
                    event.preventDefault();
                    this.emit('keydown', { key: 'camera_right' });
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
        return this.isPanning || this.isTouchPanning;
    }

    // ==========================================================================
    // Touch Gesture Handling
    // ==========================================================================

    setupTouchGestures() {
        console.log('[InputHandler] Setting up touch gesture support');

        this.canvas.addEventListener('touchstart', (e) => this.onTouchStart(e), { passive: false });
        this.canvas.addEventListener('touchmove', (e) => this.onTouchMove(e), { passive: false });
        this.canvas.addEventListener('touchend', (e) => this.onTouchEnd(e), { passive: false });
        this.canvas.addEventListener('touchcancel', (e) => this.onTouchEnd(e), { passive: false });
    }

    onTouchStart(event) {
        event.preventDefault();

        for (let touch of event.changedTouches) {
            this.touches.set(touch.identifier, {
                x: touch.clientX,
                y: touch.clientY,
                startTime: Date.now(),
                startX: touch.clientX,
                startY: touch.clientY
            });
        }

        // Two-finger gesture detected
        if (event.touches.length === 2) {
            const touch1 = event.touches[0];
            const touch2 = event.touches[1];

            this.gestureStartDistance = this.getDistance(touch1, touch2);
            this.gestureStartAngle = this.getAngle(touch1, touch2);
            this.isTouchPanning = false; // Disable single-finger pan during two-finger gesture
        } else if (event.touches.length === 1) {
            this.isTouchPanning = true;
        }
    }

    onTouchMove(event) {
        event.preventDefault();

        if (event.touches.length === 2) {
            const touch1 = event.touches[0];
            const touch2 = event.touches[1];

            // Pinch to zoom
            const currentDistance = this.getDistance(touch1, touch2);
            const zoomDelta = (currentDistance - this.gestureStartDistance) * 0.5;

            if (Math.abs(zoomDelta) > 5) {
                this.cameraController.adjustZoom(-zoomDelta);
                this.gestureStartDistance = currentDistance;
            }

            // Two-finger rotate (for first-person mode)
            if (this.cameraController.cameraMode === 'firstperson') {
                const currentAngle = this.getAngle(touch1, touch2);
                const rotateDelta = currentAngle - this.gestureStartAngle;

                if (Math.abs(rotateDelta) > 2) {
                    this.cameraController.rotateCameraByAngle(rotateDelta * 0.5);
                    this.gestureStartAngle = currentAngle;
                }
            }
        } else if (event.touches.length === 1 && this.isTouchPanning) {
            // Single-finger pan/drag (acts like right-click drag on desktop)
            const touch = event.touches[0];
            const startTouch = this.touches.get(touch.identifier);

            if (startTouch) {
                const dx = touch.clientX - startTouch.x;
                const dy = touch.clientY - startTouch.y;

                // Pan camera if moved more than threshold
                if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
                    this.cameraController.handlePan(dx, dy);

                    // Update for next frame
                    startTouch.x = touch.clientX;
                    startTouch.y = touch.clientY;
                }
            }
        }
    }

    onTouchEnd(event) {
        for (let touch of event.changedTouches) {
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

        // Reset panning state when all touches are released
        if (event.touches.length === 0) {
            this.isTouchPanning = false;
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

    getDistance(touch1, touch2) {
        return Math.sqrt(
            Math.pow(touch2.clientX - touch1.clientX, 2) +
            Math.pow(touch2.clientY - touch1.clientY, 2)
        );
    }

    getAngle(touch1, touch2) {
        return Math.atan2(
            touch2.clientY - touch1.clientY,
            touch2.clientX - touch1.clientX
        ) * 180 / Math.PI;
    }
}
