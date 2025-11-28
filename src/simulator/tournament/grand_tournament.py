"""
Grand Tournament system - Run massive Monte Carlo tournaments
"""

import time
from typing import List, Callable, Dict
from dataclasses import dataclass
import json

from ..engine.full_sim import run_full_game_simulations, SimulationStatistics
from ..models.unit import Unit


@dataclass
class TournamentResult:
    """Results from a grand tournament"""
    tournament_name: str
    matchups: List[Dict]
    total_games: int
    total_time: float
    champion: str
    
    def to_dict(self) -> Dict:
        """Export to dictionary"""
        return {
            "tournament": self.tournament_name,
            "total_games": self.total_games,
            "total_time": f"{self.total_time:.1f}s",
            "champion": self.champion,
            "matchups": self.matchups
        }
    
    def to_html(self) -> str:
        """Export tournament report as HTML"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{self.tournament_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #1a1a1a; color: #e0e0e0; }}
        h1 {{ color: #ff6b35; border-bottom: 3px solid #ff6b35; padding-bottom: 10px; }}
        h2 {{ color: #4ecdc4; margin-top: 30px; }}
        .matchup {{ background: #2a2a2a; padding: 20px; margin: 20px 0; border-left: 4px solid #ff6b35; }}
        .winner {{ color: #4ecdc4; font-weight: bold; }}
        .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }}
        .stat-box {{ background: #2a2a2a; padding: 15px; border-radius: 5px; text-align: center; }}
        .stat-value {{ font-size: 32px; color: #ff6b35; font-weight: bold; }}
        .stat-label {{ color: #888; margin-top: 5px; }}
        .champion {{ background: #ff6b35; color: #1a1a1a; padding: 20px; text-align: center; font-size: 24px; font-weight: bold; margin: 30px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>🏆 {self.tournament_name}</h1>
    
    <div class="stats">
        <div class="stat-box">
            <div class="stat-value">{self.total_games:,}</div>
            <div class="stat-label">Total Games</div>
        </div>
        <div class="stat-box">
            <div class="stat-value">{self.total_time:.1f}s</div>
            <div class="stat-label">Runtime</div>
        </div>
        <div class="stat-box">
            <div class="stat-value">{self.total_games/self.total_time:.0f}</div>
            <div class="stat-label">Games/Second</div>
        </div>
    </div>
    
    <div class="champion">
        🏆 CHAMPION: {self.champion} 🏆
    </div>
    
    <h2>Matchup Results</h2>
"""
        
        for matchup in self.matchups:
            html += f"""
    <div class="matchup">
        <h3>{matchup['army_a']} vs {matchup['army_b']}</h3>
        <p><strong>{matchup['games']:,} games played</strong></p>
        <p class="winner">Winner: {matchup['army_a']} ({matchup['army_a_win_rate']:.1f}%)</p>
        <p>Win Rate: {matchup['army_a']} {matchup['army_a_wins']:,} wins | {matchup['army_b']} {matchup['army_b_wins']:,} wins | Draws {matchup['draws']:,}</p>
        <p>Average Game: {matchup['average_turns']:.1f} turns | {matchup['average_game_time']:.2f}s</p>
    </div>
"""
        
        html += """
</body>
</html>
"""
        return html


