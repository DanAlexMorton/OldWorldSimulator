"""
Combat resolver for Warhammer: The Old World
Complete shooting and melee combat resolution
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Union
from enum import Enum

from ..models.unit import Unit
from ..models.character import Character
from ..core.dice import d6, d6_sum, roll_2d6
from ..core.calculations import (
    to_hit_ws, to_hit_bs, to_wound, armour_save,
    calculate_hits, calculate_wounds, calculate_saves,
    combat_resolution_score, break_test
)
from ..core.special_rules import CombatContext, apply_to_hit_modifiers, apply_attack_modifiers


class AttackPosition(Enum):
    """Position from which unit is attacking"""
    FRONT = "front"
    FLANK = "flank"
    REAR = "rear"


@dataclass
class CombatResult:
    """
    Result of a combat (shooting or melee).
    
    Contains detailed breakdown of hits, wounds, casualties, and outcome.
    """
    attacker_name: str
    defender_name: str
    
    # Attack breakdown
    total_attacks: int = 0
    hits: int = 0
    wounds: int = 0
    saves_made: int = 0
    casualties: int = 0
    
    # Combat resolution (melee only)
    attacker_cr: int = 0
    defender_cr: int = 0
    combat_result_difference: int = 0
    
    # Break test (melee only)
    defender_broke: bool = False
    defender_fled: bool = False
    break_test_roll: Optional[int] = None
    
    # Pursuit (if applicable)
    pursuit_distance: Optional[int] = None
    flee_distance: Optional[int] = None
    caught_fleeing: bool = False
    
    # Special events
    panic_test_required: bool = False
    overkill: int = 0
    special_effects: List[str] = field(default_factory=list)
    
    # Detailed logs
    hit_rolls: List[int] = field(default_factory=list)
    wound_rolls: List[int] = field(default_factory=list)
    save_rolls: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Export result to dictionary"""
        return {
            "attacker": self.attacker_name,
            "defender": self.defender_name,
            "attacks": self.total_attacks,
            "hits": self.hits,
            "wounds": self.wounds,
            "casualties": self.casualties,
            "combat_result": {
                "attacker_cr": self.attacker_cr,
                "defender_cr": self.defender_cr,
                "difference": self.combat_result_difference
            },
            "break_test": {
                "broke": self.defender_broke,
                "roll": self.break_test_roll
            },
            "special_effects": self.special_effects
        }


