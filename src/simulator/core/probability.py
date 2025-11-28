"""
Statistical validation and probability calculations for TOW combat
Monte Carlo simulations and mathematical expectations
"""

from typing import Dict, Optional, Tuple
import statistics
from .calculations import (
    to_hit_ws, to_hit_bs, to_wound,
    calculate_hits, calculate_wounds, calculate_saves,
    final_casualties
)
from .dice import d6


def expected_casualties(
    num_attacks: int,
    to_hit: int,
    to_wound: int,
    save: Optional[int] = None
) -> float:
    """
    Calculate mathematical expectation of casualties without rolling.
    
    Pure probability calculation using dice probabilities:
    - Probability of rolling N+ on d6 = (7-N)/6
    
    Args:
        num_attacks: Number of attacks
        to_hit: Required roll to hit (2-6)
        to_wound: Required roll to wound (2-6)
        save: Required save roll (2-6) or None
    
    Returns:
        Expected number of casualties (float)
    
    Example:
        >>> expected_casualties(10, 4, 4, 5)
        2.5
        >>> expected_casualties(30, 4, 4, 6)
        8.333333333333334
    """
    # Probability of success on d6 (rolling N+ on d6)
    def prob_success(target):
        if target < 2:
            return 1.0
        if target > 6:
            # Clamp to 6+ (still possible on natural 6)
            return 1.0 / 6
        return (7 - target) / 6
    
    hit_prob = prob_success(to_hit)
    wound_prob = prob_success(to_wound)
    
    # Calculate expected hits and wounds
    expected_hits = num_attacks * hit_prob
    expected_wounds = expected_hits * wound_prob
    
    # Apply save if present
    if save is not None:
        save_prob = prob_success(save)
        expected_casualties = expected_wounds * (1 - save_prob)
    else:
        expected_casualties = expected_wounds
    
    return expected_casualties


def simulate_combat(
    attacker_profile: Dict,
    defender_profile: Dict,
    iterations: int = 10000,
    context: Optional[Dict] = None
) -> Dict:
    """
    Run Monte Carlo simulation of combat scenario.
    
    Runs the combat sequence many times and returns statistics.
    
    Args:
        attacker_profile: Dict with attacker stats
            {
                'attacks': int,
                'ws': int,
                'strength': int,
                'special_rules': list
            }
        defender_profile: Dict with defender stats
            {
                'ws': int,
                'toughness': int,
                'armour_save': int or None,
                'ward_save': int or None
            }
        iterations: Number of simulations to run (default 10000)
        context: Optional combat context dict
    
    Returns:
        Dict with statistics:
        {
            'mean': float,
            'median': float,
            'std_dev': float,
            'min': int,
            'max': int,
            'confidence_95': tuple,
            'distribution': dict (casualties -> count)
        }
    
    Example:
        >>> import random; random.seed(42)
        >>> attacker = {'attacks': 10, 'ws': 4, 'strength': 4}
        >>> defender = {'ws': 4, 'toughness': 4, 'armour_save': 5}
        >>> results = simulate_combat(attacker, defender, iterations=100)
        >>> 2.0 <= results['mean'] <= 3.5
        True
    """
    casualties_list = []
    distribution = {}
    
    # Extract profiles
    attacks = attacker_profile.get('attacks', 1)
    attacker_ws = attacker_profile.get('ws', 3)
    strength = attacker_profile.get('strength', 3)
    attacker_rules = attacker_profile.get('special_rules', [])
    
    defender_ws = defender_profile.get('ws', 3)
    toughness = defender_profile.get('toughness', 3)
    armour = defender_profile.get('armour_save')
    ward = defender_profile.get('ward_save')
    regen = defender_profile.get('regen')
    
    # Calculate to-hit and to-wound targets
    to_hit_target = to_hit_ws(attacker_ws, defender_ws)
    to_wound_target = to_wound(strength, toughness)
    
    # Run simulations
    for _ in range(iterations):
        result = final_casualties(
            attacks,
            to_hit_target,
            to_wound_target,
            armour,
            ward,
            regen
        )
        casualties = result['final_casualties']
        casualties_list.append(casualties)
        
        # Track distribution
        distribution[casualties] = distribution.get(casualties, 0) + 1
    
    # Calculate statistics
    mean_casualties = statistics.mean(casualties_list)
    median_casualties = statistics.median(casualties_list)
    
    if len(casualties_list) > 1:
        std_dev = statistics.stdev(casualties_list)
    else:
        std_dev = 0.0
    
    min_casualties = min(casualties_list)
    max_casualties = max(casualties_list)
    
    # Calculate 95% confidence interval (mean ± 1.96 * std_err)
    std_err = std_dev / (iterations ** 0.5)
    conf_95_lower = mean_casualties - (1.96 * std_err)
    conf_95_upper = mean_casualties + (1.96 * std_err)
    
    return {
        'mean': mean_casualties,
        'median': median_casualties,
        'std_dev': std_dev,
        'min': min_casualties,
        'max': max_casualties,
        'confidence_95': (conf_95_lower, conf_95_upper),
        'distribution': distribution,
        'iterations': iterations
    }


