/**
 * StateManager - Centralized Game State Management
 * 
 * This module handles:
 * - Storing and updating the game state
 * - Merging delta updates from SSE/WebSocket
 * - Tracking local player state (selection, control, valid moves)
 * - Coordinating updates between UI and Renderer
 */

import { GAME_PHASE, TurnPhase, STATE } from './game_client.constants.js';

/**
 * Recursive merge of delta into target object.
 * Shared utility used by both StateManager and NetworkManager.
 * - null values delete the key
 * - Arrays are replaced wholesale
 * - Objects are recursively merged
 * - Primitives are overwritten
 */
function mergeDelta(target, delta) {
    if (!delta || typeof delta !== 'object') return delta;

    // If target is not an object, just replace it
    if (!target || typeof target !== 'object') return delta;

    for (const key in delta) {
        const value = delta[key];

        if (value === null) {
            delete target[key];
        } else if (Array.isArray(value)) {
            target[key] = value;
        } else if (typeof value === 'object' && !Array.isArray(value)) {
            target[key] = mergeDelta(target[key] || {}, value);
        } else {
            target[key] = value;
        }
    }
    return target;
}

class StateManager {
    constructor() {
        this.gameState = null;
        this.localPlayerId = null;
        this.selectedTokenId = null;
        this.controlledTokenId = null;
        this.validMoves = new Set();
        this.turnPhase = TurnPhase.MOVEMENT;
        
        // Callbacks for when state changes
        this.onStateChange = null;
        this.replayMode = false;
    }

    /**
     * Handle a full state update from the server
     */
    setFullState(data) {
        if (data.game_state && data.game_state.perspective_player_id) {
            this.localPlayerId = data.game_state.perspective_player_id;
        }

        if (data.game_state) {
            this.gameState = data.game_state;
            this.turnPhase = this.gameState.turn_phase || TurnPhase.MOVEMENT;
        }

        this._notifyStateChange();
    }

    /**
     * Handle a delta state update from the server
     */
    applyDelta(delta) {
        if (!this.gameState) return;

        if (delta.perspective_player_id) {
            this.localPlayerId = delta.perspective_player_id;
        }

        this.gameState = this.mergeDelta(this.gameState, delta);
        this.turnPhase = this.gameState.turn_phase || TurnPhase.MOVEMENT;

        this._notifyStateChange();
    }

    /**
     * Recursive merge of delta into target object.
     * Delegates to the shared mergeDelta utility.
     */
    mergeDelta(target, delta) {
        return mergeDelta(target, delta);
    }

    /**
     * Update selection state
     */
    setSelectedToken(tokenId, validMoves = new Set()) {
        this.selectedTokenId = tokenId;
        this.validMoves = validMoves;
        this._notifyStateChange();
    }

    /**
     * Clear selection state.
     *
     * Only notifies when something was actually selected — clearing an empty
     * selection would otherwise re-enter the state-change callback for no
     * reason.
     */
    clearSelection() {
        const hadSelection = this.selectedTokenId !== null || this.validMoves.size > 0;
        this.selectedTokenId = null;
        this.validMoves = new Set();
        if (hadSelection) {
            this._notifyStateChange();
        }
    }

    /**
     * Update controlled token (first-person mode)
     */
    setControlledToken(tokenId) {
        this.controlledTokenId = tokenId;
        // (Doesn't necessarily need a full state notify unless UI depends on it)
    }

    /**
     * Check if it's the local player's turn
     */
    isLocalPlayerTurn() {
        return this.gameState && this.gameState.current_turn_player_id === this.localPlayerId;
    }

    /**
     * Get a token by ID
     */
    getToken(tokenId) {
        return this.gameState?.tokens?.[tokenId];
    }

    /**
     * Set callback for state changes
     */
    setChangeCallback(callback) {
        this.onStateChange = callback;
    }

    _notifyStateChange() {
        if (this.onStateChange) {
            this.onStateChange(this.gameState);
        }
    }
}

export { StateManager, mergeDelta };