@dataclass
class CombatGroup:
    """
    Group of units fighting together in combat.
    
    Handles front, flank, and rear attacks with correct allocation.
    """
    front_units: List[Union[Unit, Character]] = field(default_factory=list)
    flank_units: List[Union[Unit, Character]] = field(default_factory=list)
    rear_units: List[Union[Unit, Character]] = field(default_factory=list)
    supporting_units: List[Unit] = field(default_factory=list)
    
    # Combat state
    is_charging: bool = False
    has_higher_ground: bool = False
    combat_round: int = 1
    
    def get_all_units(self) -> List[Union[Unit, Character]]:
        """Get all units in the combat group"""
        units = []
        units.extend(self.front_units)
        units.extend(self.flank_units)
        units.extend(self.rear_units)
        units.extend(self.supporting_units)
        return units
    
    def get_total_attacks(self) -> int:
        """
        Calculate total attacks from all units.
        
        Considers: front attacks, supporting attacks, flanks, rear
        """
        total = 0
        
        # Front units - full attacks
        for unit in self.front_units:
            if isinstance(unit, Character):
                # Character attacks
                attacks = unit.attacks
                if "Frenzy" in unit.special_rules:
                    attacks += 1
                if self.is_charging and "Devastating Charge" in unit.special_rules:
                    # Already counted in attacks
                    pass
                total += attacks
            else:
                # Unit attacks
                total += unit.get_attack_count()
        
        # Flank units - full attacks
        for unit in self.flank_units:
            if isinstance(unit, Character):
                total += unit.attacks
            else:
                total += unit.get_attack_count()
        
        # Rear units - full attacks
        for unit in self.rear_units:
            if isinstance(unit, Character):
                total += unit.attacks
            else:
                total += unit.get_attack_count()
        
        # Supporting units - reduced attacks (typically 1 per model in contact)
        for unit in self.supporting_units:
            # Supporting attacks: 1 per model in front rank
            supporting_attacks = min(unit.current_models, unit.formation.files if unit.formation else unit.current_models)
            total += supporting_attacks
        
        return total
    
    def get_combat_resolution_bonus(self) -> int:
        """
        Calculate combat resolution bonus from position and status.
        
        Returns:
            CR bonus (ranks, standards, flank, rear, charge, high ground)
        """
        bonus = 0
        
        # Charging bonus
        if self.is_charging:
            bonus += 1
        
        # Flank bonus
        if len(self.flank_units) > 0:
            bonus += 1
        
        # Rear bonus (replaces flank)
        if len(self.rear_units) > 0:
            bonus += 1  # +2 total with flank, so +1 more
        
        # Higher ground
        if self.has_higher_ground:
            bonus += 1
        
        # Ranks bonus (from main unit)
        if self.front_units:
            main_unit = self.front_units[0]
            if isinstance(main_unit, Unit) and main_unit.formation:
                ranks = main_unit.formation.ranks
                bonus += min(ranks - 1, 3)  # Max +3 for ranks
        
        # Standards
        for unit in self.get_all_units():
            if isinstance(unit, Unit) and unit.command.standard_bearer:
                bonus += 1
                break  # Only count one standard
        
        return bonus
    
    def has_steadfast(self, enemy_group: 'CombatGroup') -> bool:
        """
        Check if group is Steadfast.
        
        Steadfast: More ranks than enemy, not flanked/rear charged.
        
        Args:
            enemy_group: Enemy combat group
        
        Returns:
            True if Steadfast
        """
        # Not steadfast if flanked or rear charged
        if len(enemy_group.flank_units) > 0 or len(enemy_group.rear_units) > 0:
            return False
        
        # Check if we have more ranks
        if not self.front_units:
            return False
        
        main_unit = self.front_units[0]
        if not isinstance(main_unit, Unit) or not main_unit.formation:
            return False
        
        our_ranks = main_unit.formation.ranks
        
        # Enemy ranks
        if enemy_group.front_units:
            enemy_main = enemy_group.front_units[0]
            if isinstance(enemy_main, Unit) and enemy_main.formation:
                enemy_ranks = enemy_main.formation.ranks
                return our_ranks > enemy_ranks
        
        return False


