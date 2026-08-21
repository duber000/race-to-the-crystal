/**
 * Renderer3D - Main Renderer Module
 *
 * This module imports the base Renderer3D class and prototype extensions
 * from separate modules. It re-exports Renderer3D for use by game_client.js
 *
 * Prototype modules (imported for side effects):
 * - renderer.special.js: Special cells (crystal, generators, mystery)
 * - renderer.indicators.js: Hover, valid move, valid attack indicators
 * - renderer.colors.js: Special cell color updates
 * - renderer.animations.js: Animation loop and effects
 */

// Import base class
import { Renderer3D } from './renderer.base.js';

// Import TokenRenderer
import { TokenRenderer } from './renderer.tokens.js';

// Import prototype extensions (for side effects)
import './renderer.special.js';
import './renderer.indicators.js';
import './renderer.colors.js';
import './renderer.animations.js';

// Add TokenRenderer to prototype for use by other modules
Renderer3D.prototype.TokenRenderer = TokenRenderer;

/**
 * Initialize token renderer with scene
 */
Renderer3D.prototype.initTokenRenderer = function() {
    if (!this.tokenRenderer && this.scene) {
        this.tokenRenderer = new TokenRenderer(this.scene);
        this.tokenRenderer.localPlayerId = this.localPlayerId;
    }
    return this.tokenRenderer;
};

/**
 * Update tokens - delegates to TokenRenderer
 */
Renderer3D.prototype.updateTokens = function(gameState) {
    this.initTokenRenderer();
    if (this.tokenRenderer) {
        this.tokenRenderer.updateTokens(gameState);
    }
};

/**
 * Update token selection glow effect
 * Delegates to TokenRenderer
 */
Renderer3D.prototype.updateTokenSelectionGlow = function(selectedTokenId) {
    if (this.tokenRenderer) {
        this.tokenRenderer.updateTokenSelectionGlow(selectedTokenId);
    }
};

/**
 * Hide the controlled token in first-person mode (null shows all tokens).
 * Delegates to TokenRenderer; safe to call every frame.
 */
Renderer3D.prototype.updateControlledTokenVisibility = function(controlledTokenId) {
    if (this.tokenRenderer) {
        this.tokenRenderer.setControlledToken(controlledTokenId);
    }
};

/**
 * Cleanup token resources
 */
Renderer3D.prototype.cleanupTokens = function() {
    if (this.tokenRenderer) {
        this.tokenRenderer.cleanup();
    }
};

// Re-export Renderer3D
export { Renderer3D };
