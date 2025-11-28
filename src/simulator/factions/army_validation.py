"""
Army list validation for Warhammer: The Old World
Validates army composition against TOW rules
"""

from typing import List, Dict, Optional, Tuple
from ..models.unit import Unit, Character, UnitCategory


class ArmyValidationError(Exception):
    """Raised when army list validation fails"""
    pass


class ArmyList:
    """
    Represents a complete army list with validation.
    """
    
    def __init__(self, faction: str, points_limit: int = 2000):
        """
        Initialize an army list.
        
        Args:
            faction: Faction name
            points_limit: Maximum points allowed (default 2000)
        """
        self.faction = faction
        self.points_limit = points_limit
        self.units: List[Unit] = []
        self.characters: List[Character] = []
        self.general: Optional[Character] = None
    
    def add_unit(self, unit: Unit):
        """Add a unit to the army"""
        if unit.faction != self.faction:
            raise ArmyValidationError(
                f"Unit {unit.name} is from {unit.faction}, not {self.faction}"
            )
        self.units.append(unit)
    
    def add_character(self, character: Character):
        """Add a character to the army"""
        if character.faction != self.faction:
            raise ArmyValidationError(
                f"Character {character.name} is from {character.faction}, not {self.faction}"
            )
        
        self.characters.append(character)
        
        # Set general if this is the first lord or specified as general
        if character.is_general:
            self.general = character
        elif character.category == UnitCategory.LORD and not self.general:
            self.general = character
            character.is_general = True
    
    def get_total_points(self) -> int:
        """Calculate total army points"""
        total = 0
        
        for unit in self.units:
            total += unit.total_points_cost
        
        for character in self.characters:
            total += character.total_points_cost
        
        return total
    
    def get_category_points(self, category: UnitCategory) -> int:
        """Get total points spent on a category"""
        total = 0
        
        if category in [UnitCategory.LORD, UnitCategory.HERO]:
            for char in self.characters:
                if char.category == category:
                    total += char.total_points_cost
        else:
            for unit in self.units:
                if unit.category == category:
                    total += unit.total_points_cost
        
        return total
    
    def get_category_percentage(self, category: UnitCategory) -> float:
        """Get percentage of army spent on category"""
        total = self.get_total_points()
        if total == 0:
            return 0.0
        
        category_points = self.get_category_points(category)
        return (category_points / total) * 100
    
    def load_faction_rules(self) -> Optional[Dict]:
        """Load faction-specific list building rules"""
        from .loader import get_loader
        return get_loader().load_faction_rules(self.faction)
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate the army list against TOW rules and faction-specific rules.
        
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Load faction-specific rules
        faction_rules = self.load_faction_rules()
        list_rules = faction_rules.get("list_building_rules", {}) if faction_rules else {}
        
        # Get limits from faction rules (or use defaults)
        core_min = list_rules.get("core_minimum", 25)
        lords_max = list_rules.get("lords_maximum", 25)
        heroes_max = list_rules.get("heroes_maximum", 50)
        special_max = list_rules.get("special_maximum", 50)
        rare_max = list_rules.get("rare_maximum", 25)
        max_lords_count = list_rules.get("max_lords", 4)
        max_heroes_count = list_rules.get("max_heroes", 6)
        duplicate_limit = list_rules.get("duplicate_limit", 3)
        
        # Check total points
        total_points = self.get_total_points()
        if total_points > self.points_limit:
            errors.append(
                f"Army exceeds points limit: {total_points}/{self.points_limit}"
            )
        
        # Must have a general
        if not self.general:
            errors.append("Army must have a General (Lord or Hero)")
        
        # Check minimum core requirement
        core_percentage = self.get_category_percentage(UnitCategory.CORE)
        if core_percentage < core_min:
            errors.append(
                f"Core units must be at least {core_min}% of army: currently {core_percentage:.1f}%"
            )
        
        # Check maximum lords
        lords_percentage = self.get_category_percentage(UnitCategory.LORD)
        if lords_percentage > lords_max:
            errors.append(
                f"Lords cannot exceed {lords_max}% of army: currently {lords_percentage:.1f}%"
            )
        
        # Check maximum heroes
        heroes_percentage = self.get_category_percentage(UnitCategory.HERO)
        if heroes_percentage > heroes_max:
            errors.append(
                f"Heroes cannot exceed {heroes_max}% of army: currently {heroes_percentage:.1f}%"
            )
        
        # Check maximum special
        special_percentage = self.get_category_percentage(UnitCategory.SPECIAL)
        if special_percentage > special_max:
            errors.append(
                f"Special units cannot exceed {special_max}% of army: currently {special_percentage:.1f}%"
            )
        
        # Check maximum rare
        rare_percentage = self.get_category_percentage(UnitCategory.RARE)
        if rare_percentage > rare_max:
            errors.append(
                f"Rare units cannot exceed {rare_max}% of army: currently {rare_percentage:.1f}%"
            )
        
        # Check unit size minimums
        for unit in self.units:
            if unit.current_models < unit.min_unit_size:
                errors.append(
                    f"Unit {unit.name} has {unit.current_models} models but minimum is {unit.min_unit_size}"
                )
            
            if unit.current_models > unit.max_models:
                errors.append(
                    f"Unit {unit.name} has {unit.current_models} models but maximum is {unit.max_models}"
                )
        
        # Check duplicate limits
        unit_counts: Dict[str, int] = {}
        for unit in self.units:
            unit_counts[unit.name] = unit_counts.get(unit.name, 0) + 1
        
        # Check faction-specific restrictions
        special_restrictions = list_rules.get("special_restrictions", {})
        
        for unit_name, count in unit_counts.items():
            # Check if unit has special restrictions
            if unit_name in special_restrictions:
                restriction = special_restrictions[unit_name]
                max_allowed = restriction.get("max_total", duplicate_limit)
                if count > max_allowed:
                    errors.append(
                        f"Unit {unit_name} taken {count} times (maximum {max_allowed} for this faction)"
                    )
            elif count > duplicate_limit:
                errors.append(
                    f"Unit {unit_name} taken {count} times (maximum {duplicate_limit} unless specified)"
                )
        
        # Check minimum unit sizes (faction-specific)
        min_sizes = list_rules.get("minimum_unit_sizes", {})
        for unit in self.units:
            if unit.name in min_sizes:
                faction_min = min_sizes[unit.name]
                if unit.current_models < faction_min:
                    errors.append(
                        f"Unit {unit.name} has {unit.current_models} models but {self.faction} requires minimum {faction_min}"
                    )
        
        # Check character limits
        lord_count = sum(1 for c in self.characters if c.category == UnitCategory.LORD)
        hero_count = sum(1 for c in self.characters if c.category == UnitCategory.HERO)
        
        if lord_count > max_lords_count:
            errors.append(f"Too many Lords: {lord_count}/{max_lords_count} maximum")
        
        if hero_count > max_heroes_count:
            errors.append(f"Too many Heroes: {hero_count}/{max_heroes_count} maximum")
        
        # Check BSB (only one allowed)
        bsb_count = sum(1 for c in self.characters if c.is_bsb)
        if bsb_count > 1:
            errors.append("Only one Battle Standard Bearer allowed")
        
        return (len(errors) == 0, errors)
    
    def to_dict(self) -> Dict:
        """Export army list to dictionary"""
        return {
            "faction": self.faction,
            "points_limit": self.points_limit,
            "total_points": self.get_total_points(),
            "general": self.general.name if self.general else None,
            "units": [unit.to_dict() for unit in self.units],
            "characters": [char.to_dict() for char in self.characters],
            "composition": {
                "core": f"{self.get_category_percentage(UnitCategory.CORE):.1f}%",
                "special": f"{self.get_category_percentage(UnitCategory.SPECIAL):.1f}%",
                "rare": f"{self.get_category_percentage(UnitCategory.RARE):.1f}%",
                "lords": f"{self.get_category_percentage(UnitCategory.LORD):.1f}%",
                "heroes": f"{self.get_category_percentage(UnitCategory.HERO):.1f}%"
            }
        }


