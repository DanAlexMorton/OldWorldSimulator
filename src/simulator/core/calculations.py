"""
Hit/wound tables, dice math, and probability calculations
Core combat mathematics for Warhammer: The Old World
"""

from typing import Optional, Dict, Tuple
from .dice import d6, roll_with_reroll, roll_2d6


def to_hit_ws(attacker_ws: int, defender_ws: int, modifiers: Optional[Dict] = None) -> int:
    """
    Calculate the to-hit roll needed in melee combat based on WS comparison.
    
    TOW Rules - WS Comparison Table:
    - Attacker WS = Defender WS: 4+ to hit
    - Attacker WS > Defender WS: 3+ to hit
    - Attacker WS >= 2× Defender WS: 2+ to hit
    - Attacker WS < Defender WS: 5+ to hit
    - Attacker WS <= ½ Defender WS: 6+ to hit (always hit on 6)
    
    Args:
        attacker_ws: Weapon Skill of attacker (1-10)
        defender_ws: Weapon Skill of defender (1-10)
        modifiers: Optional dict with keys like {'bonus': +1, 'penalty': -1}
    
    Returns:
        int: Required D6 roll to hit (2-6)
    
    Example:
        >>> to_hit_ws(4, 4)  # Equal WS
        4
        >>> to_hit_ws(5, 3)  # Higher WS
        3
        >>> to_hit_ws(6, 3)  # Double or more
        2
    """
    # Base calculation from WS comparison
    if attacker_ws >= defender_ws * 2:
        base_target = 2
    elif attacker_ws > defender_ws:
        base_target = 3
    elif attacker_ws == defender_ws:
        base_target = 4
    elif attacker_ws * 2 <= defender_ws:
        base_target = 6
    else:  # attacker_ws < defender_ws
        base_target = 5
    
    # Apply modifiers if provided
    if modifiers:
        bonus = modifiers.get('bonus', 0)
        penalty = modifiers.get('penalty', 0)
        base_target = base_target - bonus + penalty
    
    # Clamp to valid range (2+ best, 6+ worst)
    return max(2, min(6, base_target))


def to_hit_bs(bs: int, modifiers: Optional[Dict] = None) -> int:
    """
    Calculate the to-hit roll needed for shooting attacks.
    
    TOW Rules - BS to-hit:
    - BS determines base target
    - BS 1: 6+
    - BS 2: 5+
    - BS 3: 4+
    - BS 4: 3+
    - BS 5+: 2+
    
    Common modifiers:
    - Long range: -1 (harder to hit)
    - Cover: -1
    - Moving and shooting: -1
    - Skirmisher target: -1
    - Large target: +1 (easier to hit)
    
    Args:
        bs: Ballistic Skill (1-10)
        modifiers: Optional dict with modifier keys
    
    Returns:
        int: Required D6 roll to hit (2-6)
    
    Example:
        >>> to_hit_bs(3)
        4
        >>> to_hit_bs(4, {'long_range': True})
        4
    """
    # Base BS to target conversion
    if bs <= 1:
        base_target = 6
    elif bs == 2:
        base_target = 5
    elif bs == 3:
        base_target = 4
    elif bs == 4:
        base_target = 3
    else:  # BS 5+
        base_target = 2
    
    # Apply modifiers if provided
    if modifiers:
        # Standard modifiers (penalty increases target number)
        if modifiers.get('long_range'):
            base_target += 1
        if modifiers.get('cover'):
            base_target += 1
        if modifiers.get('moving'):
            base_target += 1
        if modifiers.get('skirmisher'):
            base_target += 1
        
        # Positive modifiers (bonus decreases target number)
        if modifiers.get('large_target'):
            base_target -= 1
        
        # Generic bonus/penalty
        base_target = base_target - modifiers.get('bonus', 0) + modifiers.get('penalty', 0)
    
    # Clamp to valid range (2+ best, 6+ worst)
    return max(2, min(6, base_target))


