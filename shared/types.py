"""
Type definitions for the Race to the Crystal game.

This module defines custom types for better type safety and code clarity.
"""

from typing import NewType, TypeAlias

# Type definitions for better type safety
TokenID: TypeAlias = NewType("TokenID", int)
PlayerID: TypeAlias = NewType("PlayerID", str)

# Common compound types
Position: TypeAlias = tuple[int, int]

# Health values for tokens
HealthValue: TypeAlias = int  # Valid values: 10, 8, 6, 4

# Generator and crystal tracking
CaptureProgress: TypeAlias = tuple[int, int]  # (turns_held, turns_required)
TokenRequirement: TypeAlias = tuple[int, int]  # (current_tokens, required_tokens)