def validate_army(army_dict: Dict, points_limit: int = 2000) -> Tuple[bool, List[str]]:
    """
    Validate an army from a dictionary.
    
    Args:
        army_dict: Dict representing the army
        points_limit: Maximum points allowed
    
    Returns:
        Tuple of (is_valid, list of errors)
    
    Example:
        >>> army = {
        ...     "faction": "empire",
        ...     "units": [...],
        ...     "characters": [...]
        ... }
        >>> is_valid, errors = validate_army(army, 2000)
    """
    faction = army_dict.get("faction", "")
    army_list = ArmyList(faction, points_limit)
    
    # This is a simplified version
    # Full implementation would load units from the dict
    
    return army_list.validate()


def create_army_summary(army_list: ArmyList) -> str:
    """
    Create a human-readable army summary.
    
    Args:
        army_list: ArmyList to summarize
    
    Returns:
        Formatted string summary
    """
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"ARMY LIST - {army_list.faction.upper()}")
    lines.append(f"{'='*60}")
    lines.append(f"Points: {army_list.get_total_points()}/{army_list.points_limit}")
    lines.append(f"General: {army_list.general.name if army_list.general else 'None'}")
    lines.append("")
    
    # Lords
    lords = [c for c in army_list.characters if c.category == UnitCategory.LORD]
    if lords:
        lines.append("LORDS:")
        for lord in lords:
            lines.append(f"  - {lord.name} [{lord.total_points_cost}pts]")
        lines.append("")
    
    # Heroes
    heroes = [c for c in army_list.characters if c.category == UnitCategory.HERO]
    if heroes:
        lines.append("HEROES:")
        for hero in heroes:
            lines.append(f"  - {hero.name} [{hero.total_points_cost}pts]")
        lines.append("")
    
    # Core
    core_units = [u for u in army_list.units if u.category == UnitCategory.CORE]
    if core_units:
        lines.append("CORE:")
        for unit in core_units:
            lines.append(f"  - {unit.current_models}x {unit.name} [{unit.total_points_cost}pts]")
        lines.append("")
    
    # Special
    special_units = [u for u in army_list.units if u.category == UnitCategory.SPECIAL]
    if special_units:
        lines.append("SPECIAL:")
        for unit in special_units:
            lines.append(f"  - {unit.current_models}x {unit.name} [{unit.total_points_cost}pts]")
        lines.append("")
    
    # Rare
    rare_units = [u for u in army_list.units if u.category == UnitCategory.RARE]
    if rare_units:
        lines.append("RARE:")
        for unit in rare_units:
            lines.append(f"  - {unit.current_models}x {unit.name} [{unit.total_points_cost}pts]")
        lines.append("")
    
    # Composition breakdown
    lines.append("COMPOSITION:")
    lines.append(f"  Core:    {army_list.get_category_percentage(UnitCategory.CORE):.1f}% (min 25%)")
    lines.append(f"  Special: {army_list.get_category_percentage(UnitCategory.SPECIAL):.1f}% (max 50%)")
    lines.append(f"  Rare:    {army_list.get_category_percentage(UnitCategory.RARE):.1f}% (max 25%)")
    lines.append(f"  Lords:   {army_list.get_category_percentage(UnitCategory.LORD):.1f}% (max 25%)")
    lines.append(f"  Heroes:  {army_list.get_category_percentage(UnitCategory.HERO):.1f}% (max 50%)")
    lines.append("")
    
    # Validation
    is_valid, errors = army_list.validate()
    if is_valid:
        lines.append("✓ ARMY LIST IS VALID")
    else:
        lines.append("✗ ARMY LIST HAS ERRORS:")
        for error in errors:
            lines.append(f"  - {error}")
    
    lines.append(f"{'='*60}")
    
    return "\n".join(lines)

