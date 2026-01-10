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

const CYAN_GLOW = new BABYLON.Color3(0, 0.78, 0.78);
const ORANGE_GLOW = new BABYLON.Color3(1, 0.65, 0);
const MAGENTA_GLOW = new BABYLON.Color3(1, 0, 1);
const WHITE_GLOW = new BABYLON.Color3(1, 1, 1);
const GREEN_GLOW = new BABYLON.Color3(0, 1, 0);

const STATE = {
    DISCONNECTED: "DISCONNECTED",
    CONNECTING: "CONNECTING",
    CONNECTED: "CONNECTED",
    IN_LOBBY: "IN_LOBBY",
    GAME_STARTING: "GAME_STARTING",
    IN_GAME: "IN_GAME",
};