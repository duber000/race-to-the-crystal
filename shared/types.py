"""
Type definitions for the Race to the Crystal game.

This module defines custom types for better type safety and code clarity.
"""

from typing import NewType

# Type definitions for better type safety
TokenID = NewType("TokenID", int)
PlayerID = NewType("PlayerID", str)