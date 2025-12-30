#!/usr/bin/env python3
"""
Test script to verify 3D controls functionality.
This script tests the core functionality without requiring a graphical interface.
"""

import sys
sys.path.insert(0, '.')

from client.camera_3d import FirstPersonCamera3D
from game.game_state import GameState
from shared.enums import PlayerColor
from shared.constants import CELL_SIZE
import numpy as np

def test_camera_rotation():
    """Test camera rotation functionality."""
    print("Testing camera rotation...")
    
    camera = FirstPersonCamera3D(1280, 720)
    initial_yaw = camera.yaw
    
    # Test rotation
    camera.rotate(yaw_delta=15.0)
    assert camera.yaw == initial_yaw + 15.0, f"Expected yaw {initial_yaw + 15.0}, got {camera.yaw}"
    
    camera.rotate(yaw_delta=-30.0)
    expected_yaw = (initial_yaw - 15.0) % 360.0
    assert camera.yaw == expected_yaw, f"Expected yaw {expected_yaw}, got {camera.yaw}"
    
    print("✓ Camera rotation works correctly")

def test_camera_follow_token():
    """Test camera follow token functionality."""
    print("Testing camera follow token...")
    
    camera = FirstPersonCamera3D(1280, 720)
    
    # Test following a token at position (5, 5) with rotation 45 degrees
    token_position = (5, 5)
    token_rotation = 45.0
    
    camera.follow_token(token_position, token_rotation)
    
    # Verify camera yaw is set to token rotation
    assert camera.yaw == token_rotation, f"Expected yaw {token_rotation}, got {camera.yaw}"
    
    # Verify camera position is calculated correctly
    expected_x = token_position[0] * CELL_SIZE + CELL_SIZE / 2
    expected_y = token_position[1] * CELL_SIZE + CELL_SIZE / 2
    
    # Camera should be offset behind the token
    offset_angle = np.radians(token_rotation + 180)
    offset_x = camera.forward_offset * np.cos(offset_angle)
    offset_y = camera.forward_offset * np.sin(offset_angle)
    
    expected_camera_x = expected_x + offset_x
    expected_camera_y = expected_y + offset_y
    
    assert abs(camera.position[0] - expected_camera_x) < 0.01, f"Expected X {expected_camera_x}, got {camera.position[0]}"
    assert abs(camera.position[1] - expected_camera_y) < 0.01, f"Expected Y {expected_camera_y}, got {camera.position[1]}"
    
    print("✓ Camera follow token works correctly")

def test_ray_casting():
    """Test ray casting functionality."""
    print("Testing ray casting...")
    
    camera = FirstPersonCamera3D(1280, 720)
    camera.position = np.array([12 * CELL_SIZE, 12 * CELL_SIZE, 30.0], dtype=np.float32)
    camera.yaw = 0.0
    camera.pitch = -30.0
    
    # Test ray from screen center
    screen_center_x = 1280 // 2
    screen_center_y = 720 // 2
    ray_origin, ray_direction = camera.screen_to_ray(screen_center_x, screen_center_y, 1280, 720)
    
    # Verify ray direction is normalized
    norm = np.linalg.norm(ray_direction)
    assert abs(norm - 1.0) < 0.01, f"Expected normalized direction (norm=1), got {norm}"
    
    # Test intersection with board plane
    intersection = camera.ray_intersect_plane(ray_origin, ray_direction, plane_z=0.0)
    assert intersection is not None, "Expected intersection with board plane"
    
    world_x, world_y = intersection
    grid_x, grid_y = camera.world_to_grid(world_x, world_y)
    
    # Should intersect somewhere on the board
    assert 0 <= grid_x < 24, f"Grid X out of bounds: {grid_x}"
    assert 0 <= grid_y < 24, f"Grid Y out of bounds: {grid_y}"
    
    print("✓ Ray casting works correctly")

def test_game_state_setup():
    """Test game state setup for 3D mode."""
    print("Testing game state setup...")
    
    game_state = GameState()
    game_state.add_player('player_1', 'Test Player', PlayerColor.CYAN)
    game_state.start_game()
    
    current_player = game_state.get_current_player()
    assert current_player is not None, "Expected current player"
    assert len(current_player.token_ids) > 0, "Expected player to have tokens"
    
    # Test token access
    token_id = current_player.token_ids[0]
    token = game_state.get_token(token_id)
    assert token is not None, f"Expected token {token_id} to exist"
    assert token.is_alive, "Expected token to be alive"
    assert token.is_deployed, "Expected token to be deployed"
    
    print("✓ Game state setup works correctly")

def test_token_cycling_logic():
    """Test token cycling logic."""
    print("Testing token cycling logic...")
    
    game_state = GameState()
    game_state.add_player('player_1', 'Test Player', PlayerColor.CYAN)
    game_state.start_game()
    
    current_player = game_state.get_current_player()
    alive_tokens = []
    for token_id in current_player.token_ids:
        token = game_state.get_token(token_id)
        if token and token.is_alive:
            alive_tokens.append(token_id)
    
    assert len(alive_tokens) > 0, "Expected at least one alive token"
    
    # Simulate cycling through tokens
    controlled_token_id = None
    for i in range(3):  # Cycle 3 times
        if controlled_token_id is not None:
            try:
                current_index = alive_tokens.index(controlled_token_id)
                next_index = (current_index + 1) % len(alive_tokens)
            except ValueError:
                next_index = 0
        else:
            next_index = 0
        
        controlled_token_id = alive_tokens[next_index]
        token = game_state.get_token(controlled_token_id)
        assert token is not None, f"Expected token {controlled_token_id} to exist"
    
    print("✓ Token cycling logic works correctly")

def main():
    """Run all tests."""
    print("=" * 60)
    print("3D Controls Functionality Test")
    print("=" * 60)
    
    try:
        test_camera_rotation()
        test_camera_follow_token()
        test_ray_casting()
        test_game_state_setup()
        test_token_cycling_logic()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed! 3D controls should work correctly.")
        print("=" * 60)
        
        print("\nControls that should work in 3D mode:")
        print("  - Q/E: Rotate camera left/right")
        print("  - TAB: Cycle through tokens")
        print("  - Left Click: Select tokens/move/attack")
        print("  - V: Toggle 2D/3D view")
        print("  - Space/Enter: End turn")
        print("  - ESC: Cancel selection")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)