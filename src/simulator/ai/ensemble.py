"""
Ensemble AI - "Council of War"

Combines multiple AI agents through weighted voting:
1. MCTS (0.5) - Deep tactical search
2. Utility AI (0.3) - Fast heuristics  
3. Q-Learning (0.2) - Learned policy

Based on portfolio approaches from Ontañón (2013) and ensemble methods
from military wargames (RAND, 2024).
"""

from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from collections import Counter

from .mcts_agent import MCTSMovementAgent
from .utility_agent import UtilityAgent, create_faction_utility_agent
from .q_agent import QLearningAgent


@dataclass
class EnsembleWeights:
    """Voting weights for ensemble members"""
    mcts_weight: float = 0.5
    utility_weight: float = 0.3
    q_learning_weight: float = 0.2


class EnsembleAI:
    """
    Ensemble AI - Council of War.
    
    Combines three AI agents:
    - MCTS: Tactical search (slow, deep)
    - Utility: Fast heuristics (fast, reasonable)
    - Q-Learning: Learned policy (fast, adaptive)
    
    Uses weighted voting to select actions.
    """
    
    def __init__(
        self,
        faction: str = "neutral",
        mcts_rollouts: int = 30,
        weights: Optional[EnsembleWeights] = None,
        pretrained_q_agent: Optional[QLearningAgent] = None
    ):
        """
        Initialize ensemble AI.
        
        Args:
            faction: Faction name for utility bias
            mcts_rollouts: MCTS rollouts per decision
            weights: Voting weights
            pretrained_q_agent: Pre-trained Q-agent (or creates new)
        """
        self.faction = faction
        self.weights = weights or EnsembleWeights()
        
        # Initialize agents
        self.mcts_agent = MCTSMovementAgent(
            rollouts_per_action=mcts_rollouts,
            verbose=False
        )
        
        self.utility_agent = create_faction_utility_agent(faction)
        
        self.q_agent = pretrained_q_agent or QLearningAgent()
        
        # Statistics
        self.decisions_made = 0
        self.agent_votes: Dict[str, int] = {
            "mcts": 0,
            "utility": 0,
            "q_learning": 0,
            "unanimous": 0
        }
    
    def select_action(
        self,
        distance: float,
        our_models: int,
        enemy_models: int,
        our_strength: int,
        enemy_strength: int,
        unit_type: str,
        verbose: bool = False
    ) -> Tuple[str, Dict]:
        """
        Select action through ensemble voting.
        
        Args:
            distance: Distance to nearest enemy
            our_models: Our unit's model count
            enemy_models: Enemy unit's model count
            our_strength: Our unit's total strength
            enemy_strength: Enemy unit's total strength
            unit_type: Unit type
            verbose: Print voting process
        
        Returns:
            (selected_action, voting_details)
        """
        if verbose:
            print(f"\n{'='*60}")
            print(f"ENSEMBLE DECISION - {unit_type.upper()}")
            print(f"Distance: {distance:.1f}\", Models: {our_models} vs {enemy_models}")
            print(f"{'='*60}")
        
        # Get each agent's recommendation
        votes = {}
        
        # 1. MCTS (expensive but smart)
        if verbose:
            print("\n[1] MCTS Agent (tactical search):")
        
        # Simplified MCTS evaluation (would use full agent in production)
        mcts_action = self._mcts_recommendation(distance, our_models, enemy_models, unit_type)
        votes["mcts"] = (mcts_action, self.weights.mcts_weight)
        
        if verbose:
            print(f"  >> Recommends: {mcts_action} (weight: {self.weights.mcts_weight})")
        
        # 2. Utility AI (fast heuristics)
        if verbose:
            print("\n[2] Utility Agent (heuristic scoring):")
        
        utility_action, utility_score = self.utility_agent.select_best_action(
            distance, our_strength, enemy_strength, unit_type, verbose=verbose
        )
        votes["utility"] = (utility_action, self.weights.utility_weight)
        
        # 3. Q-Learning (learned policy)
        if verbose:
            print("\n[3] Q-Learning Agent (learned policy):")
        
        q_state = self.q_agent.discretize_state(distance, our_models, enemy_models, unit_type)
        q_action = self.q_agent.select_action(q_state, training=False)
        votes["q_learning"] = (q_action, self.weights.q_learning_weight)
        
        if verbose:
            print(f"  >> Recommends: {q_action} (weight: {self.weights.q_learning_weight})")
        
        # Weighted voting
        action_scores: Dict[str, float] = {}
        for agent_name, (action, weight) in votes.items():
            if action not in action_scores:
                action_scores[action] = 0.0
            action_scores[action] += weight
        
        # Select action with highest weighted score
        best_action = max(action_scores.items(), key=lambda x: x[1])
        selected_action, final_score = best_action
        
        # Check if unanimous
        unanimous = len(set(v[0] for v in votes.values())) == 1
        
        # Update statistics
        self.decisions_made += 1
        if unanimous:
            self.agent_votes["unanimous"] += 1
        
        # Determine which agent's vote won
        for agent_name, (action, weight) in votes.items():
            if action == selected_action:
                self.agent_votes[agent_name] += 1
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"ENSEMBLE DECISION: {selected_action.upper()}")
            print(f"Score: {final_score:.2f} | Unanimous: {unanimous}")
            print(f"{'='*60}\n")
        
        # Return selected action and voting details
        details = {
            "mcts_vote": votes["mcts"][0],
            "utility_vote": votes["utility"][0],
            "q_vote": votes["q_learning"][0],
            "selected": selected_action,
            "score": final_score,
            "unanimous": unanimous
        }
        
        return selected_action, details
    
    def _mcts_recommendation(
        self,
        distance: float,
        our_models: int,
        enemy_models: int,
        unit_type: str
    ) -> str:
        """
        Get MCTS recommendation (simplified for demo).
        
        In production, would call full MCTS agent.
        """
        # Heuristic MCTS-style logic
        if distance < 8:
            if our_models > enemy_models * 1.5:
                return "forward"  # We're winning, press
            else:
                return "refuse"  # Too close, fall back
        
        elif 8 <= distance < 16:
            return "flank_left"  # Setup flanking
        
        elif 16 <= distance < 28:
            if unit_type in ["ranged", "artillery"]:
                return "hold"  # Optimal shooting range
            else:
                return "forward"  # Close for combat
        
        else:
            return "march"  # Close distance quickly
    
    def get_statistics(self) -> Dict:
        """Get ensemble voting statistics"""
        total = max(self.decisions_made, 1)
        
        return {
            "decisions_made": self.decisions_made,
            "mcts_influence": self.agent_votes["mcts"] / total,
            "utility_influence": self.agent_votes["utility"] / total,
            "q_influence": self.agent_votes["q_learning"] / total,
            "unanimous_rate": self.agent_votes["unanimous"] / total
        }
    
    def print_statistics(self):
        """Print voting statistics"""
        stats = self.get_statistics()
        
        print(f"\n{'='*60}")
        print(f"ENSEMBLE STATISTICS - {self.decisions_made} decisions")
        print(f"{'='*60}")
        print(f"Agent Influence:")
        print(f"  MCTS:       {stats['mcts_influence']:.1%}")
        print(f"  Utility:    {stats['utility_influence']:.1%}")
        print(f"  Q-Learning: {stats['q_influence']:.1%}")
        print(f"Unanimous:    {stats['unanimous_rate']:.1%}")
        print(f"{'='*60}\n")