def resolve_shooting(
    attacker: Union[Unit, Character],
    defender: Unit,
    options: Optional[Dict] = None
) -> CombatResult:
    """
    Resolve shooting attack.
    
    TOW Shooting Rules:
    - Roll to hit (BS + modifiers)
    - Roll to wound (S vs T) using WEAPON strength
    - Apply AP to armor saves
    - Defender makes saves
    - Check for panic (25%+ casualties)
    
    Args:
        attacker: Shooting unit/character
        defender: Target unit
        options: Dict with modifiers
            {
                'long_range': bool,
                'cover': bool,
                'moving': bool,
                'stand_and_shoot': bool,
                'skirmisher_target': bool,
                'weapon_strength': int,  # Override weapon strength
                'weapon_ap': int,        # Override weapon AP
            }
    
    Returns:
        CombatResult with shooting outcome
    """
    options = options or {}
    result = CombatResult(
        attacker_name=attacker.name,
        defender_name=defender.name
    )
    
    # Get weapon stats
    ranged_weapon = None
    if hasattr(attacker, 'equipment') and attacker.equipment.ranged_weapon:
        ranged_weapon = attacker.equipment.ranged_weapon
    
    # Weapon strength (use weapon if available, else options, else S3 default for bows)
    if options.get('weapon_strength'):
        weapon_strength = options['weapon_strength']
    elif ranged_weapon and ranged_weapon.strength:
        weapon_strength = ranged_weapon.strength
    elif ranged_weapon:
        weapon_strength = ranged_weapon.get_strength(attacker.strength)
    else:
        # Default weapon strengths by special rules
        if "Handgun" in attacker.special_rules:
            weapon_strength = 4
        elif "Crossbow" in attacker.special_rules:
            weapon_strength = 4
        elif "Shooting" in attacker.special_rules:
            weapon_strength = 3  # Default bow
        else:
            weapon_strength = attacker.strength
    
    # Weapon AP
    if options.get('weapon_ap') is not None:
        weapon_ap = options['weapon_ap']
    elif ranged_weapon:
        weapon_ap = ranged_weapon.ap
    else:
        # Default AP by weapon type
        if "Handgun" in attacker.special_rules:
            weapon_ap = -1
        else:
            weapon_ap = 0
    
    # Get attacks (shots)
    if isinstance(attacker, Character):
        attacks = 1  # Characters typically get 1 shot
    else:
        attacks = attacker.current_models  # 1 shot per model typically
    
    # Check for multiple shots
    if ranged_weapon and hasattr(ranged_weapon, 'shots') and ranged_weapon.shots:
        attacks *= ranged_weapon.shots
    
    result.total_attacks = attacks
    
    # Calculate to-hit modifiers
    modifiers = {}
    if options.get('long_range'):
        modifiers['long_range'] = True
    if options.get('cover'):
        modifiers['cover'] = True
    if options.get('moving'):
        modifiers['moving'] = True
    if options.get('skirmisher_target'):
        modifiers['skirmisher'] = True
    
    # Large target bonus
    if hasattr(defender, 'is_large_target') and defender.is_large_target:
        modifiers['large_target'] = True
    
    to_hit = to_hit_bs(attacker.ballistic_skill, modifiers)
    
    # Roll to hit
    hit_result = calculate_hits(attacks, to_hit)
    result.hits = hit_result['hits']
    result.hit_rolls = hit_result['rolls']
    
    if result.hits == 0:
        return result
    
    # Calculate to-wound using WEAPON strength
    to_wound_val = to_wound(weapon_strength, defender.toughness)
    
    # Roll to wound
    wound_result = calculate_wounds(result.hits, to_wound_val)
    result.wounds = wound_result['wounds']
    result.wound_rolls = wound_result['rolls']
    
    if result.wounds == 0:
        return result
    
    # Defender saves (with AP applied)
    remaining_wounds = result.wounds
    
    # Armor save (modified by weapon AP)
    if defender.armour_save:
        modified_save = armour_save(defender.armour_save, weapon_ap)
        if modified_save:
            save_result = calculate_saves(remaining_wounds, modified_save, 'armour')
            result.saves_made += save_result['successful_saves']
            remaining_wounds = save_result['failed_saves']
            result.save_rolls.extend(save_result['rolls'])
        # else: AP negated armor entirely
    
    # Ward save (unaffected by AP)
    if defender.ward_save and remaining_wounds > 0:
        save_result = calculate_saves(remaining_wounds, defender.ward_save, 'ward')
        result.saves_made += save_result['successful_saves']
        remaining_wounds = save_result['failed_saves']
        result.save_rolls.extend(save_result['rolls'])
    
    # Apply casualties
    result.casualties = remaining_wounds
    defender.take_casualties(result.casualties)
    
    # Check for panic (25%+ casualties from shooting)
    casualties_percent = (result.casualties / defender.max_models) * 100
    if casualties_percent >= 25:
        result.panic_test_required = True
        result.special_effects.append("Panic test required (25%+ casualties)")
    
    return result


