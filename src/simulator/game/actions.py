"""
Action execution for units.

Handles movement, charges, shooting, etc.
"""

import math
from typing import Optional

from ..data.unit_factory import UnitState


def execute_action(
    unit: UnitState,
    action: str,
    target: Optional[UnitState] = None
) -> None:
    """
    Execute a movement action.
    
    Args:
        unit: Unit to move
        action: Action name (hold, advance, march, charge, shoot, flank_left, flank_right, refuse)
        target: Optional target unit
    """
    if action == "hold" or action == "shoot" or target is None:
        # Hold and shoot = don't move (shooting happens in shooting phase)
        return
    
    dx = target.position_x - unit.position_x
    dy = target.position_y - unit.position_y
    dist = math.sqrt(dx * dx + dy * dy) if (dx != 0 or dy != 0) else 1
    
    if action == "advance":
        move = min(unit.movement, dist)
        unit.position_x += (dx / dist) * move
        unit.position_y += (dy / dist) * move
        unit.has_moved = True
    
    elif action == "march":
        move = min(unit.movement * 2, dist)
        unit.position_x += (dx / dist) * move
        unit.position_y += (dy / dist) * move
        unit.has_moved = True
    
    elif action == "charge":
        max_charge = unit.movement * 2 + 7  # 2x M + 2d6 average
        if dist <= max_charge:
            unit.position_x = target.position_x
            unit.position_y = target.position_y
            unit.has_charged = True
            unit.has_moved = True
    
    elif action.startswith("flank"):
        angle = 45 if "left" in action else -45
        rad = math.radians(unit.facing + angle)
        unit.position_x += unit.movement * 0.7 * math.cos(rad)
        unit.position_y += unit.movement * 0.7 * math.sin(rad)
        unit.has_moved = True
    
    elif action == "refuse":
        rad = math.radians(unit.facing + 180)
        unit.position_x += unit.movement * 0.5 * math.cos(rad)
        unit.position_y += unit.movement * 0.5 * math.sin(rad)
        unit.has_moved = True


def get_unit_type(unit: UnitState) -> str:
    """
    Determine the tactical category of a unit.
    
    Returns:
        "artillery", "ranged", "cavalry", "monster", "character", or "infantry"
    """
    name_lower = unit.name.lower()
    rules_str = " ".join(unit.special_rules).lower()
    
    # Artillery - War Machines that don't move
    if any(w in name_lower for w in ["cannon", "mortar", "catapult", "bolt thrower", 
                                      "doom diver", "rock lobber", "helblaster"]):
        return "artillery"
    
    # Characters - Single model leaders
    if any(w in name_lower for w in ["general", "captain", "lord", "warboss", 
                                      "wizard", "shaman", "priest", "boss"]):
        return "character"
    
    # Cavalry - Fast mounted units
    if any(w in name_lower for w in ["knight", "rider", "cavalry", "boar boyz",
                                      "demigryph", "wolf rider"]):
        return "cavalry"
    
    # Monsters - Large creatures
    if any(w in name_lower for w in ["giant", "troll", "dragon", "hydra", 
                                      "arachnarok", "griffon"]):
        return "monster"
    
    # Ranged - Units with shooting capability
    if unit.can_shoot:
        return "ranged"
    
    # Default: Infantry
    return "infantry"


def smart_action(unit: UnitState, target: UnitState) -> str:
    """
    Determine the best action for a unit based on its type and capabilities.
    
    Args:
        unit: The unit to decide for
        target: Closest enemy target
    
    Returns:
        Action string
    """
    dist = unit.distance_to(target)
    unit_type = get_unit_type(unit)
    
    # ===== ARTILLERY =====
    # War machines NEVER move - they shoot from deployment
    if unit_type == "artillery":
        return "shoot"  # Always shoot, never move
    
    # ===== RANGED INFANTRY =====
    # Handgunners, Crossbowmen, Archers - stay at range and shoot
    if unit_type == "ranged":
        # Get weapon range from special rules
        max_range = 30.0  # Default crossbow range
        if "handgun" in " ".join(unit.special_rules).lower():
            max_range = 24.0
        
        if dist <= max_range:
            return "shoot"  # In range - hold and shoot
        elif dist <= max_range + unit.movement:
            return "advance"  # One move gets us in range
        else:
            return "march"  # Need to march to get in range
    
    # ===== CAVALRY =====
    # Knights, Boar Boyz - aggressive charges, flank if needed
    if unit_type == "cavalry":
        max_charge = unit.movement * 2 + 7  # M8 cavalry can charge 23"
        
        if dist <= max_charge:
            return "charge"
        elif dist <= max_charge + unit.movement * 2:
            return "march"  # Get into charge range next turn
        else:
            return "march"
    
    # ===== MONSTERS =====
    # Giants, Trolls - charge in, they're terrifying
    if unit_type == "monster":
        max_charge = unit.movement * 2 + 7
        
        if dist <= max_charge:
            return "charge"
        else:
            return "march"  # Monsters just run at the enemy
    
    # ===== CHARACTERS =====
    # Lords, Heroes - stay with their units, don't charge solo
    if unit_type == "character":
        # Characters should be cautious
        max_charge = unit.movement * 2 + 5
        
        if dist <= max_charge and dist > 5:
            return "advance"  # Move with army, don't charge alone
        elif dist <= 5:
            return "charge"  # Support nearby combat
        else:
            return "march"
    
    # ===== INFANTRY =====
    # Halberdiers, Swordsmen, Orcs - advance and charge
    max_charge = unit.movement * 2 + 7
    
    if dist <= max_charge:
        return "charge"
    elif dist <= max_charge + unit.movement * 2:
        return "march"  # Get into charge range
    else:
        return "advance"  # Steady advance

