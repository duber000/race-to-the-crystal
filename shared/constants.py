"""
Game constants and configuration parameters.
"""

# Board Configuration
BOARD_WIDTH = 24
BOARD_HEIGHT = 24

# Token Configuration
TOKEN_HEALTH_VALUES = [10, 8, 6, 4]
TOKENS_PER_HEALTH_VALUE = 5  # 5 tokens of each health value = 20 total per player
TOKENS_PER_PLAYER = 20

# UI Configuration
UI_HEALTH_VALUES = [2, 4, 6, 8, 10, 12]  # Health values that may be displayed in UI

# Movement Configuration
TOKEN_MOVEMENT_RANGE = 2  # All tokens move 2 spaces

# Combat Configuration
COMBAT_DAMAGE_MULTIPLIER = 0.5  # Damage = health * 0.5 (i.e., health // 2)

# Generator Configuration
GENERATOR_COUNT = 4  # One per quadrant
GENERATOR_CAPTURE_TOKENS_REQUIRED = 2
GENERATOR_CAPTURE_TURNS_REQUIRED = 2
GENERATOR_TOKEN_REDUCTION = (
    2  # Each disabled generator reduces crystal requirement by 2
)

# Crystal Configuration
CRYSTAL_BASE_TOKENS_REQUIRED = 12
CRYSTAL_CAPTURE_TURNS_REQUIRED = 3

# Crystal Effects Configuration
CRYSTAL_EFFECT_INITIAL_DURATION = 4  # Effects last 4 turns initially
CRYSTAL_EFFECT_REDUCTION_PER_GENERATOR = 1  # Each generator captured reduces duration by 1 turn
PHANTOM_ENEMIES_COUNT = 3  # Number of phantom tokens to show per player
CRYSTAL_RANDOM_EFFECT_ROUND_INTERVAL = 5  # Trigger random crystal effect every N rounds
CRYSTAL_DAMAGE_BOOST_MULTIPLIER = 1.5  # Damage multiplier with damage boost
CRYSTAL_SPEED_BOOST_AMOUNT = 1  # Extra movement spaces with speed boost

# Crystal Effect Animations
CRYSTAL_EFFECT_ANIMATION_DURATION = 2.0  # Duration of crystal effect animations (seconds)
CRYSTAL_FOG_SPREAD_SPEED = 100.0  # Speed at which fog spreads from crystal (pixels/sec)
CRYSTAL_GHOST_COUNT = 5  # Number of ghost particles in phantom enemies animation
CRYSTAL_LIGHTNING_FLASH_DURATION = 0.1  # Duration of lightning flash on tokens (seconds)
CRYSTAL_WHIRLWIND_COUNT = 8  # Number of whirlwind particles in speed boost animation

# Mystery Square Configuration
MYSTERY_SQUARES_PER_QUADRANT = 2
TOTAL_MYSTERY_SQUARES = MYSTERY_SQUARES_PER_QUADRANT * 4

# Player Configuration
MIN_PLAYERS = 2
MAX_PLAYERS = 4

# Turn Configuration
TURN_TIMEOUT_SECONDS = 30  # Time limit per turn

# Network Configuration
DEFAULT_SERVER_HOST = "0.0.0.0"
DEFAULT_SERVER_PORT = 5555
HEARTBEAT_INTERVAL_SECONDS = 5
RECONNECT_TIMEOUT_SECONDS = 120

# Visual Configuration (for rendering phase)
BACKGROUND_COLOR = (0, 0, 0, 255)  # Pure black for vector arcade aesthetic (RGBA)
PLAYER_COLORS = [
    (0, 255, 255),  # Cyan - Player 1
    (255, 0, 255),  # Magenta - Player 2
    (255, 255, 0),  # Yellow - Player 3
    (0, 255, 0),  # Green - Player 4
]

# Grid rendering
CELL_SIZE = 32  # Pixels per cell
GRID_LINE_COLOR = (30, 30, 40)
GRID_LINE_WIDTH = 1

# Special cell colors
GENERATOR_COLOR = (100, 100, 200)
CRYSTAL_COLOR = (255, 255, 255)
MYSTERY_COLOR = (150, 0, 150)
START_COLOR = (50, 50, 50)

# Glow effect
GLOW_INTENSITY = 3  # Number of glow layers
GLOW_ALPHA_BASE = 40

# Animation
ANIMATION_SPEED = 0.1  # Speed multiplier for animations
MOVEMENT_ANIMATION_DURATION = 0.5  # seconds
COMBAT_ANIMATION_DURATION = 0.3  # seconds

# Window
DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 720
FPS_TARGET = 60

# 3D Rendering Configuration
WALL_HEIGHT = 50.0  # Height of vertical grid walls in 3D mode
TOKEN_HEIGHT_3D = 25.0  # Height of 3D hexagonal prism tokens
CAMERA_FOV = 75.0  # Field of view in degrees (wide for Battlezone feel)

