"""
Full-game Monte Carlo simulation
Run complete 6-turn games with simple AI
"""

import time
import random
from typing import List, Callable, Dict, Optional
from dataclasses import dataclass

from .game_state import GameState, Battlefield, create_standard_battlefield, deploy_armies_standard
from .turn_manager import TurnManager
from ..models.unit import Unit


@dataclass
class FullGameResult:
    """Result from a complete game"""
    winner: str  # "player_a", "player_b", or "draw"
    turns_played: int
    player_a_points_destroyed: int
    player_b_points_destroyed: int
    player_a_units_remaining: int
    player_b_units_remaining: int
    total_time: float
    
    def to_dict(self) -> Dict:
        """Export to dictionary"""
        return {
            "winner": self.winner,
            "turns": self.turns_played,
            "points_destroyed": {
                "player_a": self.player_a_points_destroyed,
                "player_b": self.player_b_points_destroyed
            },
            "units_remaining": {
                "player_a": self.player_a_units_remaining,
                "player_b": self.player_b_units_remaining
            },
            "time": f"{self.total_time:.3f}s"
        }


@dataclass
class SimulationStatistics:
    """Statistics from multiple game simulations"""
    total_games: int
    player_a_wins: int
    player_b_wins: int
    draws: int
    player_a_win_rate: float
    player_b_win_rate: float
    draw_rate: float
    average_turns: float
    average_game_time: float
    total_time: float
    
    def to_dict(self) -> Dict:
        """Export to dictionary"""
        return {
            "total_games": self.total_games,
            "results": {
                "player_a_wins": self.player_a_wins,
                "player_b_wins": self.player_b_wins,
                "draws": self.draws
            },
            "win_rates": {
                "player_a": f"{self.player_a_win_rate:.1f}%",
                "player_b": f"{self.player_b_win_rate:.1f}%",
                "draws": f"{self.draw_rate:.1f}%"
            },
            "averages": {
                "turns": f"{self.average_turns:.1f}",
                "game_time": f"{self.average_game_time:.2f}s"
            },
            "total_time": f"{self.total_time:.1f}s"
        }


def simulate_full_game(
    army_a: List[Unit],
    army_b: List[Unit],
    max_turns: int = 6,
    verbose: bool = False
) -> FullGameResult:
    """
    Simulate a complete game with simple AI.
    
    Args:
        army_a: Player A's army
        army_b: Player B's army
        max_turns: Maximum turns (default 6)
        verbose: Print game log
    
    Returns:
        FullGameResult with outcome
    """
    start_time = time.time()
    
    # Create game state
    battlefield = create_standard_battlefield()
    game_state = GameState(
        battlefield=battlefield,
        max_turns=max_turns
    )
    
    # Deploy armies
    deploy_armies_standard(game_state, army_a, army_b)
    
    # Create turn manager
    turn_manager = TurnManager(game_state)
    
    # Play game
    turns_played = 0
    for turn in range(1, max_turns + 1):
        if game_state.game_over:
            break
        
        game_state.current_turn = turn
        
        # Player A turn
        if verbose:
            print(f"\n{'='*60}")
            print(f"TURN {turn} - PLAYER A")
            print(f"{'='*60}")
        
        turn_result_a = turn_manager.execute_full_turn("player_a")
        if verbose:
            for log_line in turn_result_a["log"]:
                print(log_line)
        
        if game_state.game_over:
            turns_played = turn
            break
        
        # Player B turn
        if verbose:
            print(f"\n{'='*60}")
            print(f"TURN {turn} - PLAYER B")
            print(f"{'='*60}")
        
        turn_result_b = turn_manager.execute_full_turn("player_b")
        if verbose:
            for log_line in turn_result_b["log"]:
                print(log_line)
        
        turns_played = turn
        
        if game_state.game_over:
            break
    
    # Final victory check
    if not game_state.game_over:
        game_state.check_victory()
    
    elapsed_time = time.time() - start_time
    
    result = FullGameResult(
        winner=game_state.winner or "draw",
        turns_played=turns_played,
        player_a_points_destroyed=game_state.player_a_points_destroyed,
        player_b_points_destroyed=game_state.player_b_points_destroyed,
        player_a_units_remaining=len(game_state.player_a_units),
        player_b_units_remaining=len(game_state.player_b_units),
        total_time=elapsed_time
    )
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"GAME OVER - WINNER: {result.winner.upper()}")
        print(f"Turns: {result.turns_played}")
        print(f"Time: {result.total_time:.2f}s")
        print(f"{'='*60}\n")
    
    return result