def run_grand_tournament(
    armies: Dict[str, Callable[[], List[Unit]]],
    games_per_matchup: int = 10000,
    tournament_name: str = "Old World Grand Tournament",
    verbose: bool = True
) -> TournamentResult:
    """
    Run a grand tournament between multiple armies.
    
    Args:
        armies: Dict of {"Army Name": factory_function}
        games_per_matchup: Games to run per matchup
        tournament_name: Tournament name
        verbose: Print progress
    
    Returns:
        TournamentResult
    
    Example:
        >>> armies = {
        ...     "Empire Gunline": create_empire_army,
        ...     "Orc Waaagh!": create_orc_army
        ... }
        >>> result = run_grand_tournament(armies, 10000)
    """
    if verbose:
        print(f"\n{'='*80}")
        print(f"TOURNAMENT: {tournament_name}")
        print(f"{'='*80}")
        print(f"Armies: {', '.join(armies.keys())}")
        print(f"Games per matchup: {games_per_matchup:,}")
        print(f"{'='*80}\n")
    
    start_time = time.time()
    
    matchups = []
    army_names = list(armies.keys())
    total_games = 0
    
    # Run all matchups (round-robin)
    for i, army_a_name in enumerate(army_names):
        for army_b_name in army_names[i+1:]:
            if verbose:
                print(f"\n{'='*80}")
                print(f"MATCHUP: {army_a_name} vs {army_b_name}")
                print(f"{'='*80}")
            
            # Run simulations
            stats = run_full_game_simulations(
                armies[army_a_name],
                armies[army_b_name],
                num_simulations=games_per_matchup,
                max_turns=6,
                verbose=verbose
            )
            
            matchup_data = {
                "army_a": army_a_name,
                "army_b": army_b_name,
                "games": games_per_matchup,
                "army_a_wins": stats.player_a_wins,
                "army_b_wins": stats.player_b_wins,
                "draws": stats.draws,
                "army_a_win_rate": stats.player_a_win_rate,
                "army_b_win_rate": stats.player_b_win_rate,
                "average_turns": stats.average_turns,
                "average_game_time": stats.average_game_time
            }
            
            matchups.append(matchup_data)
            total_games += games_per_matchup
            
            if verbose:
                print(f"\n>> {army_a_name} wins: {stats.player_a_wins:,} ({stats.player_a_win_rate:.1f}%)")
                print(f">> {army_b_name} wins: {stats.player_b_wins:,} ({stats.player_b_win_rate:.1f}%)")
                print(f">> Draws: {stats.draws:,} ({stats.draw_rate:.1f}%)")
    
    elapsed_time = time.time() - start_time
    
    # Determine overall champion (highest total wins)
    army_scores = {name: 0 for name in army_names}
    for matchup in matchups:
        army_scores[matchup["army_a"]] += matchup["army_a_wins"]
        army_scores[matchup["army_b"]] += matchup["army_b_wins"]
    
    champion = max(army_scores, key=army_scores.get)
    
    result = TournamentResult(
        tournament_name=tournament_name,
        matchups=matchups,
        total_games=total_games,
        total_time=elapsed_time,
        champion=champion
    )
    
    if verbose:
        print(f"\n{'='*80}")
        print(f"TOURNAMENT COMPLETE")
        print(f"{'='*80}")
        print(f"Total games: {total_games:,}")
        print(f"Total time: {elapsed_time:.1f}s ({total_games/elapsed_time:.1f} games/s)")
        print(f"\n>>> CHAMPION: {champion} <<<")
        print(f"{'='*80}\n")
    
    return result


def save_tournament_report(result: TournamentResult, output_file: str = "tournament_report.html"):
    """
    Save tournament report as HTML file.
    
    Args:
        result: TournamentResult
        output_file: Output file path
    """
    html = result.to_html()
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f">> Tournament report saved to: {output_file}")


def save_tournament_report_ascii(result: TournamentResult, output_file: str = "tournament_report.txt"):
    """
    Save tournament report as plain text file.
    
    Args:
        result: TournamentResult
        output_file: Output file path
    """
    txt = f"""
================================================================================
{result.tournament_name}
================================================================================

Total Games: {result.total_games:,}
Total Time: {result.total_time:.1f}s
Speed: {result.total_games/result.total_time:.1f} games/second

CHAMPION: {result.champion}

================================================================================
MATCHUP RESULTS
================================================================================

"""
    
    for matchup in result.matchups:
        txt += f"""
{matchup['army_a']} vs {matchup['army_b']}
----------------------------------------
Games: {matchup['games']:,}
Winner: {matchup['army_a']} ({matchup['army_a_win_rate']:.1f}%)
Results:
  - {matchup['army_a']}: {matchup['army_a_wins']:,} wins
  - {matchup['army_b']}: {matchup['army_b_wins']:,} wins
  - Draws: {matchup['draws']:,}
Average: {matchup['average_turns']:.1f} turns, {matchup['average_game_time']:.2f}s/game

"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(txt)
    
    print(f">> Tournament report saved to: {output_file}")


def save_tournament_json(result: TournamentResult, output_file: str = "tournament_result.json"):
    """
    Save tournament result as JSON.
    
    Args:
        result: TournamentResult
        output_file: Output file path
    """
    data = result.to_dict()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print(f">> Tournament data saved to: {output_file}")

