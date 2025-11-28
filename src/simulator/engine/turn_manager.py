"""
Turn manager for Warhammer: The Old World
Complete turn sequence with all phases
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Callable
from enum import Enum
import random

from .game_state import GameState, UnitState, Position
from ..models.unit import Unit
from ..models.character import Character
from ..combat.resolver import (
    CombatGroup, resolve_shooting, resolve_melee_combat,
    run_full_combat_round, CombatResult
)
from ..core.dice import d6, roll_2d6, d6_sum


class TurnPhase(Enum):
    """Turn phases in order"""
    START = "start"
    COMPULSORY_MOVES = "compulsory"
    MOVEMENT = "movement"
    MAGIC = "magic"
    SHOOTING = "shooting"
    CHARGE = "charge"
    COMBAT = "combat"
    END = "end"


@dataclass
class MovementResult:
    """Result of a movement action"""
    unit: UnitState
    start_position: Position
    end_position: Position
    distance_moved: float
    is_march: bool = False
    is_charge: bool = False
    success: bool = True
    message: str = ""


@dataclass
class ChargeResult:
    """Result of a charge action"""
    charger: UnitState
    target: UnitState
    charge_distance: float
    charge_roll: int
    required_distance: float
    success: bool
    reaction: str = "hold"  # hold, flee, stand_and_shoot
    message: str = ""


@dataclass
class MagicResult:
    """Result of magic phase"""
    caster: UnitState
    spell_name: str
    casting_roll: int
    casting_value: int
    success: bool
    irresistible: bool = False
    miscast: bool = False
    dispelled: bool = False
    effect: Optional[CombatResult] = None


class TurnManager:
    """
    Manages complete turn sequence for TOW.
    
    Turn Order:
    1. Start Phase (reserves, board effects)
    2. Compulsory Moves (random movement, fleeing)
    3. Movement Phase
    4. Magic Phase
    5. Shooting Phase
    6. Charge Phase
    7. Combat Phase
    8. End Phase (rally, panic checks)
    """
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.current_phase = TurnPhase.START
        self.phase_log: List[str] = []
    
    def execute_full_turn(self, player: str) -> Dict:
        """
        Execute a complete turn for player.
        
        Args:
            player: "player_a" or "player_b"
        
        Returns:
            Dict with turn summary
        """
        self.game_state.active_player = player
        self.phase_log = []
        
        # CRITICAL: Reset turn state for active player's units
        for unit in self.game_state.get_all_units(player):
            unit.reset_turn_state()
        
        results = {
            "player": player,
            "turn": self.game_state.current_turn,
            "phases": {}
        }
        
        # Execute each phase
        results["phases"]["start"] = self.phase_start()
        results["phases"]["compulsory"] = self.phase_compulsory_moves()
        results["phases"]["movement"] = self.phase_movement()
        results["phases"]["magic"] = self.phase_magic()
        results["phases"]["shooting"] = self.phase_shooting()
        results["phases"]["charge"] = self.phase_charge()
        results["phases"]["combat"] = self.phase_combat()
        results["phases"]["end"] = self.phase_end()
        
        results["log"] = self.phase_log
        
        return results
    
    # ========================================================================
    # PHASE 1: START PHASE
    # ========================================================================
    
    def phase_start(self) -> Dict:
        """
        Start of turn phase.
        
        - Check reserves
        - Apply start-of-turn effects
        """
        self.current_phase = TurnPhase.START
        self.log(f"=== START OF TURN {self.game_state.current_turn} - {self.game_state.active_player.upper()} ===")
        
        return {"reserves": 0, "effects": []}
    
    # ========================================================================
    # PHASE 2: COMPULSORY MOVES
    # ========================================================================
    
    def phase_compulsory_moves(self) -> Dict:
        """
        Compulsory moves phase.
        
        - Fleeing units move 2D6"
        - Random movement units (fanatics, etc.)
        - Frenzied units must charge if able
        """
        self.current_phase = TurnPhase.COMPULSORY_MOVES
        
        results = {
            "fleeing_moves": [],
            "frenzied_charges": []
        }
        
        # Move fleeing units
        for unit in self.game_state.get_all_units(self.game_state.active_player):
            if unit.is_fleeing:
                flee_distance = roll_2d6()
                # Move away from enemy
                angle = unit.position.facing + 180  # Opposite direction
                new_pos = unit.position.move(flee_distance, angle)
                
                # Check if fled off board
                if not self.game_state.battlefield.is_valid_position(new_pos.x, new_pos.y):
                    self.log(f"{unit.unit.name} flees off the board - DESTROYED!")
                    unit.unit.current_models = 0
                    results["fleeing_moves"].append({
                        "unit": unit.unit.name,
                        "fled_off_board": True
                    })
                else:
                    unit.position = new_pos
                    self.log(f"{unit.unit.name} flees {flee_distance}\"")
                    results["fleeing_moves"].append({
                        "unit": unit.unit.name,
                        "distance": flee_distance
                    })
        
        # Frenzied units must charge (simplified - Phase 4.5 feature)
        
        return results
    
    # ========================================================================
    # PHASE 3: MOVEMENT PHASE
    # ========================================================================
    
    def phase_movement(self) -> Dict:
        """
        Movement phase.
        
        Units can:
        - Move up to M"
        - March (2x M") if >8" from enemy
        - Reform (half move)
        - Wheel/pivot (90° free)
        """
        self.current_phase = TurnPhase.MOVEMENT
        self.log("--- MOVEMENT PHASE ---")
        
        results = {
            "moves": []
        }
        
        # All units can potentially move (AI or player chooses)
        # For now, simple AI: move toward nearest enemy
        for unit in self.game_state.get_all_units(self.game_state.active_player):
            if unit.can_move():
                # Simple AI: move toward closest enemy
                enemies = self.game_state.get_enemy_units(self.game_state.active_player)
                if enemies:
                    closest = min(enemies, key=lambda e: unit.distance_to(e))
                    move_result = self.move_unit_toward(unit, closest.position, march=False)
                    results["moves"].append(move_result)
        
        return results
    
    def move_unit_toward(
        self, 
        unit: UnitState, 
        target: Position,
        march: bool = False
    ) -> Dict:
        """
        Move unit toward target position.
        
        Args:
            unit: Unit to move
            target: Target position
            march: Whether to march (2x movement)
        
        Returns:
            Movement result dict
        """
        start_pos = Position(unit.position.x, unit.position.y, unit.position.facing)
        
        # Calculate movement distance
        base_move = unit.unit.movement
        max_distance = base_move * 2 if march else base_move
        
        # Can only march if >8" from enemy
        if march:
            enemies = self.game_state.get_enemy_units(unit.owner)
            for enemy in enemies:
                if unit.distance_to(enemy) <= 8.0:
                    march = False
                    max_distance = base_move
                    break
        
        # Calculate angle to target
        angle = unit.position.angle_to(target)
        
        # Update facing
        unit.position.facing = angle
        
        # Move toward target
        distance_to_target = unit.position.distance_to(target)
        move_distance = min(max_distance, distance_to_target - 1.0)  # Stop 1" away
        
        if move_distance > 0:
            unit.position = unit.position.move(move_distance, angle)
            unit.has_moved = True
            unit.has_marched = march
            
            self.log(f"{unit.unit.name} {'marches' if march else 'moves'} {move_distance:.1f}\"")
        
        return {
            "unit": unit.unit.name,
            "distance": move_distance,
            "marched": march,
            "start": start_pos.to_dict(),
            "end": unit.position.to_dict()
        }
    
    # ========================================================================
    # PHASE 4: MAGIC PHASE
    # ========================================================================
    
    def phase_magic(self) -> Dict:
        """
        Magic phase.
        
        - Roll 2D6 for Winds of Magic
        - Casters attempt to cast spells
        - Opponent attempts to dispel
        """
        self.current_phase = TurnPhase.MAGIC
        self.log("--- MAGIC PHASE ---")
        
        # Roll Winds of Magic
        winds = roll_2d6()
        power_dice = winds
        dispel_dice = winds // 2  # Opponent gets half
        
        self.log(f"Winds of Magic: {winds} (Power: {power_dice}, Dispel: {dispel_dice})")
        
        results = {
            "winds": winds,
            "power_dice": power_dice,
            "dispel_dice": dispel_dice,
            "spells_cast": []
        }
        
        # Find wizards
        wizards = [u for u in self.game_state.get_all_units(self.game_state.active_player)
                  if isinstance(u.unit, Character) and u.unit.magic_level > 0]
        
        if not wizards:
            self.log("No wizards available")
            return results
        
        # Each wizard can attempt to cast (simplified)
        for wizard_state in wizards:
            wizard = wizard_state.unit
            if power_dice > 0:
                spell_result = self.cast_spell(
                    wizard_state, 
                    "Fireball",  # Default spell
                    power_dice
                )
                results["spells_cast"].append(spell_result)
                power_dice -= 2  # Spent dice
        
        return results
    
    def cast_spell(
        self,
        caster_state: UnitState,
        spell_name: str,
        power_dice_available: int
    ) -> Dict:
        """
        Attempt to cast a spell.
        
        Args:
            caster_state: Wizard casting
            spell_name: Name of spell
            power_dice_available: Power dice available
        
        Returns:
            Dict with cast result
        """
        caster = caster_state.unit
        
        # Simplified spell list
        spells = {
            "Fireball": {"casting_value": 7, "type": "damage"},
            "Mystic Shield": {"casting_value": 5, "type": "buff"},
            "Curse": {"casting_value": 6, "type": "debuff"}
        }
        
        spell = spells.get(spell_name, spells["Fireball"])
        casting_value = spell["casting_value"]
        
        # Use 2 dice (simplified)
        dice_to_roll = min(2, power_dice_available)
        casting_roll = d6_sum(dice_to_roll)
        
        # Check for doubles (irresistible force / miscast)
        rolls = d6(dice_to_roll)
        is_double = len(set(rolls)) == 1 if len(rolls) == 2 else False
        
        success = casting_roll >= casting_value
        irresistible = is_double and success
        miscast = is_double and casting_roll <= 3
        
        if success:
            self.log(f"{caster.name} casts {spell_name} ({casting_roll} vs {casting_value})")
            
            # Apply spell effect
            if spell["type"] == "damage":
                # Find target
                enemies = self.game_state.get_enemy_units(caster_state.owner)
                if enemies:
                    target = enemies[0]  # Target closest
                    damage = d6_sum(1)  # D6 S4 hits (simplified)
                    self.log(f"  Fireball hits {target.unit.name} for {damage} wounds")
                    target.unit.take_casualties(damage)
        else:
            self.log(f"{caster.name} fails to cast {spell_name} ({casting_roll} vs {casting_value})")
        
        return {
            "caster": caster.name,
            "spell": spell_name,
            "roll": casting_roll,
            "target": casting_value,
            "success": success,
            "irresistible": irresistible,
            "miscast": miscast
        }
    
    # ========================================================================
    # PHASE 5: SHOOTING PHASE
    # ========================================================================
    
    def phase_shooting(self) -> Dict:
        """
        Shooting phase.
        
        Units shoot at visible enemies in range.
        """
        self.current_phase = TurnPhase.SHOOTING
        self.log("--- SHOOTING PHASE ---")
        
        results = {
            "shots": []
        }
        
        # Find units that can shoot
        for unit in self.game_state.get_all_units(self.game_state.active_player):
            if unit.can_shoot() and unit.unit.ballistic_skill > 0:
                # Find target
                enemies = self.game_state.get_enemy_units(unit.owner)
                valid_targets = [
                    e for e in enemies 
                    if unit.distance_to(e) <= 24.0  # Simplified range
                    and self.game_state.battlefield.has_line_of_sight(
                        unit.position, e.position
                    )
                ]
                
                if valid_targets:
                    target = min(valid_targets, key=lambda e: unit.distance_to(e))
                    shoot_result = self.shoot_at_target(unit, target)
                    results["shots"].append(shoot_result)
        
        return results
    
    def shoot_at_target(self, shooter: UnitState, target: UnitState) -> Dict:
        """
        Resolve shooting attack.
        
        Args:
            shooter: Shooting unit
            target: Target unit
        
        Returns:
            Shooting result dict
        """
        distance = shooter.distance_to(target)
        
        # Determine modifiers
        options = {
            "long_range": distance > 12.0,
            "cover": False  # Check terrain
        }
        
        # Check for cover
        terrain = self.game_state.battlefield.get_terrain_at(
            target.position.x, target.position.y
        )
        if any(t.provides_cover for t in terrain):
            options["cover"] = True
        
        # Resolve shooting using Phase 3 resolver
        result = resolve_shooting(shooter.unit, target.unit, options)
        
        self.log(f"{shooter.unit.name} shoots at {target.unit.name}: "
                f"{result.hits} hits, {result.casualties} casualties")
        
        return {
            "shooter": shooter.unit.name,
            "target": target.unit.name,
            "distance": distance,
            "hits": result.hits,
            "casualties": result.casualties,
            "panic": result.panic_test_required
        }
    
    # ========================================================================
    # PHASE 6: CHARGE PHASE
    # ========================================================================
    
    def phase_charge(self) -> Dict:
        """
        Charge phase.
        
        Units declare and resolve charges.
        """
        self.current_phase = TurnPhase.CHARGE
        self.log("--- CHARGE PHASE ---")
        
        results = {
            "charges": []
        }
        
        # Find units that can charge
        for unit in self.game_state.get_all_units(self.game_state.active_player):
            if unit.can_charge():
                # Find chargeable targets
                enemies = self.game_state.get_enemy_units(unit.owner)
                valid_targets = [
                    e for e in enemies
                    if unit.is_in_charge_arc(e)
                    and unit.distance_to(e) <= unit.unit.movement + 12  # Max charge range
                ]
                
                if valid_targets:
                    target = min(valid_targets, key=lambda e: unit.distance_to(e))
                    charge_result = self.declare_charge(unit, target)
                    results["charges"].append(charge_result)
                    
                    # Only one charge per unit
                    break
        
        return results
    
    def declare_charge(self, charger: UnitState, target: UnitState) -> Dict:
        """
        Declare and resolve a charge.
        
        Args:
            charger: Charging unit
            target: Target unit
        
        Returns:
            Charge result dict
        """
        distance = charger.distance_to(target)
        
        # Target can react
        reaction = self.charge_reaction(target, charger, distance)
        
        if reaction == "flee":
            # Target flees 2D6"
            flee_distance = roll_2d6()
            target.is_fleeing = True
            angle = target.position.facing + 180
            target.position = target.position.move(flee_distance, angle)
            
            self.log(f"{target.unit.name} flees {flee_distance}\" from charge!")
            
            # Charger pursues
            charge_roll = roll_2d6()
            total_charge = charger.unit.movement + charge_roll
            
            if total_charge >= distance + flee_distance:
                self.log(f"{charger.unit.name} catches fleeing {target.unit.name}!")
                target.unit.current_models = 0
                return {
                    "charger": charger.unit.name,
                    "target": target.unit.name,
                    "reaction": "flee",
                    "caught": True
                }
            else:
                self.log(f"{charger.unit.name} fails to catch {target.unit.name}")
                return {
                    "charger": charger.unit.name,
                    "target": target.unit.name,
                    "reaction": "flee",
                    "caught": False
                }
        
        # Roll charge distance: 2D6 + Movement
        charge_roll = roll_2d6()
        total_charge = charger.unit.movement + charge_roll
        
        if total_charge >= distance:
            # Charge succeeds
            charger.has_charged = True
            charger.in_combat = True
            target.in_combat = True
            charger.engaged_with.append(target)
            target.engaged_with.append(charger)
            
            # Move charger into contact
            angle = charger.position.angle_to(target.position)
            charger.position = charger.position.move(distance - 1.0, angle)
            
            self.log(f"{charger.unit.name} charges {target.unit.name}! "
                    f"({charge_roll}+{charger.unit.movement} = {total_charge}\" vs {distance:.1f}\")")
            
            return {
                "charger": charger.unit.name,
                "target": target.unit.name,
                "distance": distance,
                "roll": charge_roll,
                "total": total_charge,
                "success": True,
                "reaction": reaction
            }
        else:
            # Charge fails
            self.log(f"{charger.unit.name} fails charge on {target.unit.name} "
                    f"({total_charge}\" vs {distance:.1f}\")")
            
            return {
                "charger": charger.unit.name,
                "target": target.unit.name,
                "distance": distance,
                "roll": charge_roll,
                "total": total_charge,
                "success": False
            }
    
    def charge_reaction(self, target: UnitState, charger: UnitState, distance: float) -> str:
        """
        Determine charge reaction.
        
        Args:
            target: Unit being charged
            charger: Charging unit
            distance: Distance of charge
        
        Returns:
            Reaction: "hold", "flee", or "stand_and_shoot"
        """
        # Simple AI: flee if outmatched
        if target.unit.current_models < charger.unit.current_models // 2:
            if target.unit.leadership < 7:
                return "flee"
        
        # Stand and shoot if have ranged weapons and distance > 6"
        if target.unit.ballistic_skill > 0 and distance > 6.0:
            return "stand_and_shoot"
        
        return "hold"
    
    # ========================================================================
    # PHASE 7: COMBAT PHASE
    # ========================================================================
    
    def phase_combat(self) -> Dict:
        """
        Combat phase.
        
        Resolve all combats.
        """
        self.current_phase = TurnPhase.COMBAT
        self.log("--- COMBAT PHASE ---")
        
        results = {
            "combats": []
        }
        
        # Find all units in combat
        units_in_combat = [
            u for u in self.game_state.get_all_units()
            if u.in_combat and len(u.engaged_with) > 0
        ]
        
        # Group into combat pairs (simplified)
        resolved = []  # Use list instead of set since UnitState isn't hashable
        for unit in units_in_combat:
            if unit in resolved:
                continue
            
            if unit.engaged_with:
                enemy = unit.engaged_with[0]
                
                # Create combat groups
                side_a = CombatGroup(
                    front_units=[unit.unit],
                    is_charging=unit.has_charged
                )
                side_b = CombatGroup(
                    front_units=[enemy.unit],
                    is_charging=enemy.has_charged
                )
                
                # Resolve combat using Phase 3 resolver
                result_a, result_b = run_full_combat_round(
                    side_a, side_b,
                    round_number=1
                )
                
                self.log(f"COMBAT: {unit.unit.name} vs {enemy.unit.name}")
                self.log(f"  {unit.unit.name}: {result_a.casualties} casualties inflicted, "
                        f"CR {result_a.attacker_cr}")
                self.log(f"  {enemy.unit.name}: {result_b.casualties} casualties inflicted, "
                        f"CR {result_b.attacker_cr}")
                
                # Check for breaks
                if result_b.defender_fled:
                    self.log(f"  {enemy.unit.name} BREAKS AND FLEES!")
                    enemy.is_fleeing = True
                    enemy.in_combat = False
                    unit.in_combat = False
                
                if result_a.defender_fled:
                    self.log(f"  {unit.unit.name} BREAKS AND FLEES!")
                    unit.is_fleeing = True
                    unit.in_combat = False
                    enemy.in_combat = False
                
                results["combats"].append({
                    "unit_a": unit.unit.name,
                    "unit_b": enemy.unit.name,
                    "casualties_a": result_a.casualties,
                    "casualties_b": result_b.casualties,
                    "cr_a": result_a.attacker_cr,
                    "cr_b": result_b.attacker_cr,
                    "winner": unit.unit.name if result_a.combat_result_difference > 0 else enemy.unit.name
                })
                
                resolved.append(unit)
                resolved.append(enemy)
        
        return results
    
    # ========================================================================
    # PHASE 8: END PHASE
    # ========================================================================
    
    def phase_end(self) -> Dict:
        """
        End of turn phase.
        
        - Rally fleeing units
        - Panic checks
        - Remove destroyed units
        """
        self.current_phase = TurnPhase.END
        self.log("--- END PHASE ---")
        
        results = {
            "rallied": [],
            "panic_checks": [],
            "destroyed": []
        }
        
        # Rally fleeing units
        for unit in self.game_state.get_all_units(self.game_state.active_player):
            if unit.is_fleeing:
                rally_roll = roll_2d6()
                if rally_roll <= unit.unit.leadership:
                    unit.is_fleeing = False
                    unit.is_rallying = True
                    self.log(f"{unit.unit.name} rallies!")
                    results["rallied"].append(unit.unit.name)
                else:
                    self.log(f"{unit.unit.name} continues to flee")
        
        # Remove destroyed units
        self.game_state.remove_destroyed_units()
        
        # Check victory
        self.game_state.check_victory()
        
        return results
    
    def log(self, message: str) -> None:
        """Add message to phase log"""
        self.phase_log.append(message)
        # Could also print if verbose mode

