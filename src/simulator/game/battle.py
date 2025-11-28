"""
Battle management.

Main battle class that orchestrates a full game.
"""

from typing import Dict, List, Optional, Callable

from ..data.unit_factory import UnitState, create_army_units
from .actions import execute_action, smart_action
from .combat import resolve_combat, resolve_shooting_phase


class Battle:
    """
    Manages a single battle between two armies.
    
    Usage:
        battle = Battle(army_a, army_b)
        battle.set_ai("player_a", my_ai_function)
        battle.set_ai("player_b", my_ai_function)
        winner = battle.run()
    """
    
    def __init__(
        self,
        army_a: Dict,
        army_b: Dict,
        max_turns: int = 6,
        verbose: bool = False
    ):
        """
        Initialize battle.
        
        Args:
            army_a: Player A's army dict
            army_b: Player B's army dict
            max_turns: Maximum turns before draw
            verbose: Print detailed output
        """
        self.max_turns = max_turns
        self.verbose = verbose
        self.current_turn = 0
        self.game_over = False
        self.winner: Optional[str] = None
        
        # Store army info
        self.faction_a = army_a.get("faction", "Player A")
        self.faction_b = army_b.get("faction", "Player B")
        
        # Create units
        self.units_a = create_army_units(
            army_a, start_y=8, facing=90
        )
        self.units_b = create_army_units(
            army_b, start_y=40, facing=270
        )
        
        # AI functions (player -> decision function)
        self._ai: Dict[str, Callable] = {}
    
    def set_ai(self, player: str, ai_func: Callable) -> None:
        """
        Set AI function for a player.
        
        AI function signature:
            def ai(unit: UnitState, enemies: List[UnitState]) -> str
        
        Returns action: "hold", "advance", "march", "charge", 
                       "flank_left", "flank_right", "refuse"
        """
        self._ai[player] = ai_func
    
    def _get_decision(
        self,
        player: str,
        unit: UnitState,
        enemies: List[UnitState]
    ) -> str:
        """Get AI decision for a unit."""
        if not enemies:
            return "hold"
        
        closest = min(enemies, key=lambda e: unit.distance_to(e))
        
        # Artillery ALWAYS shoots - override any AI decision
        name_lower = unit.name.lower()
        if any(w in name_lower for w in ["cannon", "mortar", "catapult", "bolt thrower",
                                          "doom diver", "rock lobber", "helblaster"]):
            return "shoot"
        
        # Use custom AI if set
        if player in self._ai:
            decision = self._ai[player](unit, enemies)
            # Override bad AI decisions with smart defaults
            if decision in ["flank_left", "flank_right", "refuse", "march"]:
                # Check if this is a ranged unit that should shoot
                if unit.can_shoot and unit.distance_to(closest) <= 30:
                    return "shoot"
                return smart_action(unit, closest)
            return decision
        
        # Default: use smart action
        return smart_action(unit, closest)
    
    def _run_player_turn(
        self,
        player: str,
        my_units: List[UnitState],
        enemy_units: List[UnitState]
    ) -> None:
        """Run one player's movement phase."""
        faction = self.faction_a if player == "player_a" else self.faction_b
        
        for unit in my_units:
            if not unit.is_alive:
                continue
            
            enemies = [e for e in enemy_units if e.is_alive]
            if not enemies:
                continue
            
            action = self._get_decision(player, unit, enemies)
            closest = min(enemies, key=lambda e: unit.distance_to(e))
            execute_action(unit, action, closest)
            
            if self.verbose:
                print(f"  {faction} {unit.name}: {action}")
    
    def _check_victory(self) -> None:
        """Check if game is over."""
        a_alive = sum(1 for u in self.units_a if u.is_alive)
        b_alive = sum(1 for u in self.units_b if u.is_alive)
        
        if a_alive == 0:
            self.game_over = True
            self.winner = "player_b"
        elif b_alive == 0:
            self.game_over = True
            self.winner = "player_a"
    
    def run_turn(self) -> None:
        """Run one complete turn."""
        self.current_turn += 1
        
        if self.verbose:
            print(f"\n--- Turn {self.current_turn} ---")
        
        # Reset turn flags
        for unit in self.units_a + self.units_b:
            unit.reset_turn()
        
        # Player A moves
        if self.verbose:
            print("  [Movement - Player A]")
        self._run_player_turn("player_a", self.units_a, self.units_b)
        
        # Player A shooting phase
        if self.verbose:
            print("  [Shooting - Player A]")
        casualties_a = resolve_shooting_phase(self.units_a, self.units_b, self.verbose)
        if self.verbose and casualties_a > 0:
            print(f"    Total: {casualties_a} casualties")
        
        # Player B moves
        if self.verbose:
            print("  [Movement - Player B]")
        self._run_player_turn("player_b", self.units_b, self.units_a)
        
        # Player B shooting phase
        if self.verbose:
            print("  [Shooting - Player B]")
        casualties_b = resolve_shooting_phase(self.units_b, self.units_a, self.verbose)
        if self.verbose and casualties_b > 0:
            print(f"    Total: {casualties_b} casualties")
        
        # Combat phase
        if self.verbose:
            print("  [Combat]")
        resolve_combat(self.units_a, self.units_b)
        
        # Check victory
        self._check_victory()
    
    def run(self) -> str:
        """
        Run full battle.
        
        Returns:
            "player_a", "player_b", or "draw"
        """
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"BATTLE: {self.faction_a} vs {self.faction_b}")
            print(f"{'='*60}")
        
        for _ in range(self.max_turns):
            self.run_turn()
            if self.game_over:
                break
        
        # Determine winner if not decided
        if not self.game_over:
            a_models = sum(u.models for u in self.units_a)
            b_models = sum(u.models for u in self.units_b)
            
            if a_models > b_models:
                self.winner = "player_a"
            elif b_models > a_models:
                self.winner = "player_b"
            else:
                self.winner = "draw"
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"WINNER: {self.winner}")
            print(f"{'='*60}")
        
        return self.winner
    
    def get_stats(self) -> Dict:
        """Get battle statistics."""
        return {
            "turns": self.current_turn,
            "winner": self.winner,
            "faction_a": self.faction_a,
            "faction_b": self.faction_b,
            "a_remaining": sum(u.models for u in self.units_a),
            "b_remaining": sum(u.models for u in self.units_b),
            "a_casualties": sum(u.max_models - u.models for u in self.units_a),
            "b_casualties": sum(u.max_models - u.models for u in self.units_b)
        }

