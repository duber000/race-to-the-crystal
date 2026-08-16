// ==========================================================================
// Input Handler - Manages mouse, keyboard, and touch input
// ==========================================================================

import { CELL_SIZE, INPUT_CONFIG, TIMEOUT_CONFIG } from './game_client.constants.js';

/**
 * Input Handler - Manages mouse, keyboard, and touch input for the game.
 * Handles pointer events, keyboard shortcuts, and touch gestures.
 */
class InputHandler {
    /**
     * Create an input handler.
     * @param {BABYLON.Scene} scene - Babylon.js scene
     * @param {HTMLCanvasElement} canvas - Canvas element
     * @param {CameraController} cameraController - Camera controller instance
     * @param {Object} gameState - Game state object
     * @param {string} connectionState - Current connection state
     * @param {BABYLON.Engine} engine - Babylon.js engine
     * @param {Object} deviceCapabilities - Device capabilities object
     */
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
        this.isLMBDown = false;
        this.isRMBDown = false;
        this.lmbDownPosition = { x: 0, y: 0 };
        this.isLMBDragging = false;
        this.lastPanPosition = { x: 0, y: 0 };
        this.hoveredCell = null;
        this.lastPointerMoveTime = 0;
        this.pointerLocked = false;

        // Touch state (for tap detection only)
        this.touches = new Map();
        this.lastTapTime = 0;
        this.lastTapPosition = null;

    // Action debouncing (prevents rapid key spam)
    this.lastActionTime = {};

    // Error handling configuration
    this.errorConfig = {
        maxErrors: TIMEOUT_CONFIG.MAX_ERRORS,
        errorTimeout: TIMEOUT_CONFIG.ERROR_TIMEOUT_MS
    };

    this.errorCount = 0;
    this.lastErrorTime = 0;

        this.eventHandlers = new Map();

