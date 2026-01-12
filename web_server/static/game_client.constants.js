const CELL_SIZE = 32;
const BOARD_WIDTH = 24;
const BOARD_HEIGHT = 24;
const WALL_HEIGHT = 40;
const TOKEN_HEIGHT = 20;

const PLAYER_COLORS = [
    new BABYLON.Color3(0, 1, 1),
    new BABYLON.Color3(1, 0, 1),
    new BABYLON.Color3(1, 1, 0),
    new BABYLON.Color3(0, 1, 0),
];

const TurnPhase = {
    MOVEMENT: 1,
    ACTION: 2,
    END_TURN: 3,
};

const CrystalEffect = {
    FOG_OF_WAR: 1,
    PHANTOM_ENEMIES: 2,
    DAMAGE_BOOST: 3,
    SPEED_BOOST: 4,
};

// Crystal Effect Animation Constants
const CRYSTAL_EFFECT_ANIMATION_DURATION = 2.0; // seconds
const CRYSTAL_FOG_SPREAD_SPEED = 100.0; // pixels per second
const CRYSTAL_GHOST_COUNT = 5;
const CRYSTAL_LIGHTNING_FLASH_DURATION = 0.1; // seconds
const CRYSTAL_WHIRLWIND_COUNT = 8;

const CYAN_GLOW = new BABYLON.Color3(0, 0.78, 0.78);
const ORANGE_GLOW = new BABYLON.Color3(1, 0.65, 0);
const MAGENTA_GLOW = new BABYLON.Color3(1, 0, 1);
const WHITE_GLOW = new BABYLON.Color3(1, 1, 1);
const GREEN_GLOW = new BABYLON.Color3(0, 1, 0);
const RED_GLOW = new BABYLON.Color3(1, 0, 0);

const STATE = {
    DISCONNECTED: "DISCONNECTED",
    CONNECTING: "CONNECTING",
    CONNECTED: "CONNECTED",
    IN_LOBBY: "IN_LOBBY",
    GAME_STARTING: "GAME_STARTING",
    IN_GAME: "IN_GAME",
};