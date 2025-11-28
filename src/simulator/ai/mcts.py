"""
Monte Carlo Tree Search (MCTS) for Warhammer: The Old World

Implements UCB1-based tree search with game-specific rollouts.
Designed for turn-based tactical decisions (movement, shooting, charges).

Performance: ~100 rollouts per decision point using our 288 games/sec engine.
"""

import math
import random
import copy
from typing import List, Optional, Tuple, Callable
from dataclasses import dataclass, field


@dataclass
class MCTSNode:
    """
    Node in the MCTS search tree.
    
    Represents a game state + action that led to it.
    """
    state: any  # GameState or simplified state representation
    action: Optional[Tuple] = None  # (unit_id, action_type, params)
    parent: Optional['MCTSNode'] = None
    children: List['MCTSNode'] = field(default_factory=list)
    
    visits: int = 0
    value: float = 0.0  # Total reward accumulated
    
    # For optimization
    untried_actions: List[Tuple] = field(default_factory=list)
    
    def ucb1(self, exploration_constant: float = 1.41) -> float:
        """
        Upper Confidence Bound for Trees (UCB1).
        
        Balances exploitation (high value) vs exploration (low visits).
        
        Args:
            exploration_constant: C parameter (√2 is theoretical optimum)
        
        Returns:
            UCB1 score (higher = should be selected)
        """
        if self.visits == 0:
            return float('inf')  # Prioritize unvisited nodes
        
        if self.parent is None:
            return self.value / self.visits
        
        exploitation = self.value / self.visits
        exploration = exploration_constant * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )
        
        return exploitation + exploration
    
    def best_child(self, exploration: float = 0.0) -> 'MCTSNode':
        """
        Select best child node.
        
        Args:
            exploration: 0 for final selection, >0 for search
        
        Returns:
            Child with highest UCB1 score
        """
        if not self.children:
            return None
        
        if exploration == 0.0:
            # Final selection: pure exploitation
            return max(self.children, key=lambda c: c.value / max(c.visits, 1))
        else:
            # During search: UCB1
            return max(self.children, key=lambda c: c.ucb1(exploration))
    
    def is_fully_expanded(self) -> bool:
        """Check if all actions have been tried"""
        return len(self.untried_actions) == 0


class MCTS:
    """
    Monte Carlo Tree Search planner.
    
    Builds a search tree via:
    1. Selection: Traverse tree using UCB1
    2. Expansion: Add new child node
    3. Simulation: Rollout to terminal state
    4. Backpropagation: Update node values
    
    Usage:
        mcts = MCTS(rollout_fn=simulate_game, expansion_fn=generate_moves)
        best_action = mcts.search(current_state, iterations=100)
    """
    
    def __init__(
        self,
        rollout_fn: Callable,
        expansion_fn: Callable,
        exploration_constant: float = 1.41,
        max_depth: int = 10
    ):
        """
        Initialize MCTS planner.
        
        Args:
            rollout_fn: Function(state) -> reward (simulate to end)
            expansion_fn: Function(state) -> List[actions] (generate valid moves)
            exploration_constant: UCB1 C parameter
            max_depth: Max tree depth (prevent infinite expansion)
        """
        self.rollout_fn = rollout_fn
        self.expansion_fn = expansion_fn
        self.exploration_constant = exploration_constant
        self.max_depth = max_depth
    
    def search(
        self,
        initial_state,
        iterations: int = 100,
        verbose: bool = False
    ) -> Tuple:
        """
        Run MCTS search from initial state.
        
        Args:
            initial_state: Current game state
            iterations: Number of MCTS iterations (more = better, slower)
            verbose: Print search progress
        
        Returns:
            Best action (type, params) or None
        """
        # Create root node
        root = MCTSNode(state=initial_state)
        root.untried_actions = self.expansion_fn(initial_state)
        
        if not root.untried_actions:
            return None  # No valid actions
        
        # Run MCTS iterations
        for i in range(iterations):
            node = root
            depth = 0
            
            # 1. Selection: Traverse tree using UCB1
            while node.is_fully_expanded() and node.children and depth < self.max_depth:
                node = node.best_child(self.exploration_constant)
                depth += 1
            
            # 2. Expansion: Add new child if not fully expanded
            if not node.is_fully_expanded() and depth < self.max_depth:
                action = node.untried_actions.pop()
                child_state = self._apply_action(node.state, action)
                child = MCTSNode(
                    state=child_state,
                    action=action,
                    parent=node
                )
                child.untried_actions = self.expansion_fn(child_state)
                node.children.append(child)
                node = child
            
            # 3. Simulation: Rollout to terminal state
            reward = self.rollout_fn(node.state)
            
            # 4. Backpropagation: Update node statistics
            while node is not None:
                node.visits += 1
                node.value += reward
                node = node.parent
            
            if verbose and (i + 1) % 10 == 0:
                print(f"  MCTS iteration {i+1}/{iterations}")
        
        # Select best action (most visited child)
        best_child = root.best_child(exploration=0.0)
        
        if best_child and verbose:
            print(f"  Best action: {best_child.action}")
            print(f"  Visits: {best_child.visits}, Value: {best_child.value:.2f}")
            print(f"  Win rate: {best_child.value / best_child.visits:.1%}")
        
        return best_child.action if best_child else None
    
    def _apply_action(self, state, action):
        """
        Apply action to state (create new state).
        
        This is a placeholder - should be implemented by specific game.
        """
        # Deep copy state
        new_state = copy.deepcopy(state)
        
        # Apply action (game-specific)
        # For TOW: move unit, resolve combat, etc.
        
        return new_state