def create_ensemble_for_faction(
    faction: str,
    mcts_rollouts: int = 30,
    pretrained_q_path: Optional[str] = None
) -> EnsembleAI:
    """
    Create faction-tuned ensemble AI.
    
    Args:
        faction: Faction name
        mcts_rollouts: MCTS rollouts per decision
        pretrained_q_path: Path to pre-trained Q-agent
    
    Returns:
        Configured EnsembleAI
    """
    # Load Q-agent if available
    q_agent = None
    if pretrained_q_path:
        try:
            q_agent = QLearningAgent()
            q_agent.load(pretrained_q_path)
        except:
            print(f"Warning: Could not load Q-agent from {pretrained_q_path}")
            q_agent = None
    
    # Adjust weights for faction
    weights = EnsembleWeights()
    
    if faction.lower() in ["orcs", "orcs & goblins"]:
        # Orcs: More aggressive, rely more on utility (fast decisions)
        weights.utility_weight = 0.4
        weights.mcts_weight = 0.4
        weights.q_learning_weight = 0.2
    
    elif faction.lower() in ["empire", "dwarfs"]:
        # Empire/Dwarfs: More tactical, rely more on MCTS
        weights.mcts_weight = 0.6
        weights.utility_weight = 0.2
        weights.q_learning_weight = 0.2
    
    return EnsembleAI(
        faction=faction,
        mcts_rollouts=mcts_rollouts,
        weights=weights,
        pretrained_q_agent=q_agent
    )

