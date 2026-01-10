/**
 * InputHandler - Mouse and keyboard input handling
 *
 * Responsibilities:
 * - Mouse movement, clicks, and hover detection
 * - Keyboard shortcuts
 * - Camera controls (pan, zoom, rotate)
 * - Event listener setup and cleanup
 *
 * Usage:
 *   const input = new InputHandler(scene, canvas, cameraController);
 *   input.setupEventListeners();
 *   input.on('click', (gridX, gridY) => { ... });
 *   input.on('keydown', (key) => { ... });
 */

class InputHandler {
    constructor(scene, canvas, cameraController, gameState, connectionState) {
        this.scene = scene;
        this.canvas = canvas;
        this.cameraController = cameraController;
        this.gameState = gameState;
        this.connectionState = connectionState;

        this.isPanning = false;
        this.lastPanPosition = { x: 0, y: 0 };
        this.hoveredCell = null;

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
        this.setupWindowListeners();
    }

    setupPointerListeners() {
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

        this.canvas.addEventListener("mousedown", (e) => {
            if (e.button === 2) {
                this.cameraController.activateMouseLook(e.clientX, e.clientY);
            }
        });

        this.canvas.addEventListener("mouseup", (e) => {
            if (e.button === 2) {
                this.cameraController.deactivateMouseLook();
            }
        });

        this.canvas.addEventListener("mousemove", (e) => {
            if (this.cameraController.mouseLookActive) {
                this.cameraController.handleMouseMotion(e.movementX, e.movementY);
            }
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
        return this.isPanning;
    }
}
