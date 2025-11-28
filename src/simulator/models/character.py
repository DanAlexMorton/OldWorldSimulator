"""
Character models for Warhammer: The Old World
Heroes and Lords with special abilities
"""

from dataclasses import dataclass, field
from typing import Optional, List
from .unit import Unit, UnitCategory, TroopType, BaseSize, Equipment, Weapon


@dataclass
class Character(Unit):
    """
    Character (Hero or Lord) with special abilities.
    
    Characters can:
    - Join units
    - Issue and accept challenges
    - Benefit from Look Out Sir!
    - Use magic (if wizard)
    - Grant leadership bonuses
    """
    # Character-specific attributes
    is_general: bool = False
    is_bsb: bool = False  # Battle Standard Bearer
    magic_level: int = 0  # 0 = not a wizard
    lore_of_magic: Optional[str] = None
    
    # Mounted options
    mount: Optional[Unit] = None  # Horse, griffin, etc.
    is_mounted: bool = False
    
    # Current status
    joined_unit: Optional[Unit] = None
    in_challenge: bool = False
    challenge_opponent: Optional['Character'] = None
    
    # Leadership range
    inspiring_presence_range: int = 12  # Inches
    hold_your_ground_range: int = 6  # BSB range
    
    def __post_init__(self):
        """Initialize character-specific values"""
        super().__post_init__()
        
        # Characters are always unit size 1
        self.current_models = 1
        self.max_models = 1
        self.min_unit_size = 1
        
        # Update category if general
        if self.is_general:
            self.special_rules.append("General")
        
        # BSB gets reroll break tests
        if self.is_bsb:
            self.special_rules.append("Battle Standard Bearer")
    
    def join_unit(self, unit: Unit) -> bool:
        """
        Join a unit.
        
        Args:
            unit: Unit to join
        
        Returns:
            True if successfully joined
        """
        # Check if can join (same faction, not fleeing, etc.)
        if unit.faction != self.faction:
            return False
        
        if unit.is_fleeing or self.is_fleeing:
            return False
        
        # Leave current unit if any
        if self.joined_unit:
            self.leave_unit()
        
        self.joined_unit = unit
        return True
    
    def leave_unit(self) -> bool:
        """
        Leave current unit.
        
        Returns:
            True if successfully left
        """
        if not self.joined_unit:
            return False
        
        self.joined_unit = None
        return True
    
    def can_issue_challenge(self) -> bool:
        """
        Check if character can issue a challenge.
        
        Returns:
            True if can challenge
        """
        if not self.is_alive:
            return False
        
        if self.in_challenge:
            return False
        
        # Must be in combat
        # (Checked by game logic)
        
        return True
    
    def issue_challenge(self, opponent: 'Character') -> bool:
        """
        Issue a challenge to enemy character.
        
        Args:
            opponent: Enemy character to challenge
        
        Returns:
            True if challenge issued successfully
        """
        if not self.can_issue_challenge():
            return False
        
        if not opponent.can_accept_challenge():
            return False
        
        self.in_challenge = True
        self.challenge_opponent = opponent
        opponent.in_challenge = True
        opponent.challenge_opponent = self
        
        return True
    
    def can_accept_challenge(self) -> bool:
        """
        Check if character can accept a challenge.
        
        Returns:
            True if can accept
        """
        return self.can_issue_challenge()
    
    def refuse_challenge(self) -> bool:
        """
        Refuse a challenge (character cannot fight this round).
        
        Returns:
            True if refused successfully
        """
        if not self.joined_unit:
            return False
        
        # Character cannot fight this round
        # (Handled by combat logic)
        
        return True
    
    def end_challenge(self):
        """End the current challenge"""
        if self.challenge_opponent:
            self.challenge_opponent.in_challenge = False
            self.challenge_opponent.challenge_opponent = None
        
        self.in_challenge = False
        self.challenge_opponent = None
    
    def can_look_out_sir(self) -> bool:
        """
        Check if character can benefit from Look Out Sir!
        
        Returns:
            True if can use LOS
        """
        if not self.joined_unit:
            return False
        
        if not self.is_alive:
            return False
        
        # Must have 5+ models in unit
        if self.joined_unit.current_models < 5:
            return False
        
        # Cannot use if in challenge
        if self.in_challenge:
            return False
        
        return True
    
    def look_out_sir_save(self) -> int:
        """
        Get Look Out Sir! save value.
        
        Returns:
            Required roll for LOS (typically 2+ for characters)
        """
        # Lords: 2+
        # Heroes: 4+
        if self.category == UnitCategory.LORD:
            return 2
        else:
            return 4
    
    def grant_leadership(self, unit: Unit) -> Optional[int]:
        """
        Grant leadership bonus to unit.
        
        Args:
            unit: Unit to grant leadership to
        
        Returns:
            Leadership value to use, or None if not applicable
        """
        if not self.is_general:
            return None
        
        if unit.faction != self.faction:
            return None
        
        # Check range (if positions were tracked)
        # For now, assume in range
        
        return self.leadership
    
    def bsb_reroll_available(self, unit: Unit) -> bool:
        """
        Check if BSB reroll is available for unit.
        
        Args:
            unit: Unit checking for reroll
        
        Returns:
            True if BSB reroll can be used
        """
        if not self.is_bsb:
            return False
        
        if unit.faction != self.faction:
            return False
        
        if not self.is_alive:
            return False
        
        # Check range (within 6")
        # For now, assume in range
        
        return True
    
    def cast_spell(self, spell_name: str, casting_value: int, power_dice: int) -> dict:
        """
        Attempt to cast a spell.
        
        Args:
            spell_name: Name of spell to cast
            casting_value: Required casting value
            power_dice: Number of power dice to use
        
        Returns:
            Dict with result
        """
        if self.magic_level == 0:
            return {"success": False, "reason": "Not a wizard"}
        
        if power_dice > 6:
            return {"success": False, "reason": "Maximum 6 dice per spell"}
        
        # Dice rolling would happen here
        # This is a placeholder for the magic phase implementation
        
        return {
            "success": False,
            "reason": "Magic phase not yet implemented"
        }
    
    def get_combined_profile(self) -> dict:
        """
        Get combined profile if mounted.
        
        Returns:
            Dict with combined M, T, W, etc.
        """
        if not self.mount:
            return {
                "M": self.movement,
                "WS": self.weapon_skill,
                "BS": self.ballistic_skill,
                "S": self.strength,
                "T": self.toughness,
                "W": self.wounds,
                "I": self.initiative,
                "A": self.attacks,
                "Ld": self.leadership
            }
        
        # Combined profile rules:
        # M = mount's M
        # T = mount's T
        # W = rider + mount
        # Others = rider's values
        
        return {
            "M": self.mount.movement,
            "WS": self.weapon_skill,
            "BS": self.ballistic_skill,
            "S": self.strength,
            "T": self.mount.toughness,
            "W": self.wounds + self.mount.wounds,
            "I": self.initiative,
            "A": self.attacks + self.mount.attacks,
            "Ld": self.leadership
        }
    
    def allocate_wounds(self, wounds: int, source_ap: int = 0) -> dict:
        """
        Allocate wounds to character (with Look Out Sir! if applicable).
        
        Args:
            wounds: Number of wounds to allocate
            source_ap: AP value of attacking weapon
        
        Returns:
            Dict with wound allocation results
        """
        if wounds <= 0:
            return {"wounds_taken": 0, "look_out_sir_used": False}
        
        look_out_sir_saves = 0
        
        # Check if Look Out Sir! applies
        if self.can_look_out_sir():
            from src.simulator.core.dice import d6
            
            los_target = self.look_out_sir_save()
            
            for _ in range(wounds):
                roll = d6(1)[0]
                if roll >= los_target:
                    look_out_sir_saves += 1
                    # Wound transferred to unit
        
        # Remaining wounds hit character
        wounds_to_character = wounds - look_out_sir_saves
        
        # Character makes saves
        actual_wounds = wounds_to_character
        
        if self.armour_save:
            from src.simulator.core.calculations import armour_save, calculate_saves
            save_value = armour_save(self.armour_save, source_ap)
            if save_value:
                save_result = calculate_saves(wounds_to_character, save_value)
                actual_wounds = save_result['failed_saves']
        
        # Apply wounds
        self.wounds = max(0, self.wounds - actual_wounds)
        if self.wounds == 0:
            self.current_models = 0
        
        return {
            "wounds_taken": actual_wounds,
            "look_out_sir_used": look_out_sir_saves > 0,
            "look_out_sir_saves": look_out_sir_saves
        }


def create_character(name: str, profile: dict, category: UnitCategory, **kwargs) -> Character:
    """
    Create a character from profile dict.
    
    Args:
        name: Character name
        profile: Dict with M, WS, BS, S, T, W, I, A, Ld
        category: LORD or HERO
        **kwargs: Additional character attributes
    
    Returns:
        Configured Character instance
    """
    return Character(
        name=name,
        category=category,
        movement=profile["M"],
        weapon_skill=profile["WS"],
        ballistic_skill=profile["BS"],
        strength=profile["S"],
        toughness=profile["T"],
        wounds=profile["W"],
        initiative=profile["I"],
        attacks=profile["A"],
        leadership=profile["Ld"],
        faction=kwargs.get("faction", ""),
        troop_type=kwargs.get("troop_type", TroopType.INFANTRY),
        base_size=kwargs.get("base_size", BaseSize.MEDIUM_25),
        max_models=1,
        current_models=1,
        **{k: v for k, v in kwargs.items() if k not in ["faction", "troop_type", "base_size"]}
    )

