/**
 * GUIManager - Babylon.js GUI-based UI components
 *
 * Creates touch-friendly UI elements using Babylon.js GUI that work
 * on both desktop (clickable) and mobile (touchable).
 *
 * Features:
 * - Bottom action bar with Deploy, Move/Attack, End Turn buttons
 * - Deployment menu for token selection
 * - Camera toggle button
 * - Adaptive sizing based on device
 *
 * Usage:
 *   const gui = new GUIManager(scene, deviceCapabilities);
 *   gui.initialize();
 *   gui.on('action', (data) => { ... });
 */
class GUIManager {
    constructor(scene, deviceCapabilities) {
        this.scene = scene;
        this.deviceCapabilities = deviceCapabilities;
        this.advancedTexture = null;
        this.actionBar = null;
        this.deployMenu = null;
        this.deployMenuOverlay = null;
        this.moveAttackBtn = null;
        this.eventHandlers = new Map();

        console.log('[GUIManager] Initialized');
    }

    /**
     * Initialize the GUI system
     */
    initialize() {
        // Create fullscreen UI texture
        this.advancedTexture = BABYLON.GUI.AdvancedDynamicTexture.CreateFullscreenUI("UI", true, this.scene);

        // Show action bar on mobile (or optionally on desktop too)
        if (this.deviceCapabilities.isMobile()) {
            console.log('[GUIManager] Creating mobile action bar');
            this.createActionBar();
        }
    }

    /**
     * Create bottom action bar with game control buttons
     */
    createActionBar() {
        const uiScale = this.deviceCapabilities.getUIScale();

        // Bottom container
        this.actionBar = new BABYLON.GUI.StackPanel("actionBar");
        this.actionBar.height = `${Math.floor(100 * uiScale)}px`;
        this.actionBar.width = "100%";
        this.actionBar.verticalAlignment = BABYLON.GUI.Control.VERTICAL_ALIGNMENT_BOTTOM;
        this.actionBar.isVertical = false;
        this.actionBar.background = "rgba(0, 0, 0, 0.8)";
        this.actionBar.spacing = 10;
        this.actionBar.paddingBottom = `${Math.floor(10 * uiScale)}px`;
        this.actionBar.paddingTop = `${Math.floor(10 * uiScale)}px`;
        this.actionBar.paddingLeft = `${Math.floor(10 * uiScale)}px`;
        this.actionBar.paddingRight = `${Math.floor(10 * uiScale)}px`;

        this.advancedTexture.addControl(this.actionBar);

        // Deploy button
        const deployBtn = this.createActionButton("Deploy", "#0ff", () => {
            console.log('[GUIManager] Deploy button clicked');
            this.emit('action', { type: 'deploy' });
        }, uiScale);
        this.actionBar.addControl(deployBtn);

        // Move/Attack button (dynamic text based on game state)
        this.moveAttackBtn = this.createActionButton("Select", "#0ff", () => {
            console.log('[GUIManager] Move/Attack button clicked');
            this.emit('action', { type: 'move_attack' });
        }, uiScale);
        this.actionBar.addControl(this.moveAttackBtn);

        // End Turn button
        const endTurnBtn = this.createActionButton("End\nTurn", "#0f0", () => {
            console.log('[GUIManager] End Turn button clicked');
            this.emit('action', { type: 'end_turn' });
        }, uiScale);
        this.actionBar.addControl(endTurnBtn);

        // Camera Toggle button
        const cameraBtn = this.createActionButton("📷", "#f0f", () => {
            console.log('[GUIManager] Camera toggle button clicked');
            this.emit('action', { type: 'camera_toggle' });
        }, uiScale);
        cameraBtn.width = `${Math.floor(80 * uiScale)}px`;
        this.actionBar.addControl(cameraBtn);

        console.log('[GUIManager] Action bar created');
    }

