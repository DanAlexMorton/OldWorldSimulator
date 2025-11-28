"""
MCTS Agent for TOW - Integrates MCTS search with game engine

Provides intelligent tactical decision-making for:
- Movement phase: Positioning, flanking, refusing
- Shooting phase: Target prioritization
- Charge phase: Charge vs hold decisions
"""

import copy
import random
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

from .mcts import SimplifiedMCTS, evaluate_board_state
from ..engine.game_state import GameState, UnitState, Position
from ..engine.full_sim import simulate_full_game


@dataclass
class MovementAction:
    """Represents a movement action for a unit"""
    unit_id: str  # Unit name
    direction: str  # "forward", "flank_left", "flank_right", "refuse", "hold"
    distance: float  # Distance in inches
    
    def __repr__(self):
        return f"{self.unit_id}:{self.direction}({self.distance}\")"


class MCTSMovementAgent:
    """
    MCTS-powered movement agent for TOW.
    
    Uses simplified MCTS (rollouts per action) for tactical movement decisions.
    Each unit gets smart positioning based on win rate predictions.
    """
    
    def __init__(
        self,
        rollouts_per_action: int = 50,
        verbose: bool = False
    ):
        """
        Initialize MCTS movement agent.
        
        Args:
            rollouts_per_action: Number of game simulations per move option
            verbose: Print decision-making details
        """
        self.rollouts_per_action = rollouts_per_action
        self.verbose = verbose
        self.mcts = SimplifiedMCTS(
            rollout_fn=self._rollout_game,
            exploration_fn=self._generate_movement_options
        )
    
    def select_movement(
        self,
        game_state: GameState,
        unit: UnitState
    ) -> Optional[Position]:
        """
        Use MCTS to select best movement for unit.
        
        Args:
            game_state: Current game state
            unit: Unit to move
        
        Returns:
            Target position or None (no move)
        """
        if self.verbose:
            print(f"\n  MCTS planning move for {unit.unit.name}...")
        
        # Store context for rollouts
        self.current_player = game_state.active_player
        self.unit_to_move = unit
        
        # Run MCTS search
        best_action = self.mcts.search(
            initial_state=game_state,
            iterations_per_action=self.rollouts_per_action,
            verbose=self.verbose
        )
        
        if best_action:
            direction, distance = best_action
            new_pos = self._calculate_position(unit.position, direction, distance)
            
            if self.verbose:
                print(f"  → {direction} {distance}\" to {new_pos}")
            
            return new_pos
        
        return None
    
    def _generate_movement_options(self, game_state: GameState) -> List[Tuple]:
        """
        Generate valid movement options for current unit.
        
        Returns list of (direction, distance) tuples.
        """
        unit = self.unit_to_move
        
        # Movement distances based on unit type
        base_move = unit.unit.movement
        march_dist = base_move * 2
        
        # Find nearest enemy
        enemies = game_state.get_all_units(
            "player_b" if self.current_player == "player_a" else "player_a"
        )
        
        if not enemies:
            return [("hold", 0)]
        
        nearest_enemy = min(enemies, key=lambda e: self._distance(unit.position, e.position))
        dist_to_enemy = self._distance(unit.position, nearest_enemy.position)
        
        options = [
            ("hold", 0),  # Don't move
        ]
        
        # Forward moves (toward enemy)
        if dist_to_enemy > base_move:
            options.append(("forward", base_move))
        if dist_to_enemy > march_dist and not unit.in_combat:
            options.append(("forward", march_dist))
        
        # Flanking moves (setup +1 CR bonus)
        if dist_to_enemy > base_move * 1.5:
            options.append(("flank_left", base_move * 0.7))
            options.append(("flank_right", base_move * 0.7))
        
        # Refuse (fall back if threatened)
        if dist_to_enemy < base_move * 2:
            options.append(("refuse", base_move * 0.5))
        
        return options
    
    def _rollout_game(self, game_state: GameState) -> float:
        """
        Simulate game to completion and return reward.
        
        Args:
            game_state: State to simulate from
        
        Returns:
            Reward (1.0 = win, 0.5 = draw, 0.0 = loss)
        """
        # Quick evaluation if game is over
        if game_state.game_over:
            return evaluate_board_state(game_state, self.current_player)
        
        # For speed: use heuristic evaluation instead of full simulation
        # (Full sim would be: result = simulate_full_game(...))
        return evaluate_board_state(game_state, self.current_player)
    
    def _calculate_position(
        self,
        current_pos: Position,
        direction: str,
        distance: float
    ) -> Position:
        """
        Calculate new position based on movement direction.
        
        Uses simple direction toward/away from enemy center.
        
        Args:
            current_pos: Current position
            direction: Movement direction
            distance: Distance to move
        
        Returns:
            New position
        """
        import math
        
        x, y = current_pos.x, current_pos.y
        
        # Find nearest enemy for direction reference
        enemies = None
        if hasattr(self, 'current_player'):
            from ..engine.game_state import GameState
            # Simplified - just use stored enemy direction
            enemy_x = 60 if self.current_player == "player_a" else 12
            enemy_y = 30
        else:
            enemy_x = 60
            enemy_y = 30
        
        # Calculate angle to enemy
        dx = enemy_x - x
        dy = enemy_y - y
        angle_to_enemy = math.atan2(dy, dx)
        
        if direction == "hold":
            return current_pos
        
        elif direction == "forward":
            # Move toward enemy
            x += distance * math.cos(angle_to_enemy)
            y += distance * math.sin(angle_to_enemy)
        
        elif direction == "flank_left":
            # Move at 45° left of enemy
            new_angle = angle_to_enemy + math.radians(45)
            x += distance * math.cos(new_angle)
            y += distance * math.sin(new_angle)
        
        elif direction == "flank_right":
            # Move at 45° right of enemy
            new_angle = angle_to_enemy - math.radians(45)
            x += distance * math.cos(new_angle)
            y += distance * math.sin(new_angle)
        
        elif direction == "refuse":
            # Move away from enemy
            x -= distance * math.cos(angle_to_enemy)
            y -= distance * math.sin(angle_to_enemy)
        
        return Position(x=x, y=y)
    
    def _distance(self, pos1: Position, pos2: Position) -> float:
        """Calculate distance between positions"""
        return ((pos1.x - pos2.x)**2 + (pos1.y - pos2.y)**2)**0.5


