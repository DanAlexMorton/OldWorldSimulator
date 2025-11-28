"""
Army builder - Load armies from JSON files and create Unit objects
"""

import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from ..models.unit import Unit, create_unit, TroopType, BaseSize, UnitCategory, Formation, Equipment, Weapon
from ..models.character import Character


class ArmyBuilder:
    """Build armies from JSON army list files"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.unit_cache: Dict[str, Dict] = {}
    
    def load_army_from_file(self, army_file: str) -> List[Unit]:
        """
        Load army from JSON file.
        
        Args:
            army_file: Path to army JSON file
        
        Returns:
            List of Unit objects
        """
        with open(army_file, 'r') as f:
            army_data = json.load(f)
        
        return self.build_army_from_dict(army_data)
    
    def build_army_from_dict(self, army_data: Dict) -> List[Unit]:
        """
        Build army from dictionary.
        
        Args:
            army_data: Army composition dictionary
        
        Returns:
            List of Unit objects
        """
        units = []
        composition = army_data.get("army_composition", {})
        
        # Add heroes
        for hero_data in composition.get("heroes", []):
            hero = self._create_hero(hero_data, army_data["faction"])
            if hero:
                units.append(hero)
        
        # Add lords
        for lord_data in composition.get("lords", []):
            lord = self._create_lord(lord_data, army_data["faction"])
            if lord:
                units.append(lord)
        
        # Add core units
        for unit_data in composition.get("core", []):
            unit = self._create_unit_from_data(unit_data, army_data["faction"], UnitCategory.CORE)
            if unit:
                units.append(unit)
        
        # Add special units
        for unit_data in composition.get("special", []):
            unit = self._create_unit_from_data(unit_data, army_data["faction"], UnitCategory.SPECIAL)
            if unit:
                units.append(unit)
        
        # Add rare units
        for unit_data in composition.get("rare", []):
            unit = self._create_unit_from_data(unit_data, army_data["faction"], UnitCategory.RARE)
            if unit:
                units.append(unit)
        
        return units
    
    def _create_unit_from_data(self, unit_data: Dict, faction: str, category: UnitCategory) -> Optional[Unit]:
        """Create a unit from JSON data"""
        unit_type = unit_data.get("type")
        models = unit_data.get("models", 1)
        
        # Simplified profile (would normally load from unit database)
        profile = self._get_unit_profile(unit_type, faction)
        if not profile:
            # Create default profile
            profile = {
                "M": 4, "WS": 3, "BS": 3, "S": 3, "T": 3,
                "W": 1, "I": 3, "A": 1, "Ld": 7
            }
        
        # Determine troop type and base size
        troop_type, base_size = self._get_unit_type_and_base(unit_type)
        
        # Create unit
        unit = create_unit(
            name=unit_data.get("name", unit_type),
            profile=profile,
            faction=faction,
            category=category,
            troop_type=troop_type,
            base_size=base_size,
            max_models=models,
            current_models=models,
            armour_save=self._get_armour_save(unit_data),
            special_rules=self._get_special_rules(unit_type)
        )
        
        # Set formation if specified
        if "formation" in unit_data:
            form = unit_data["formation"]
            unit.formation = Formation(
                ranks=form.get("ranks", 1),
                files=form.get("files", models)
            )
        
        # Set command group
        if "command" in unit_data:
            cmd = unit_data["command"]
            unit.command.champion = cmd.get("champion", False)
            unit.command.musician = cmd.get("musician", False)
            unit.command.standard_bearer = cmd.get("standard_bearer", False)
        
        return unit
    
    def _create_hero(self, hero_data: Dict, faction: str) -> Optional[Character]:
        """Create a hero character"""
        hero_type = hero_data.get("type", "Captain")
        
        # Get profile (would load from database)
        profile = self._get_hero_profile(hero_type, faction)
        if not profile:
            profile = {
                "M": 4, "WS": 5, "BS": 4, "S": 4, "T": 4,
                "W": 2, "I": 5, "A": 3, "Ld": 8
            }
        
        hero = Character(
            name=hero_data.get("name", hero_type),
            movement=profile["M"],
            weapon_skill=profile["WS"],
            ballistic_skill=profile["BS"],
            strength=profile["S"],
            toughness=profile["T"],
            wounds=profile["W"],
            initiative=profile["I"],
            attacks=profile["A"],
            leadership=profile["Ld"],
            armour_save=4,
            faction=faction,
            category=UnitCategory.HERO,
            troop_type=TroopType.INFANTRY,
            base_size=BaseSize.MEDIUM_25,
            max_models=1,
            current_models=1,
            is_general=hero_data.get("is_general", False),
            is_bsb=hero_data.get("is_bsb", False),
            magic_level=hero_data.get("magic_level", 0),
            lore_of_magic=hero_data.get("lore")
        )
        
        return hero
    
    def _create_lord(self, lord_data: Dict, faction: str) -> Optional[Character]:
        """Create a lord character"""
        lord_type = lord_data.get("type", "General")
        
        # Get profile (would load from database)
        profile = self._get_lord_profile(lord_type, faction)
        if not profile:
            profile = {
                "M": 4, "WS": 6, "BS": 5, "S": 4, "T": 4,
                "W": 3, "I": 6, "A": 4, "Ld": 9
            }
        
        lord = Character(
            name=lord_data.get("name", lord_type),
            movement=profile["M"],
            weapon_skill=profile["WS"],
            ballistic_skill=profile["BS"],
            strength=profile["S"],
            toughness=profile["T"],
            wounds=profile["W"],
            initiative=profile["I"],
            attacks=profile["A"],
            leadership=profile["Ld"],
            armour_save=3,
            faction=faction,
            category=UnitCategory.LORD,
            troop_type=TroopType.INFANTRY,
            base_size=BaseSize.MEDIUM_25,
            max_models=1,
            current_models=1,
            is_general=lord_data.get("is_general", False),
            magic_level=lord_data.get("magic_level", 0),
            lore_of_magic=lord_data.get("lore")
        )
        
        return lord
    
    def _get_unit_profile(self, unit_type: str, faction: str) -> Optional[Dict]:
        """Get unit profile from database or cache"""
        # Simplified - would load from JSON files
        profiles = {
            "State Troops": {"M": 4, "WS": 3, "BS": 3, "S": 3, "T": 3, "W": 1, "I": 3, "A": 1, "Ld": 7},
            "Handgunners": {"M": 4, "WS": 3, "BS": 3, "S": 3, "T": 3, "W": 1, "I": 3, "A": 1, "Ld": 7},
            "Crossbowmen": {"M": 4, "WS": 3, "BS": 3, "S": 3, "T": 3, "W": 1, "I": 3, "A": 1, "Ld": 7},
            "Knights of the Empire": {"M": 4, "WS": 4, "BS": 3, "S": 3, "T": 3, "W": 1, "I": 3, "A": 1, "Ld": 8},
            "Greatswords": {"M": 4, "WS": 4, "BS": 3, "S": 3, "T": 3, "W": 1, "I": 3, "A": 1, "Ld": 8},
            "Orc Boyz": {"M": 4, "WS": 3, "BS": 3, "S": 3, "T": 4, "W": 1, "I": 2, "A": 1, "Ld": 7},
            "Orc Arrer Boyz": {"M": 4, "WS": 3, "BS": 3, "S": 3, "T": 4, "W": 1, "I": 2, "A": 1, "Ld": 7},
            "Goblin Archers": {"M": 4, "WS": 2, "BS": 3, "S": 3, "T": 3, "W": 1, "I": 3, "A": 1, "Ld": 5},
            "Black Orcs": {"M": 4, "WS": 4, "BS": 3, "S": 4, "T": 4, "W": 1, "I": 2, "A": 1, "Ld": 8},
            "Orc Boar Boyz": {"M": 4, "WS": 3, "BS": 3, "S": 3, "T": 4, "W": 1, "I": 2, "A": 1, "Ld": 7},
            "Trolls": {"M": 6, "WS": 3, "BS": 1, "S": 5, "T": 4, "W": 3, "I": 1, "A": 3, "Ld": 4},
        }
        return profiles.get(unit_type)
    
    def _get_hero_profile(self, hero_type: str, faction: str) -> Optional[Dict]:
        """Get hero profile"""
        profiles = {
            "Captain": {"M": 4, "WS": 5, "BS": 4, "S": 4, "T": 4, "W": 2, "I": 5, "A": 3, "Ld": 8},
            "Battle Wizard": {"M": 4, "WS": 3, "BS": 3, "S": 3, "T": 3, "W": 2, "I": 3, "A": 1, "Ld": 7},
            "Orc Big Boss": {"M": 4, "WS": 5, "BS": 3, "S": 4, "T": 4, "W": 2, "I": 3, "A": 3, "Ld": 8},
            "Orc Shaman": {"M": 4, "WS": 3, "BS": 3, "S": 3, "T": 4, "W": 2, "I": 2, "A": 1, "Ld": 7},
        }
        return profiles.get(hero_type)
    
    def _get_lord_profile(self, lord_type: str, faction: str) -> Optional[Dict]:
        """Get lord profile"""
        profiles = {
            "Orc Warboss": {"M": 4, "WS": 6, "BS": 3, "S": 5, "T": 5, "W": 3, "I": 3, "A": 4, "Ld": 9},
        }
        return profiles.get(lord_type)
    
    def _get_unit_type_and_base(self, unit_type: str) -> Tuple[TroopType, BaseSize]:
        """Determine troop type and base size"""
        if "Knight" in unit_type or "Boar" in unit_type:
            return TroopType.CAVALRY, BaseSize.CAVALRY_25x50
        elif "Cannon" in unit_type or "Lobber" in unit_type or "Catapult" in unit_type:
            return TroopType.WAR_MACHINE, BaseSize.LARGE_40
        elif "Troll" in unit_type:
            return TroopType.MONSTROUS_INFANTRY, BaseSize.LARGE_40
        else:
            return TroopType.INFANTRY, BaseSize.MEDIUM_25
    
    def _get_armour_save(self, unit_data: Dict) -> Optional[int]:
        """Calculate armour save from equipment"""
        equipment = unit_data.get("equipment", [])
        
        # Simplified armour calculation
        if "Heavy Armor" in str(equipment) and "Shield" in str(equipment):
            return 4
        elif "Heavy Armor" in str(equipment):
            return 5
        elif "Light Armor" in str(equipment) and "Shield" in str(equipment):
            return 5
        elif "Light Armor" in str(equipment):
            return 6
        elif "Shield" in str(equipment):
            return 6
        
        return None
    
    def _get_special_rules(self, unit_type: str) -> List[str]:
        """Get special rules for unit type"""
        rules_map = {
            "Handgunners": ["Move or Fire", "Armor Piercing (1)"],
            "Knights": ["Lance"],
            "Orc Boyz": ["Animosity"],
            "Goblin Archers": ["Animosity"],
            "Black Orcs": ["Immune to Psychology"],
            "Orc Boar Boyz": ["Animosity"],
            "Trolls": ["Regeneration (4+)", "Stupidity"],
        }
        return rules_map.get(unit_type, [])


def load_army_from_json(file_path: str) -> List[Unit]:
    """
    Convenience function to load army from JSON file.
    
    Args:
        file_path: Path to army JSON file
    
    Returns:
        List of Unit objects
    """
    builder = ArmyBuilder()
    return builder.load_army_from_file(file_path)

