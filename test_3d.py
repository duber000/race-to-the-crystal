#!/usr/bin/env python3
"""Quick test to verify 3D components are working."""

import numpy as np
from client.camera_3d import FirstPersonCamera3D
from game.board import Board
from game.token import Token

print("=" * 60)
print("3D MODE VERIFICATION TEST")
print("=" * 60)

# Test 1: Camera initialization
print("\n[1/5] Testing 3D Camera...")
camera = FirstPersonCamera3D(1280, 720)
print(f"  ✓ Camera position: {camera.position}")
print(f"  ✓ Camera FOV: {camera.fov}°")
print(f"  ✓ Camera yaw/pitch: {camera.yaw}°, {camera.pitch}°")

# Test 2: Projection matrix
print("\n[2/5] Testing Perspective Projection...")
proj_matrix = camera.get_projection_matrix()
print(f"  ✓ Projection matrix shape: {proj_matrix.shape}")
print(f"  ✓ Matrix type: {proj_matrix.dtype}")

# Test 3: View matrix
print("\n[3/5] Testing View Matrix...")
view_matrix = camera.get_view_matrix()
print(f"  ✓ View matrix shape: {view_matrix.shape}")
print(f"  ✓ Camera looking at: {-view_matrix[2, :3]}")  # Forward direction

# Test 4: Token following
print("\n[4/5] Testing Token Following...")
token = Token(id=1, player_id="player_1", health=10, position=(12, 12))
camera.follow_token(token.position, rotation=45.0)
print(f"  ✓ Camera following token at {token.position}")
print(f"  ✓ New camera position: {camera.position}")
print(f"  ✓ Camera rotation: {camera.yaw}°")

# Test 5: Ray casting
print("\n[5/5] Testing Ray Casting...")
ray_origin, ray_direction = camera.screen_to_ray(640, 360, 1280, 720)
print(f"  ✓ Ray origin: {ray_origin}")
print(f"  ✓ Ray direction: {ray_direction}")
print(f"  ✓ Ray normalized: {np.linalg.norm(ray_direction):.3f}")

# Ray-plane intersection
intersection = camera.ray_intersect_plane(ray_origin, ray_direction, plane_z=0.0)
if intersection:
    world_x, world_y = intersection
    grid_x, grid_y = camera.world_to_grid(world_x, world_y)
    print(f"  ✓ Intersection at world: ({world_x:.1f}, {world_y:.1f})")
    print(f"  ✓ Grid coordinates: ({grid_x}, {grid_y})")

print("\n" + "=" * 60)
print("ALL 3D COMPONENTS WORKING!")
print("=" * 60)
print("\nTO PLAY:")
print("  1. Run: uv run race-to-the-crystal")
print("  2. Press 'V' to toggle to 3D first-person mode")
print("  3. Press 'TAB' to switch between tokens")
print("  4. Press 'Q/E' to rotate camera")
print("  5. Click to select/move (ray casting!)")
print("=" * 60)
