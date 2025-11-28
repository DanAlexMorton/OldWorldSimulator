"""
Army loading utilities.

Loads army lists from JSON files in the armies/ directory.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional


class ArmyNotFoundError(Exception):
    """Raised when army file is not found."""
    pass


def get_armies_directory() -> Path:
    """Get path to armies directory."""
    # Look relative to project root
    root = Path(__file__).parent.parent.parent.parent
    armies_dir = root / "armies"
    
    if not armies_dir.exists():
        armies_dir.mkdir(parents=True)
    
    return armies_dir


def get_available_armies() -> List[str]:
    """List all available army JSON files."""
    armies_dir = get_armies_directory()
    return [f.stem for f in armies_dir.glob("*.json")]


def load_army_from_json(filepath: str) -> Dict:
    """
    Load army from JSON file.
    
    Args:
        filepath: Path to JSON file (can be relative or absolute)
    
    Returns:
        Army dict with 'name', 'faction', 'units' keys
    
    Raises:
        ArmyNotFoundError: If file not found
        ValueError: If JSON format is invalid
    """
    # Try absolute path first
    path = Path(filepath)
    
    # If not found, try relative to armies directory
    if not path.exists():
        armies_dir = get_armies_directory()
        path = armies_dir / filepath
        
        # Try with .json extension
        if not path.exists() and not filepath.endswith('.json'):
            path = armies_dir / f"{filepath}.json"
    
    if not path.exists():
        raise ArmyNotFoundError(f"Army file not found: {filepath}")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return normalize_army_data(data)


def load_army_from_dict(data: Dict) -> Dict:
    """
    Load army from dictionary.
    
    Args:
        data: Army data dict
    
    Returns:
        Normalized army dict
    """
    return normalize_army_data(data)


def normalize_army_data(data: Dict) -> Dict:
    """
    Normalize army data to standard format.
    
    Ensures consistent structure regardless of input format.
    """
    # Handle list format (just units)
    if isinstance(data, list):
        return {
            "name": "Custom Army",
            "faction": "Unknown",
            "units": data
        }
    
    # Handle dict format
    if isinstance(data, dict):
        result = {
            "name": data.get("name", "Custom Army"),
            "faction": data.get("faction", "Unknown"),
            "units": []
        }
        
        # Get units from various possible keys
        if "units" in data:
            result["units"] = data["units"]
        elif "army" in data:
            result["units"] = data["army"]
        else:
            # Assume the dict itself contains unit data
            result["units"] = [data]
        
        return result
    
    raise ValueError(f"Invalid army data format: {type(data)}")


def save_army_to_json(army: Dict, filepath: str) -> None:
    """
    Save army to JSON file.
    
    Args:
        army: Army dict to save
        filepath: Output path
    """
    path = Path(filepath)
    
    # Default to armies directory
    if not path.parent.exists():
        armies_dir = get_armies_directory()
        path = armies_dir / filepath
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(army, f, indent=2)