def resolve_melee_combat(
    side_a: CombatGroup,
    side_b: CombatGroup,
    round_number: int = 1
) -> Tuple[CombatResult, CombatResult]:
    """
    Resolve a full round of melee combat.
    
    TOW Melee Rules:
    1. Determine who strikes first (Initiative or special rules)
    2. Resolve attacks (both sides)
    3. Calculate combat resolution
    4. Loser takes break test
    5. Winner pursues if loser flees
    
    Args:
        side_a: First combat group
        side_b: Second combat group
        round_number: Which round of combat (for Hatred, etc.)
    
    Returns:
        Tuple of (side_a_result, side_b_result)
    """
    # Create combat context
    context = CombatContext(
        round_number=round_number,
        is_charging=side_a.is_charging,
        is_flanking=len(side_a.flank_units) > 0,
        is_rear_charge=len(side_a.rear_units) > 0
    )
    
    # Resolve side A attacks
    result_a = _resolve_combat_attacks(side_a, side_b, context)
    
    # Resolve side B attacks (if any models left)
    context_b = CombatContext(
        round_number=round_number,
        is_charging=side_b.is_charging,
        is_flanking=len(side_b.flank_units) > 0,
        is_rear_charge=len(side_b.rear_units) > 0
    )
    result_b = _resolve_combat_attacks(side_b, side_a, context_b)
    
    # Calculate combat resolution
    side_a_wounds = result_a.casualties
    side_b_wounds = result_b.casualties
    
    side_a_bonus = side_a.get_combat_resolution_bonus()
    side_b_bonus = side_b.get_combat_resolution_bonus()
    
    result_a.attacker_cr = side_a_wounds + side_a_bonus
    result_a.defender_cr = side_b_wounds + side_b_bonus
    result_a.combat_result_difference = result_a.attacker_cr - result_a.defender_cr
    
    result_b.attacker_cr = side_b_wounds + side_b_bonus
    result_b.defender_cr = side_a_wounds + side_a_bonus
    result_b.combat_result_difference = result_b.attacker_cr - result_b.defender_cr
    
    # Determine loser and break test
    if result_a.combat_result_difference > 0:
        # Side A won - side B takes break test
        _resolve_break_test(side_b, result_b, -result_a.combat_result_difference, side_a)
    elif result_b.combat_result_difference > 0:
        # Side B won - side A takes break test
        _resolve_break_test(side_a, result_a, -result_b.combat_result_difference, side_b)
    # else: draw - no break tests
    
    return (result_a, result_b)


def _resolve_combat_attacks(
    attacker_group: CombatGroup,
    defender_group: CombatGroup,
    context: CombatContext
) -> CombatResult:
    """
    Resolve attacks from one combat group to another.
    
    Args:
        attacker_group: Attacking group
        defender_group: Defending group
        context: Combat context
    
    Returns:
        CombatResult
    """
    attacker_units = attacker_group.get_all_units()
    defender_units = defender_group.get_all_units()
    
    if not attacker_units or not defender_units:
        return CombatResult(
            attacker_name="Unknown",
            defender_name="Unknown"
        )
    
    # Get main attacker and defender
    main_attacker = attacker_units[0]
    main_defender = defender_units[0]
    
    result = CombatResult(
        attacker_name=main_attacker.name,
        defender_name=main_defender.name
    )
    
    # Get total attacks
    total_attacks = attacker_group.get_total_attacks()
    result.total_attacks = total_attacks
    
    if total_attacks == 0:
        return result
    
    # Calculate to-hit (using main attacker/defender stats)
    if isinstance(main_attacker, Character):
        attacker_ws = main_attacker.weapon_skill
        attacker_strength = main_attacker.strength
    else:
        attacker_ws = main_attacker.weapon_skill
        attacker_strength = main_attacker.get_effective_strength(attacker_group.is_charging)
    
    if isinstance(main_defender, Character):
        defender_ws = main_defender.weapon_skill
        defender_toughness = main_defender.toughness
    else:
        defender_ws = main_defender.weapon_skill
        defender_toughness = main_defender.toughness
    
    to_hit = to_hit_ws(attacker_ws, defender_ws)
    
    # Apply special rules modifiers
    special_rules = main_attacker.special_rules if hasattr(main_attacker, 'special_rules') else []
    hit_mods = apply_to_hit_modifiers(to_hit, special_rules, context)
    
    # Roll to hit
    hit_special_rules = {}
    if hit_mods.get('reroll_misses'):
        hit_special_rules['reroll_failed_hits'] = True
    
    hit_result = calculate_hits(total_attacks, hit_mods['modified_target'], hit_special_rules)
    result.hits = hit_result['hits']
    result.hit_rolls = hit_result['rolls']
    
    if result.hits == 0:
        return result
    
    # Roll to wound
    to_wound_val = to_wound(attacker_strength, defender_toughness)
    wound_result = calculate_wounds(result.hits, to_wound_val)
    result.wounds = wound_result['wounds']
    result.wound_rolls = wound_result['rolls']
    
    if result.wounds == 0:
        return result
    
    # Defender saves
    remaining_wounds = result.wounds
    
    # Armor save
    if isinstance(main_defender, Unit) and main_defender.armour_save:
        save_result = calculate_saves(remaining_wounds, main_defender.armour_save, 'armour')
        result.saves_made += save_result['successful_saves']
        remaining_wounds = save_result['failed_saves']
    
    # Ward save
    if hasattr(main_defender, 'ward_save') and main_defender.ward_save and remaining_wounds > 0:
        save_result = calculate_saves(remaining_wounds, main_defender.ward_save, 'ward')
        result.saves_made += save_result['successful_saves']
        remaining_wounds = save_result['failed_saves']
    
    # Apply casualties
    result.casualties = remaining_wounds
    if isinstance(main_defender, Unit):
        main_defender.take_casualties(result.casualties)
    
    return result


