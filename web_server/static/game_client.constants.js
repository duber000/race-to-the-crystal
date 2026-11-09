// ==========================================================================
// Game Constants - Centralized configuration values
// ==========================================================================

// Board configuration
// WIDTH and HEIGHT MUST match the server's shared/constants (BOARD_WIDTH
// and BOARD_HEIGHT = 18) — the state grid is 18x18 and the cells are
// placed for that size. The desktop renderer framed the 3D view off this.
export const BOARD_CONFIG = {
    WIDTH: 18,
    HEIGHT: 18,
    CELL_SIZE: 32,
    WALL_HEIGHT: 40,
    TOKEN_HEIGHT: 20
};

// Player colors — lazy to avoid BABYLON global access at module parse time
let _playerColors = null;
export function getPlayerColors() {
    if (!_playerColors) {
        _playerColors = [
            new BABYLON.Color3(0, 1, 1),     // Cyan
            new BABYLON.Color3(1, 0, 1),     // Magenta
            new BABYLON.Color3(1, 1, 0),     // Yellow
            new BABYLON.Color3(0, 1, 0)      // Green
        ];
    }
    return _playerColors;
}
// Backward-compat alias (only safe to use after BABYLON loads)
export const PLAYER_COLORS = new Proxy([], {
    get(_, prop) { return getPlayerColors()[prop]; }
});

// Game phases
//
// These MUST match the wire format produced by the server's state serializer
// (game/state_serializer.kuki), which stringifies the enums:
//
//   "phase":      "SETUP" | "PLAYING" | "ENDED"
//   "turn_phase": "MOVEMENT" | "ACTION" | "END_TURN"
//
// They are strings, not ordinals — comparing against numbers silently
// disables every phase-gated behaviour (move vs. attack vs. deploy).
export const GAME_PHASE = {
    MOVEMENT: "MOVEMENT",
    ACTION: "ACTION",
    END_TURN: "END_TURN"
};

// Top-level game phase, as sent in game_state.phase
export const GAME_STATE_PHASE = {
    SETUP: "SETUP",
    PLAYING: "PLAYING",
    ENDED: "ENDED"
};

// Crystal effects
export const CRYSTAL_EFFECT = {
    FOG_OF_WAR: 1,
    PHANTOM_ENEMIES: 2,
    DAMAGE_BOOST: 3,
    SPEED_BOOST: 4
};

// Crystal effect animation constants
export const CRYSTAL_EFFECT_ANIMATION = {
    DURATION: 2.0,           // seconds
    FOG_SPREAD_SPEED: 100.0,  // pixels per second
    GHOST_COUNT: 5,
    LIGHTNING_FLASH_DURATION: 0.1, // seconds
    WHIRLWIND_COUNT: 8
};

// Glow colors — lazy to avoid BABYLON global access at module parse time
let _glowColors = null;
export function getGlowColors() {
    if (!_glowColors) {
        _glowColors = {
            CYAN:    new BABYLON.Color3(0, 0.78, 0.78),
            ORANGE:  new BABYLON.Color3(1, 0.65, 0),
            MAGENTA: new BABYLON.Color3(1, 0, 1),
            WHITE:   new BABYLON.Color3(1, 1, 1),
            GREEN:   new BABYLON.Color3(0, 1, 0),
            RED:     new BABYLON.Color3(1, 0, 0)
        };
    }
    return _glowColors;
}
// Backward-compat alias (only safe to use after BABYLON loads)
export const GLOW_COLORS = new Proxy({}, {
    get(_, prop) { return getGlowColors()[prop]; }
});

// UI states
export const UI_STATE = {
    DISCONNECTED: "DISCONNECTED",
    CONNECTING: "CONNECTING",
    CONNECTED: "CONNECTED",
    IN_LOBBY: "IN_LOBBY",
    GAME_STARTING: "GAME_STARTING",
    IN_GAME: "IN_GAME"
};

// Action debounce delay
export const INPUT_CONFIG = {
    ACTION_DEBOUNCE_MS: 200,
    DRAG_THRESHOLD: 10  // Pixels to trigger drag
};

// Timeout configuration
export const TIMEOUT_CONFIG = {
    ERROR_TIMEOUT_MS: 3000,
    MAX_ERRORS: 5,
};

// Backward compatibility aliases
export const TurnPhase = GAME_PHASE;
export const STATE = UI_STATE;
export const CELL_SIZE = BOARD_CONFIG.CELL_SIZE;

// Export derived constants for ES6 modules
export const WALL_HEIGHT = BOARD_CONFIG.WALL_HEIGHT;
export const TOKEN_HEIGHT = BOARD_CONFIG.TOKEN_HEIGHT;
export const BOARD_WIDTH = BOARD_CONFIG.WIDTH;
export const BOARD_HEIGHT = BOARD_CONFIG.HEIGHT;

