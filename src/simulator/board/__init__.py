"""
Board module - GameState, positioning (abstract/vec2)
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class Vec2:
    """2D vector for positioning"""
    x: float
    y: float
    
    def distance_to(self, other):
        """Calculate distance to another position"""
        return ((self.x - other.x)**2 + (self.y - other.y)**2)**0.5


class GameState:
    """
    Manages the overall game state
    """
    def __init__(self, board_width=72, board_height=48):
        self.board_width = board_width  # inches
        self.board_height = board_height
        self.units = []
        self.turn = 1
        self.current_phase = "movement"
        
    def add_unit(self, unit, position: Vec2):
        """Add a unit to the board"""
        # TODO: Implement unit placement
        pass
    
    def get_units_in_range(self, position: Vec2, range_inches: float):
        """Get all units within range of a position"""
        # TODO: Implement range checking
        pass

