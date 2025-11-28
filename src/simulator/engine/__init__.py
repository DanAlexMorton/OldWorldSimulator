"""
Game engine module - Full game state and turn management
"""

from .game_state import (
    Position, Terrain, TerrainType,
    Battlefield, GameState, UnitState,
    create_standard_battlefield, deploy_armies_standard
)

from .turn_manager import (
    TurnPhase, TurnManager,
    MovementResult, ChargeResult, MagicResult
)

from .full_sim import (
    FullGameResult, SimulationStatistics,
    simulate_full_game, run_full_game_simulations,
    run_quick_game_test, benchmark_full_game_speed,
    play_single_game_with_log
)

__all__ = [
    "Position", "Terrain", "TerrainType",
    "Battlefield", "GameState", "UnitState",
    "create_standard_battlefield", "deploy_armies_standard",
    "TurnPhase", "TurnManager",
    "MovementResult", "ChargeResult", "MagicResult",
    "FullGameResult", "SimulationStatistics",
    "simulate_full_game", "run_full_game_simulations",
    "run_quick_game_test", "benchmark_full_game_speed",
    "play_single_game_with_log"
]

