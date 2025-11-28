"""
Unit and model definitions for Warhammer: The Old World
Complete unit dataclass with all Ravening Hordes statistics
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class TroopType(Enum):
    """Type of troop for movement and rules"""
    INFANTRY = "infantry"
    CAVALRY = "cavalry"
    MONSTROUS_INFANTRY = "monstrous_infantry"
    MONSTROUS_CAVALRY = "monstrous_cavalry"
    CHARIOT = "chariot"
    MONSTER = "monster"
    WAR_MACHINE = "war_machine"
    SWARM = "swarm"


class BaseSize(Enum):
    """Standard base sizes in mm"""
    SMALL_20 = 20
    MEDIUM_25 = 25
    LARGE_40 = 40
    CAVALRY_25x50 = (25, 50)
    MONSTER_40x40 = 40
    MONSTER_50x50 = 50
    MONSTER_60x60 = 60
    MONSTER_100x100 = 100
    CHARIOT_50x100 = (50, 100)


class UnitCategory(Enum):
    """Army list categories"""
    CORE = "core"
    SPECIAL = "special"
    RARE = "rare"
    LORD = "lord"
    HERO = "hero"


@dataclass
class Weapon:
    """Weapon profile for units"""
    name: str
    strength: Optional[int] = None  # None means user strength
    strength_bonus: int = 0  # Bonus to user strength
    ap: int = 0  # Armor piercing modifier (negative)
    special_rules: List[str] = field(default_factory=list)
    range: Optional[int] = None  # Range in inches (for shooting)
    requires_two_hands: bool = False
    
    def get_strength(self, user_strength: int) -> int:
        """Calculate final strength of weapon"""
        if self.strength is not None:
            return self.strength
        return user_strength + self.strength_bonus


@dataclass
class Equipment:
    """Unit equipment loadout"""
    melee_weapon: Weapon = field(default_factory=lambda: Weapon("Hand Weapon"))
    ranged_weapon: Optional[Weapon] = None
    armor: List[str] = field(default_factory=list)  # ["Light Armour", "Shield"]
    magic_items: List[str] = field(default_factory=list)
    
    def calculate_armor_save(self) -> Optional[int]:
        """Calculate armor save from equipment"""
        save = None
        
        # Base armor values (6+ to 1+)
        armor_values = {
            "Light Armour": 6,
            "Heavy Armour": 5,
            "Full Plate Armour": 4,
            "Shield": 1,  # +1 bonus
            "Barding": 1,  # +1 bonus for mounts
        }
        
        for armor_piece in self.armor:
            if armor_piece in armor_values:
                value = armor_values[armor_piece]
                if armor_piece in ["Shield", "Barding"]:
                    # These are bonuses (+1 to save)
                    if save is not None:
                        save = max(2, save - value)
                else:
                    # These are base saves
                    if save is None:
                        save = value
                    else:
                        save = min(save, value)
        
        return save


@dataclass
class Command:
    """Command group options"""
    champion: bool = False
    musician: bool = False
    standard_bearer: bool = False
    magic_standard: Optional[str] = None
    
    @property
    def has_full_command(self) -> bool:
        """Check if unit has full command group"""
        return self.champion and self.musician and self.standard_bearer


@dataclass
class Formation:
    """Unit formation on battlefield"""
    ranks: int = 1
    files: int = 1
    
    @property
    def total_models(self) -> int:
        """Total models in formation"""
        return self.ranks * files
    
    def is_horde(self, unit_size: int) -> bool:
        """Check if unit qualifies for Horde rule (10+ wide)"""
        return self.files >= 10
    
    def get_rank_bonus(self) -> int:
        """Get combat resolution rank bonus (max +3)"""
        return min(self.ranks - 1, 3)
    
    def can_fight(self, rank: int, unit) -> bool:
        """Determine if models in this rank can fight"""
        if rank == 1:
            return True
        if rank == 2:
            # Second rank can support or use spears
            return True
        if rank == 3:
            # Third rank only with spears or horde
            if "Spear" in [w.name for w in [unit.equipment.melee_weapon]]:
                return True
            if self.is_horde(self.files * self.ranks):
                return True
        return False


@dataclass
class Unit:
    """
    Complete unit representation for Warhammer: The Old World.
    
    Based on Ravening Hordes and Forces of Fantasy profiles.
    """
    # Identification
    name: str
    faction: str
    category: UnitCategory
    troop_type: TroopType
    base_size: BaseSize
    
    # Core Statistics (The profile line)
    movement: int  # M
    weapon_skill: int  # WS
    ballistic_skill: int  # BS
    strength: int  # S
    toughness: int  # T
    wounds: int  # W
    initiative: int  # I
    attacks: int  # A
    leadership: int  # Ld
    
    # Unit composition
    max_models: int  # Maximum unit size
    current_models: int  # Current models remaining
    min_unit_size: int = 1  # Minimum unit size
    
    # Equipment and upgrades
    equipment: Equipment = field(default_factory=Equipment)
    command: Command = field(default_factory=Command)
    
    # Special rules and abilities
    special_rules: List[str] = field(default_factory=list)
    
    # Saves
    armour_save: Optional[int] = None  # Calculated from equipment if None
    ward_save: Optional[int] = None
    regeneration: Optional[int] = None
    
    # Formation
    formation: Optional[Formation] = None
    
    # Points and restrictions
    points_cost_per_model: int = 0
    points_cost_base: int = 0  # Base cost before models
    
    # Game state
    unit_strength: int = 1  # US per model (usually 1, cavalry=2, monsters=5+)
    is_large_target: bool = False
    is_ethereal: bool = False
    is_flammable: bool = False
    is_immune_to_psychology: bool = False
    is_unbreakable: bool = False
    is_stubborn: bool = False
    
    # Status effects (managed during game)
    is_fleeing: bool = False
    is_shaken: bool = False
    has_charged: bool = False
    combat_round: int = 0  # Which round of combat (for Hatred, etc.)
    
    def __post_init__(self):
        """Initialize calculated values"""
        # Calculate armor save from equipment if not provided
        if self.armour_save is None:
            self.armour_save = self.equipment.calculate_armor_save()
        
        # Initialize formation if not provided
        if self.formation is None:
            # Default to single rank
            self.formation = Formation(ranks=1, files=self.current_models)
        
        # Parse special rules for automatic flags
        self._parse_special_rules()
    
    def _parse_special_rules(self):
        """Parse special rules and set automatic flags"""
        rule_flags = {
            "Ethereal": "is_ethereal",
            "Immune to Psychology": "is_immune_to_psychology",
            "Unbreakable": "is_unbreakable",
            "Stubborn": "is_stubborn",
            "Large Target": "is_large_target",
            "Flammable": "is_flammable",
        }
        
        for rule in self.special_rules:
            rule_name = rule.split('(')[0].strip()  # Handle "Ward Save (5+)"
            if rule_name in rule_flags:
                setattr(self, rule_flags[rule_name], True)
    
    @property
    def is_alive(self) -> bool:
        """Check if unit has any models remaining"""
        return self.current_models > 0
    
    @property
    def total_unit_strength(self) -> int:
        """Calculate total unit strength"""
        return self.unit_strength * self.current_models
    
    @property
    def total_points_cost(self) -> int:
        """Calculate total points cost"""
        cost = self.points_cost_base + (self.points_cost_per_model * self.current_models)
        
        # Add command group costs (simplified - should come from data)
        if self.command.champion:
            cost += 10
        if self.command.musician:
            cost += 5
        if self.command.standard_bearer:
            cost += 10
        
        return cost
    
    def take_casualties(self, casualties: int) -> int:
        """
        Remove casualties from the unit.
        
        Args:
            casualties: Number of models to remove
        
        Returns:
            Actual casualties removed
        """
        actual_casualties = min(casualties, self.current_models)
        self.current_models -= actual_casualties
        
        # Update formation
        if self.formation:
            # Recalculate formation (remove from rear ranks first)
            total_models = self.current_models
            files = self.formation.files
            ranks = (total_models + files - 1) // files  # Ceiling division
            self.formation.ranks = max(1, ranks)
        
        return actual_casualties
    
    def restore_models(self, models: int) -> int:
        """
        Restore models (e.g., from healing magic).
        
        Args:
            models: Number of models to restore
        
        Returns:
            Actual models restored
        """
        actual_restored = min(models, self.max_models - self.current_models)
        self.current_models += actual_restored
        return actual_restored
    
    def reform_formation(self, ranks: int, files: int) -> bool:
        """
        Reform the unit into new formation.
        
        Args:
            ranks: New number of ranks
            files: New number of files
        
        Returns:
            True if reform succeeded
        """
        if ranks * files != self.current_models:
            return False
        
        self.formation = Formation(ranks=ranks, files=files)
        return True
    
    def can_charge(self) -> bool:
        """Check if unit can declare a charge"""
        if not self.is_alive:
            return False
        if self.is_fleeing:
            return False
        # Check for Frenzy (must charge if able)
        # This would be checked by game logic
        return True
    
    def get_fighting_models(self) -> int:
        """
        Calculate how many models can fight.
        
        Based on formation and special rules (spears, horde, etc.)
        """
        if not self.is_alive or not self.formation:
            return 0
        
        fighting_models = 0
        
        # First rank always fights
        fighting_models += min(self.formation.files, self.current_models)
        
        # Check if we have enough models for second rank
        if self.current_models > self.formation.files:
            # Second rank can support
            second_rank_models = min(self.formation.files, 
                                     self.current_models - self.formation.files)
            fighting_models += second_rank_models
        
        # Check for spears (3rd rank fights)
        has_spears = "Spear" in [self.equipment.melee_weapon.name]
        if has_spears and self.current_models > 2 * self.formation.files:
            third_rank_models = min(self.formation.files,
                                   self.current_models - 2 * self.formation.files)
            fighting_models += third_rank_models
        
        # Check for Horde (extra attacks)
        if self.formation.is_horde(self.current_models):
            # Horde rule handled separately in combat calculations
            pass
        
        return fighting_models
    
    def get_attack_count(self) -> int:
        """
        Calculate total attacks for the unit.
        
        Considers: base attacks, extra ranks, horde, frenzy, etc.
        """
        fighting_models = self.get_fighting_models()
        attacks_per_model = self.attacks
        
        # Apply special rules
        if "Frenzy" in self.special_rules:
            attacks_per_model += 1
        
        total_attacks = fighting_models * attacks_per_model
        
        # Horde bonus (extra attacks for 10+ wide units)
        if self.formation and self.formation.is_horde(self.current_models):
            total_attacks += self.formation.files  # +1 attack per file
        
        return total_attacks
    
    def get_effective_strength(self, charging: bool = False) -> int:
        """
        Get effective strength for combat.
        
        Args:
            charging: Whether unit is charging
        
        Returns:
            Modified strength value
        """
        strength = self.strength
        
        # Weapon bonuses
        if self.equipment.melee_weapon:
            strength = self.equipment.melee_weapon.get_strength(self.strength)
        
        # Charging bonuses
        if charging:
            if "Devastating Charge" in self.special_rules:
                strength += 1
            if "Lance" in [self.equipment.melee_weapon.name]:
                if self.troop_type == TroopType.CAVALRY:
                    strength += 2
        
        return strength
    
    def to_dict(self) -> Dict[str, Any]:
        """Export unit to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "faction": self.faction,
            "category": self.category.value,
            "troop_type": self.troop_type.value,
            "current_models": self.current_models,
            "max_models": self.max_models,
            "profile": {
                "M": self.movement,
                "WS": self.weapon_skill,
                "BS": self.ballistic_skill,
                "S": self.strength,
                "T": self.toughness,
                "W": self.wounds,
                "I": self.initiative,
                "A": self.attacks,
                "Ld": self.leadership
            },
            "equipment": {
                "melee_weapon": self.equipment.melee_weapon.name,
                "armor": self.equipment.armor
            },
            "special_rules": self.special_rules,
            "points_cost": self.total_points_cost
        }


# Convenience function for creating basic units
def create_unit(name: str, profile: Dict[str, int], **kwargs) -> Unit:
    """
    Create a unit from a profile dict.
    
    Args:
        name: Unit name
        profile: Dict with M, WS, BS, S, T, W, I, A, Ld
        **kwargs: Additional unit attributes
    
    Returns:
        Configured Unit instance
    """
    return Unit(
        name=name,
        movement=profile["M"],
        weapon_skill=profile["WS"],
        ballistic_skill=profile["BS"],
        strength=profile["S"],
        toughness=profile["T"],
        wounds=profile["W"],
        initiative=profile["I"],
        attacks=profile["A"],
        leadership=profile["Ld"],
        **kwargs
    )
