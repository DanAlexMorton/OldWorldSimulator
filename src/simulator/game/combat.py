"""
Combat resolution.

Handles melee and shooting combat.
"""

import random
from typing import List, Tuple

from ..data.unit_factory import UnitState


# Weapon stats: (strength, ap, range)
RANGED_WEAPONS = {
    "Handgun": (4, -1, 24),
    "Crossbow": (4, 0, 30),
    "Bow": (3, 0, 24),
    "Longbow": (3, 0, 30),
    "Shortbow": (3, 0, 18),
    "Pistol": (4, -1, 12),
}


def roll_to_hit(attacks: int, to_hit: int = 4) -> int:
    """Roll to hit and return number of hits."""
    return sum(1 for _ in range(attacks) if random.randint(1, 6) >= to_hit)


def roll_to_wound(hits: int, strength: int, toughness: int) -> int:
    """Roll to wound and return number of wounds."""
    # Calculate required roll
    diff = strength - toughness
    if diff >= 2:
        to_wound = 2
    elif diff == 1:
        to_wound = 3
    elif diff == 0:
        to_wound = 4
    elif diff == -1:
        to_wound = 5
    else:
        to_wound = 6
    
    return sum(1 for _ in range(hits) if random.randint(1, 6) >= to_wound)


def get_weapon_from_rules(special_rules: List[str]) -> Tuple[int, int, int]:
    """
    Get weapon stats from special rules.
    
    Returns: (strength, ap, range)
    """
    for rule in special_rules:
        if rule in RANGED_WEAPONS:
            return RANGED_WEAPONS[rule]
    
    # Check for keywords
    rules_str = " ".join(special_rules).lower()
    if "handgun" in rules_str:
        return RANGED_WEAPONS["Handgun"]
    elif "crossbow" in rules_str:
        return RANGED_WEAPONS["Crossbow"]
    elif "longbow" in rules_str:
        return RANGED_WEAPONS["Longbow"]
    elif "bow" in rules_str or "archer" in rules_str:
        return RANGED_WEAPONS["Bow"]
    elif "pistol" in rules_str:
        return RANGED_WEAPONS["Pistol"]
    
    # Default bow
    return (3, 0, 24)


def resolve_shooting(
    shooter: UnitState,
    target: UnitState,
    max_range: float = 24.0
) -> int:
    """
    Resolve shooting from one unit to another.
    
    Args:
        shooter: Shooting unit (must have can_shoot=True)
        target: Target unit
        max_range: Maximum range for shooting
    
    Returns:
        Number of casualties inflicted
    """
    if not shooter.can_shoot or not shooter.is_alive or not target.is_alive:
        return 0
    
    distance = shooter.distance_to(target)
    
    # Get weapon stats
    weapon_s, weapon_ap, weapon_range = get_weapon_from_rules(shooter.special_rules)
    
    if distance > weapon_range:
        return 0
    
    # Calculate to-hit (BS3 = 4+, BS4 = 3+)
    # Assume BS3 for basic troops
    to_hit = 4
    
    # Long range penalty
    if distance > weapon_range / 2:
        to_hit += 1
    
    to_hit = max(2, min(6, to_hit))
    
    # Roll to hit
    shots = shooter.models
    hits = roll_to_hit(shots, to_hit)
    
    if hits == 0:
        return 0
    
    # Roll to wound using weapon strength
    wounds = roll_to_wound(hits, weapon_s, target.toughness)
    
    if wounds == 0:
        return 0
    
    # Apply casualties
    casualties = target.take_casualties(wounds)
    
    return casualties


def resolve_shooting_phase(
    shooters: List[UnitState],
    targets: List[UnitState],
    verbose: bool = False
) -> int:
    """
    Resolve all shooting for one player.
    
    Args:
        shooters: Shooting player's units
        targets: Enemy units
        verbose: Print debug info
    
    Returns:
        Total casualties inflicted
    """
    total_casualties = 0
    
    for shooter in shooters:
        if not shooter.can_shoot or not shooter.is_alive:
            continue
        
        # Find closest valid target
        valid_targets = [t for t in targets if t.is_alive]
        if not valid_targets:
            continue
        
        target = min(valid_targets, key=lambda t: shooter.distance_to(t))
        
        casualties = resolve_shooting(shooter, target)
        total_casualties += casualties
        
        if verbose and casualties > 0:
            print(f"  {shooter.name} shoots {target.name}: {casualties} casualties")
    
    return total_casualties


def resolve_melee(
    attacker: UnitState,
    defender: UnitState
) -> Tuple[int, int]:
    """
    Resolve melee combat between two units.
    
    Returns:
        (attacker_wounds_dealt, defender_wounds_dealt)
    """
    # Attacker strikes
    a_hits = roll_to_hit(attacker.models)
    a_wounds = roll_to_wound(a_hits, attacker.strength, defender.toughness)
    defender.take_casualties(a_wounds)
    
    # Defender strikes back (if alive)
    d_wounds = 0
    if defender.is_alive:
        d_hits = roll_to_hit(defender.models)
        d_wounds = roll_to_wound(d_hits, defender.strength, attacker.toughness)
        attacker.take_casualties(d_wounds)
    
    return a_wounds, d_wounds


def resolve_combat(
    units_a: List[UnitState],
    units_b: List[UnitState],
    contact_distance: float = 5.0
) -> None:
    """
    Resolve all combats between units in contact.
    
    Args:
        units_a: Player A's units
        units_b: Player B's units
        contact_distance: Distance threshold for combat
    """
    for unit_a in units_a:
        if not unit_a.is_alive:
            continue
        
        for unit_b in units_b:
            if not unit_b.is_alive:
                continue
            
            if unit_a.distance_to(unit_b) < contact_distance:
                resolve_melee(unit_a, unit_b)

