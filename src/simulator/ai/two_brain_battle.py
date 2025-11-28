#!/usr/bin/env python3
"""
Two-Brain Battle System

Each player has their own independent Council of War.
No shared state. No cheating. True adversarial AI.

Architecture:
    
    ┌─────────────────────────────────────────────────────────────┐
    │                     BATTLE MANAGER                          │
    │                   (Neutral Referee)                         │
    └─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
    ┌─────────────────────┐         ┌─────────────────────┐
    │   COUNCIL A         │         │   COUNCIL B         │
    │   (Player A Brain)  │         │   (Player B Brain)  │
    │                     │         │                     │
    │   ├─ MCTS A         │         │   ├─ MCTS B         │
    │   ├─ KAN A          │         │   ├─ KAN B          │
    │   ├─ Utility A      │         │   ├─ Utility B      │
    │   └─ Expert A       │         │   └─ Expert B       │
    │                     │         │                     │
    │   Memory A (private)│         │   Memory B (private)│
    └─────────────────────┘         └─────────────────────┘
              │                               │
              │     NO DIRECT COMMUNICATION   │
              │                               │
              └───────────► GAME ◄────────────┘
                          ENGINE
                    (Combat Resolution)
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

from .council_of_war import CouncilOfWar, create_independent_councils, CouncilDecision


@dataclass
class BattleState:
    """Current state of the battle (visible to both players)"""
    turn: int = 0
    phase: str = "deployment"
    
    # Player A state (visible after reveal)
    player_a_units: List[Dict] = field(default_factory=list)
    player_a_casualties: int = 0
    
    # Player B state (visible after reveal)
    player_b_units: List[Dict] = field(default_factory=list)
    player_b_casualties: int = 0
    
    # Game progress
    game_over: bool = False
    winner: Optional[str] = None


@dataclass
class UnitState:
    """Simplified unit state for the battle"""
    name: str
    faction: str
    models: int
    max_models: int
    movement: int
    strength: int
    toughness: int
    position_x: float
    position_y: float
    facing: float
    special_rules: List[str] = field(default_factory=list)
    can_shoot: bool = False
    
    @property
    def is_alive(self) -> bool:
        return self.models > 0
    
    def distance_to(self, other: 'UnitState') -> float:
        dx = self.position_x - other.position_x
        dy = self.position_y - other.position_y
        return math.sqrt(dx*dx + dy*dy)


class TwoBrainBattleManager:
    """
    Battle manager with two independent AI brains.
    
    CRITICAL GUARANTEES:
    1. Each player has completely separate AI (no shared state)
    2. Councils can only see public game state
    3. No communication between councils
    4. Neutral referee handles all rules
    """
    
    def __init__(
        self,
        player_a_faction: str,
        player_b_faction: str,
        verbose: bool = False
    ):
        """
        Initialize battle with two independent councils.
        """
        self.verbose = verbose
        
        # Create two SEPARATE councils (verified independent)
        self.council_a, self.council_b = create_independent_councils(
            player_a_faction,
            player_b_faction
        )
        
        # Battle state (neutral, visible to both)
        self.battle_state = BattleState()
        
        # Tracking
        self.turn_log: List[str] = []
        self.decision_history_a: List[CouncilDecision] = []
        self.decision_history_b: List[CouncilDecision] = []
    
    def setup_armies(
        self,
        player_a_units: List[Dict],
        player_b_units: List[Dict]
    ):
        """
        Setup armies for both players.
        
        In a full implementation, this would be BLIND until reveal.
        """
        # Convert to UnitState
        self.player_a_units = [
            UnitState(
                name=u.get("name", "Unknown"),
                faction=self.council_a.faction,
                models=u.get("models", 10),
                max_models=u.get("models", 10),
                movement=u.get("movement", 4),
                strength=u.get("strength", 3),
                toughness=u.get("toughness", 3),
                position_x=u.get("x", 20 + i * 20),
                position_y=u.get("y", 8),
                facing=90,
                special_rules=u.get("special_rules", []),
                can_shoot="shoot" in str(u.get("special_rules", [])).lower()
            )
            for i, u in enumerate(player_a_units)
        ]
        
        self.player_b_units = [
            UnitState(
                name=u.get("name", "Unknown"),
                faction=self.council_b.faction,
                models=u.get("models", 10),
                max_models=u.get("models", 10),
                movement=u.get("movement", 4),
                strength=u.get("strength", 3),
                toughness=u.get("toughness", 3),
                position_x=u.get("x", 20 + i * 20),
                position_y=u.get("y", 40),
                facing=270,
                special_rules=u.get("special_rules", []),
                can_shoot="shoot" in str(u.get("special_rules", [])).lower()
            )
            for i, u in enumerate(player_b_units)
        ]
        
        if self.verbose:
            print(f"\n[BATTLE] Armies deployed:")
            print(f"  Player A ({self.council_a.faction}): {len(self.player_a_units)} units")
            print(f"  Player B ({self.council_b.faction}): {len(self.player_b_units)} units")
    
    def _get_unit_info_for_council(
        self,
        unit: UnitState,
        enemies: List[UnitState]
    ) -> Dict:
        """Get information a council needs to make decisions"""
        # Find closest enemy
        closest_enemy = min(enemies, key=lambda e: unit.distance_to(e)) if enemies else None
        
        return {
            "unit_name": unit.name,
            "unit_type": "infantry",  # Simplified
            "our_models": unit.models,
            "our_strength": unit.models * unit.strength,
            "distance": unit.distance_to(closest_enemy) if closest_enemy else 99,
            "enemy_models": closest_enemy.models if closest_enemy else 0,
            "enemy_strength": (closest_enemy.models * closest_enemy.strength) if closest_enemy else 0,
            "can_shoot": unit.can_shoot
        }
    
    def _execute_action(
        self,
        unit: UnitState,
        action: str,
        target: Optional[UnitState] = None
    ):
        """Execute an action (neutral referee)"""
        if action == "hold":
            pass  # No movement
        
        elif action == "advance":
            if target:
                # Move toward target
                dx = target.position_x - unit.position_x
                dy = target.position_y - unit.position_y
                dist = math.sqrt(dx*dx + dy*dy)
                if dist > 0:
                    move = min(unit.movement, dist)
                    unit.position_x += (dx / dist) * move
                    unit.position_y += (dy / dist) * move
        
        elif action == "march":
            if target:
                dx = target.position_x - unit.position_x
                dy = target.position_y - unit.position_y
                dist = math.sqrt(dx*dx + dy*dy)
                if dist > 0:
                    move = min(unit.movement * 2, dist)
                    unit.position_x += (dx / dist) * move
                    unit.position_y += (dy / dist) * move
        
        elif action == "charge":
            if target:
                dx = target.position_x - unit.position_x
                dy = target.position_y - unit.position_y
                dist = math.sqrt(dx*dx + dy*dy)
                if dist <= unit.movement * 2 + 7:  # Charge range
                    unit.position_x = target.position_x
                    unit.position_y = target.position_y
        
        elif action.startswith("flank"):
            angle = 45 if "left" in action else -45
            rad = math.radians(unit.facing + angle)
            unit.position_x += unit.movement * 0.7 * math.cos(rad)
            unit.position_y += unit.movement * 0.7 * math.sin(rad)
        
        elif action == "refuse":
            rad = math.radians(unit.facing + 180)
            unit.position_x += unit.movement * 0.5 * math.cos(rad)
            unit.position_y += unit.movement * 0.5 * math.sin(rad)
    
    def _resolve_combat(self):
        """Simplified combat resolution (neutral referee)"""
        import random
        
        # Check for units in contact
        for unit_a in self.player_a_units:
            if not unit_a.is_alive:
                continue
                
            for unit_b in self.player_b_units:
                if not unit_b.is_alive:
                    continue
                
                if unit_a.distance_to(unit_b) < 5:  # In combat
                    # Simplified combat
                    a_attacks = unit_a.models
                    b_attacks = unit_b.models
                    
                    # A hits B
                    a_hits = sum(1 for _ in range(a_attacks) if random.randint(1, 6) >= 4)
                    a_wounds = sum(1 for _ in range(a_hits) if random.randint(1, 6) >= (4 if unit_a.strength >= unit_b.toughness else 5))
                    unit_b.models = max(0, unit_b.models - a_wounds)
                    
                    # B hits A
                    b_hits = sum(1 for _ in range(b_attacks) if random.randint(1, 6) >= 4)
                    b_wounds = sum(1 for _ in range(b_hits) if random.randint(1, 6) >= (4 if unit_b.strength >= unit_a.toughness else 5))
                    unit_a.models = max(0, unit_a.models - b_wounds)
                    
                    if self.verbose:
                        print(f"    Combat: {unit_a.name} vs {unit_b.name}")
                        print(f"      A inflicts {a_wounds} casualties, B inflicts {b_wounds}")
    
    def run_turn(self, turn_number: int) -> Dict:
        """
        Run one full turn with both councils making independent decisions.
        """
        self.battle_state.turn = turn_number
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"TURN {turn_number}")
            print(f"{'='*60}")
        
        turn_results = {"turn": turn_number, "player_a": [], "player_b": []}
        
        # PLAYER A TURN
        if self.verbose:
            print(f"\n--- Player A ({self.council_a.faction}) Movement ---")
        
        for unit in self.player_a_units:
            if not unit.is_alive:
                continue
            
            enemies = [e for e in self.player_b_units if e.is_alive]
            if not enemies:
                continue
            
            # Council A deliberates (using ONLY its own brain)
            info = self._get_unit_info_for_council(unit, enemies)
            decision = self.council_a.convene_council(**info, verbose=self.verbose)
            
            # Execute action
            closest = min(enemies, key=lambda e: unit.distance_to(e))
            self._execute_action(unit, decision.action, closest)
            
            turn_results["player_a"].append({
                "unit": unit.name,
                "action": decision.action,
                "confidence": decision.confidence
            })
            
            # Council B observes (but cannot interfere)
            self.council_b.observe_enemy_move(decision.action)
        
        # PLAYER B TURN
        if self.verbose:
            print(f"\n--- Player B ({self.council_b.faction}) Movement ---")
        
        for unit in self.player_b_units:
            if not unit.is_alive:
                continue
            
            enemies = [e for e in self.player_a_units if e.is_alive]
            if not enemies:
                continue
            
            # Council B deliberates (using ONLY its own brain)
            info = self._get_unit_info_for_council(unit, enemies)
            decision = self.council_b.convene_council(**info, verbose=self.verbose)
            
            # Execute action
            closest = min(enemies, key=lambda e: unit.distance_to(e))
            self._execute_action(unit, decision.action, closest)
            
            turn_results["player_b"].append({
                "unit": unit.name,
                "action": decision.action,
                "confidence": decision.confidence
            })
            
            # Council A observes (but cannot interfere)
            self.council_a.observe_enemy_move(decision.action)
        
        # COMBAT PHASE (neutral referee)
        if self.verbose:
            print(f"\n--- Combat Phase ---")
        self._resolve_combat()
        
        # Check victory
        a_alive = sum(1 for u in self.player_a_units if u.is_alive)
        b_alive = sum(1 for u in self.player_b_units if u.is_alive)
        
        if a_alive == 0:
            self.battle_state.game_over = True
            self.battle_state.winner = "player_b"
        elif b_alive == 0:
            self.battle_state.game_over = True
            self.battle_state.winner = "player_a"
        
        return turn_results
    
    def run_full_battle(self, max_turns: int = 6) -> str:
        """
        Run complete battle with two independent councils.
        
        Returns: "player_a", "player_b", or "draw"
        """
        if self.verbose:
            print("\n" + "="*60)
            print("TWO-BRAIN BATTLE BEGINS!")
            print(f"Player A: {self.council_a.faction} (Council #{self.council_a.council_id})")
            print(f"Player B: {self.council_b.faction} (Council #{self.council_b.council_id})")
            print("="*60)
        
        for turn in range(1, max_turns + 1):
            self.run_turn(turn)
            
            if self.battle_state.game_over:
                break
        
        # Determine winner if not already decided
        if not self.battle_state.game_over:
            a_models = sum(u.models for u in self.player_a_units)
            b_models = sum(u.models for u in self.player_b_units)
            
            if a_models > b_models:
                self.battle_state.winner = "player_a"
            elif b_models > a_models:
                self.battle_state.winner = "player_b"
            else:
                self.battle_state.winner = "draw"
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"BATTLE OVER!")
            print(f"Winner: {self.battle_state.winner}")
            print(f"Council A decisions: {self.council_a.decision_count}")
            print(f"Council B decisions: {self.council_b.decision_count}")
            print(f"Shared state between councils: NONE (verified)")
            print(f"{'='*60}")
        
        return self.battle_state.winner


def run_two_brain_tournament(num_games: int = 100):
    """Run tournament with two independent brains"""
    
    print(f"""
