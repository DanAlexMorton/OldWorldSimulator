"""
Monte Carlo battle simulation
Run thousands of simulations to calculate win rates and statistics
"""

import random
from typing import List, Dict, Callable, Optional
from dataclasses import dataclass
import time

from ..models.unit import Unit
from ..models.character import Character
from .resolver import simulate_full_battle, CombatGroup, run_full_combat_round


@dataclass
class SimulationResult:
    """Results from Monte Carlo simulation"""
    total_simulations: int
    army_a_wins: int
    army_b_wins: int
    draws: int
    army_a_win_rate: float
    army_b_win_rate: float
    draw_rate: float
    average_rounds: float
    average_a_survivors: float
    average_b_survivors: float
    execution_time: float
    
    def to_dict(self) -> Dict:
        """Export to dictionary"""
        return {
            "total_simulations": self.total_simulations,
            "results": {
                "army_a_wins": self.army_a_wins,
                "army_b_wins": self.army_b_wins,
                "draws": self.draws
            },
            "win_rates": {
                "army_a": f"{self.army_a_win_rate:.1f}%",
                "army_b": f"{self.army_b_win_rate:.1f}%",
                "draws": f"{self.draw_rate:.1f}%"
            },
            "averages": {
                "rounds": f"{self.average_rounds:.1f}",
                "army_a_survivors": f"{self.average_a_survivors:.1f}",
                "army_b_survivors": f"{self.average_b_survivors:.1f}"
            },
            "execution_time": f"{self.execution_time:.2f}s"
        }


def run_simulations(
    army_a_factory: Callable[[], List[Unit]],
    army_b_factory: Callable[[], List[Unit]],
    num_simulations: int = 10000,
    max_rounds: int = 6,
    seed: Optional[int] = None,
    verbose: bool = False
) -> SimulationResult:
    """
    Run Monte Carlo simulations of battles.
    
    Args:
        army_a_factory: Function that creates Army A units (fresh for each sim)
        army_b_factory: Function that creates Army B units (fresh for each sim)
        num_simulations: Number of simulations to run (default 10000)
        max_rounds: Maximum combat rounds per battle
        seed: Random seed for reproducibility
        verbose: Print progress updates
    
    Returns:
        SimulationResult with statistics
    
    Example:
        >>> def create_empire():
        ...     return [create_unit("Halberdiers", {...}, models=30)]
        >>> def create_orcs():
        ...     return [create_unit("Orc Boyz", {...}, models=25)]
        >>> results = run_simulations(create_empire, create_orcs, 10000)
        >>> print(f"Empire win rate: {results.army_a_win_rate:.1f}%")
    """
    if seed is not None:
        random.seed(seed)
    
    start_time = time.time()
    
    army_a_wins = 0
    army_b_wins = 0
    draws = 0
    
    total_rounds = 0
    total_a_survivors = 0
    total_b_survivors = 0
    
    # Run simulations
    for sim_num in range(num_simulations):
        if verbose and (sim_num + 1) % 1000 == 0:
            print(f"Simulation {sim_num + 1}/{num_simulations}...")
        
        # Create fresh armies
        army_a = army_a_factory()
        army_b = army_b_factory()
        
        # Run battle
        result = simulate_full_battle(army_a, army_b, max_rounds)
        
        # Record results
        if result['winner'] == 'Army A':
            army_a_wins += 1
        elif result['winner'] == 'Army B':
            army_b_wins += 1
        else:
            draws += 1
        
        total_rounds += result['rounds']
        total_a_survivors += result['army_a_survivors']
        total_b_survivors += result['army_b_survivors']
    
    execution_time = time.time() - start_time
    
    # Calculate statistics
    sim_result = SimulationResult(
        total_simulations=num_simulations,
        army_a_wins=army_a_wins,
        army_b_wins=army_b_wins,
        draws=draws,
        army_a_win_rate=(army_a_wins / num_simulations) * 100,
        army_b_win_rate=(army_b_wins / num_simulations) * 100,
        draw_rate=(draws / num_simulations) * 100,
        average_rounds=total_rounds / num_simulations,
        average_a_survivors=total_a_survivors / num_simulations,
        average_b_survivors=total_b_survivors / num_simulations,
        execution_time=execution_time
    )
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"SIMULATION COMPLETE")
        print(f"{'='*60}")
        print(f"Total simulations: {num_simulations}")
        print(f"Execution time: {execution_time:.2f}s")
        print(f"Speed: {num_simulations/execution_time:.0f} battles/second")
        print(f"\nResults:")
        print(f"  Army A wins: {army_a_wins} ({sim_result.army_a_win_rate:.1f}%)")
        print(f"  Army B wins: {army_b_wins} ({sim_result.army_b_win_rate:.1f}%)")
        print(f"  Draws: {draws} ({sim_result.draw_rate:.1f}%)")
        print(f"\nAverages:")
        print(f"  Rounds: {sim_result.average_rounds:.1f}")
        print(f"  Army A survivors: {sim_result.average_a_survivors:.1f}")
        print(f"  Army B survivors: {sim_result.average_b_survivors:.1f}")
        print(f"{'='*60}")
    
    return sim_result