def to_wound(strength: int, toughness: int, modifiers: Optional[Dict] = None) -> int:
    """
    Calculate the to-wound roll needed based on Strength vs Toughness.
    
    TOW Rules - Wound Table:
    - S >= 2× T: 2+ to wound
    - S > T: 3+ to wound
    - S = T: 4+ to wound
    - S < T: 5+ to wound
    - S <= ½ T: 6+ to wound
    
    Special: Always wound on natural 6, never on natural 1.
    
    Args:
        strength: Attacker's Strength (1-10)
        toughness: Defender's Toughness (1-10)
        modifiers: Optional dict with keys like {'bonus': +1, 'always_wounds_on': 5}
    
    Returns:
        int: Required D6 roll to wound (2-6)
    
    Example:
        >>> to_wound(4, 4)  # Equal S and T
        4
        >>> to_wound(6, 3)  # Double or more
        2
        >>> to_wound(3, 6)  # Half or less
        6
    """
    # Base calculation from S vs T comparison
    if strength >= toughness * 2:
        base_target = 2
    elif strength > toughness:
        base_target = 3
    elif strength == toughness:
        base_target = 4
    elif strength * 2 <= toughness:
        base_target = 6
    else:  # strength < toughness
        base_target = 5
    
    # Apply modifiers if provided
    if modifiers:
        bonus = modifiers.get('bonus', 0)
        penalty = modifiers.get('penalty', 0)
        base_target = base_target - bonus + penalty
        
        # Special rules like Poisoned Attacks
        if 'always_wounds_on' in modifiers:
            base_target = min(base_target, modifiers['always_wounds_on'])
    
    # Clamp to valid range (2+ best, 6+ worst)
    return max(2, min(6, base_target))


def armour_save(base_save: Optional[int], ap_modifier: int = 0, special_rules: Optional[Dict] = None) -> Optional[int]:
    """
    Calculate modified armor save after AP and special rules.
    
    TOW Rules:
    - AP modifier worsens save (e.g., AP -1 makes 4+ into 5+)
    - If save becomes 7+ or worse, no save allowed (return None)
    - Ward saves ignore AP
    
    Args:
        base_save: Base armor save value (2-6), or None for no armor
        ap_modifier: Armor Penetration modifier (negative number, e.g., -1, -2)
        special_rules: Optional dict with rule flags
    
    Returns:
        Modified armor save (2-6) or None if no save possible
    
    Example:
        >>> armour_save(4, -1)
        5
        >>> armour_save(6, -2)
        None
    """
    if base_save is None:
        return None
    
    # Check for special rules that negate armor
    if special_rules and special_rules.get('ignore_armour'):
        return None
    
    # Apply AP modifier (negative AP makes save worse)
    modified_save = base_save - ap_modifier
    
    # If save becomes 7+ or worse, no save allowed
    if modified_save > 6:
        return None
    
    # Ensure save can't be better than 2+
    return max(2, modified_save)


def ward_save(ward_value: Optional[int], special_rules: Optional[Dict] = None) -> Optional[int]:
    """
    Return ward save target (unmodified by AP).
    
    TOW Rules:
    - Ward saves ignore AP
    - Typically 4+, 5+, or 6+
    - Some effects can cancel ward saves
    
    Args:
        ward_value: Ward save value (2-6) or None
        special_rules: Optional dict with rule flags
    
    Returns:
        Ward save target or None
    
    Example:
        >>> ward_save(5)
        5
    """
    if ward_value is None:
        return None
    
    # Check for effects that cancel ward saves
    if special_rules and special_rules.get('no_ward_save'):
        return None
    
    return ward_value


def regeneration_save(regen_value: Optional[int], special_rules: Optional[Dict] = None) -> Optional[int]:
    """
    Return regeneration save target.
    
    TOW Rules:
    - Regeneration works after armor save, before removing models
    - Typically 4+, 5+, or 6+
    - Flaming attacks negate regeneration
    
    Args:
        regen_value: Regeneration save value (2-6) or None
        special_rules: Optional dict with rule flags
    
    Returns:
        Regeneration save target or None
    
    Example:
        >>> regeneration_save(5)
        5
        >>> regeneration_save(5, {'flaming': True})
        None
    """
    if regen_value is None:
        return None
    
    # Flaming attacks negate regeneration
    if special_rules and special_rules.get('flaming'):
        return None
    
    return regen_value


def calculate_hits(num_attacks: int, to_hit_target: int, special_rules: Optional[Dict] = None) -> Dict:
    """
    Roll attacks and count successful hits, applying special rules.
    
    Args:
        num_attacks: Number of attacks to roll
        to_hit_target: Required roll to hit (2-6)
        special_rules: Optional dict with reroll flags, etc.
    
    Returns:
        Dict with keys: hits (int), rolls (list), rerolls_used (bool)
    
    Example:
        >>> import random; random.seed(42)
        >>> calculate_hits(5, 4)
        {'hits': 3, 'rolls': [6, 1, 6, 1, 4], 'rerolls_used': False}
    """
    if num_attacks <= 0:
        return {'hits': 0, 'rolls': [], 'rerolls_used': False}
    
    reroll_fails = special_rules.get('reroll_failed_hits') if special_rules else False
    reroll_ones = special_rules.get('reroll_ones_to_hit') if special_rules else False
    
    if reroll_fails or reroll_ones:
        hits, rolls, rerolls = roll_with_reroll(
            to_hit_target,
            num_attacks,
            reroll_fails=reroll_fails,
            reroll_ones=reroll_ones
        )
        return {
            'hits': hits,
            'rolls': rolls,
            'rerolls': rerolls,
            'rerolls_used': len(rerolls) > 0
        }
    else:
        rolls = d6(num_attacks)
        hits = sum(1 for roll in rolls if roll >= to_hit_target)
        return {
            'hits': hits,
            'rolls': rolls,
            'rerolls_used': False
        }


