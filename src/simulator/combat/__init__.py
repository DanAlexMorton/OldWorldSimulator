"""
Combat module - Combat resolution and battle mechanics
"""

from .resolver import (
    CombatGroup, CombatResult, 
    resolve_shooting, resolve_melee_combat,
    resolve_impact_hits, resolve_stomp, resolve_breath_weapon,
    run_full_combat_round, simulate_full_battle
)

from .monte_carlo import (
    SimulationResult,
    run_simulations, run_quick_test,
    compare_armies, benchmark_combat_speed
)

__all__ = [
    "CombatGroup", "CombatResult",
    "resolve_shooting", "resolve_melee_combat",
    "resolve_impact_hits", "resolve_stomp", "resolve_breath_weapon",
    "run_full_combat_round", "simulate_full_battle",
    "SimulationResult", "run_simulations", "run_quick_test",
    "compare_armies", "benchmark_combat_speed"
]