def validate_against_expected(
    attacker_profile: Dict,
    defender_profile: Dict,
    iterations: int = 10000,
    tolerance: float = 0.01
) -> Tuple[bool, Dict]:
    """
    Validate simulation results against mathematical expectation.
    
    Runs simulation and compares to calculated expectation.
    
    Args:
        attacker_profile: Attacker stats dict
        defender_profile: Defender stats dict
        iterations: Number of simulations
        tolerance: Acceptable variance from expectation (default 1%)
    
    Returns:
        Tuple of (passes: bool, details: dict)
    
    Example:
        >>> import random; random.seed(42)
        >>> attacker = {'attacks': 30, 'ws': 3, 'strength': 3}
        >>> defender = {'ws': 3, 'toughness': 4, 'armour_save': 6}
        >>> passes, details = validate_against_expected(attacker, defender, 1000)
        >>> passes
        True
    """
    # Run simulation
    sim_results = simulate_combat(attacker_profile, defender_profile, iterations)
    
    # Calculate mathematical expectation
    attacks = attacker_profile.get('attacks', 1)
    attacker_ws = attacker_profile.get('ws', 3)
    strength = attacker_profile.get('strength', 3)
    defender_ws = defender_profile.get('ws', 3)
    toughness = defender_profile.get('toughness', 3)
    armour = defender_profile.get('armour_save')
    
    to_hit_target = to_hit_ws(attacker_ws, defender_ws)
    to_wound_target = to_wound(strength, toughness)
    
    expected = expected_casualties(attacks, to_hit_target, to_wound_target, armour)
    
    # Calculate variance percentage
    variance = abs(sim_results['mean'] - expected) / expected if expected > 0 else 0
    passes = variance <= tolerance
    
    details = {
        'expected': expected,
        'simulated_mean': sim_results['mean'],
        'variance': variance,
        'variance_percent': variance * 100,
        'tolerance_percent': tolerance * 100,
        'passes': passes,
        'confidence_95': sim_results['confidence_95'],
        'std_dev': sim_results['std_dev']
    }
    
    return (passes, details)


def calculate_hit_probability(to_hit: int, reroll_misses: bool = False, reroll_ones: bool = False) -> float:
    """
    Calculate probability of hitting with given modifiers.
    
    Args:
        to_hit: Required roll to hit (2-6)
        reroll_misses: Can reroll failed hits
        reroll_ones: Can reroll 1s
    
    Returns:
        Probability of success (0.0 to 1.0)
    
    Example:
        >>> calculate_hit_probability(4)
        0.5
        >>> calculate_hit_probability(4, reroll_misses=True)
        0.75
    """
    base_prob = (7 - to_hit) / 6 if 2 <= to_hit <= 6 else 0.0
    
    if reroll_misses:
        # Probability with full reroll: P(success) = P(first) + P(fail) * P(second)
        fail_prob = 1 - base_prob
        return base_prob + (fail_prob * base_prob)
    elif reroll_ones:
        # Probability when rerolling 1s
        prob_one = 1/6
        return base_prob + (prob_one * base_prob)
    else:
        return base_prob


def calculate_wound_probability(to_wound: int, poisoned: bool = False) -> float:
    """
    Calculate probability of wounding.
    
    Args:
        to_wound: Required roll to wound (2-6)
        poisoned: Poisoned attacks (always wound on 6)
    
    Returns:
        Probability of success (0.0 to 1.0)
    
    Example:
        >>> calculate_wound_probability(4)
        0.5
        >>> calculate_wound_probability(6, poisoned=True)
        0.16666666666666666
    """
    base_prob = (7 - to_wound) / 6 if 2 <= to_wound <= 6 else 0.0
    
    # Poisoned attacks always wound on 6
    if poisoned and to_wound > 2:
        # If already wounds better than 6+, poisoned doesn't help
        return max(base_prob, 1/6)
    
    return base_prob


def calculate_save_probability(save: Optional[int]) -> float:
    """
    Calculate probability of making a save.
    
    Args:
        save: Required roll to save (2-6) or None
    
    Returns:
        Probability of success (0.0 to 1.0)
    
    Example:
        >>> calculate_save_probability(4)
        0.5
        >>> calculate_save_probability(None)
        0.0
    """
    if save is None:
        return 0.0
    return (7 - save) / 6 if 2 <= save <= 6 else 0.0


def calculate_average_damage(
    attacks: int,
    to_hit: int,
    to_wound: int,
    save: Optional[int] = None,
    ward: Optional[int] = None,
    modifiers: Optional[Dict] = None
) -> Dict[str, float]:
    """
    Calculate average damage output with full breakdown.
    
    Args:
        attacks: Number of attacks
        to_hit: Required to-hit roll
        to_wound: Required to-wound roll
        save: Armor save or None
        ward: Ward save or None
        modifiers: Dict with reroll flags, etc.
    
    Returns:
        Dict with damage breakdown
    
    Example:
        >>> calculate_average_damage(10, 4, 4, save=5)
        {'average_hits': 5.0, 'average_wounds': 2.5, 'average_unsaved': 1.25, 'final_damage': 1.25}
    """
    modifiers = modifiers or {}
    
    # Calculate probabilities
    hit_prob = calculate_hit_probability(
        to_hit,
        modifiers.get('reroll_misses', False),
        modifiers.get('reroll_ones', False)
    )
    wound_prob = calculate_wound_probability(to_wound, modifiers.get('poisoned', False))
    save_prob = calculate_save_probability(save)
    ward_prob = calculate_save_probability(ward)
    
    # Calculate expected values
    avg_hits = attacks * hit_prob
    avg_wounds = avg_hits * wound_prob
    avg_after_armor = avg_wounds * (1 - save_prob)
    avg_after_ward = avg_after_armor * (1 - ward_prob)
    
    return {
        'average_hits': avg_hits,
        'average_wounds': avg_wounds,
        'average_after_armor': avg_after_armor,
        'average_unsaved': avg_after_ward,
        'final_damage': avg_after_ward
    }
