#!/usr/bin/env python3
"""
Comprehensive test for all 3D controls functionality.
This script tests the complete 3D navigation system including mouse-look.
"""

import sys
sys.path.insert(0, '.')

from client.camera_3d import FirstPersonCamera3D
from game.game_state import GameState
from shared.enums import PlayerColor
from shared.constants import CELL_SIZE
import numpy as np

def test_complete_3d_navigation():
    """Test the complete 3D navigation system."""
    print("Testing complete 3D navigation system...")
    
    # Create a game state for testing
    game_state = GameState()
    game_state.add_player('player_1', 'Test Player', PlayerColor.CYAN)
    game_state.start_game()
    
    # Create a mock game window (without actually creating a window)
    # We'll test the camera and navigation logic directly
    camera = FirstPersonCamera3D(1280, 720)
    
    # Test 1: Basic camera setup
    print("  1. Testing basic camera setup...")
    assert camera.fov == 75.0, f"Expected FOV 75.0, got {camera.fov}"
    assert camera.aspect_ratio == 1280/720, f"Expected aspect ratio {1280/720}, got {camera.aspect_ratio}"
    
    # Test 2: Token following
    print("  2. Testing token following...")
    token_position = (5, 5)
    token_rotation = 45.0
    camera.follow_token(token_position, token_rotation)
    
    assert camera.yaw == token_rotation, f"Expected yaw {token_rotation}, got {camera.yaw}"
    
    # Test 3: Manual rotation (Q/E keys simulation)
    print("  3. Testing manual rotation...")
    initial_yaw = camera.yaw
    camera.rotate(yaw_delta=15.0)  # Simulate Q key
    expected_yaw = (initial_yaw + 15.0) % 360.0
    assert abs(camera.yaw - expected_yaw) < 0.01, f"Expected yaw {expected_yaw}, got {camera.yaw}"
    
    # Test 4: Mouse-look rotation
    print("  4. Testing mouse-look rotation...")
    # Simulate mouse movement (dx=100, dy=50 with sensitivity=0.2)
    dx, dy = 100, 50
    sensitivity = 0.2
    yaw_delta = -dx * sensitivity
    pitch_delta = -dy * sensitivity
    
    camera.rotate(yaw_delta=yaw_delta, pitch_delta=pitch_delta)
    expected_yaw = (camera.yaw + yaw_delta) % 360.0
    expected_pitch = camera.pitch + pitch_delta
    
    assert abs(camera.yaw - expected_yaw) < 0.01, f"Expected yaw {expected_yaw}, got {camera.yaw}"
    assert abs(camera.pitch - expected_pitch) < 0.01, f"Expected pitch {expected_pitch}, got {camera.pitch}"
    
    # Test 5: Pitch clamping
    print("  5. Testing pitch clamping...")
    camera.rotate(pitch_delta=100.0)  # Try to go beyond max
    assert camera.pitch <= 89.0, f"Pitch should be clamped to <= 89.0, got {camera.pitch}"
    
    camera.rotate(pitch_delta=-200.0)  # Try to go beyond min
    assert camera.pitch >= -89.0, f"Pitch should be clamped to >= -89.0, got {camera.pitch}"
    
    # Test 6: Ray casting for selection
    print("  6. Testing ray casting...")
    # Position camera looking at board center
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
    
    # Test 7: View and projection matrices
    print("  7. Testing view and projection matrices...")
    view_matrix = camera.get_view_matrix()
    projection_matrix = camera.get_projection_matrix()
    
    # Matrices should be 4x4
    assert view_matrix.shape == (4, 4), f"View matrix should be 4x4, got {view_matrix.shape}"
    assert projection_matrix.shape == (4, 4), f"Projection matrix should be 4x4, got {projection_matrix.shape}"
    
    # Matrices should be invertible
    view_det = np.linalg.det(view_matrix)
    proj_det = np.linalg.det(projection_matrix)
    assert abs(view_det) > 0.01, f"View matrix should be invertible, determinant: {view_det}"
    assert abs(proj_det) > 0.01, f"Projection matrix should be invertible, determinant: {proj_det}"
    
    print("✓ Complete 3D navigation system works correctly")

def test_game_state_integration():
    """Test integration with game state."""
    print("Testing game state integration...")
    
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
    
    # Test that token has valid position
    grid_x, grid_y = token.position
    assert 0 <= grid_x < 24, f"Token X position out of bounds: {grid_x}"
    assert 0 <= grid_y < 24, f"Token Y position out of bounds: {grid_y}"
    
    print("✓ Game state integration works correctly")

def main():
    """Run all comprehensive 3D controls tests."""
    print("=" * 70)
    print("Comprehensive 3D Controls Functionality Test")
    print("=" * 70)
    
    try:
        test_complete_3d_navigation()
        test_game_state_integration()
        
        print("\n" + "=" * 70)
        print("✓ All comprehensive 3D controls tests passed!")
        print("=" * 70)
        
        print("\n🎮 3D Controls Summary:")
        print("━" * 70)
        print("📌 Basic Navigation:")
        print("  • Q/E keys: Rotate camera left/right around current token")
        print("  • TAB key: Cycle through your tokens")
        print("  • Arrow keys/WASD: Move camera position")
        print("  • Mouse wheel: Zoom in/out (adjust FOV)")
        print("  • +/- keys: Zoom in/out")
        
        print("\n🖱️ Mouse-Look (Immersive Navigation):")
        print("  • Right-click + drag: Look around freely")
        print("  • Move mouse left/right: Rotate camera yaw")
        print("  • Move mouse up/down: Rotate camera pitch")
        print("  • Release right-click: Exit mouse-look mode")
        print("  • Cursor hides during mouse-look for immersion")
        
        print("\n🎯 Selection & Gameplay:")
        print("  • Left-click: Select tokens, move, or attack")
        print("  • Space/Enter: End turn")
        print("  • ESC: Cancel selection")
        print("  • V key: Toggle between 2D and 3D views")
        
        print("\n🔧 Advanced Features:")
        print("  • Pitch clamping (±89°) to prevent gimbal lock")
        print("  • Yaw wrapping (0-360°) for continuous rotation")
        print("  • Ray casting for accurate 3D selection")
        print("  • First-person perspective following selected token")
        print("  • Smooth camera transitions")
        
        print("\n💡 Tips:")
        print("  • Use mouse-look for precise aiming and exploration")
        print("  • Use Q/E keys for quick rotation adjustments")
        print("  • Use TAB to quickly switch between your tokens")
        print("  • Combine mouse-look with token cycling for best navigation")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)