def _resolve_break_test(
    losing_group: CombatGroup,
    result: CombatResult,
    cr_difference: int,
    winning_group: CombatGroup
) -> None:
    """
    Resolve break test for losing group.
    
    Modifies result in place with break test outcome.
    
    Args:
        losing_group: Group that lost combat
        result: CombatResult to update
        cr_difference: Negative CR difference
        winning_group: Winning group (for steadfast check)
    """
    units = losing_group.get_all_units()
    if not units:
        return
    
    main_unit = units[0]
    
    # Check for Unbreakable
    if hasattr(main_unit, 'is_unbreakable') and main_unit.is_unbreakable:
        result.special_effects.append("Unbreakable - no break test")
        return
    
    # Build modifiers
    modifiers = {}
    
    # Steadfast
    if losing_group.has_steadfast(winning_group):
        modifiers['steadfast'] = True
        result.special_effects.append("Steadfast - ignore CR")
    
    # Stubborn
    if hasattr(main_unit, 'is_stubborn') and main_unit.is_stubborn:
        modifiers['stubborn'] = True
        result.special_effects.append("Stubborn - ignore CR")
    
    # Break test
    leadership = main_unit.leadership
    broke, roll = break_test(leadership, cr_difference, modifiers)
    
    result.break_test_roll = roll
    result.defender_broke = broke
    
    if broke:
        result.defender_fled = True
        result.special_effects.append(f"Failed break test - FLEEING!")
        
        # Mark unit as fleeing
        if isinstance(main_unit, Unit):
            main_unit.is_fleeing = True
        
        # Roll flee distance
        flee_roll = roll_2d6()
        result.flee_distance = flee_roll
        result.special_effects.append(f"Flees {flee_roll}\"")
        
        # Winner pursues
        pursue_roll = roll_2d6()
        result.pursuit_distance = pursue_roll
        result.special_effects.append(f"Enemy pursues {pursue_roll}\"")
        
        # Check if caught
        if pursue_roll >= flee_roll:
            result.caught_fleeing = True
            result.special_effects.append("CAUGHT AND DESTROYED!")
            if isinstance(main_unit, Unit):
                main_unit.current_models = 0


def resolve_impact_hits(
    attacker: Union[Unit, Character],
    defender: Unit,
    charging: bool = True
) -> CombatResult:
    """
    Resolve Impact Hits when charging.
    
    TOW Rules: Chariots, cavalry, monsters cause automatic hits when charging.
    Impact hits are resolved before combat.
    
    Args:
        attacker: Charging unit/character
        defender: Target unit
        charging: Must be charging to get impact hits
    
    Returns:
        CombatResult with impact hit outcome
    """
    result = CombatResult(
        attacker_name=attacker.name,
        defender_name=defender.name
    )
    
    if not charging:
        return result
    
    # Check for Impact Hits special rule
    impact_hits = None
    for rule in attacker.special_rules:
        if "Impact Hits" in rule:
            if "D6" in rule:
                impact_hits = d6(1)[0]
            elif "D3" in rule:
                from ..core.dice import roll_d3
                impact_hits = roll_d3()
            break
    
    if not impact_hits:
        return result
    
    result.special_effects.append(f"Impact Hits: {impact_hits} automatic hits")
    result.hits = impact_hits
    result.total_attacks = impact_hits
    
    # Roll to wound (S of unit)
    strength = attacker.strength
    to_wound_val = to_wound(strength, defender.toughness)
    
    wound_result = calculate_wounds(impact_hits, to_wound_val)
    result.wounds = wound_result['wounds']
    
    # Defender saves
    remaining_wounds = result.wounds
    
    if defender.armour_save:
        save_result = calculate_saves(remaining_wounds, defender.armour_save, 'armour')
        result.saves_made = save_result['successful_saves']
        remaining_wounds = save_result['failed_saves']
    
    result.casualties = remaining_wounds
    defender.take_casualties(result.casualties)
    
    return result