def run_quick_test(
    army_a_factory: Callable[[], List[Unit]],
    army_b_factory: Callable[[], List[Unit]],
    num_tests: int = 100
) -> Dict:
    """
    Quick test run for debugging (100 simulations).
    
    Args:
        army_a_factory: Army A factory
        army_b_factory: Army B factory
        num_tests: Number of tests (default 100)
    
    Returns:
        Dict with quick results
    """
    result = run_simulations(
        army_a_factory,
        army_b_factory,
        num_simulations=num_tests,
        verbose=False
    )
    
    return result.to_dict()


def compare_armies(
    armies: Dict[str, Callable[[], List[Unit]]],
    num_simulations: int = 1000
) -> Dict:
    """
    Round-robin comparison of multiple armies.
    
    Args:
        armies: Dict of {"Army Name": factory_function}
        num_simulations: Simulations per matchup
    
    Returns:
        Dict with tournament results
    
    Example:
        >>> armies = {
        ...     "Empire Halberdiers": create_empire_halberdiers,
        ...     "Orc Boyz": create_orc_boyz,
        ...     "High Elf Spearmen": create_high_elf_spearmen
        ... }
        >>> results = compare_armies(armies, 1000)
    """
    army_names = list(armies.keys())
    matchups = []
    
    # Run all matchups
    for i, army_a_name in enumerate(army_names):
        for army_b_name in army_names[i+1:]:
            print(f"\nMatchup: {army_a_name} vs {army_b_name}")
            
            result = run_simulations(
                armies[army_a_name],
                armies[army_b_name],
                num_simulations=num_simulations,
                verbose=True
            )
            
            matchups.append({
                "army_a": army_a_name,
                "army_b": army_b_name,
                "army_a_wins": result.army_a_wins,
                "army_b_wins": result.army_b_wins,
                "draws": result.draws,
                "army_a_win_rate": result.army_a_win_rate,
                "army_b_win_rate": result.army_b_win_rate
            })
    
    # Calculate overall standings
    standings = {name: {"wins": 0, "losses": 0, "draws": 0} for name in army_names}
    
    for matchup in matchups:
        army_a = matchup["army_a"]
        army_b = matchup["army_b"]
        
        standings[army_a]["wins"] += matchup["army_a_wins"]
        standings[army_a]["losses"] += matchup["army_b_wins"]
        standings[army_a]["draws"] += matchup["draws"]
        
        standings[army_b]["wins"] += matchup["army_b_wins"]
        standings[army_b]["losses"] += matchup["army_a_wins"]
        standings[army_b]["draws"] += matchup["draws"]
    
    # Calculate win rates
    for name in army_names:
        total_battles = standings[name]["wins"] + standings[name]["losses"] + standings[name]["draws"]
        if total_battles > 0:
            standings[name]["win_rate"] = (standings[name]["wins"] / total_battles) * 100
        else:
            standings[name]["win_rate"] = 0.0
    
    return {
        "matchups": matchups,
        "standings": standings,
        "simulations_per_matchup": num_simulations
    }


def benchmark_combat_speed() -> Dict:
    """
    Benchmark combat resolution speed.
    
    Returns:
        Dict with benchmark results
    """
    from ..models.unit import create_unit, TroopType, BaseSize, UnitCategory
    
    print("Running combat benchmark...")
    
    # Create test armies
    def create_test_army():
        profile = {"M": 4, "WS": 4, "BS": 3, "S": 3, "T": 3, "W": 1, "I": 3, "A": 1, "Ld": 7}
        unit = create_unit(
            "Test Unit",
            profile,
            faction="test",
            category=UnitCategory.CORE,
            troop_type=TroopType.INFANTRY,
            base_size=BaseSize.MEDIUM_25,
            max_models=30,
            current_models=30
        )
        return [unit]
    
    # Benchmark different simulation counts
    benchmarks = {}
    
    for count in [100, 1000, 10000]:
        start = time.time()
        result = run_simulations(
            create_test_army,
            create_test_army,
            num_simulations=count,
            verbose=False
        )
        elapsed = time.time() - start
        
        benchmarks[f"{count}_simulations"] = {
            "time": f"{elapsed:.2f}s",
            "battles_per_second": f"{count/elapsed:.0f}"
        }
    
    return benchmarks

