"""
Data loading and army management module.
"""

from .army_loader import (
    load_army_from_json,
    load_army_from_dict,
    get_available_armies,
    ArmyNotFoundError
)

from .unit_factory import (
    create_unit_state,
    UnitState
)

__all__ = [
    "load_army_from_json",
    "load_army_from_dict", 
    "get_available_armies",
    "ArmyNotFoundError",
    "create_unit_state",
    "UnitState"
]