def resolve_stomp(
    attacker: Union[Unit, Character],
    defender: Unit
) -> CombatResult:
    """
    Resolve Stomp attacks at end of combat.
    
    TOW Rules: Large monsters stomp at end of combat phase.
    D6 S5 hits with no armor save.
    
    Args:
        attacker: Monster with Stomp
        defender: Target unit
    
    Returns:
        CombatResult with stomp outcome
    """
    result = CombatResult(
        attacker_name=attacker.name,
        defender_name=defender.name
    )
    
    # Check for Stomp or Thunderstomp
    has_stomp = "Stomp" in attacker.special_rules
    has_thunderstomp = "Thunderstomp" in attacker.special_rules
    
    if not (has_stomp or has_thunderstomp):
        return result
    
    # Roll D6 hits
    stomp_hits = d6(1)[0]
    result.hits = stomp_hits
    result.total_attacks = stomp_hits
    result.special_effects.append(f"Stomp: {stomp_hits} S5 hits (no armor save)")
    
    # Roll to wound at S5
    to_wound_val = to_wound(5, defender.toughness)
    wound_result = calculate_wounds(stomp_hits, to_wound_val)
    result.wounds = wound_result['wounds']
    
    # No armor save for Stomp
    if has_thunderstomp:
        # Thunderstomp causes D3 wounds each
        from ..core.dice import roll_d3
        total_wounds = 0
        for _ in range(result.wounds):
            total_wounds += roll_d3()
        result.casualties = total_wounds
        result.special_effects.append(f"Thunderstomp: D3 wounds each = {total_wounds} total")
    else:
        result.casualties = result.wounds
    
    # Ward saves still apply
    remaining_wounds = result.casualties
    if defender.ward_save:
        save_result = calculate_saves(remaining_wounds, defender.ward_save, 'ward')
        result.saves_made = save_result['successful_saves']
        remaining_wounds = save_result['failed_saves']
        result.casualties = remaining_wounds
    
    defender.take_casualties(result.casualties)
    
    return result


def resolve_breath_weapon(
    attacker: Union[Unit, Character],
    defender: Unit,
    weapon_strength: int = 4
) -> CombatResult:
    """
    Resolve Breath Weapon attack.
    
    TOW Rules: Template weapon that hits multiple models.
    Simplified: hits D6 models.
    
    Args:
        attacker: Unit with breath weapon
        defender: Target unit
        weapon_strength: Strength of breath weapon (default 4)
    
    Returns:
        CombatResult with breath weapon outcome
    """
    result = CombatResult(
        attacker_name=attacker.name,
        defender_name=defender.name
    )
    
    # Check for Breath Weapon
    has_breath = False
    is_flaming = False
    
    for rule in attacker.special_rules:
        if "Breath Weapon" in rule:
            has_breath = True
            if "Flaming" in rule:
                is_flaming = True
            if "Str 5" in rule or "S5" in rule:
                weapon_strength = 5
            break
    
    if not has_breath:
        return result
    
    # Template hits D6 models
    template_hits = d6(1)[0]
    result.hits = template_hits
    result.total_attacks = template_hits
    result.special_effects.append(f"Breath Weapon: hits {template_hits} models")
    
    if is_flaming:
        result.special_effects.append("Flaming - negates Regeneration")
    
    # Roll to wound
    to_wound_val = to_wound(weapon_strength, defender.toughness)
    wound_result = calculate_wounds(template_hits, to_wound_val)
    result.wounds = wound_result['wounds']
    
    # Defender saves
    remaining_wounds = result.wounds
    
    if defender.armour_save:
        save_result = calculate_saves(remaining_wounds, defender.armour_save, 'armour')
        result.saves_made = save_result['successful_saves']
        remaining_wounds = save_result['failed_saves']
    
    # Regeneration negated by flaming
    if not is_flaming and defender.regeneration:
        save_result = calculate_saves(remaining_wounds, defender.regeneration, 'regeneration')
        result.saves_made += save_result['successful_saves']
        remaining_wounds = save_result['failed_saves']
    
    result.casualties = remaining_wounds
    defender.take_casualties(result.casualties)
    
    return result