# Camera modes: Overview vs First-Person
CAMERA_OVERVIEW_PITCH = -60.0  # Pitch for overview mode (looking down)
CAMERA_FIRST_PERSON_PITCH = (
    -15.0
)  # Pitch for first-person mode (looking forward/slightly down)
CAMERA_OVERVIEW_HEIGHT = 150.0  # Height for overview mode
CAMERA_FIRST_PERSON_HEIGHT = 30.0  # Height for first-person mode (token eye level)
CAMERA_FIRST_PERSON_OFFSET = -20.0  # Distance behind token in first-person mode

# Legacy constants (kept for initial camera setup)
CAMERA_HEIGHT_ABOVE_TOKEN = 100.0  # Eye height above token (high for better overview)
CAMERA_FORWARD_OFFSET = (
    -50.0
)  # Distance behind token (negative = behind, farther back for better view)

CAMERA_NEAR_PLANE = 1.0  # Near clipping plane
CAMERA_FAR_PLANE = 2000.0  # Far clipping plane (board is 768x768)

# UI Configuration
HUD_HEIGHT = 80  # Height of HUD bar at top of screen (pixels)
CORNER_INDICATOR_SIZE = 40  # Size of corner deployment indicator (pixels)
CORNER_INDICATOR_MARGIN = 20  # Margin from screen edges (pixels)
DEPLOYMENT_MENU_SPACING = 80  # Spacing for deployment menu options (pixels)
MENU_OPTION_CLICK_RADIUS = 30  # Click detection radius for menu options (pixels)
HEXAGON_SIDES = 6  # Number of sides for hexagonal shapes
CIRCLE_SEGMENTS = 12  # Number of segments for rendering circles

# Chat Widget Configuration (for network games)
CHAT_WIDGET_WIDTH = 320  # Width of chat widget (pixels)
CHAT_WIDGET_HEIGHT = 300  # Height of chat widget (pixels)
CHAT_WIDGET_X = 10  # X position of chat widget
CHAT_WIDGET_Y = 200  # Y position of chat widget (safe zone between corners)

# Camera Controls
CAMERA_PAN_SPEED = 10  # Speed of camera panning with arrow keys
CAMERA_INITIAL_ZOOM = 1.0  # Initial camera zoom level
CAMERA_ROTATION_INCREMENT = 15.0  # Degrees to rotate camera per key press (Q/E keys)
MOUSE_LOOK_SENSITIVITY = 0.2  # Mouse sensitivity for 3D camera look-around

# Audio Configuration
BACKGROUND_MUSIC_VOLUME = 0.9  # Volume for background music (0.0 to 1.0)
GENERATOR_HUM_VOLUME = (
    0.4  # Volume for generator hum audio (0.0 to 1.0) - reduced for chill vibe
)
SOUND_EFFECTS_VOLUME = 0.8  # Volume for game sound effects (0.0 to 1.0)

# Animation Configuration (extends existing ANIMATION_SPEED)
MYSTERY_ANIMATION_DURATION = 1.0  # Duration of mystery square animation (seconds)

# Board Generation Configuration
MYSTERY_PLACEMENT_MAX_ATTEMPTS = (
    100  # Max attempts to place mystery squares per quadrant
)
MYSTERY_PLACEMENT_EDGE_MARGIN = (
    2  # Margin from board edges when placing mystery squares
)

# 3D Special Cell Parameters
GENERATOR_HEIGHT_3D = 40.0
CRYSTAL_HEIGHT_3D = 50.0
MYSTERY_CYLINDER_SEGMENTS = 16
GENERATOR_CRYSTAL_LINE_SEGMENTS = 20

# 3D Colors (RGBA format)
BOARD_GRID_COLOR_3D = (0.0, 0.78, 0.78, 0.7)
GENERATOR_COLOR_3D = (1.0, 0.65, 0.0, 0.8)
CRYSTAL_COLOR_3D = (1.0, 0.0, 1.0, 0.9)
MYSTERY_COLOR_3D = (0.0, 1.0, 1.0, 0.7)
GEN_CRYSTAL_LINE_COLOR_3D = (1.0, 0.65, 0.0, 0.9)
DEPLOYMENT_ZONE_COLOR_3D = (1.0, 1.0, 0.6, 0.5)
VALID_MOVE_COLOR_3D = (0.0, 1.0, 0.7, 0.7)  # Slightly cyan-green
HOVER_INDICATOR_COLOR_3D = (1.0, 1.0, 1.0, 0.9)

# HUD and UI Colors (RGBA)
HUD_BACKGROUND_COLOR = (20, 20, 30, 200)
HUD_TEXT_COLOR_PRIMARY = (255, 255, 255)
HUD_TEXT_COLOR_SECONDARY = (200, 200, 200)
HUD_TEXT_COLOR_TERTIARY = (150, 150, 150)