def run_full_game_simulations(
    army_a_factory: Callable[[], List[Unit]],
    army_b_factory: Callable[[], List[Unit]],
    num_simulations: int = 1000,
    max_turns: int = 6,
    seed: Optional[int] = None,
    verbose: bool = False
) -> SimulationStatistics:
    """
    Run multiple full-game simulations.
    
    Args:
        army_a_factory: Function that creates Player A's army
        army_b_factory: Function that creates Player B's army
        num_simulations: Number of games to simulate
        max_turns: Maximum turns per game
        seed: Random seed for reproducibility
        verbose: Print progress
    
    Returns:
        SimulationStatistics
    
    Example:
        >>> def create_empire():
        ...     return [create_unit("Halberdiers", {...}, 30)]
        >>> def create_orcs():
        ...     return [create_unit("Orc Boyz", {...}, 25)]
        >>> stats = run_full_game_simulations(create_empire, create_orcs, 100)
        >>> print(f"Empire wins: {stats.player_a_win_rate:.1f}%")
    """
    if seed is not None:
        random.seed(seed)
    
    start_time = time.time()
    
    player_a_wins = 0
    player_b_wins = 0
    draws = 0
    total_turns = 0
    total_game_time = 0.0
    
    if verbose:
        print(f"Running {num_simulations} full-game simulations...")
        print(f"Max turns per game: {max_turns}")
        print(f"{'='*60}\n")
    
    for sim_num in range(num_simulations):
        if verbose and (sim_num + 1) % 10 == 0:
            print(f"Simulation {sim_num + 1}/{num_simulations}...")
        
        # Create fresh armies
        army_a = army_a_factory()
        army_b = army_b_factory()
        
        # Run game
        result = simulate_full_game(army_a, army_b, max_turns=max_turns, verbose=False)
        
        # Record results
        if result.winner == "player_a":
            player_a_wins += 1
        elif result.winner == "player_b":
            player_b_wins += 1
        else:
            draws += 1
        
        total_turns += result.turns_played
        total_game_time += result.total_time
    
    elapsed_time = time.time() - start_time
    
    # Calculate statistics
    stats = SimulationStatistics(
        total_games=num_simulations,
        player_a_wins=player_a_wins,
        player_b_wins=player_b_wins,
        draws=draws,
        player_a_win_rate=(player_a_wins / num_simulations) * 100,
        player_b_win_rate=(player_b_wins / num_simulations) * 100,
        draw_rate=(draws / num_simulations) * 100,
        average_turns=total_turns / num_simulations,
        average_game_time=total_game_time / num_simulations,
        total_time=elapsed_time
    )
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"SIMULATION COMPLETE")
        print(f"{'='*60}")
        print(f"Total games: {num_simulations}")
        print(f"Total time: {elapsed_time:.1f}s")
        print(f"Speed: {num_simulations/elapsed_time:.1f} games/second")
        print(f"\nResults:")
        print(f"  Player A wins: {player_a_wins} ({stats.player_a_win_rate:.1f}%)")
        print(f"  Player B wins: {player_b_wins} ({stats.player_b_win_rate:.1f}%)")
        print(f"  Draws: {draws} ({stats.draw_rate:.1f}%)")
        print(f"\nAverages:")
        print(f"  Turns per game: {stats.average_turns:.1f}")
        print(f"  Time per game: {stats.average_game_time:.2f}s")
        print(f"{'='*60}")
    
    return stats


def run_quick_game_test(
    army_a_factory: Callable[[], List[Unit]],
    army_b_factory: Callable[[], List[Unit]],
    num_games: int = 10
) -> Dict:
    """
    Quick test with 10 games.
    
    Args:
        army_a_factory: Army A factory
        army_b_factory: Army B factory
        num_games: Number of games (default 10)
    
    Returns:
        Dict with results
    """
    stats = run_full_game_simulations(
        army_a_factory,
        army_b_factory,
        num_simulations=num_games,
        verbose=False
    )
    
    return stats.to_dict()


def benchmark_full_game_speed() -> Dict:
    """
    Benchmark full game simulation speed.
    
    Returns:
        Dict with benchmark results
    """
    from ..models.unit import create_unit, TroopType, BaseSize, UnitCategory
    
    print("Benchmarking full-game simulation speed...")
    
    # Create simple test armies
    def create_test_army():
        profile = {"M": 4, "WS": 4, "BS": 3, "S": 3, "T": 3, "W": 1, "I": 3, "A": 1, "Ld": 7}
        unit1 = create_unit(
            "Test Infantry",
            profile,
            faction="test",
            category=UnitCategory.CORE,
            troop_type=TroopType.INFANTRY,
            base_size=BaseSize.MEDIUM_25,
            max_models=20,
            current_models=20
        )
        unit2 = create_unit(
            "Test Archers",
            profile,
            faction="test",
            category=UnitCategory.CORE,
            troop_type=TroopType.INFANTRY,
            base_size=BaseSize.MEDIUM_25,
            max_models=10,
            current_models=10
        )
        return [unit1, unit2]
    
    # Benchmark different game counts
    benchmarks = {}
    
    for count in [10, 100]:
        start = time.time()
        stats = run_full_game_simulations(
            create_test_army,
            create_test_army,
            num_simulations=count,
            verbose=False
        )
        elapsed = time.time() - start
        
        benchmarks[f"{count}_games"] = {
            "time": f"{elapsed:.2f}s",
            "games_per_second": f"{count/elapsed:.1f}",
            "avg_turns": f"{stats.average_turns:.1f}"
        }
        
        print(f"{count} games: {elapsed:.2f}s ({count/elapsed:.1f} games/s)")
    
    return benchmarks


def play_single_game_with_log(
    army_a: List[Unit],
    army_b: List[Unit]
) -> FullGameResult:
    """
    Play a single game with full logging.
    
    Useful for debugging and watching a battle unfold.
    
    Args:
        army_a: Player A's army
        army_b: Player B's army
    
    Returns:
        FullGameResult
    """
    print("\n" + "="*60)
    print("STARTING FULL GAME")
    print("="*60)
    
    print(f"\nPlayer A Army:")
    for unit in army_a:
        print(f"  - {unit.name}: {unit.current_models} models")
    
    print(f"\nPlayer B Army:")
    for unit in army_b:
        print(f"  - {unit.name}: {unit.current_models} models")
    
    result = simulate_full_game(army_a, army_b, verbose=True)
    
    return result