def calculate_wounds(num_hits: int, to_wound_target: int, special_rules: Optional[Dict] = None) -> Dict:
    """
    Roll to wound and count successful wounds, applying special rules.
    
    Args:
        num_hits: Number of hits to roll for wounds
        to_wound_target: Required roll to wound (2-6)
        special_rules: Optional dict with multiple wounds, killing blow, etc.
    
    Returns:
        Dict with keys: wounds (int), killing_blows (int), multi_wounds (dict)
    
    Example:
        >>> import random; random.seed(42)
        >>> calculate_wounds(3, 4)
        {'wounds': 2, 'rolls': [6, 1, 6], 'killing_blows': 0}
    """
    if num_hits <= 0:
        return {'wounds': 0, 'rolls': [], 'killing_blows': 0}
    
    rolls = d6(num_hits)
    wounds = sum(1 for roll in rolls if roll >= to_wound_target)
    
    result = {
        'wounds': wounds,
        'rolls': rolls,
        'killing_blows': 0
    }
    
    # Check for Killing Blow (natural 6 auto-wounds, ignores armor)
    if special_rules and special_rules.get('killing_blow'):
        killing_blows = sum(1 for roll in rolls if roll == 6)
        result['killing_blows'] = killing_blows
    
    # Check for Multiple Wounds
    if special_rules and 'multiple_wounds' in special_rules:
        result['multiple_wounds'] = special_rules['multiple_wounds']
    
    return result


def calculate_saves(num_wounds: int, save_target: Optional[int], save_type: str = 'armour', special_rules: Optional[Dict] = None) -> Dict:
    """
    Roll saves and return unsaved wounds.
    
    Args:
        num_wounds: Number of wounds to save against
        save_target: Required roll to save (2-6) or None if no save
        save_type: Type of save ('armour', 'ward', 'regeneration')
        special_rules: Optional dict with save reroll flags
    
    Returns:
        Dict with keys: failed_saves (int), successful_saves (int), reroll_used (bool)
    
    Example:
        >>> import random; random.seed(42)
        >>> calculate_saves(3, 4)
        {'failed_saves': 1, 'successful_saves': 2, 'rolls': [6, 1, 6], 'reroll_used': False}
    """
    if num_wounds <= 0 or save_target is None:
        return {
            'failed_saves': num_wounds,
            'successful_saves': 0,
            'rolls': [],
            'reroll_used': False
        }
    
    rolls = d6(num_wounds)
    successful_saves = sum(1 for roll in rolls if roll >= save_target)
    failed_saves = num_wounds - successful_saves
    
    return {
        'failed_saves': failed_saves,
        'successful_saves': successful_saves,
        'rolls': rolls,
        'reroll_used': False
    }


def final_casualties(
    num_attacks: int,
    to_hit: int,
    to_wound: int,
    armour_save: Optional[int] = None,
    ward_save: Optional[int] = None,
    regen: Optional[int] = None,
    special_rules: Optional[Dict] = None
) -> Dict:
    """
    Complete damage pipeline from attacks to final casualties.
    
    Executes the full combat sequence:
    1. Roll to hit
    2. Roll to wound
    3. Roll armor saves
    4. Roll ward saves
    5. Roll regeneration
    
    Args:
        num_attacks: Number of attacks
        to_hit: Required roll to hit (2-6)
        to_wound: Required roll to wound (2-6)
        armour_save: Armor save target or None
        ward_save: Ward save target or None
        regen: Regeneration save target or None
        special_rules: Optional dict with various rule flags
    
    Returns:
        Dict with detailed breakdown of each step
    
    Example:
        >>> import random; random.seed(42)
        >>> final_casualties(10, 4, 4, armour_save=5)
        {'hits': 6, 'wounds': 4, 'saved_by_armour': 2, 'saved_by_ward': 0, 'saved_by_regen': 0, 'final_casualties': 2}
    """
    # Step 1: Calculate hits
    hit_result = calculate_hits(num_attacks, to_hit, special_rules)
    hits = hit_result['hits']
    
    # Step 2: Calculate wounds
    wound_result = calculate_wounds(hits, to_wound, special_rules)
    wounds = wound_result['wounds']
    
    remaining_wounds = wounds
    saved_by_armour = 0
    saved_by_ward = 0
    saved_by_regen = 0
    
    # Step 3: Armor saves
    if armour_save is not None and remaining_wounds > 0:
        save_result = calculate_saves(remaining_wounds, armour_save, 'armour', special_rules)
        saved_by_armour = save_result['successful_saves']
        remaining_wounds = save_result['failed_saves']
    
    # Step 4: Ward saves (on wounds that got through armor)
    if ward_save is not None and remaining_wounds > 0:
        save_result = calculate_saves(remaining_wounds, ward_save, 'ward', special_rules)
        saved_by_ward = save_result['successful_saves']
        remaining_wounds = save_result['failed_saves']
    
    # Step 5: Regeneration (on wounds that got through everything)
    if regen is not None and remaining_wounds > 0:
        save_result = calculate_saves(remaining_wounds, regen, 'regeneration', special_rules)
        saved_by_regen = save_result['successful_saves']
        remaining_wounds = save_result['failed_saves']
    
    return {
        'hits': hits,
        'wounds': wounds,
        'saved_by_armour': saved_by_armour,
        'saved_by_ward': saved_by_ward,
        'saved_by_regen': saved_by_regen,
        'final_casualties': remaining_wounds
    }


