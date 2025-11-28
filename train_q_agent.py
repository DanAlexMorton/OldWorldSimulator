#!/usr/bin/env python3
"""
Train Q-Learning Agent with Self-Play

Trains tabular Q-agent through 10K episodes of simplified TOW scenarios.
Saves trained agent for use in Ensemble AI.
"""

from src.simulator.ai.q_agent import QLearningAgent, QLearningConfig, train_q_agent_self_play


def main():
    """Train and save Q-agent"""
    print("""
================================================================================
Q-LEARNING TRAINING - WARHAMMER: THE OLD WORLD
================================================================================

Training tabular Q-Learning agent through self-play simulations.

Configuration:
  - Episodes: 10,000
  - Learning rate: 0.1
  - Discount factor: 0.95
  - Exploration: 0.2 -> 0.05 (decay)
  
State space:
  - Distance bins: close/near/mid/far/very_far
  - Model ratio: outnumbered/even/outnumber
  - Unit type: infantry/cavalry/artillery

Actions: hold, forward, march, flank_left, flank_right, refuse

================================================================================
""")
    
    # Create agent with config
    config = QLearningConfig(
        learning_rate=0.1,
        discount_factor=0.95,
        exploration_rate=0.2,
        exploration_decay=0.995,
        min_exploration=0.05
    )
    
    agent = QLearningAgent(config)
    
    # Train
    trained_agent = train_q_agent_self_play(
        agent,
        num_episodes=10000,
        verbose=True
    )
    
    # Save
    trained_agent.save("data/q_agent_trained.pkl")
    trained_agent.export_policy("data/q_agent_policy.json")
    
    print("""
================================================================================
TRAINING COMPLETE
================================================================================

Saved files:
  - data/q_agent_trained.pkl (Q-table for loading)
  - data/q_agent_policy.json (Human-readable policy)

To use in Ensemble AI:
  >>> from src.simulator.ai import EnsembleAI
  >>> ensemble = EnsembleAI(pretrained_q_path="data/q_agent_trained.pkl")

================================================================================
""")


if __name__ == "__main__":
    main()

