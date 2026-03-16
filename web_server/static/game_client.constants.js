// ==========================================================================
// Game Constants - Centralized configuration values
// ==========================================================================

// Board configuration
export const BOARD_CONFIG = {
    WIDTH: 24,
    HEIGHT: 24,
    CELL_SIZE: 32,
    WALL_HEIGHT: 40,
    TOKEN_HEIGHT: 20
};

// Player colors
export const PLAYER_COLORS = [
    new BABYLON.Color3(0, 1, 1),     // Cyan
    new BABYLON.Color3(1, 0, 1),     // Magenta
    new BABYLON.Color3(1, 1, 0),     // Yellow
    new BABYLON.Color3(0, 1, 0)      // Green
];

// Game phases
export const GAME_PHASE = {
    MOVEMENT: 1,
    ACTION: 2,
    END_TURN: 3
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

// Glow colors
export const GLOW_COLORS = {
    CYAN: new BABYLON.Color3(0, 0.78, 0.78),
    ORANGE: new BABYLON.Color3(1, 0.65, 0),
    MAGENTA: new BABYLON.Color3(1, 0, 1),
    WHITE: new BABYLON.Color3(1, 1, 1),
    GREEN: new BABYLON.Color3(0, 1, 0),
    RED: new BABYLON.Color3(1, 0, 0)
};

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
    SSE_SILENCE_MS: 30000,
    SSE_CHECK_INTERVAL_MS: 5000,
    ERROR_TIMEOUT_MS: 3000,
    MAX_ERRORS: 5,
    RECONNECT_MAX_DELAY_MS: 30000,
    RECONNECT_MAX_ATTEMPTS: 4
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
