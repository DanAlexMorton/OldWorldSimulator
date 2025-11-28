"""
Utility-Based AI for TOW - Fast Heuristic Decision Making

Scores actions based on weighted utility functions.
Much faster than MCTS but less deep. Good for quick decisions and baseline policy.

Based on utility theory from Dill et al. (2013) "Utility-Based AI for Games"
"""

import math
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass


@dataclass
class UtilityWeights:
    """Weights for utility scoring"""
    threat_weight: float = 1.0
    position_weight: float = 0.8
    objective_weight: float = 0.6
    safety_weight: float = 0.7
    aggression_bias: float = 0.0  # Positive = aggressive, negative = defensive


class UtilityAgent:
    """
    Utility-based movement agent.
    
    Evaluates each action by summing weighted utility scores:
    - Threat reduction (minimize enemy threat)
    - Position quality (optimal range, flanking)
    - Objective control (terrain, VP)
    - Safety (avoid dangerous positions)
    """
    
    def __init__(self, weights: Optional[UtilityWeights] = None):
        """
        Initialize utility agent.
        
        Args:
            weights: Utility function weights
        """
        self.weights = weights or UtilityWeights()
        self.actions = ["hold", "forward", "march", "flank_left", "flank_right", "refuse"]
    
    def evaluate_action(
        self,
        action: str,
        distance: float,
        unit_strength: int,
        enemy_strength: int,
        unit_type: str
    ) -> float:
        """
        Calculate utility score for an action.
        
        Args:
            action: Action to evaluate
            distance: Current distance to nearest enemy
            unit_strength: Our unit's strength (models × S)
            enemy_strength: Enemy unit's strength
            unit_type: "infantry", "cavalry", "artillery", "ranged"
        
        Returns:
            Utility score (higher = better)
        """
        # Simulate new distance after action
        new_distance = self._simulate_distance(action, distance)
        
        # Calculate utility components
        threat_util = self._threat_utility(new_distance, unit_strength, enemy_strength)
        position_util = self._position_utility(new_distance, unit_type)
        safety_util = self._safety_utility(new_distance, unit_strength, enemy_strength)
        
        # Weighted sum
        total_utility = (
            self.weights.threat_weight * threat_util +
            self.weights.position_weight * position_util +
            self.weights.safety_weight * safety_util +
            self.weights.aggression_bias  # Faction bias
        )
        
        return total_utility
    
    def select_best_action(
        self,
        distance: float,
        unit_strength: int,
        enemy_strength: int,
        unit_type: str,
        verbose: bool = False
    ) -> Tuple[str, float]:
        """
        Select action with highest utility.
        
        Args:
            distance: Distance to nearest enemy
            unit_strength: Our unit's strength
            enemy_strength: Enemy unit's strength
            unit_type: Unit type
            verbose: Print utility scores
        
        Returns:
            (best_action, utility_score)
        """
        scores = []
        
        for action in self.actions:
            utility = self.evaluate_action(
                action, distance, unit_strength, enemy_strength, unit_type
            )
            scores.append((action, utility))
            
            if verbose:
                print(f"  {action:12s}: {utility:+.3f}")
        
        # Return best action
        best = max(scores, key=lambda x: x[1])
        
        if verbose:
            print(f"  >> BEST: {best[0]} (utility: {best[1]:+.3f})")
        
        return best
    
    def _simulate_distance(self, action: str, current_distance: float) -> float:
        """Simulate new distance after action"""
        if action == "hold":
            return current_distance
        elif action == "forward":
            return current_distance - 4
        elif action == "march":
            return current_distance - 8
        elif action.startswith("flank"):
            return current_distance - 3  # Slight advance
        elif action == "refuse":
            return current_distance + 2
        else:
            return current_distance
    
    def _threat_utility(self, distance: float, our_strength: int, enemy_strength: int) -> float:
        """
        Threat utility - prefer positions that minimize enemy threat.
        
        Returns value in [0, 1]
        """
        # Strength ratio
        strength_ratio = our_strength / max(enemy_strength, 1)
        
        # If we're stronger, closing distance is good
        # If weaker, maintaining distance is good
        if strength_ratio > 1.2:
            # We're stronger - close for combat
            ideal_distance = 8.0
        elif strength_ratio < 0.8:
            # We're weaker - maintain range
            ideal_distance = 24.0
        else:
            # Even match - optimal shooting range
            ideal_distance = 18.0
        
        # Score based on distance to ideal
        distance_error = abs(distance - ideal_distance)
        utility = 1.0 - min(distance_error / 30.0, 1.0)
        
        return utility
    
    def _position_utility(self, distance: float, unit_type: str) -> float:
        """
        Position quality utility.
        
        Different unit types prefer different ranges:
        - Ranged: 12-24" (shooting range)
        - Cavalry: 8-12" (charge range)
        - Infantry: 6-12" (combat range)
        - Artillery: 24+" (safe range)
        
        Returns value in [0, 1]
        """
        if unit_type == "ranged" or unit_type == "artillery":
            # Prefer 12-24" range
            if 12 <= distance <= 24:
                return 1.0
            elif distance < 12:
                return 0.3  # Too close
            elif distance > 36:
                return 0.2  # Too far
            else:
                return 0.6
        
        elif unit_type == "cavalry":
            # Prefer charge range (8-14")
            if 8 <= distance <= 14:
                return 1.0
            elif distance < 8:
                return 0.5  # Already engaged
            else:
                return 0.4
        
        elif unit_type == "infantry":
            # Prefer close combat (< 12")
            if distance < 12:
                return 1.0
            elif distance < 24:
                return 0.6
            else:
                return 0.3
        
        else:
            # Default: prefer mid-range
            if 12 <= distance <= 24:
                return 1.0
            else:
                return 0.5
    
    def _safety_utility(self, distance: float, our_strength: int, enemy_strength: int) -> float:
        """
        Safety utility - avoid dangerous positions.
        
        Danger zones:
        - Too close when outnumbered (< 8" and weak)
        - Too exposed (no support)
        
        Returns value in [0, 1]
        """
        strength_ratio = our_strength / max(enemy_strength, 1)
        
        # Danger: Close + outnumbered
        if distance < 8 and strength_ratio < 0.8:
            return 0.2  # Very dangerous!
        
        # Danger: Mid-range + outnumbered (will get charged)
        if 8 <= distance <= 16 and strength_ratio < 0.7:
            return 0.4
        
        # Safe: Far + even or winning
        if distance > 24 or strength_ratio > 1.0:
            return 1.0
        
        # Moderate safety
        return 0.6
    
    def set_faction_bias(self, faction: str):
        """
        Set faction-specific bias.
        
        Args:
            faction: "empire", "orcs", "bretonnia", etc.
        """
        if faction.lower() in ["orcs", "orcs & goblins", "chaos"]:
            # Aggressive factions
            self.weights.aggression_bias = 0.3
            self.weights.safety_weight = 0.5  # Care less about safety
        
        elif faction.lower() in ["empire", "dwarfs", "high elves"]:
            # Defensive factions
            self.weights.aggression_bias = -0.2
            self.weights.safety_weight = 1.0  # Very cautious
        
        elif faction.lower() in ["bretonnia", "vampire counts"]:
            # Balanced
            self.weights.aggression_bias = 0.1
            self.weights.safety_weight = 0.7
        
        else:
            # Neutral
            self.weights.aggression_bias = 0.0
            self.weights.safety_weight = 0.7


def create_faction_utility_agent(faction: str) -> UtilityAgent:
    """
    Create utility agent with faction-specific tuning.
    
    Args:
        faction: Faction name
    
    Returns:
        Configured UtilityAgent
    """
    agent = UtilityAgent()
    agent.set_faction_bias(faction)
    return agent

