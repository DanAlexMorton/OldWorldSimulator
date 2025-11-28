#!/usr/bin/env python3
"""
Ensemble AI Demonstration - "Council of War"

Shows how three AI agents vote on decisions:
- MCTS: Deep tactical search
- Utility: Fast heuristics
- Q-Learning: Learned policy

Phase 6.2 deliverable.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.simulator.ai import EnsembleAI, create_ensemble_for_faction


def demo_scenario():
    """Demonstrate ensemble voting"""
    print("""
================================================================================
ENSEMBLE AI - "COUNCIL OF WAR" DEMONSTRATION
================================================================================

Three AI agents vote on movement decisions:

1. MCTS Agent (weight: 0.5)
   - Deep tactical search using rollouts
   - Slow but finds flanking opportunities

2. Utility Agent (weight: 0.3)
   - Fast heuristic scoring
   - Faction-biased (Empire defensive, Orcs aggressive)

3. Q-Learning Agent (weight: 0.2)
   - Learned policy from 10K self-play games
   - Adapts based on experience

================================================================================
""")
    
    # Create ensemble
    ensemble = create_ensemble_for_faction("Empire", mcts_rollouts=30)
    
    # Test scenarios
    scenarios = [
        {
            "name": "Empire Handgunners vs Orc Boyz - Long Range",
            "distance": 30.0,
            "our_models": 20,
            "enemy_models": 30,
            "our_strength": 60,  # 20×S3
            "enemy_strength": 90,  # 30×S3
            "unit_type": "ranged"
        },
        {
            "name": "Empire Knights vs Goblin Archers - Charge Range",
            "distance": 12.0,
            "our_models": 8,
            "enemy_models": 20,
            "our_strength": 32,  # 8×S4 (cavalry)
            "enemy_strength": 60,  # 20×S3
            "unit_type": "cavalry"
        },
        {
            "name": "Empire Spearmen vs Black Orcs - Close Combat",
            "distance": 6.0,
            "our_models": 25,
            "enemy_models": 15,
            "our_strength": 75,  # 25×S3
            "enemy_strength": 60,  # 15×S4
            "unit_type": "infantry"
        }
    ]
    
    # Run scenarios
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'='*80}")
        print(f"SCENARIO {i}: {scenario['name']}")
        print(f"{'='*80}")
        print(f"Distance: {scenario['distance']:.1f}\"")
        print(f"Our Unit: {scenario['our_models']} models, STR {scenario['our_strength']}")
        print(f"Enemy: {scenario['enemy_models']} models, STR {scenario['enemy_strength']}")
        print(f"Type: {scenario['unit_type']}")
        
        # Get ensemble decision
        action, details = ensemble.select_action(
            distance=scenario['distance'],
            our_models=scenario['our_models'],
            enemy_models=scenario['enemy_models'],
            our_strength=scenario['our_strength'],
            enemy_strength=scenario['enemy_strength'],
            unit_type=scenario['unit_type'],
            verbose=True
        )
        
        print(f"\n{'='*80}")
        print(f"FINAL DECISION: {action.upper()}")
        print(f"Voting breakdown:")
        print(f"  MCTS:       {details['mcts_vote']}")
        print(f"  Utility:    {details['utility_vote']}")
        print(f"  Q-Learning: {details['q_vote']}")
        print(f"  Unanimous:  {details['unanimous']}")
        print(f"{'='*80}\n")
    
    # Print overall statistics
    ensemble.print_statistics()
    
    print("""
================================================================================
ANALYSIS
================================================================================

Ensemble AI provides:
1. **Robustness**: Multiple perspectives reduce errors
2. **Speed**: Utility + Q-Learning fast, MCTS only when needed
3. **Adaptability**: Q-Learning improves with experience
4. **Explainability**: Can see which agent influenced decision

Target Performance: 55-65% win rate (Phase 6.1 achieved 48%)

================================================================================
NEXT STEPS (Phase 6.3)
================================================================================

1. Full Tournament Integration
   - Hook ensemble into TurnManager
   - Run 10K Empire Ensemble vs Orc Simple
   - Validate 55%+ win rate

2. KAN Evaluation Network
   - Replace MCTS rollouts with learned value function
   - Kolmogorov-Arnold Networks for interpretability
   - Target: 65%+ win rate, faster than MCTS

3. Full RL Policy (Phase 6.4)
   - PPO/A3C for complete policy learning
   - Self-play on 100K+ games
   - Target: 75%+ win rate

================================================================================
""")


if __name__ == "__main__":
    demo_scenario()

