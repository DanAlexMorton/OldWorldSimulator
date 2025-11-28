"""
Unit state factory.

Creates UnitState objects from army data.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class UnitState:
    """
    Runtime state of a unit in battle.
    
    This is the simplified representation used during games.
    Separate from the full Unit model for performance.
    """
    name: str
    faction: str
    models: int
    max_models: int
    movement: int
    strength: int
    toughness: int
    position_x: float
    position_y: float
    facing: float
    special_rules: List[str] = field(default_factory=list)
    can_shoot: bool = False
    has_moved: bool = False
    has_charged: bool = False
    is_fleeing: bool = False
    
    @property
    def is_alive(self) -> bool:
        """Check if unit has models remaining."""
        return self.models > 0
    
    def distance_to(self, other: 'UnitState') -> float:
        """Calculate distance to another unit."""
        dx = self.position_x - other.position_x
        dy = self.position_y - other.position_y
        return math.sqrt(dx * dx + dy * dy)
    
    def take_casualties(self, casualties: int) -> int:
        """
        Remove casualties from unit.
        
        Returns actual casualties taken.
        """
        actual = min(casualties, self.models)
        self.models -= actual
        return actual
    
    def reset_turn(self) -> None:
        """Reset per-turn flags."""
        self.has_moved = False
        self.has_charged = False


def create_unit_state(
    unit_data: Dict,
    faction: str,
    position_x: float,
    position_y: float,
    facing: float = 0
) -> UnitState:
    """
    Create UnitState from unit dictionary.
    
    Args:
        unit_data: Unit definition dict
        faction: Faction name
        position_x: X position on battlefield
        position_y: Y position on battlefield
        facing: Facing angle in degrees
    
    Returns:
        Configured UnitState
    """
    special_rules = unit_data.get("special_rules", [])
    
    # Detect shooting capability
    can_shoot = any(
        rule.lower() in ["shooting", "shoot", "ranged", "bow", "gun", "crossbow"]
        for rule in special_rules
    ) or any(
        keyword in str(special_rules).lower()
        for keyword in ["shoot", "bow", "gun", "pistol", "crossbow"]
    )
    
    return UnitState(
        name=unit_data.get("name", "Unknown Unit"),
        faction=faction,
        models=unit_data.get("models", 10),
        max_models=unit_data.get("models", 10),
        movement=unit_data.get("movement", 4),
        strength=unit_data.get("strength", 3),
        toughness=unit_data.get("toughness", 3),
        position_x=position_x,
        position_y=position_y,
        facing=facing,
        special_rules=special_rules,
        can_shoot=can_shoot
    )


def create_army_units(
    army: Dict,
    start_x: float = 15,
    start_y: float = 8,
    spacing: float = 20,
    facing: float = 90
) -> List[UnitState]:
    """
    Create all unit states for an army.
    
    Args:
        army: Army dict with 'faction' and 'units'
        start_x: Starting X position
        start_y: Y position for all units
        spacing: Horizontal spacing between units
        facing: Facing angle
    
    Returns:
        List of UnitState objects
    """
    faction = army.get("faction", "Unknown")
    units = army.get("units", [])
    
    return [
        create_unit_state(
            unit_data=unit,
            faction=faction,
            position_x=start_x + i * spacing,
            position_y=start_y,
            facing=facing
        )
        for i, unit in enumerate(units)
    ]