        this.boundMouseMove = null;
        this.boundPointerDown = null;
        this.boundPointerUp = null;
    }

    /**
     * Register an event handler.
     * @param {string} event - Event name
     * @param {Function} handler - Event handler function
     */
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
    }

    /**
     * Emit an event to all registered handlers.
     * @param {string} event - Event name
     * @param {Object} data - Event data
     */
    emit(event, data) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => handler(data));
        }
    }

    /**
     * Setup all event listeners for pointer, keyboard, and touch input.
     */
    setupEventListeners() {
        this.setupPointerListeners();
        this.setupKeyboardListeners();

        // Add touch-specific listeners only if touch is supported
        if (this.deviceCapabilities && this.deviceCapabilities.hasTouch()) {
            this.setupTouchGestures();
        }
    }

    /**
     * Setup pointer event listeners for mouse and touch input.
     */
    setupPointerListeners() {
        // Store bound handlers for proper cleanup
        this.boundPointerLock = () => {
            this.pointerLocked = document.pointerLockElement === this.canvas;
        };
        this.boundPointerDown = (event) => {
            if (this.cameraController.cameraMode === "firstperson" && !this.pointerLocked) {
                this.canvas.requestPointerLock();
            }
            this.handlePointerDown(event);
        };
        this.boundPointerUp = (event) => {
            this.handlePointerUp(event);
        };
        this.boundMouseMove = (event) => {
            this.handleMouseMove(event);
        };
        this.boundMouseLeave = (event) => {
            this.handleMouseLeave(event);
        };
        this.boundTouchStart = (event) => {
            this.handleTouchStart(event);
        };
        this.boundTouchEnd = (event) => {
            this.handleTouchEnd(event);
        };
        this.boundTouchMove = (event) => {
            this.handleTouchMove(event);
        };

        // Pointer lock for FPS mouse look
        document.addEventListener('pointerlockchange', this.boundPointerLock);

        // Mouse down
        this.canvas.addEventListener('mousedown', this.boundPointerDown);

        // Mouse up
        this.canvas.addEventListener('mouseup', this.boundPointerUp);

        // Mouse move
        this.canvas.addEventListener('mousemove', this.boundMouseMove);

        // Mouse leave
        this.canvas.addEventListener('mouseleave', this.boundMouseLeave);

        // Touch start
        this.canvas.addEventListener('touchstart', this.boundTouchStart);

        // Touch end
        this.canvas.addEventListener('touchend', this.boundTouchEnd);

        // Touch move
        this.canvas.addEventListener('touchmove', this.boundTouchMove);
    }

    /**
     * Setup keyboard event listeners.
     */
    setupKeyboardListeners() {
        this.boundKeyDown = (event) => {
            this.handleKeyDown(event);
        };
        document.addEventListener('keydown', this.boundKeyDown);
    }

    /**
     * Setup touch gestures using Babylon.js built-in support.
     */
    setupTouchGestures() {
        // Setup Babylon.js built-in touch gestures for camera control
        if (this.cameraController.camera && this.cameraController.camera.inputs) {
            // Enable pinch-to-zoom and two-finger pan
            const pointers = this.cameraController.camera.inputs.attached.pointers;
            if (pointers) {
                pointers.multiTouchPanning = true;
                pointers.pinchToZoom = true;
            }
        }
    }

    /**
     * Handle pointer down event (mouse/touch press).
     * @param {PointerEvent} event - Pointer event
     */
    handlePointerDown(event) {
        if (event.button === 0) { // Left mouse button
            this.isLMBDown = true;
            this.lmbDownPosition = { x: event.clientX, y: event.clientY };
            this.lastPanPosition = { x: event.clientX, y: event.clientY };
            this.isLMBDragging = false;
        } else if (event.button === 2) { // Right mouse button
            this.isRMBDown = true;
            this.isPanning = true;
            this.lastPanPosition = { x: event.clientX, y: event.clientY };
        }

        // Prevent context menu on right-click
        if (event.button === 2) {
            event.preventDefault();
        }
    }

    /**
     * Handle pointer up event (mouse/touch release).
     * @param {PointerEvent} event - Pointer event
     */
    handlePointerUp(event) {
        if (event.button === 0 && this.isLMBDown) { // Left mouse button
            this.isLMBDown = false;
            
            // Check if it was a click or drag
            const deltaX = event.clientX - this.lmbDownPosition.x;
            const deltaY = event.clientY - this.lmbDownPosition.y;
            const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
            
            if (distance < INPUT_CONFIG.DRAG_THRESHOLD) {
                this.handleClick(event);
            }
            this.isLMBDragging = false;
        } else if (event.button === 2 && this.isRMBDown) { // Right mouse button
            this.isRMBDown = false;
            this.isPanning = false;
        }
    }

    /**
     * Handle mouse move event.
     * Updates hover state and handles camera panning.
     * @param {MouseEvent} event - Mouse event
     */
    handleMouseMove(event) {
        // FPS mouse look: pointer lock gives us raw movementX/Y
        if (this.cameraController.cameraMode === "firstperson" && this.pointerLocked) {
            const deltaX = event.movementX || 0;
            const deltaY = event.movementY || 0;
            this.cameraController.applyMouseLook(deltaX, deltaY);
            return;
        }

        // Update hover state
        this.updateHoverState(event);

        // LMB drag: pan the camera once movement passes the click threshold
        if (this.isLMBDown && !this.isLMBDragging) {
            const dx = event.clientX - this.lmbDownPosition.x;
            const dy = event.clientY - this.lmbDownPosition.y;
            if (Math.sqrt(dx * dx + dy * dy) > INPUT_CONFIG.DRAG_THRESHOLD) {
                this.isLMBDragging = true;
                this.lastPanPosition = { x: event.clientX, y: event.clientY };
            }
        }

        // Handle panning (right-button or left-button drag)
        if (this.isPanning || this.isLMBDragging) {
            const deltaX = event.clientX - this.lastPanPosition.x;
            const deltaY = event.clientY - this.lastPanPosition.y;

            this.cameraController.moveCameraRight(-deltaX * 0.01);
            this.cameraController.moveCameraForward(deltaY * 0.01);

            this.lastPanPosition = { x: event.clientX, y: event.clientY };
        }
    }

    /**
     * Handle mouse leave event.
     * Resets all input state.
     * @param {MouseEvent} event - Mouse event
     */
    handleMouseLeave(event) {
        this.isLMBDown = false;
        this.isRMBDown = false;
        this.isPanning = false;
        this.isLMBDragging = false;
        this.hoveredCell = null;
        this.emit('hover', { gridX: null, gridY: null });
    }

    /**
     * Handle touch start event.
     * Initializes tap detection.
     * @param {TouchEvent} event - Touch event
     */
    handleTouchStart(event) {
        // Handle single tap detection
        if (event.touches.length === 1) {
            const touch = event.touches[0];
            this.touches.set(touch.identifier, {
                startX: touch.clientX,
                startY: touch.clientY,
                startTime: Date.now(),
                isTap: true
            });
        }
    }

    /**
     * Handle touch end event.
     * Detects taps and emits click events.
     * @param {TouchEvent} event - Touch event
     */
    handleTouchEnd(event) {
        // Handle tap detection
        const now = Date.now();
        
        for (let i = 0; i < event.changedTouches.length; i++) {
            const touch = event.changedTouches[i];
            const touchData = this.touches.get(touch.identifier);
            
            if (touchData) {
                const deltaX = touch.clientX - touchData.startX;
                const deltaY = touch.clientY - touchData.startY;
                const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
                const duration = now - touchData.startTime;
                
                // Check if it was a tap (short duration, small movement)
                if (duration < 300 && distance < 10) {
                    this.handleTap(touch);
                }
                
                this.touches.delete(touch.identifier);
            }
        }
    }

    /**
     * Handle touch move event.
     * Updates touch position and invalidates tap detection if moved.
     * @param {TouchEvent} event - Touch event
     */
    handleTouchMove(event) {
        // Prevent default scrolling behavior (only when event is cancelable)
        if (event.cancelable) {
            event.preventDefault();
        }
        
        // Update touch data for tap detection
        for (let i = 0; i < event.touches.length; i++) {
            const touch = event.touches[i];
            const touchData = this.touches.get(touch.identifier);
            
            if (touchData) {
                touchData.currentX = touch.clientX;
                touchData.currentY = touch.clientY;
                
                // If movement exceeds threshold, it's not a tap
                const deltaX = touch.clientX - touchData.startX;
                const deltaY = touch.clientY - touchData.startY;
                const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
                
                if (distance > 10) {
                    touchData.isTap = false;
                }
            }
        }
    }

    /**
     * Exit pointer lock mode.
     */
    exitPointerLock() {
        if (this.pointerLocked) {
            document.exitPointerLock();
        }
    }

    /**
     * Handle keyboard key down event.
     * Processes game control keys and emits key events.
     * @param {KeyboardEvent} event - Keyboard event
     */
    handleKeyDown(event) {
        const key = event.key.toLowerCase();

        // Prevent default browser behavior for game keys
        const gameKeys = [
            'end', 'escape', 'd', 'r', 'v', 'tab', 'q', 'e', 'arrowup', 'arrowdown',
            'arrowleft', 'arrowright', 'm', 'w', 'a', 's', 'z', 'x', 'c', ' ',
            'enter', '+', '=', '-', '_', '1', '2', '3', '4'
        ];

        if (gameKeys.includes(key)) {
            event.preventDefault();
        }

        // Exit pointer lock on Escape or when toggling camera back to overview
        if (key === 'escape' || key === 'v') {
            this.exitPointerLock();
        }

        // Debounce rapid key presses
        if (!this.shouldAllowAction(key)) {
            return;
        }

        // Handle game keys
        switch (key) {
            case 'end':
            case ' ':
            case 'enter':
                this.emit('keydown', { key: 'end_turn' });
                break;
            case 'escape':
                this.emit('keydown', { key: 'cancel' });
                break;
            case 'd':
            case 'r':
                this.emit('keydown', { key: 'deploy' });
                break;
            case 'v':
                this.emit('keydown', { key: 'camera_toggle' });
                break;
            case 'tab':
                this.emit('keydown', { key: 'cycle_token' });
                break;
            case 'q':
                this.emit('keydown', { key: 'rotate_left' });
                break;
            case 'e':
                this.emit('keydown', { key: 'rotate_right' });
                break;
            case 'arrowup':
            case 'w':
                this.emit('keydown', { key: 'move_token_forward' });
                break;
            case 'arrowdown':
            case 's':
                this.emit('keydown', { key: 'move_token_backward' });
                break;
            case 'arrowleft':
            case 'a':
                this.emit('keydown', { key: 'move_token_left' });
                break;
            case 'arrowright':
                this.emit('keydown', { key: 'move_token_right' });
                break;
            case 'm':
                this.emit('keydown', { key: 'toggle_music' });
                break;
            case 'z':
                this.emit('keydown', { key: 'camera_forward' });
                break;
            case 'x':
                this.emit('keydown', { key: 'camera_backward' });
                break;
            case 'c':
                this.emit('keydown', { key: 'camera_left' });
                break;
            case '+':
            case '=':
                this.emit('keydown', { key: 'zoom_in' });
                break;
            case '-':
            case '_':
                this.emit('keydown', { key: 'zoom_out' });
                break;
            case '1':
            case '2':
            case '3':
            case '4':
                this.emit('keydown', { key: 'switch_player', playerIndex: parseInt(key, 10) - 1 });
                break;
            default:
                if (event.ctrlKey && key === 'q') {
                    this.emit('keydown', { key: 'quit' });
                }
                break;
        }
    }

    /**
     * Handle mouse click event.
     * Converts screen coordinates to grid coordinates and emits click event.
     * @param {MouseEvent} event - Mouse event
     */
    handleClick(event) {
        // Convert screen coordinates to grid coordinates
        const rect = this.canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        // Use Babylon.js picking to get grid coordinates
        const pickResult = this.scene.pick(x, y);
        if (pickResult.hit) {
            // Convert 3D position to grid coordinates
            const worldPos = pickResult.pickedPoint;
            const gridX = Math.floor(worldPos.x / CELL_SIZE);
            const gridY = Math.floor(worldPos.z / CELL_SIZE);
            
            // Emit click event
            this.emit('click', { gridX, gridY });
        }
    }

    /**
     * Handle touch tap event.
     * Converts touch coordinates to grid coordinates and emits click event.
     * @param {Touch} touch - Touch object
     */
    handleTap(touch) {
        // Convert touch coordinates to grid coordinates
        const rect = this.canvas.getBoundingClientRect();
        const x = touch.clientX - rect.left;
        const y = touch.clientY - rect.top;
        
        // Use Babylon.js picking to get grid coordinates
        const pickResult = this.scene.pick(x, y);
        if (pickResult.hit) {
            // Convert 3D position to grid coordinates
            const worldPos = pickResult.pickedPoint;
            const gridX = Math.floor(worldPos.x / CELL_SIZE);
            const gridY = Math.floor(worldPos.z / CELL_SIZE);
            
            // Emit click event (treat tap as click)
            this.emit('click', { gridX, gridY });
        }
    }

    /**
     * Update hover state based on mouse position.
     * Emits hover event when hovered cell changes.
     * @param {MouseEvent} event - Mouse event
     */
    updateHoverState(event) {
        // Convert screen coordinates to grid coordinates
        const rect = this.canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        // Use Babylon.js picking to get grid coordinates
        const pickResult = this.scene.pick(x, y);
        if (pickResult.hit) {
            // Convert 3D position to grid coordinates
            const worldPos = pickResult.pickedPoint;
            const gridX = Math.floor(worldPos.x / CELL_SIZE);
            const gridY = Math.floor(worldPos.z / CELL_SIZE);
            
            // Only emit hover event if cell has changed
            if (this.hoveredCell === null || 
                this.hoveredCell.gridX !== gridX || 
                this.hoveredCell.gridY !== gridY) {
                
                this.hoveredCell = { gridX, gridY };
                this.emit('hover', { gridX, gridY });
            }
        } else if (this.hoveredCell !== null) {
            // No cell hovered
            this.hoveredCell = null;
            this.emit('hover', { gridX: null, gridY: null });
        }
    }

    /**
     * Check if action should be allowed based on debounce timing.
     * @param {string} actionKey - Action identifier
     * @returns {boolean} True if action is allowed
     */
    shouldAllowAction(actionKey) {
        const now = Date.now();
        const lastTime = this.lastActionTime[actionKey];

        if (!lastTime || (now - lastTime) > INPUT_CONFIG.ACTION_DEBOUNCE_MS) {
            this.lastActionTime[actionKey] = now;
            return true;
        }

        return false;
    }

    /**
     * Dispose all event listeners and clean up resources.
     */
    dispose() {
        // Remove event listeners using stored bound handlers
        if (this.boundPointerLock) document.removeEventListener('pointerlockchange', this.boundPointerLock);
        if (this.boundPointerDown) this.canvas.removeEventListener('mousedown', this.boundPointerDown);
        if (this.boundPointerUp) this.canvas.removeEventListener('mouseup', this.boundPointerUp);
        if (this.boundMouseMove) this.canvas.removeEventListener('mousemove', this.boundMouseMove);
        if (this.boundMouseLeave) this.canvas.removeEventListener('mouseleave', this.boundMouseLeave);
        if (this.boundTouchStart) this.canvas.removeEventListener('touchstart', this.boundTouchStart);
        if (this.boundTouchEnd) this.canvas.removeEventListener('touchend', this.boundTouchEnd);
        if (this.boundTouchMove) this.canvas.removeEventListener('touchmove', this.boundTouchMove);
        if (this.boundKeyDown) document.removeEventListener('keydown', this.boundKeyDown);
        
        // Clear event handlers
        this.eventHandlers.clear();
        this.touches.clear();
    }
}

export { InputHandler };
