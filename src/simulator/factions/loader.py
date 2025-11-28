"""
Faction and unit loader system
Load units from JSON files and instantiate them with equipment options
"""

import json
from pathlib import Path
from typing import Dict, Optional, Any, List
from ..models.unit import (
    Unit, TroopType, BaseSize, UnitCategory,
    Weapon, Equipment, Command, create_unit
)
from ..models.character import Character, create_character


class UnitLoader:
    """Loads unit definitions from JSON files"""
    
    def __init__(self, data_dir: str = "data/units"):
        """
        Initialize the unit loader.
        
        Args:
            data_dir: Directory containing unit JSON files
        """
        self.data_dir = Path(data_dir)
        self._unit_cache: Dict[str, Dict] = {}
        self._faction_cache: Dict[str, Dict] = {}
    
    def load_unit_data(self, unit_name: str, faction: str) -> Optional[Dict]:
        """
        Load raw unit data from JSON.
        
        Args:
            unit_name: Name of the unit
            faction: Faction name
        
        Returns:
            Dict with unit data, or None if not found
        """
        cache_key = f"{faction}:{unit_name}"
        
        if cache_key in self._unit_cache:
            return self._unit_cache[cache_key]
        
        # Try to find unit file
        faction_dir = self.data_dir / faction
        
        if not faction_dir.exists():
            return None
        
        # Try direct file
        unit_file = faction_dir / f"{unit_name.lower().replace(' ', '_')}.json"
        
        if not unit_file.exists():
            # Try searching in faction's units file
            units_file = faction_dir / "units.json"
            if units_file.exists():
                with open(units_file, 'r') as f:
                    units_data = json.load(f)
                
                if unit_name in units_data:
                    self._unit_cache[cache_key] = units_data[unit_name]
                    return units_data[unit_name]
        else:
            with open(unit_file, 'r') as f:
                unit_data = json.load(f)
                self._unit_cache[cache_key] = unit_data
                return unit_data
        
        return None
    
    def load_unit(self, unit_name: str, faction: str = None, 
                  options: Optional[Dict[str, Any]] = None) -> Optional[Unit]:
        """
        Load and instantiate a unit.
        
        Args:
            unit_name: Name of the unit
            faction: Faction name (optional if in unit data)
            options: Dict with options like {"models": 30, "full_command": True}
        
        Returns:
            Configured Unit instance or None
        
        Example:
            >>> loader = UnitLoader()
            >>> unit = loader.load_unit("Empire Halberdiers", "empire", 
            ...                         options={"models": 30, "full_command": True})
        """
        options = options or {}
        
        # Load unit data
        unit_data = self.load_unit_data(unit_name, faction)
        
        if not unit_data:
            return None
        
        # Extract base profile
        profile = unit_data.get("profile", {})
        
        # Determine faction
        faction = faction or unit_data.get("faction", "")
        
        # Parse troop type
        troop_type_str = unit_data.get("troop_type", "infantry")
        troop_type = TroopType[troop_type_str.upper()]
        
        # Parse base size
        base_size_value = unit_data.get("base_size", 25)
        if isinstance(base_size_value, int):
            base_size = BaseSize(base_size_value)
        else:
            base_size = BaseSize.MEDIUM_25
        
        # Parse category
        category_str = unit_data.get("category", "core")
        category = UnitCategory[category_str.upper()]
        
        # Create equipment
        equipment_data = unit_data.get("equipment", {})
        melee_weapon_name = equipment_data.get("melee_weapon", "Hand Weapon")
        melee_weapon = Weapon(name=melee_weapon_name)
        
        # Apply weapon stats
        weapon_stats = unit_data.get("weapon_stats", {}).get(melee_weapon_name, {})
        if weapon_stats:
            melee_weapon.strength_bonus = weapon_stats.get("strength_bonus", 0)
            melee_weapon.ap = weapon_stats.get("ap", 0)
            melee_weapon.special_rules = weapon_stats.get("special_rules", [])
        
        armor = equipment_data.get("armor", [])
        equipment = Equipment(
            melee_weapon=melee_weapon,
            armor=armor
        )
        
        # Create command group
        command = Command()
        if options.get("full_command"):
            command.champion = True
            command.musician = True
            command.standard_bearer = True
        elif options.get("command"):
            cmd_opts = options["command"]
            command.champion = cmd_opts.get("champion", False)
            command.musician = cmd_opts.get("musician", False)
            command.standard_bearer = cmd_opts.get("standard", False)
        
        # Determine unit size
        models = options.get("models", unit_data.get("min_unit_size", 10))
        
        # Create unit
        unit = Unit(
            name=unit_name,
            faction=faction,
            category=category,
            troop_type=troop_type,
            base_size=base_size,
            movement=profile["M"],
            weapon_skill=profile["WS"],
            ballistic_skill=profile["BS"],
            strength=profile["S"],
            toughness=profile["T"],
            wounds=profile["W"],
            initiative=profile["I"],
            attacks=profile["A"],
            leadership=profile["Ld"],
            max_models=unit_data.get("max_unit_size", 100),
            current_models=models,
            min_unit_size=unit_data.get("min_unit_size", 10),
            equipment=equipment,
            command=command,
            special_rules=unit_data.get("special_rules", []),
            points_cost_per_model=unit_data.get("points_per_model", 0),
            points_cost_base=unit_data.get("points_base", 0),
            unit_strength=unit_data.get("unit_strength", 1)
        )
        
        return unit
    
    def load_character(self, character_name: str, faction: str = None,
                      options: Optional[Dict[str, Any]] = None) -> Optional[Character]:
        """
        Load and instantiate a character.
        
        Args:
            character_name: Name of the character
            faction: Faction name
            options: Dict with options like {"magic_level": 2, "mount": "horse"}
        
        Returns:
            Configured Character instance or None
        """
        options = options or {}
        
        # Load character data
        char_data = self.load_unit_data(character_name, faction)
        
        if not char_data:
            return None
        
        # Extract profile
        profile = char_data.get("profile", {})
        
        # Determine faction
        faction = faction or char_data.get("faction", "")
        
        # Parse category (LORD or HERO)
        category_str = char_data.get("category", "hero")
        category = UnitCategory[category_str.upper()]
        
        # Parse troop type
        troop_type_str = char_data.get("troop_type", "infantry")
        troop_type = TroopType[troop_type_str.upper()]
        
        # Parse base size
        base_size_value = char_data.get("base_size", 25)
        if isinstance(base_size_value, int):
            base_size = BaseSize(base_size_value)
        else:
            base_size = BaseSize.MEDIUM_25
        
        # Create equipment
        equipment_data = char_data.get("equipment", {})
        melee_weapon_name = equipment_data.get("melee_weapon", "Hand Weapon")
        melee_weapon = Weapon(name=melee_weapon_name)
        
        armor = equipment_data.get("armor", [])
        equipment = Equipment(
            melee_weapon=melee_weapon,
            armor=armor
        )
        
        # Create character
        character = Character(
            name=character_name,
            faction=faction,
            category=category,
            troop_type=troop_type,
            base_size=base_size,
            movement=profile["M"],
            weapon_skill=profile["WS"],
            ballistic_skill=profile["BS"],
            strength=profile["S"],
            toughness=profile["T"],
            wounds=profile["W"],
            initiative=profile["I"],
            attacks=profile["A"],
            leadership=profile["Ld"],
            max_models=1,
            current_models=1,
            equipment=equipment,
            special_rules=char_data.get("special_rules", []),
            points_cost_base=char_data.get("points_cost", 0),
            is_general=options.get("is_general", False),
            is_bsb=options.get("is_bsb", False),
            magic_level=options.get("magic_level", char_data.get("magic_level", 0)),
            lore_of_magic=options.get("lore", char_data.get("lore")),
            unit_strength=char_data.get("unit_strength", 1)
        )
        
        return character
    
    def load_faction_rules(self, faction: str) -> Optional[Dict]:
        """
        Load faction-specific rules and restrictions.
        
        Args:
            faction: Faction name
        
        Returns:
            Dict with faction rules
        """
        if faction in self._faction_cache:
            return self._faction_cache[faction]
        
        faction_file = Path("data/factions") / f"{faction}.json"
        
        if not faction_file.exists():
            return None
        
        with open(faction_file, 'r') as f:
            faction_data = json.load(f)
            self._faction_cache[faction] = faction_data
            return faction_data
    
    def get_available_units(self, faction: str, category: Optional[UnitCategory] = None) -> List[str]:
        """
        Get list of available units for a faction.
        
        Args:
            faction: Faction name
            category: Optional category filter (CORE, SPECIAL, RARE, etc.)
        
        Returns:
            List of unit names
        """
        faction_rules = self.load_faction_rules(faction)
        
        if not faction_rules:
            return []
        
        units = faction_rules.get("units", {})
        
        if category:
            return units.get(category.value, [])
        
        # Return all units
        all_units = []
        for cat_units in units.values():
            all_units.extend(cat_units)
        
        return all_units


# Global loader instance
_loader = None


def get_loader() -> UnitLoader:
    """Get global unit loader instance"""
    global _loader
    if _loader is None:
        _loader = UnitLoader()
    return _loader


def load_unit(unit_name: str, faction: str = None, options: Optional[Dict] = None) -> Optional[Unit]:
    """
    Convenience function to load a unit.
    
    Args:
        unit_name: Name of the unit
        faction: Faction name
        options: Dict with options
    
    Returns:
        Configured Unit instance
    
    Example:
        >>> unit = load_unit("Empire Halberdiers", "empire", 
        ...                  options={"models": 30, "full_command": True})
    """
    return get_loader().load_unit(unit_name, faction, options)


def load_character(character_name: str, faction: str = None, options: Optional[Dict] = None) -> Optional[Character]:
    """
    Convenience function to load a character.
    
    Args:
        character_name: Name of the character
        faction: Faction name
        options: Dict with options
    
    Returns:
        Configured Character instance
    """
    return get_loader().load_character(character_name, faction, options)