def run_full_combat_round(
    side_a: CombatGroup,
    side_b: CombatGroup,
    round_number: int = 1
) -> Tuple[CombatResult, CombatResult]:
    """
    Run a complete combat round including all special attacks.
    
    Sequence:
    1. Impact Hits (if charging)
    2. Normal combat
    3. Stomp attacks
    4. Combat resolution
    5. Break tests
    6. Pursuit
    
    Args:
        side_a: First combat group
        side_b: Second combat group
        round_number: Combat round number
    
    Returns:
        Tuple of (side_a_result, side_b_result)
    """
    # Step 1: Impact Hits (charging units)
    if side_a.is_charging:
        for unit in side_a.get_all_units():
            if "Impact Hits" in unit.special_rules:
                impact_result = resolve_impact_hits(unit, side_b.get_all_units()[0], True)
                # Record impact hits
    
    if side_b.is_charging:
        for unit in side_b.get_all_units():
            if "Impact Hits" in unit.special_rules:
                impact_result = resolve_impact_hits(unit, side_a.get_all_units()[0], True)
    
    # Step 2: Normal combat
    result_a, result_b = resolve_melee_combat(side_a, side_b, round_number)
    
    # Step 3: Stomp attacks (if applicable)
    for unit in side_a.get_all_units():
        if "Stomp" in unit.special_rules or "Thunderstomp" in unit.special_rules:
            stomp_result = resolve_stomp(unit, side_b.get_all_units()[0])
            result_a.casualties += stomp_result.casualties
            result_a.special_effects.extend(stomp_result.special_effects)
    
    for unit in side_b.get_all_units():
        if "Stomp" in unit.special_rules or "Thunderstomp" in unit.special_rules:
            stomp_result = resolve_stomp(unit, side_a.get_all_units()[0])
            result_b.casualties += stomp_result.casualties
            result_b.special_effects.extend(stomp_result.special_effects)
    
    return (result_a, result_b)


def simulate_full_battle(
    army_a_units: List[Unit],
    army_b_units: List[Unit],
    max_rounds: int = 6
) -> Dict:
    """
    Simulate a full battle between two armies.
    
    Simplified simulation: All units engage in one big combat.
    
    Args:
        army_a_units: Army A's units
        army_b_units: Army B's units
        max_rounds: Maximum combat rounds
    
    Returns:
        Dict with battle outcome
    """
    # Create combat groups
    side_a = CombatGroup(front_units=army_a_units, is_charging=True)
    side_b = CombatGroup(front_units=army_b_units)
    
    results = {
        'winner': None,
        'rounds': 0,
        'army_a_survivors': 0,
        'army_b_survivors': 0,
        'round_results': []
    }
    
    for round_num in range(1, max_rounds + 1):
        # Check if either side destroyed
        if not any(u.is_alive for u in army_a_units):
            results['winner'] = 'Army B'
            break
        if not any(u.is_alive for u in army_b_units):
            results['winner'] = 'Army A'
            break
        
        # Run combat round
        result_a, result_b = run_full_combat_round(side_a, side_b, round_num)
        
        results['round_results'].append({
            'round': round_num,
            'army_a': result_a.to_dict(),
            'army_b': result_b.to_dict()
        })
        
        # Check for routs
        if result_b.defender_fled or result_b.caught_fleeing:
            results['winner'] = 'Army A'
            break
        if result_a.defender_fled or result_a.caught_fleeing:
            results['winner'] = 'Army B'
            break
        
        # After first round, no longer charging
        side_a.is_charging = False
        side_b.is_charging = False
        
        results['rounds'] = round_num
    
    # Count survivors
    results['army_a_survivors'] = sum(u.current_models for u in army_a_units if u.is_alive)
    results['army_b_survivors'] = sum(u.current_models for u in army_b_units if u.is_alive)
    
    if not results['winner']:
        # Determine by survivors
        if results['army_a_survivors'] > results['army_b_survivors']:
            results['winner'] = 'Army A'
        elif results['army_b_survivors'] > results['army_a_survivors']:
            results['winner'] = 'Army B'
        else:
            results['winner'] = 'Draw'
    
    return results