    /**
     * Create a styled action button
     * @param {string} text - Button text
     * @param {string} color - Button color
     * @param {function} callback - Click callback
     * @param {number} uiScale - UI scale factor
     * @returns {BABYLON.GUI.Button}
     */
    createActionButton(text, color, callback, uiScale = 1.0) {
        const button = BABYLON.GUI.Button.CreateSimpleButton("btn_" + text.replace(/\n/g, '_'), text);
        button.width = "23%";
        button.height = `${Math.floor(70 * uiScale)}px`;
        button.color = color;
        button.background = "#000080";
        button.thickness = 2;
        button.fontSize = Math.floor(16 * uiScale);
        button.cornerRadius = 10;
        button.fontFamily = "'Courier New', monospace";
        button.shadowBlur = 10;
        button.shadowColor = color;

        // Hover effect (works on desktop)
        button.onPointerEnterObservable.add(() => {
            button.background = color;
            button.color = "#000";
        });

        button.onPointerOutObservable.add(() => {
            button.background = "#000080";
            button.color = color;
        });

        // Click/touch handler
        button.onPointerUpObservable.add(() => {
            callback();

            // Touch feedback
            if (this.deviceCapabilities.hasTouch() && this.deviceCapabilities.hasVibration()) {
                this.deviceCapabilities.vibrate(50);
            }
        });

        return button;
    }

    /**
     * Create deployment menu for selecting token health
     */
    createDeploymentMenu() {
        if (this.deployMenu) {
            this.deployMenu.isVisible = true;
            this.deployMenuOverlay.isVisible = true;
            return;
        }

        const uiScale = this.deviceCapabilities.getUIScale();

        // Overlay background
        this.deployMenuOverlay = new BABYLON.GUI.Rectangle("deployOverlay");
        this.deployMenuOverlay.width = "100%";
        this.deployMenuOverlay.height = "100%";
        this.deployMenuOverlay.background = "rgba(0, 0, 0, 0.7)";
        this.deployMenuOverlay.thickness = 0;
        this.advancedTexture.addControl(this.deployMenuOverlay);

        // Menu panel
        this.deployMenu = new BABYLON.GUI.Rectangle("deployMenu");
        this.deployMenu.width = this.deviceCapabilities.isMobile() ? "90%" : "400px";
        this.deployMenu.height = `${Math.floor(350 * uiScale)}px`;
        this.deployMenu.background = "rgba(0, 0, 128, 0.95)";
        this.deployMenu.thickness = 3;
        this.deployMenu.color = "#0ff";
        this.deployMenu.cornerRadius = 10;
        this.deployMenu.verticalAlignment = BABYLON.GUI.Control.VERTICAL_ALIGNMENT_CENTER;
        this.deployMenu.horizontalAlignment = BABYLON.GUI.Control.HORIZONTAL_ALIGNMENT_CENTER;

        this.deployMenuOverlay.addControl(this.deployMenu);

        // Title
        const title = new BABYLON.GUI.TextBlock("deployTitle", "SELECT TOKEN TO DEPLOY");
        title.height = "50px";
        title.fontSize = Math.floor(18 * uiScale);
        title.color = "#0ff";
        title.fontFamily = "'Courier New', monospace";
        title.fontWeight = "bold";
        title.textVerticalAlignment = BABYLON.GUI.Control.VERTICAL_ALIGNMENT_TOP;
        title.paddingTop = "20px";
        this.deployMenu.addControl(title);

        // Token buttons grid
        const grid = new BABYLON.GUI.Grid();
        grid.width = "90%";
        grid.height = `${Math.floor(200 * uiScale)}px`;
        grid.verticalAlignment = BABYLON.GUI.Control.VERTICAL_ALIGNMENT_CENTER;
        grid.addRowDefinition(0.5);
        grid.addRowDefinition(0.5);
        grid.addColumnDefinition(0.5);
        grid.addColumnDefinition(0.5);

        const tokenHealths = [10, 8, 6, 4];
        tokenHealths.forEach((health, index) => {
            const btn = this.createTokenButton(health, uiScale);
            const row = Math.floor(index / 2);
            const col = index % 2;
            grid.addControl(btn, row, col);
        });

        this.deployMenu.addControl(grid);

        // Close button
        const closeBtn = BABYLON.GUI.Button.CreateSimpleButton("closeDeployMenu", "Cancel");
        closeBtn.width = `${Math.floor(150 * uiScale)}px`;
        closeBtn.height = `${Math.floor(50 * uiScale)}px`;
        closeBtn.color = "#0ff";
        closeBtn.background = "#000";
        closeBtn.thickness = 2;
        closeBtn.fontSize = Math.floor(14 * uiScale);
        closeBtn.cornerRadius = 5;
        closeBtn.verticalAlignment = BABYLON.GUI.Control.VERTICAL_ALIGNMENT_BOTTOM;
        closeBtn.paddingBottom = `${Math.floor(20 * uiScale)}px`;
        closeBtn.fontFamily = "'Courier New', monospace";

        closeBtn.onPointerUpObservable.add(() => {
            this.hideDeploymentMenu();
        });

        this.deployMenu.addControl(closeBtn);

        // Click overlay to close
        this.deployMenuOverlay.onPointerUpObservable.add((eventData) => {
            // Only close if clicking on overlay, not menu
            if (eventData.target === this.deployMenuOverlay) {
                this.hideDeploymentMenu();
            }
        });

        console.log('[GUIManager] Deployment menu created');
    }

