// ==========================================================================
// Input Handler - Manages mouse, keyboard, and touch input
// ==========================================================================

import { CELL_SIZE, INPUT_CONFIG } from './game_client.constants.js';

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
        this.isLMBDown = false;
        this.isRMBDown = false;
        this.lmbDownPosition = { x: 0, y: 0 };
        this.isLMBDragging = false;
        this.lastPanPosition = { x: 0, y: 0 };
        this.hoveredCell = null;
        this.lastPointerMoveTime = 0;

        // Touch state (for tap detection only)
        this.touches = new Map();
        this.lastTapTime = 0;
        this.lastTapPosition = null;

    // Action debouncing (prevents rapid key spam)
    this.lastActionTime = {};

    // Error handling configuration
    this.errorConfig = {
        maxErrors: 5,
        errorTimeout: 3000
    };

    this.errorCount = 0;
    this.lastErrorTime = 0;

        this.eventHandlers = new Map();

        this.boundMouseMove = null;
        this.boundPointerDown = null;
        this.boundPointerUp = null;
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
    }

    setupPointerListeners() {
        // Mouse down
        this.canvas.addEventListener('mousedown', (event) => {
            this.handlePointerDown(event);
        });

        // Mouse up
        this.canvas.addEventListener('mouseup', (event) => {
            this.handlePointerUp(event);
        });

        // Mouse move
        this.canvas.addEventListener('mousemove', (event) => {
            this.handleMouseMove(event);
        });

        // Mouse leave
        this.canvas.addEventListener('mouseleave', (event) => {
            this.handleMouseLeave(event);
        });

        // Touch start
        this.canvas.addEventListener('touchstart', (event) => {
            this.handleTouchStart(event);
        });

        // Touch end
        this.canvas.addEventListener('touchend', (event) => {
            this.handleTouchEnd(event);
        });

        // Touch move
        this.canvas.addEventListener('touchmove', (event) => {
            this.handleTouchMove(event);
        });
    }

    setupKeyboardListeners() {
        document.addEventListener('keydown', (event) => {
            this.handleKeyDown(event);
        });
    }

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

    handlePointerUp(event) {
        if (event.button === 0 && this.isLMBDown) { // Left mouse button
            this.isLMBDown = false;
            
            // Check if it was a click or drag
            const deltaX = event.clientX - this.lmbDownPosition.x;
            const deltaY = event.clientY - this.lmbDownPosition.y;
            const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
            
            if (distance < 5) { // Click threshold
                this.handleClick(event);
            }
        } else if (event.button === 2 && this.isRMBDown) { // Right mouse button
            this.isRMBDown = false;
            this.isPanning = false;
        }
    }

    handleMouseMove(event) {
        // FPS mouse look: when in first-person mode, mouse movement rotates the view
        if (this.cameraController.cameraMode === "firstperson") {
            if (this.isLMBDown || this.isRMBDown) {
                const deltaX = event.clientX - this.lastPanPosition.x;
                const deltaY = event.clientY - this.lastPanPosition.y;
                this.cameraController.applyMouseLook(deltaX, deltaY);
                this.lastPanPosition = { x: event.clientX, y: event.clientY };
            }
            return;
        }

        // Update hover state
        this.updateHoverState(event);

        // Handle panning
        if (this.isPanning) {
            const deltaX = event.clientX - this.lastPanPosition.x;
            const deltaY = event.clientY - this.lastPanPosition.y;

            this.cameraController.moveCameraRight(-deltaX * 0.01);
            this.cameraController.moveCameraForward(deltaY * 0.01);

            this.lastPanPosition = { x: event.clientX, y: event.clientY };
        }
    }

    handleMouseLeave(event) {
        this.isLMBDown = false;
        this.isRMBDown = false;
        this.isPanning = false;
        this.hoveredCell = null;
        this.emit('hover', { gridX: null, gridY: null });
    }

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

    handleTouchMove(event) {
        // Prevent default scrolling behavior
        event.preventDefault();
        
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

    handleKeyDown(event) {
        const key = event.key.toLowerCase();
        
        // Prevent default browser behavior for game keys
        const gameKeys = [
            'end', 'escape', 'd', 'v', 'tab', 'q', 'e', 'arrowup', 'arrowdown',
            'arrowleft', 'arrowright', 'm', 'w', 'a', 's', 'z', 'x', 'c'
        ];
        
        if (gameKeys.includes(key)) {
            event.preventDefault();
        }

        // Debounce rapid key presses
        if (!this.shouldAllowAction(key)) {
            return;
        }

        // Handle game keys
        switch (key) {
            case 'end':
                this.emit('keydown', { key: 'end_turn' });
                break;
            case 'escape':
                this.emit('keydown', { key: 'cancel' });
                break;
            case 'd':
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
            case 'd':
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
            case ' ': // Space bar for camera right
                this.emit('keydown', { key: 'camera_right' });
                break;
        }
    }

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

  shouldAllowAction(actionKey) {
    const now = Date.now();
    const lastTime = this.lastActionTime[actionKey];

    if (!lastTime || (now - lastTime) > INPUT_CONFIG.ACTION_DEBOUNCE_MS) {
        this.lastActionTime[actionKey] = now;
        return true;
    }

    return false;
  }

    dispose() {
        // Remove event listeners
        this.canvas.removeEventListener('mousedown', this.boundPointerDown);
        this.canvas.removeEventListener('mouseup', this.boundPointerUp);
        this.canvas.removeEventListener('mousemove', this.boundMouseMove);
        
        document.removeEventListener('keydown', this.boundKeyDown);
        
        // Clear event handlers
        this.eventHandlers.clear();
    }
}

export { InputHandler };
