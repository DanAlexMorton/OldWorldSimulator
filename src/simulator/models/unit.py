"""
Base Unit dataclass and related models
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Unit:
    """
    Represents a unit on the battlefield
    """
    name: str
    movement: int
    weapon_skill: int
    ballistic_skill: int
    strength: int
    toughness: int
    wounds: int
    initiative: int
    attacks: int
    leadership: int
    armor_save: Optional[int] = None
    unit_size: int = 1
    special_rules: List[str] = None
    
    def __post_init__(self):
        if self.special_rules is None:
            self.special_rules = []
    
    @property
    def is_alive(self):
        """Check if unit has any models remaining"""
        return self.unit_size > 0
    
    def take_casualties(self, casualties):
        """Remove casualties from the unit"""
        self.unit_size = max(0, self.unit_size - casualties)
        return self.unit_size


@dataclass
class Character(Unit):
    """
    Represents a character (hero or lord)
    """
    character_type: str = "hero"  # "hero" or "lord"
    magic_level: Optional[int] = None

