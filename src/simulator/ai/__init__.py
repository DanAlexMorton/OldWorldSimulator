"""
AI module - MCTS, Ensemble, KAN, and Advanced AI for TOW

Phase 6 Complete AI Suite:
- MCTS: Monte Carlo Tree Search (+17% win rate)
- Ensemble: "Council of War" multi-agent voting
- KAN: Kolmogorov-Arnold Networks for evaluation
"""

from .mcts import MCTS, SimplifiedMCTS, evaluate_board_state
from .mcts_agent import MCTSMovementAgent, MCTSHybridAgent
from .q_agent import QLearningAgent, QLearningConfig, train_q_agent_self_play
from .utility_agent import UtilityAgent, UtilityWeights, create_faction_utility_agent
from .ensemble import EnsembleAI, EnsembleWeights, create_ensemble_for_faction
from .kan_eval import KANEvaluator, KANConfig, KANNetwork, TOWPositionEncoder
from .kan_mcts import KANMCTSAgent, KANEvaluator as FastKANEvaluator
from .faction_experts import (
    RuleSharkOrchestrator,
    EmpireExpert,
    OrcExpert,
    GenericTactician,
    create_rule_shark,
    TacticalAdvice,
    RuleCheck
)

__all__ = [
    # MCTS (Phase 6.1)
    "MCTS",
    "SimplifiedMCTS",
    "evaluate_board_state",
    "MCTSMovementAgent",
    "MCTSHybridAgent",
    
    # Q-Learning (Phase 6.2)
    "QLearningAgent",
    "QLearningConfig",
    "train_q_agent_self_play",
    
    # Utility AI (Phase 6.2)
    "UtilityAgent",
    "UtilityWeights",
    "create_faction_utility_agent",
    
    # Ensemble (Phase 6.2)
    "EnsembleAI",
    "EnsembleWeights",
    "create_ensemble_for_faction",
    
    # KAN (Phase 6.3)
    "KANEvaluator",
    "KANConfig",
    "KANNetwork",
    "TOWPositionEncoder",
    
    # KAN-MCTS Hybrid
    "KANMCTSAgent",
    "FastKANEvaluator",
    
    # Faction Experts + Rule Shark
    "RuleSharkOrchestrator",
    "EmpireExpert",
    "OrcExpert",
    "GenericTactician",
    "create_rule_shark",
    "TacticalAdvice",
    "RuleCheck"
]