def combat_resolution_score(
    wounds_caused: int,
    ranks: int = 0,
    standards: int = 0,
    charging: bool = False,
    flank: bool = False,
    rear: bool = False,
    overkill: int = 0
) -> int:
    """
    Calculate combat resolution score.
    
    TOW Rules - Combat Resolution:
    - Wounds caused
    - Rank bonus (up to +3 for 3+ ranks)
    - Standard (+1)
    - Outnumber (+1, calculated elsewhere)
    - Flank (+1)
    - Rear (+2)
    - Charging (+1)
    - Overkill (excess wounds on characters, max +5)
    
    Args:
        wounds_caused: Unsaved wounds caused
        ranks: Number of complete ranks (max +3)
        standards: Number of standards (0 or 1)
        charging: Unit charged this turn
        flank: Attacking enemy flank
        rear: Attacking enemy rear
        overkill: Excess wounds on characters
    
    Returns:
        Total combat resolution score
    
    Example:
        >>> combat_resolution_score(wounds_caused=5, ranks=3, standards=1, charging=True)
        10
    """
    score = wounds_caused
    
    # Rank bonus (max +3)
    score += min(ranks, 3)
    
    # Standard bonus
    score += min(standards, 1)
    
    # Charging bonus
    if charging:
        score += 1
    
    # Flank attack
    if flank:
        score += 1
    
    # Rear attack (replaces flank, doesn't stack)
    if rear:
        score += 2  # This already includes the flank
    
    # Overkill (max +5)
    score += min(overkill, 5)
    
    return score


def break_test(
    leadership: int,
    combat_result_diff: int,
    modifiers: Optional[Dict] = None
) -> Tuple[bool, int]:
    """
    Determine if unit breaks from combat.
    
    TOW Rules:
    - Roll 2d6 vs Leadership minus combat result difference
    - If roll > modified Ld, unit breaks
    - Natural 12 always fails
    - Modifiers: Steadfast (ignore CR diff), Stubborn, Inspiring Presence, etc.
    
    Args:
        leadership: Unit's base Leadership (2-10)
        combat_result_diff: Negative difference in combat resolution
        modifiers: Optional dict with rule flags like 'steadfast', 'stubborn'
    
    Returns:
        Tuple of (broke: bool, roll_result: int)
    
    Example:
        >>> import random; random.seed(42)
        >>> break_test(7, -3)
        (False, 7)
    """
    # Calculate modified leadership
    modified_ld = leadership
    
    if modifiers:
        # Steadfast: ignore combat result difference
        if modifiers.get('steadfast'):
            combat_result_diff = 0
        
        # Stubborn: ignore combat result difference
        if modifiers.get('stubborn'):
            combat_result_diff = 0
        
        # Inspiring Presence: use general's Leadership
        if 'inspiring_presence' in modifiers:
            modified_ld = modifiers['inspiring_presence']
        
        # Other bonuses/penalties
        modified_ld += modifiers.get('bonus', 0)
        modified_ld -= modifiers.get('penalty', 0)
    
    # Apply combat result difference
    modified_ld += combat_result_diff  # combat_result_diff is negative when losing
    
    # Roll 2d6 for test
    roll = roll_2d6()
    
    # Natural 12 always fails
    if roll >= 12:
        return (True, roll)
    
    # Pass if roll <= modified Ld
    broke = roll > modified_ld
    
    return (broke, roll)