    /**
     * Create a token selection button
     * @param {number} health - Token health value
     * @param {number} uiScale - UI scale factor
     * @returns {BABYLON.GUI.Button}
     */
    createTokenButton(health, uiScale) {
        const button = BABYLON.GUI.Button.CreateSimpleButton(`token_${health}`, `${health} HP`);
        button.width = `${Math.floor(140 * uiScale)}px`;
        button.height = `${Math.floor(60 * uiScale)}px`;
        button.color = "#0ff";
        button.background = "#000080";
        button.thickness = 2;
        button.fontSize = Math.floor(16 * uiScale);
        button.cornerRadius = 8;
        button.fontFamily = "'Courier New', monospace";

        button.onPointerEnterObservable.add(() => {
            button.background = "#0ff";
            button.color = "#000";
        });

        button.onPointerOutObservable.add(() => {
            button.background = "#000080";
            button.color = "#0ff";
        });

        button.onPointerUpObservable.add(() => {
            console.log(`[GUIManager] Selected token: ${health} HP`);
            this.emit('deploy_select', { health });
            this.hideDeploymentMenu();

            if (this.deviceCapabilities.hasTouch() && this.deviceCapabilities.hasVibration()) {
                this.deviceCapabilities.vibrate(50);
            }
        });

        return button;
    }

    /**
     * Hide the deployment menu
     */
    hideDeploymentMenu() {
        if (this.deployMenuOverlay) {
            this.advancedTexture.removeControl(this.deployMenuOverlay);
            this.deployMenuOverlay = null;
            this.deployMenu = null;
        }
        console.log('[GUIManager] Deployment menu hidden');
    }

    /**
     * Show the deployment menu
     */
    showDeploymentMenu() {
        this.createDeploymentMenu();
    }

    /**
     * Update the Move/Attack button text dynamically
     * @param {string} text - New button text
     */
    updateMoveAttackButton(text) {
        if (this.moveAttackBtn && this.moveAttackBtn.textBlock) {
            this.moveAttackBtn.textBlock.text = text;
        }
    }

    /**
     * Set action bar visibility
     * @param {boolean} visible
     */
    setActionBarVisibility(visible) {
        if (this.actionBar) {
            this.actionBar.isVisible = visible;
        }
    }

    /**
     * Check if action bar exists
     * @returns {boolean}
     */
    hasActionBar() {
        return this.actionBar !== null;
    }

    // ==========================================================================
    // Event System
    // ==========================================================================

    /**
     * Register event handler
     * @param {string} event - Event name
     * @param {function} handler - Event handler function
     */
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
    }

    /**
     * Emit event to all registered handlers
     * @param {string} event - Event name
     * @param {object} data - Event data
     */
    emit(event, data) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => handler(data));
        }
    }

    /**
     * Clean up GUI resources
     */
    dispose() {
        if (this.advancedTexture) {
            this.advancedTexture.dispose();
        }
        console.log('[GUIManager] Disposed');
    }
}
