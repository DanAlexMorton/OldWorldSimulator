#!/usr/bin/env python3
"""
Army Validator AI (Rule Shark 2.0)

Validates army lists against official TOW rules:
- Points limits (exactly 2000)
- Composition (Core ≥25%, Lords ≤25%, etc.)
- Unit limits (1 Steam Tank, 1 Giant, etc.)

Also provides AI optimization to legalize invalid lists.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of army validation."""
    valid: bool
    total_points: int
    target_points: int
    points_diff: int
    composition: Dict[str, float]
    composition_valid: bool
    limit_issues: List[str]
    suggestions: List[str] = field(default_factory=list)


@dataclass
class UnitEntry:
    """A unit in the army."""
    name: str
    count: int
    points_each: int
    category: str
    
    @property
    def total_points(self) -> int:
        return self.count * self.points_each


class ArmyValidatorAI:
    """
    Validates and optimizes army lists.
    
    Usage:
        validator = ArmyValidatorAI()
        result = validator.validate(army_dict)
        if not result.valid:
            optimized = validator.optimize(army_dict)
    """
    
    def __init__(self, points_file: str = "data/official_points.json"):
        """Load official points data."""
        path = Path(points_file)
        if not path.exists():
            # Try relative to project root
            root = Path(__file__).parent.parent.parent.parent
            path = root / points_file
        
        if not path.exists():
            raise FileNotFoundError(f"Points file not found: {points_file}")
        
        with open(path, 'r') as f:
            self.data = json.load(f)
        
        self.comp_rules = self.data.get("composition_rules", {})
        self.points_limits = self.data.get("points_limits", {"standard": 2000})
    
    def get_unit_points(self, faction: str, unit_name: str) -> Optional[Dict]:
        """Get unit info from official data."""
        faction_key = self._normalize_faction(faction)
        
        if faction_key not in self.data:
            return None
        
        faction_data = self.data[faction_key]
        unit_key = unit_name.lower().replace(" ", "_").replace("-", "_")
        
        # Check units
        if "units" in faction_data and unit_key in faction_data["units"]:
            return faction_data["units"][unit_key]
        
        # Check characters
        if "characters" in faction_data and unit_key in faction_data["characters"]:
            return faction_data["characters"][unit_key]
        
        return None
    
    def _normalize_faction(self, faction: str) -> str:
        """Normalize faction name to match JSON keys."""
        faction_lower = faction.lower()
        
        if "empire" in faction_lower:
            return "Empire"
        elif "orc" in faction_lower or "goblin" in faction_lower:
            return "Orcs_Goblins"
        
        return faction
    
    def validate(self, army: Dict, target_points: int = 2000, tolerance: int = 50) -> ValidationResult:
        """
        Validate an army list.
        
        Args:
            army: Army dict with 'faction' and 'units'
            target_points: Target points limit (default 2000)
            tolerance: Allowed points variance (default 50 = +/-2.5%)
        
        Returns:
            ValidationResult with all validation info
        """
        faction = army.get("faction", "Unknown")
        units = army.get("units", [])
        
        # Calculate total points and composition
        total_points = 0
        category_points = {"lords": 0, "heroes": 0, "core": 0, "special": 0, "rare": 0}
        limit_issues = []
        unit_counts = {}
        
        for unit in units:
            name = unit.get("name", "unknown")
            count = unit.get("models", 1)
            
            # Look up official points
            unit_info = self.get_unit_points(faction, name)
            
            if unit_info:
                points = unit_info["points"] * count
                category = unit_info.get("category", "core")
                
                total_points += points
                category_points[category] = category_points.get(category, 0) + points
                
                # Track counts for limits
                unit_key = name.lower().replace(" ", "_")
                unit_counts[unit_key] = unit_counts.get(unit_key, 0) + 1
                
                # Check army limits
                if "army_limit" in unit_info:
                    if unit_counts[unit_key] > unit_info["army_limit"]:
                        limit_issues.append(f"Max {unit_info['army_limit']} {name} allowed")
            else:
                # Estimate from unit data
                est_points = unit.get("points", count * 10)
                total_points += est_points
                category_points["core"] += est_points
        
        # Calculate composition percentages
        composition = {}
        for cat, pts in category_points.items():
            composition[cat] = (pts / total_points * 100) if total_points > 0 else 0
        
        # Check composition rules
        comp_valid = True
        suggestions = []
        
        # Core minimum
        if composition.get("core", 0) < 25:
            comp_valid = False
            suggestions.append(f"Core is {composition['core']:.1f}%, need >= 25%")
        
        # Lords maximum
        if composition.get("lords", 0) > 25:
            comp_valid = False
            suggestions.append(f"Lords is {composition['lords']:.1f}%, need <= 25%")
        
        # Special maximum
        if composition.get("special", 0) > 50:
            comp_valid = False
            suggestions.append(f"Special is {composition['special']:.1f}%, need <= 50%")
        
        # Rare maximum
        if composition.get("rare", 0) > 25:
            comp_valid = False
            suggestions.append(f"Rare is {composition['rare']:.1f}%, need <= 25%")
        
        # Points check (with tolerance)
        points_diff = total_points - target_points
        points_valid = abs(points_diff) <= tolerance and total_points <= target_points
        
        if points_diff > tolerance:
            suggestions.append(f"Over by {points_diff} pts - remove units")
        elif points_diff < -tolerance:
            suggestions.append(f"Under by {-points_diff} pts - add units")
        
        return ValidationResult(
            valid=points_valid and comp_valid and len(limit_issues) == 0,
            total_points=total_points,
            target_points=target_points,
            points_diff=points_diff,
            composition=composition,
            composition_valid=comp_valid,
            limit_issues=limit_issues,
            suggestions=suggestions
        )
    
    def optimize(self, army: Dict, target_points: int = 2000) -> Dict:
        """
        AI optimizer: Suggest changes to make army legal.
        
        Uses greedy algorithm to add/remove units to hit target.
        """
        result = self.validate(army, target_points)
        
        if result.valid:
            return {"army": army, "changes": [], "valid": True}
        
        faction = army.get("faction", "Unknown")
        faction_key = self._normalize_faction(faction)
        changes = []
        
        # Get available units
        if faction_key not in self.data:
            return {"army": army, "changes": ["Unknown faction"], "valid": False}
        
        faction_data = self.data[faction_key]
        
        # Points adjustment
        diff = result.points_diff
        
        if diff > 0:
            # Over points - suggest removing models
            for unit in army.get("units", []):
                unit_info = self.get_unit_points(faction, unit.get("name", ""))
                if unit_info:
                    pts_per_model = unit_info["points"]
                    models_to_remove = min(diff // pts_per_model, unit.get("models", 1) - unit_info.get("min", 1))
                    if models_to_remove > 0:
                        changes.append(f"Remove {models_to_remove} {unit['name']} (-{models_to_remove * pts_per_model} pts)")
                        diff -= models_to_remove * pts_per_model
                        if diff <= 0:
                            break
        
        elif diff < 0:
            # Under points - suggest adding models
            diff = -diff
            
            # Find cheap core units to add
            if "units" in faction_data:
                core_units = [(name, info) for name, info in faction_data["units"].items() 
                              if info.get("category") == "core"]
                core_units.sort(key=lambda x: x[1]["points"])
                
                for name, info in core_units:
                    pts = info["points"]
                    models_to_add = diff // pts
                    if models_to_add > 0:
                        changes.append(f"Add {models_to_add} {name.replace('_', ' ').title()} (+{models_to_add * pts} pts)")
                        diff -= models_to_add * pts
                        if diff <= 0:
                            break
        
        # Composition fixes
        if not result.composition_valid:
            if result.composition.get("core", 0) < 25:
                changes.append("Add more Core units to reach 25% minimum")
            if result.composition.get("lords", 0) > 25:
                changes.append("Remove Lords to get under 25% maximum")
        
        return {
            "army": army,
            "changes": changes,
            "original_points": result.total_points,
            "target_points": target_points,
            "valid": False
        }
    
    def create_legal_army(self, faction: str, target_points: int = 2000) -> Dict:
        """
        AI: Generate a legal army list from scratch.
        
        Creates a balanced, legal army for the faction.
        """
        faction_key = self._normalize_faction(faction)
        
        if faction_key not in self.data:
            return {"error": f"Unknown faction: {faction}"}
        
        faction_data = self.data[faction_key]
        army = {"faction": faction, "units": []}
        total = 0
        
        # Add required Core (minimum 25% = 500 pts for 2000)
        core_target = int(target_points * 0.30)  # Aim for 30% core
        
        if "units" in faction_data:
            core_units = [(name, info) for name, info in faction_data["units"].items() 
                          if info.get("category") == "core"]
            
            for name, info in core_units[:3]:  # Add up to 3 core units
                pts = info["points"]
                min_size = info.get("min", 10)
                count = min(min_size + 10, info.get("max", 30))
                unit_total = count * pts
                
                if total + unit_total <= target_points:
                    army["units"].append({
                        "name": name.replace("_", " ").title(),
                        "models": count,
                        "points": unit_total
                    })
                    total += unit_total
        
        # Add Special
        if "units" in faction_data:
            special_units = [(name, info) for name, info in faction_data["units"].items() 
                             if info.get("category") == "special"]
            
            for name, info in special_units[:2]:
                pts = info["points"]
                min_size = info.get("min", 5)
                count = min_size
                unit_total = count * pts
                
                if total + unit_total <= target_points:
                    army["units"].append({
                        "name": name.replace("_", " ").title(),
                        "models": count,
                        "points": unit_total
                    })
                    total += unit_total
        
        # Add a character
        if "characters" in faction_data:
            chars = list(faction_data["characters"].items())
            if chars:
                name, info = chars[0]
                pts = info["points"]
                if total + pts <= target_points:
                    army["units"].append({
                        "name": name.replace("_", " ").title(),
                        "models": 1,
                        "points": pts
                    })
                    total += pts
        
        army["total_points"] = total
        return army


def validate_army_file(filepath: str) -> None:
    """Validate an army JSON file."""
    validator = ArmyValidatorAI()
    
    with open(filepath, 'r') as f:
        army = json.load(f)
    
    result = validator.validate(army)
    
    print(f"\n{'='*60}")
    print(f"ARMY VALIDATION: {army.get('faction', 'Unknown')}")
    print(f"{'='*60}")
    print(f"Valid: {'YES' if result.valid else 'NO'}")
    print(f"Points: {result.total_points}/{result.target_points} ({result.points_diff:+d})")
    print(f"\nComposition:")
    for cat, pct in result.composition.items():
        print(f"  {cat.capitalize():10s}: {pct:5.1f}%")
    
    if result.limit_issues:
        print(f"\nLimit Issues:")
        for issue in result.limit_issues:
            print(f"  - {issue}")
    
    if result.suggestions:
        print(f"\nSuggestions:")
        for sug in result.suggestions:
            print(f"  - {sug}")
    
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        validate_army_file(sys.argv[1])
    else:
        # Demo
        validator = ArmyValidatorAI()
        
        # Generate legal Empire army
        print("\n=== GENERATING LEGAL EMPIRE ARMY ===")
        empire = validator.create_legal_army("Empire", 2000)
        print(json.dumps(empire, indent=2))
        
        # Validate it
        result = validator.validate(empire)
        print(f"\nValid: {result.valid}")
        print(f"Points: {result.total_points}")

