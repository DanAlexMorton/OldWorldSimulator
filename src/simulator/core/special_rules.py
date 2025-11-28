"""
Special Rules Framework for Warhammer: The Old World
Extensible system for parsing and applying special rules
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import json
from pathlib import Path


@dataclass
class SpecialRule:
    """
    Definition of a special rule.
    
    Attributes:
        name: Rule name (e.g., "Hatred", "Frenzy")
        rule_type: Type of rule ('passive', 'trigger', 'modifier')
        phase: List of phases this rule applies to
        effect: Flexible dict containing rule parameters
        conditions: Dict specifying when this rule applies
        description: Human-readable description
    """
    name: str
    rule_type: str
    phase: List[str]
    effect: Dict[str, Any]
    conditions: Dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class CombatContext:
    """
    Holds situational information for rule evaluation.
    
    Attributes:
        round_number: Current round of combat (1+)
        is_charging: True if unit charged this turn
        is_flanking: True if attacking flank
        is_rear_charge: True if charging rear
        terrain: Type of terrain or None
        range_band: For shooting ('short', 'long', 'extreme')
        attacker_special_rules: List of attacker's special rule names
        defender_special_rules: List of defender's special rule names
    """
    round_number: int = 1
    is_charging: bool = False
    is_flanking: bool = False
    is_rear_charge: bool = False
    terrain: Optional[str] = None
    range_band: str = "short"
    attacker_special_rules: List[str] = field(default_factory=list)
    defender_special_rules: List[str] = field(default_factory=list)


class RuleRegistry:
    """
    Central registry for special rules.
    Singleton pattern for global rule access.
    """
    _instance = None
    _rules: Dict[str, SpecialRule] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RuleRegistry, cls).__new__(cls)
        return cls._instance
    
    def register_rule(self, rule: SpecialRule) -> None:
        """Register a special rule in the registry."""
        self._rules[rule.name.lower()] = rule
    
    def get_rule(self, name: str) -> Optional[SpecialRule]:
        """Get a rule by name (case-insensitive)."""
        return self._rules.get(name.lower())
    
    def get_rules_by_phase(self, phase: str) -> List[SpecialRule]:
        """Get all rules that apply to a specific phase."""
        return [rule for rule in self._rules.values() if phase in rule.phase]
    
    def has_rule(self, name: str) -> bool:
        """Check if a rule exists in the registry."""
        return name.lower() in self._rules
    
    def load_from_json(self, json_path: str) -> None:
        """Load rules from a JSON file."""
        path = Path(json_path)
        if not path.exists():
            return
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        for rule_name, rule_data in data.items():
            rule = parse_rule_from_json(rule_name, rule_data)
            self.register_rule(rule)
    
    def clear(self) -> None:
        """Clear all registered rules (useful for testing)."""
        self._rules.clear()


def parse_rule_from_json(rule_name: str, rule_data: Dict) -> SpecialRule:
    """
    Parse a special rule from JSON data.
    
    Args:
        rule_name: Name of the rule
        rule_data: Dict containing rule definition
    
    Returns:
        SpecialRule object
    
    Example:
        >>> data = {
        ...     "type": "modifier",
        ...     "phase": ["melee_combat"],
        ...     "effect": {"reroll_failed_hits": True, "duration": "first_round"}
        ... }
        >>> rule = parse_rule_from_json("Hatred", data)
        >>> rule.name
        'Hatred'
    """
    return SpecialRule(
        name=rule_name,
        rule_type=rule_data.get('type', 'passive'),
        phase=rule_data.get('phase', []),
        effect=rule_data.get('effect', {}),
        conditions=rule_data.get('conditions', {}),
        description=rule_data.get('description', '')
    )


def has_rule(unit, rule_name: str) -> bool:
    """
    Check if a unit has a specific special rule.
    
    Args:
        unit: Unit object with special_rules attribute
        rule_name: Name of the rule to check
    
    Returns:
        True if unit has the rule
    
    Example:
        >>> from src.simulator.models.unit import Unit
        >>> unit = Unit(name="Test", models=10, movement=4, weapon_skill=4,
        ...             ballistic_skill=3, strength=3, toughness=3, wounds=1,
        ...             initiative=3, attacks=1, leadership=7,
        ...             special_rules=["Hatred", "Frenzy"])
        >>> has_rule(unit, "Hatred")
        True
    """
    if not hasattr(unit, 'special_rules'):
        return False
    return rule_name.lower() in [r.lower() for r in unit.special_rules]


def get_rule_value(unit, rule_name: str, default=None) -> Any:
    """
    Get the value of a parameterized rule (e.g., "Ward Save (5+)").
    
    Args:
        unit: Unit object with special_rules attribute
        rule_name: Base name of the rule (e.g., "Ward Save")
        default: Default value if rule not found
    
    Returns:
        Rule value or default
    
    Example:
        >>> from src.simulator.models.unit import Unit
        >>> unit = Unit(name="Test", models=10, movement=4, weapon_skill=4,
        ...             ballistic_skill=3, strength=3, toughness=3, wounds=1,
        ...             initiative=3, attacks=1, leadership=7,
        ...             ward_save=5)
        >>> get_rule_value(unit, "ward_save", 7)
        5
    """
    # Try direct attribute access first
    if hasattr(unit, rule_name):
        value = getattr(unit, rule_name)
        return value if value is not None else default
    
    # Try parsing from special_rules list
    if hasattr(unit, 'special_rules'):
        rule_name_lower = rule_name.lower()
        for rule in unit.special_rules:
            rule_lower = rule.lower()
            if rule_name_lower in rule_lower:
                # Try to extract value from parentheses (e.g., "Ward Save (5+)")
                import re
                match = re.search(r'\((\d+)\+?\)', rule)
                if match:
                    return int(match.group(1))
    
    return default


def apply_to_hit_modifiers(
    base_target: int,
    special_rules: List[str],
    context: CombatContext
) -> Dict:
    """
    Apply special rules that modify to-hit rolls.
    
    Args:
        base_target: Base to-hit target number (2-6)
        special_rules: List of special rule names
        context: Combat context with situational information
    
    Returns:
        Dict with modified target and reroll flags
    
    Example:
        >>> ctx = CombatContext(round_number=1, is_charging=True)
        >>> apply_to_hit_modifiers(4, ["Hatred"], ctx)
        {'modified_target': 4, 'reroll_misses': True, 'reroll_ones': False, 'auto_hit_on': None, 'rules_applied': ['Hatred']}
    """
    modified_target = base_target
    reroll_misses = False
    reroll_ones = False
    auto_hit_on = None
    rules_applied = []
    
    registry = RuleRegistry()
    
    for rule_name in special_rules:
        rule = registry.get_rule(rule_name)
        if rule is None:
            continue
        
        # Check if rule applies to this phase
        if 'melee_combat' not in rule.phase and 'shooting' not in rule.phase:
            continue
        
        effect = rule.effect
        
        # Hatred: Reroll failed hits in first round
        if rule_name.lower() == 'hatred':
            if context.round_number == 1 or effect.get('duration') == 'always':
                reroll_misses = True
                rules_applied.append('Hatred')
        
        # Reroll 1s to hit
        if effect.get('reroll_ones_to_hit'):
            reroll_ones = True
            rules_applied.append(rule_name)
        
        # Bonus to hit
        if 'to_hit_bonus' in effect:
            modified_target -= effect['to_hit_bonus']
            rules_applied.append(rule_name)
        
        # Penalty to hit
        if 'to_hit_penalty' in effect:
            modified_target += effect['to_hit_penalty']
            rules_applied.append(rule_name)
    
    # Clamp target to valid range
    modified_target = max(2, min(6, modified_target))
    
    return {
        'modified_target': modified_target,
        'reroll_misses': reroll_misses,
        'reroll_ones': reroll_ones,
        'auto_hit_on': auto_hit_on,
        'rules_applied': rules_applied
    }


def apply_to_wound_modifiers(
    base_target: int,
    special_rules: List[str],
    context: CombatContext
) -> Dict:
    """
    Apply special rules that modify to-wound rolls.
    
    Args:
        base_target: Base to-wound target number (2-6)
        special_rules: List of special rule names
        context: Combat context
    
    Returns:
        Dict with modified target and special wound effects
    
    Example:
        >>> ctx = CombatContext()
        >>> apply_to_wound_modifiers(4, ["Poisoned Attacks"], ctx)
        {'modified_target': 4, 'always_wounds_on': 6, 'rules_applied': ['Poisoned Attacks']}
    """
    modified_target = base_target
    always_wounds_on = None
    multiple_wounds = None
    rules_applied = []
    
    registry = RuleRegistry()
    
    for rule_name in special_rules:
        rule = registry.get_rule(rule_name)
        if rule is None:
            continue
        
        effect = rule.effect
        
        # Poisoned Attacks: Always wound on 6
        if 'poisoned' in rule_name.lower() or effect.get('poisoned'):
            always_wounds_on = 6
            rules_applied.append(rule_name)
        
        # Multiple Wounds
        if 'multiple_wounds' in effect:
            multiple_wounds = effect['multiple_wounds']
            rules_applied.append(rule_name)
        
        # Bonus to wound
        if 'to_wound_bonus' in effect:
            modified_target -= effect['to_wound_bonus']
            rules_applied.append(rule_name)
    
    # Clamp target to valid range
    modified_target = max(2, min(6, modified_target))
    
    return {
        'modified_target': modified_target,
        'always_wounds_on': always_wounds_on,
        'multiple_wounds': multiple_wounds,
        'rules_applied': rules_applied
    }


def apply_save_modifiers(
    base_save: Optional[int],
    special_rules: List[str],
    context: CombatContext
) -> Dict:
    """
    Apply special rules that modify saves.
    
    Args:
        base_save: Base save value or None
        special_rules: List of special rule names
        context: Combat context
    
    Returns:
        Dict with save modifiers
    
    Example:
        >>> ctx = CombatContext()
        >>> apply_save_modifiers(4, ["Ignore Armour"], ctx)
        {'ignore_armour': True, 'no_ward_save': False, 'rules_applied': ['Ignore Armour']}
    """
    ignore_armour = False
    no_ward_save = False
    rules_applied = []
    
    registry = RuleRegistry()
    
    for rule_name in special_rules:
        rule = registry.get_rule(rule_name)
        if rule is None:
            continue
        
        effect = rule.effect
        
        # Ignore Armour
        if effect.get('ignore_armour'):
            ignore_armour = True
            rules_applied.append(rule_name)
        
        # Cancel Ward Saves
        if effect.get('no_ward_save'):
            no_ward_save = True
            rules_applied.append(rule_name)
    
    return {
        'ignore_armour': ignore_armour,
        'no_ward_save': no_ward_save,
        'rules_applied': rules_applied
    }


def apply_attack_modifiers(
    base_attacks: int,
    base_strength: int,
    special_rules: List[str],
    context: CombatContext
) -> Dict:
    """
    Apply special rules that modify attacks and strength.
    
    Args:
        base_attacks: Base number of attacks
        base_strength: Base Strength value
        special_rules: List of special rule names
        context: Combat context
    
    Returns:
        Dict with modified attacks, strength, and initiative flags
    
    Example:
        >>> ctx = CombatContext(is_charging=True)
        >>> apply_attack_modifiers(1, 4, ["Great Weapons"], ctx)
        {'attacks': 1, 'strength': 6, 'always_strikes_last': True, 'always_strikes_first': False, 'rules_applied': ['Great Weapons']}
    """
    attacks = base_attacks
    strength = base_strength
    always_strikes_last = False
    always_strikes_first = False
    rules_applied = []
    
    registry = RuleRegistry()
    
    for rule_name in special_rules:
        rule = registry.get_rule(rule_name)
        if rule is None:
            continue
        
        effect = rule.effect
        
        # Great Weapons: +2 Strength, Always Strikes Last
        if 'great weapons' in rule_name.lower():
            strength += effect.get('strength_bonus', 2)
            always_strikes_last = effect.get('always_strikes_last', True)
            rules_applied.append(rule_name)
        
        # Frenzy: +1 Attack
        if 'frenzy' in rule_name.lower():
            attacks += effect.get('extra_attacks', 1)
            rules_applied.append(rule_name)
        
        # Always Strikes First
        if effect.get('always_strikes_first'):
            always_strikes_first = True
            rules_applied.append(rule_name)
        
        # Strength bonus (generic)
        if 'strength_bonus' in effect and 'great weapons' not in rule_name.lower():
            strength += effect['strength_bonus']
            rules_applied.append(rule_name)
        
        # Extra attacks (generic)
        if 'extra_attacks' in effect and 'frenzy' not in rule_name.lower():
            attacks += effect['extra_attacks']
            rules_applied.append(rule_name)
    
    return {
        'attacks': attacks,
        'strength': strength,
        'always_strikes_last': always_strikes_last,
        'always_strikes_first': always_strikes_first,
        'rules_applied': rules_applied
    }


# Initialize example rules for validation
def initialize_example_rules():
    """
    Initialize a few example rules to validate the framework.
    These serve as templates for future rule implementations.
    """
    registry = RuleRegistry()
    
    # Hatred
    registry.register_rule(SpecialRule(
        name="Hatred",
        rule_type="modifier",
        phase=["melee_combat"],
        effect={
            "reroll_failed_hits": True,
            "duration": "first_round"
        },
        description="Reroll failed to-hit rolls in first round of combat"
    ))
    
    # Great Weapons
    registry.register_rule(SpecialRule(
        name="Great Weapons",
        rule_type="modifier",
        phase=["melee_combat"],
        effect={
            "strength_bonus": 2,
            "always_strikes_last": True
        },
        description="+2 Strength, Always Strikes Last"
    ))
    
    # Armor Piercing
    registry.register_rule(SpecialRule(
        name="Armor Piercing",
        rule_type="modifier",
        phase=["shooting", "melee_combat"],
        effect={
            "ap_modifier": -1
        },
        conditions={
            "variable": True
        },
        description="Modify AP value of weapon"
    ))