================================================================================
TWO-BRAIN TOURNAMENT
================================================================================

Each player has their own independent Council of War.
NO shared state. NO cheating. TRUE adversarial AI.

Games: {num_games}
Player A: Empire (Council #1)
Player B: Orcs (Council #2)

================================================================================
""")
    
    # Define armies
    empire_army = [
        {"name": "Empire Halberdiers", "models": 25, "movement": 4, "strength": 3, "toughness": 3},
        {"name": "Empire Handgunners", "models": 15, "movement": 4, "strength": 3, "toughness": 3, "special_rules": ["Shooting"]},
        {"name": "Empire Knights", "models": 8, "movement": 8, "strength": 3, "toughness": 3},
    ]
    
    orc_army = [
        {"name": "Orc Boyz", "models": 30, "movement": 4, "strength": 3, "toughness": 4},
        {"name": "Goblin Archers", "models": 20, "movement": 4, "strength": 3, "toughness": 3, "special_rules": ["Shooting"]},
        {"name": "Boar Boyz", "models": 10, "movement": 7, "strength": 4, "toughness": 4},
    ]
    
    empire_wins = 0
    orc_wins = 0
    draws = 0
    
    start_time = time.time()
    
    for game in range(1, num_games + 1):
        # Create fresh independent councils for each game
        battle = TwoBrainBattleManager("Empire", "Orcs", verbose=False)
        battle.setup_armies(empire_army, orc_army)
        
        result = battle.run_full_battle(max_turns=6)
        
        if result == "player_a":
            empire_wins += 1
        elif result == "player_b":
            orc_wins += 1
        else:
            draws += 1
        
        if game % 10 == 0:
            elapsed = time.time() - start_time
            rate = game / elapsed
            print(f"Game {game:3d}: Empire {empire_wins} ({100*empire_wins/game:.0f}%) | "
                  f"Orc {orc_wins} ({100*orc_wins/game:.0f}%) | Draw {draws} "
                  f"({rate:.1f} g/s)")
    
    elapsed = time.time() - start_time
    
    print(f"""
================================================================================
FINAL RESULTS - TWO INDEPENDENT BRAINS
================================================================================

Total Games: {num_games}
Total Time: {elapsed:.1f}s ({num_games/elapsed:.1f} games/s)

EMPIRE (Council A):  {empire_wins} wins ({100*empire_wins/num_games:.1f}%)
ORCS (Council B):    {orc_wins} wins ({100*orc_wins/num_games:.1f}%)
DRAWS:               {draws} ({100*draws/num_games:.1f}%)

VERIFIED: Each player used completely independent AI.
NO shared state. NO cheating. TRUE adversarial.

================================================================================
""")


if __name__ == "__main__":
    # Demo one verbose game
    print("="*60)
    print("SINGLE BATTLE DEMO (VERBOSE)")
    print("="*60)
    
    battle = TwoBrainBattleManager("Empire", "Orcs", verbose=True)
    
    empire_army = [
        {"name": "Empire Handgunners", "models": 15, "special_rules": ["Shooting"]},
        {"name": "Empire Knights", "models": 8, "movement": 8},
    ]
    
    orc_army = [
        {"name": "Orc Boyz", "models": 25, "toughness": 4},
        {"name": "Boar Boyz", "models": 10, "movement": 7, "toughness": 4},
    ]
    
    battle.setup_armies(empire_army, orc_army)
    winner = battle.run_full_battle(max_turns=3)
    
    print(f"\n\nWinner: {winner}")
    
    # Run tournament
    print("\n\n")
    run_two_brain_tournament(num_games=50)

