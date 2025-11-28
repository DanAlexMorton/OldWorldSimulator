"""
Game engine module.

Provides the core game loop and battle management.
"""

from .battle import Battle
from .actions import execute_action
from .combat import resolve_combat

__all__ = [
    "Battle",
    "execute_action",
    "resolve_combat"
]