class MCTSHybridAgent:
    """
    Hybrid agent: MCTS for key decisions, simple heuristics for others.
    
    Uses MCTS for:
    - Critical units (characters, artillery, elite troops)
    - Early game positioning (turns 1-2)
    
    Uses simple AI for:
    - Cheap units (fodder)
    - Late game (when position is decided)
    """
    
    def __init__(
        self,
        mcts_rollouts: int = 30,
        use_mcts_for: List[str] = None,
        verbose: bool = False
    ):
        """
        Initialize hybrid agent.
        
        Args:
            mcts_rollouts: Rollouts for MCTS units
            use_mcts_for: Unit types to use MCTS for (default: ["character", "cavalry", "artillery"])
            verbose: Print decisions
        """
        self.mcts_agent = MCTSMovementAgent(
            rollouts_per_action=mcts_rollouts,
            verbose=verbose
        )
        self.use_mcts_for = use_mcts_for or ["character", "cavalry", "artillery"]
        self.verbose = verbose
    
    def should_use_mcts(self, unit: UnitState, turn: int) -> bool:
        """
        Decide if unit should use MCTS or simple AI.
        
        Args:
            unit: Unit to check
            turn: Current turn number
        
        Returns:
            True if should use MCTS
        """
        # Always use MCTS for first 2 turns (positioning critical)
        if turn <= 2:
            return True
        
        # Use for specific unit types
        troop_type = str(unit.unit.troop_type).lower()
        for keyword in self.use_mcts_for:
            if keyword in troop_type or keyword in unit.unit.name.lower():
                return True
        
        return False
    
    def select_movement(
        self,
        game_state: GameState,
        unit: UnitState
    ) -> Optional[Position]:
        """
        Select movement using MCTS or simple heuristics.
        
        Args:
            game_state: Current game state
            unit: Unit to move
        
        Returns:
            Target position or None
        """
        if self.should_use_mcts(unit, game_state.current_turn):
            if self.verbose:
                print(f"  Using MCTS for {unit.unit.name}")
            return self.mcts_agent.select_movement(game_state, unit)
        else:
            if self.verbose:
                print(f"  Using simple AI for {unit.unit.name}")
            return self._simple_movement(game_state, unit)
    
    def _simple_movement(
        self,
        game_state: GameState,
        unit: UnitState
    ) -> Optional[Position]:
        """Simple forward movement toward nearest enemy"""
        enemies = game_state.get_all_units(
            "player_b" if game_state.active_player == "player_a" else "player_a"
        )
        
        if not enemies:
            return None
        
        # Find nearest enemy
        nearest = min(enemies, key=lambda e: 
                     self.mcts_agent._distance(unit.position, e.position))
        
        # Move toward enemy
        import math
        dx = nearest.position.x - unit.position.x
        dy = nearest.position.y - unit.position.y
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist < 0.1:
            return None
        
        # Move max distance toward enemy
        move_dist = min(unit.unit.movement, dist)
        new_x = unit.position.x + (dx / dist) * move_dist
        new_y = unit.position.y + (dy / dist) * move_dist
        
        return Position(x=new_x, y=new_y)

