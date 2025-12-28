#!/usr/bin/env python3
"""
Test script for mouse-look functionality.
This script tests the mouse-look implementation without requiring a graphical interface.
"""

import sys
sys.path.insert(0, '.')

from client.camera_3d import FirstPersonCamera3D
from shared.constants import CELL_SIZE
import numpy as np

def test_mouse_look_basic():
    """Test basic mouse-look functionality."""
    print("Testing basic mouse-look functionality...")
    
    camera = FirstPersonCamera3D(1280, 720)
    initial_yaw = camera.yaw
    initial_pitch = camera.pitch
    
    # Simulate mouse movement (like what would happen in on_mouse_motion)
    # Right mouse movement (positive dx)
    dx, dy = 100, 50
    sensitivity = 0.2
    
    yaw_delta = -dx * sensitivity  # Negative because right movement should rotate left
    pitch_delta = -dy * sensitivity  # Negative because up movement should rotate down
    
    camera.rotate(yaw_delta=yaw_delta, pitch_delta=pitch_delta)
    
    expected_yaw = (initial_yaw + yaw_delta) % 360.0
    expected_pitch = initial_pitch + pitch_delta
    
    assert abs(camera.yaw - expected_yaw) < 0.01, f"Expected yaw {expected_yaw}, got {camera.yaw}"
    assert abs(camera.pitch - expected_pitch) < 0.01, f"Expected pitch {expected_pitch}, got {camera.pitch}"
    
    print("✓ Basic mouse-look rotation works correctly")

def test_mouse_look_pitch_clamping():
    """Test that pitch is properly clamped to avoid gimbal lock."""
    print("Testing mouse-look pitch clamping...")
    
    camera = FirstPersonCamera3D(1280, 720)
    
    # Try to rotate pitch beyond limits
    camera.rotate(pitch_delta=100.0)  # Should be clamped to max
    assert camera.pitch <= 89.0, f"Pitch should be clamped to <= 89.0, got {camera.pitch}"
    
    camera.rotate(pitch_delta=-200.0)  # Should be clamped to min
    assert camera.pitch >= -89.0, f"Pitch should be clamped to >= -89.0, got {camera.pitch}"
    
    print("✓ Mouse-look pitch clamping works correctly")

def test_mouse_look_yaw_wrapping():
    """Test that yaw wraps around correctly."""
    print("Testing mouse-look yaw wrapping...")
    
    camera = FirstPersonCamera3D(1280, 720)
    
    # Rotate beyond 360 degrees
    camera.rotate(yaw_delta=400.0)
    expected_yaw = 40.0  # 400 % 360
    assert abs(camera.yaw - expected_yaw) < 0.01, f"Expected yaw {expected_yaw}, got {camera.yaw}"
    
    # Rotate negative
    camera.rotate(yaw_delta=-100.0)
    expected_yaw = (40.0 - 100.0) % 360.0  # 320.0
    assert abs(camera.yaw - expected_yaw) < 0.01, f"Expected yaw {expected_yaw}, got {camera.yaw}"
    
    print("✓ Mouse-look yaw wrapping works correctly")

def test_mouse_look_view_matrix():
    """Test that view matrix is correctly updated after mouse-look rotations."""
    print("Testing mouse-look view matrix updates...")
    
    camera = FirstPersonCamera3D(1280, 720)
    
    # Get initial view matrix
    initial_view = camera.get_view_matrix()
    
    # Apply some rotation
    camera.rotate(yaw_delta=45.0, pitch_delta=10.0)
    
    # Get updated view matrix
    updated_view = camera.get_view_matrix()
    
    # View matrices should be different
    assert not np.array_equal(initial_view, updated_view), "View matrix should change after rotation"
    
    # View matrix should still be valid (determinant should be non-zero)
    det = np.linalg.det(updated_view)
    assert abs(det) > 0.01, f"View matrix should be invertible, determinant: {det}"
    
    print("✓ Mouse-look view matrix updates correctly")

def test_mouse_look_sensitivity():
    """Test different sensitivity values."""
    print("Testing mouse-look sensitivity...")
    
    # Test with different sensitivity values
    sensitivities = [0.1, 0.2, 0.5, 1.0]
    
    for sensitivity in sensitivities:
        camera = FirstPersonCamera3D(1280, 720)
        initial_yaw = camera.yaw
        
        # Simulate mouse movement
        dx = 100
        yaw_delta = -dx * sensitivity
        camera.rotate(yaw_delta=yaw_delta)
        
        expected_yaw = (initial_yaw + yaw_delta) % 360.0
        assert abs(camera.yaw - expected_yaw) < 0.01, f"Sensitivity {sensitivity}: Expected yaw {expected_yaw}, got {camera.yaw}"
    
    print("✓ Mouse-look sensitivity works correctly")

def main():
    """Run all mouse-look tests."""
    print("=" * 60)
    print("Mouse-Look Functionality Test")
    print("=" * 60)
    
    try:
        test_mouse_look_basic()
        test_mouse_look_pitch_clamping()
        test_mouse_look_yaw_wrapping()
        test_mouse_look_view_matrix()
        test_mouse_look_sensitivity()
        
        print("\n" + "=" * 60)
        print("✓ All mouse-look tests passed!")
        print("=" * 60)
        
        print("\nMouse-look controls:")
        print("  - Right-click + drag: Look around in 3D mode")
        print("  - Move mouse left/right: Rotate camera yaw")
        print("  - Move mouse up/down: Rotate camera pitch")
        print("  - Release right-click: Exit mouse-look mode")
        print("\nFeatures:")
        print("  - Smooth camera rotation based on mouse movement")
        print("  - Pitch clamping to prevent gimbal lock")
        print("  - Yaw wrapping for continuous rotation")
        print("  - Cursor hiding during mouse-look for immersion")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)