"""
Q-Learning Agent for TOW - Tabular RL

Learns optimal movement policies through self-play.
Uses simplified state space (distance bins, model ratios) for tractable learning.

Based on Watkins & Dayan (1992) Q-Learning algorithm.
"""

import random
import json
import pickle
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class QLearningConfig:
    """Configuration for Q-Learning agent"""
    learning_rate: float = 0.1
    discount_factor: float = 0.95
    exploration_rate: float = 0.2
    exploration_decay: float = 0.995
    min_exploration: float = 0.05


class QLearningAgent:
    """
    Q-Learning agent for movement decisions.
    
    Uses tabular Q-table with discretized state space:
    - Distance to nearest enemy (bins: 0-6", 6-12", 12-24", 24-36", 36+")
    - Model ratio (bins: outnumbered, even, outnumber)
    - Unit type (infantry, cavalry, artillery)
    
    Actions: hold, forward, march, flank_left, flank_right, refuse
    """
    
    def __init__(self, config: Optional[QLearningConfig] = None):
        """
        Initialize Q-Learning agent.
        
        Args:
            config: Learning configuration
        """
        self.config = config or QLearningConfig()
        
        # Q-table: {state: {action: Q-value}}
        self.q_table: Dict[Tuple, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        
        # Learning statistics
        self.episodes = 0
        self.total_reward = 0.0
        self.exploration_rate = self.config.exploration_rate
        
        # Action space
        self.actions = ["hold", "forward", "march", "flank_left", "flank_right", "refuse"]
    
    def discretize_state(
        self,
        distance: float,
        our_models: int,
        enemy_models: int,
        unit_type: str
    ) -> Tuple:
        """
        Convert continuous state to discrete bins.
        
        Args:
            distance: Distance to nearest enemy (inches)
            our_models: Our unit's model count
            enemy_models: Nearest enemy's model count
            unit_type: "infantry", "cavalry", or "artillery"
        
        Returns:
            Discrete state tuple
        """
        # Distance bins
        if distance < 6:
            dist_bin = "close"
        elif distance < 12:
            dist_bin = "near"
        elif distance < 24:
            dist_bin = "mid"
        elif distance < 36:
            dist_bin = "far"
        else:
            dist_bin = "very_far"
        
        # Model ratio bins
        ratio = our_models / max(enemy_models, 1)
        if ratio < 0.7:
            ratio_bin = "outnumbered"
        elif ratio < 1.3:
            ratio_bin = "even"
        else:
            ratio_bin = "outnumber"
        
        return (dist_bin, ratio_bin, unit_type)
    
    def select_action(
        self,
        state: Tuple,
        training: bool = False
    ) -> str:
        """
        Select action using epsilon-greedy policy.
        
        Args:
            state: Discretized state tuple
            training: If True, use exploration; if False, be greedy
        
        Returns:
            Selected action
        """
        # Exploration (if training)
        if training and random.random() < self.exploration_rate:
            return random.choice(self.actions)
        
        # Exploitation (greedy)
        q_values = self.q_table[state]
        
        if not q_values:
            # No experience in this state - random choice
            return random.choice(self.actions)
        
        # Select best action
        best_action = max(q_values.items(), key=lambda x: x[1])
        return best_action[0]
    
    def update(
        self,
        state: Tuple,
        action: str,
        reward: float,
        next_state: Tuple,
        done: bool = False
    ):
        """
        Update Q-value using Q-learning update rule.
        
        Q(s,a) ← Q(s,a) + α[r + γ max Q(s',a') - Q(s,a)]
        
        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Resulting state
            done: True if episode ended
        """
        # Current Q-value
        current_q = self.q_table[state][action]
        
        # Max Q-value of next state
        if done:
            max_next_q = 0.0
        else:
            next_q_values = self.q_table[next_state]
            max_next_q = max(next_q_values.values()) if next_q_values else 0.0
        
        # Q-learning update
        td_target = reward + self.config.discount_factor * max_next_q
        td_error = td_target - current_q
        new_q = current_q + self.config.learning_rate * td_error
        
        # Update Q-table
        self.q_table[state][action] = new_q
        
        # Update statistics
        self.total_reward += reward
    
    def decay_exploration(self):
        """Decay exploration rate over time"""
        self.exploration_rate = max(
            self.config.min_exploration,
            self.exploration_rate * self.config.exploration_decay
        )
    
    def end_episode(self):
        """Mark end of training episode"""
        self.episodes += 1
        self.decay_exploration()
    
    def get_statistics(self) -> Dict:
        """Get learning statistics"""
        return {
            "episodes": self.episodes,
            "total_reward": self.total_reward,
            "avg_reward": self.total_reward / max(self.episodes, 1),
            "exploration_rate": self.exploration_rate,
            "q_table_size": len(self.q_table)
        }
    
    def save(self, filepath: str):
        """
        Save Q-table to file.
        
        Args:
            filepath: Path to save file (.pkl)
        """
        data = {
            "q_table": dict(self.q_table),
            "config": self.config,
            "statistics": self.get_statistics()
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
    
    def load(self, filepath: str):
        """
        Load Q-table from file.
        
        Args:
            filepath: Path to load file (.pkl)
        """
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        self.q_table = defaultdict(lambda: defaultdict(float), data["q_table"])
        self.config = data["config"]
        stats = data["statistics"]
        self.episodes = stats["episodes"]
        self.total_reward = stats["total_reward"]
        self.exploration_rate = stats["exploration_rate"]
    
    def export_policy(self, filepath: str):
        """
        Export learned policy as human-readable JSON.
        
        Args:
            filepath: Path to JSON file
        """
        policy = {}
        
        for state, actions in self.q_table.items():
            if not actions:  # Skip empty action sets
                continue
            
            state_str = f"dist={state[0]}, ratio={state[1]}, type={state[2]}"
            best_action = max(actions.items(), key=lambda x: x[1])
            policy[state_str] = {
                "action": best_action[0],
                "q_value": round(best_action[1], 3),
                "all_actions": {k: round(v, 3) for k, v in actions.items()}
            }
        
        with open(filepath, 'w') as f:
            json.dump(policy, f, indent=2)


def train_q_agent_self_play(
    agent: QLearningAgent,
    num_episodes: int = 10000,
    verbose: bool = True
) -> QLearningAgent:
    """
    Train Q-agent through self-play simulations.
    
    Simplified training loop:
    1. Initialize random positions
    2. Agent selects moves
    3. Evaluate outcome (distance change, combat result)
    4. Update Q-values
    
    Args:
        agent: Q-Learning agent to train
        num_episodes: Number of training episodes
        verbose: Print progress
    
    Returns:
        Trained agent
    """
    if verbose:
        print(f"\nTraining Q-Learning agent ({num_episodes:,} episodes)...")
    
    for episode in range(num_episodes):
        # Simulate episode
        distance = random.uniform(12, 48)
        our_models = random.randint(10, 30)
        enemy_models = random.randint(10, 30)
        unit_type = random.choice(["infantry", "cavalry", "artillery"])
        
        # Get state
        state = agent.discretize_state(distance, our_models, enemy_models, unit_type)
        
        # Select action
        action = agent.select_action(state, training=True)
        
        # Simulate outcome
        if action == "forward":
            distance -= 4
        elif action == "march":
            distance -= 8
        elif action == "refuse":
            distance += 2
        elif action.startswith("flank"):
            distance -= 3
        
        # Calculate reward
        # Good: Stay in optimal range (12-24")
        # Bad: Too close (< 8") or too far (> 36")
        if 12 <= distance <= 24:
            reward = 1.0
        elif distance < 8:
            reward = -1.0  # Danger!
        elif distance > 36:
            reward = -0.5  # Too far
        else:
            reward = 0.0
        
        # Add combat simulation reward
        if distance < 12:
            # Combat likely
            if our_models > enemy_models:
                reward += 0.5
            else:
                reward -= 0.5
        
        # Get next state
        next_state = agent.discretize_state(distance, our_models, enemy_models, unit_type)
        
        # Update Q-value
        done = distance < 4 or distance > 72
        agent.update(state, action, reward, next_state, done)
        
        # End episode
        agent.end_episode()
        
        # Progress
        if verbose and (episode + 1) % 1000 == 0:
            stats = agent.get_statistics()
            print(f"  Episode {episode+1:,}: "
                  f"Avg Reward = {stats['avg_reward']:.3f}, "
                  f"Exploration = {stats['exploration_rate']:.3f}, "
                  f"Q-Table Size = {stats['q_table_size']}")
    
    if verbose:
        print(f"\nTraining complete!")
        stats = agent.get_statistics()
        print(f"  Final avg reward: {stats['avg_reward']:.3f}")
        print(f"  Q-table size: {stats['q_table_size']} states learned")
    
    return agent

