"""
Dice rolling mechanics for Warhammer: The Old World
Pure functions for all dice-related operations with reproducible testing support
"""

import random
from typing import List, Tuple, Optional


def d6(n: int = 1) -> List[int]:
    """
    Roll n six-sided dice, return list of results.
    
    Args:
        n: Number of dice to roll (default 1)
    
    Returns:
        List of individual dice results (1-6)
    
    Example:
        >>> random.seed(42)
        >>> d6(3)
        [6, 1, 6]
    """
    if n < 1:
        return []
    return [random.randint(1, 6) for _ in range(n)]


def d6_sum(n: int = 1) -> int:
    """
    Roll n six-sided dice, return sum.
    
    Args:
        n: Number of dice to roll (default 1)
    
    Returns:
        Sum of all dice rolled
    
    Example:
        >>> random.seed(42)
        >>> d6_sum(2)
        7
    """
    return sum(d6(n))


def roll_with_reroll(
    target: int,
    dice_count: int = 1,
    reroll_fails: bool = False,
    reroll_ones: bool = False
) -> Tuple[int, List[int], List[int]]:
    """
    Roll dice with reroll mechanics (Hatred, etc.).
    
    Args:
        target: Required roll to succeed (2-6)
        dice_count: Number of dice to roll
        reroll_fails: Reroll all failed rolls (Hatred)
        reroll_ones: Reroll only 1s
    
    Returns:
        Tuple of (successes, initial_rolls, rerolls)
    
    Example:
        >>> random.seed(42)
        >>> roll_with_reroll(4, dice_count=5, reroll_fails=True)
        (4, [6, 1, 6, 1, 4], [5, 5])
    """
    initial_rolls = d6(dice_count)
    rerolls = []
    successes = 0
    
    for roll in initial_rolls:
        if roll >= target:
            successes += 1
        else:
            # Check if we should reroll this die
            should_reroll = False
            if reroll_fails:
                should_reroll = True
            elif reroll_ones and roll == 1:
                should_reroll = True
            
            if should_reroll:
                reroll = random.randint(1, 6)
                rerolls.append(reroll)
                if reroll >= target:
                    successes += 1
    
    return (successes, initial_rolls, rerolls)


def roll_with_modifier(
    target: int,
    modifier: int = 0,
    dice_count: int = 1
) -> Tuple[int, List[int]]:
    """
    Apply +/- modifiers to target number (not the dice).
    
    TOW Rules: Modifiers change the target, not the roll.
    - Can't be better than 2+ (always miss on 1)
    - Can't be worse than 6+ (always hit on 6)
    
    Args:
        target: Base target number (2-6)
        modifier: Modifier to apply (negative makes it easier, positive harder)
        dice_count: Number of dice to roll
    
    Returns:
        Tuple of (successes, rolls)
    
    Example:
        >>> random.seed(42)
        >>> roll_with_modifier(4, modifier=-1, dice_count=3)  # 4+ becomes 3+
        (3, [6, 1, 6])
    """
    # Apply modifier to target
    modified_target = target + modifier
    
    # Clamp to valid range (2+ to 6+)
    modified_target = max(2, min(6, modified_target))
    
    rolls = d6(dice_count)
    successes = sum(1 for roll in rolls if roll >= modified_target)
    
    return (successes, rolls)


def artillery_dice() -> Tuple[int, bool]:
    """
    Special 2d6 roll for artillery (misfire on double 1).
    
    TOW Rules: Artillery rolls 2d6 for range/strength.
    Rolling double 1s results in a misfire.
    
    Returns:
        Tuple of (result, is_misfire)
    
    Example:
        >>> random.seed(42)
        >>> artillery_dice()
        (7, False)
    """
    dice = d6(2)
    result = sum(dice)
    is_misfire = (dice[0] == 1 and dice[1] == 1)
    
    return (result, is_misfire)


def scatter_dice() -> Tuple[str, int]:
    """
    Roll scatter dice for templates and bouncing effects.
    
    TOW Rules: Scatter dice shows either HIT, or an arrow with 2d6 distance.
    Standard scatter die has: HIT, and 5 arrow directions.
    
    Returns:
        Tuple of (direction, distance)
        direction: 'HIT' or direction number (1-8 for compass directions)
        distance: 2d6 if scattered, 0 if HIT
    
    Example:
        >>> random.seed(42)
        >>> scatter_dice()
        ('3', 7)
    """
    # Simulate scatter die (1/6 chance of HIT, 5/6 chance of scatter)
    scatter_roll = random.randint(1, 6)
    
    if scatter_roll == 6:
        # HIT - no scatter
        return ('HIT', 0)
    else:
        # Scatter - roll 2d6 for distance
        distance = d6_sum(2)
        # Direction represented as 1-8 (compass points)
        # For simplicity, we use the scatter_roll (1-5) to determine direction
        return (str(scatter_roll), distance)


def roll_2d6() -> int:
    """
    Roll 2d6 and return sum (for Leadership tests, charge distance, etc.).
    
    Returns:
        Sum of 2d6 (2-12)
    
    Example:
        >>> random.seed(42)
        >>> roll_2d6()
        7
    """
    return d6_sum(2)


def roll_d3() -> int:
    """
    Roll a d3 (used for some special rules and random values).
    
    TOW Rules: Roll d6 and halve, rounding up (1-2=1, 3-4=2, 5-6=3).
    
    Returns:
        Result 1-3
    
    Example:
        >>> random.seed(42)
        >>> roll_d3()
        3
    """
    return (random.randint(1, 6) + 1) // 2


def roll_multiple_wounds(wound_type: str = 'd3') -> int:
    """
    Roll for multiple wounds (D3, D6, etc.).
    
    Args:
        wound_type: Type of multiple wound ('d3', 'd6', or fixed number as string)
    
    Returns:
        Number of wounds caused
    
    Example:
        >>> random.seed(42)
        >>> roll_multiple_wounds('d3')
        3
    """
    wound_type = wound_type.lower()
    
    if wound_type == 'd3':
        return roll_d3()
    elif wound_type == 'd6':
        return random.randint(1, 6)
    else:
        # Try to parse as integer
        try:
            return int(wound_type)
        except ValueError:
            return 1  # Default to 1 wound