class SimplifiedMCTS:
    """
    Simplified MCTS for quick decision-making.
    
    Instead of building a full tree, just evaluates each immediate action
    with multiple rollouts. Faster but less accurate than full MCTS.
    
    Good for: Quick tactical decisions with limited branching
    """
    
    def __init__(self, rollout_fn: Callable, exploration_fn: Callable):
        self.rollout_fn = rollout_fn
        self.exploration_fn = exploration_fn
    
    def search(
        self,
        initial_state,
        iterations_per_action: int = 50,
        verbose: bool = False
    ) -> Tuple:
        """
        Evaluate each action with multiple rollouts.
        
        Args:
            initial_state: Current game state
            iterations_per_action: Rollouts per action
            verbose: Print results
        
        Returns:
            Best action or None
        """
        actions = self.exploration_fn(initial_state)
        
        if not actions:
            return None
        
        # Evaluate each action
        action_scores = []
        for action in actions:
            total_reward = 0.0
            
            for _ in range(iterations_per_action):
                # Apply action and rollout
                state = self._apply_action(initial_state, action)
                reward = self.rollout_fn(state)
                total_reward += reward
            
            avg_reward = total_reward / iterations_per_action
            action_scores.append((action, avg_reward))
            
            if verbose:
                print(f"  Action {action}: {avg_reward:.3f}")
        
        # Return best action
        best_action, best_score = max(action_scores, key=lambda x: x[1])
        
        if verbose:
            print(f"  Best: {best_action} (score: {best_score:.3f})")
        
        return best_action
    
    def _apply_action(self, state, action):
        """Apply action to state (deep copy)"""
        return copy.deepcopy(state)


# Utility functions for TOW integration

def evaluate_board_state(game_state, player: str) -> float:
    """
    Quick heuristic evaluation of board position.
    
    Returns value from player's perspective (higher = better for player).
    
    Args:
        game_state: Current GameState
        player: "player_a" or "player_b"
    
    Returns:
        Evaluation score (0.0 to 1.0, 0.5 = even)
    """
    if game_state.game_over:
        if game_state.winner == player:
            return 1.0
        elif game_state.winner == "draw":
            return 0.5
        else:
            return 0.0
    
    # Count surviving models
    if player == "player_a":
        our_units = game_state.player_a_units
        their_units = game_state.player_b_units
    else:
        our_units = game_state.player_b_units
        their_units = game_state.player_a_units
    
    our_models = sum(u.unit.current_models for u in our_units)
    their_models = sum(u.unit.current_models for u in their_units)
    
    if our_models + their_models == 0:
        return 0.5
    
    # Normalize to 0-1
    ratio = our_models / (our_models + their_models)
    return ratio

