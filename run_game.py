#!/usr/bin/env python3
"""
Warhammer: The Old World Battle Simulator

Usage:
    python run_game.py army_a.json army_b.json           # Run 100 games
    python run_game.py army_a.json army_b.json -n 1000   # Run 1000 games
    python run_game.py army_a.json army_b.json -v        # Verbose single game
"""

import argparse
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.simulator.data import load_army_from_json, ArmyNotFoundError
from src.simulator.game import Battle
from src.simulator.ai.council_of_war import CouncilOfWar
import random


def get_unit_type(unit_name: str, can_shoot: bool) -> str:
    """Determine unit type from name."""
    name_lower = unit_name.lower()
    
    # Artillery
    if any(w in name_lower for w in ["cannon", "mortar", "bolt thrower", 
                                      "doom diver", "rock lobber", "helblaster"]):
        return "artillery"
    
    # Cavalry
    if any(w in name_lower for w in ["knight", "rider", "cavalry", "boar boyz",
                                      "demigryph", "wolf rider"]):
        return "cavalry"
    
    # Monsters
    if any(w in name_lower for w in ["giant", "troll", "dragon", "hydra", 
                                      "arachnarok", "griffon"]):
        return "monster"
    
    # Characters
    if any(w in name_lower for w in ["general", "captain", "lord", "warboss", 
                                      "wizard", "shaman", "priest", "boss"]):
        return "character"
    
    # Ranged
    if can_shoot:
        return "ranged"
    
    return "infantry"


def create_council_ai(faction: str):
    """Create Two-Brain Council AI."""
    council = CouncilOfWar(
        player_id="player",
        faction=faction,
        council_id=random.randint(1000, 9999)
    )
    
    def ai(unit, enemies):
        if not enemies:
            return "hold"
        closest = min(enemies, key=lambda e: unit.distance_to(e))
        
        # Detect unit type
        unit_type = get_unit_type(unit.name, unit.can_shoot)
        
        decision = council.convene_council(
            unit_name=unit.name,
            unit_type=unit_type,
            distance=unit.distance_to(closest),
            our_models=unit.models,
            enemy_models=closest.models,
            our_strength=unit.models * unit.strength,
            enemy_strength=closest.models * closest.strength,
            can_shoot=unit.can_shoot
        )
        return decision.action
    
    return ai


def run_tournament(army_a: dict, army_b: dict, num_games: int):
    """Run tournament with Council AI."""
    faction_a = army_a.get("faction", "Player A")
    faction_b = army_b.get("faction", "Player B")
    
    print(f"""
{'='*60}
{faction_a} vs {faction_b}
Games: {num_games}
{'='*60}
""")
    
    a_wins, b_wins, draws = 0, 0, 0
    start = time.time()
    
    for game in range(1, num_games + 1):
        battle = Battle(army_a, army_b, verbose=False)
        battle.set_ai("player_a", create_council_ai(faction_a))
        battle.set_ai("player_b", create_council_ai(faction_b))
        
        result = battle.run()
        
        if result == "player_a":
            a_wins += 1
        elif result == "player_b":
            b_wins += 1
        else:
            draws += 1
        
        if game % max(1, num_games // 10) == 0:
            elapsed = time.time() - start
            rate = game / elapsed if elapsed > 0 else 0
            print(f"Game {game:4d}: {faction_a} {a_wins} ({100*a_wins/game:.0f}%) | "
                  f"{faction_b} {b_wins} ({100*b_wins/game:.0f}%) | "
                  f"Draw {draws} ({rate:.0f} g/s)")
    
    elapsed = time.time() - start
    
    print(f"""
{'='*60}
RESULTS
{'='*60}
{faction_a}: {a_wins} wins ({100*a_wins/num_games:.1f}%)
{faction_b}: {b_wins} wins ({100*b_wins/num_games:.1f}%)
Draws: {draws} ({100*draws/num_games:.1f}%)
Time: {elapsed:.1f}s ({num_games/elapsed:.0f} games/s)
{'='*60}
""")


def run_single_game(army_a: dict, army_b: dict):
    """Run single verbose game."""
    faction_a = army_a.get("faction", "Player A")
    faction_b = army_b.get("faction", "Player B")
    
    battle = Battle(army_a, army_b, verbose=True)
    battle.set_ai("player_a", create_council_ai(faction_a))
    battle.set_ai("player_b", create_council_ai(faction_b))
    battle.run()


def main():
    parser = argparse.ArgumentParser(
        description="TOW Battle Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_game.py armies/empire.json armies/orcs.json
  python run_game.py armies/empire.json armies/orcs.json -n 1000
  python run_game.py armies/empire.json armies/orcs.json -v
"""
    )
    
    parser.add_argument("army_a", help="Player A army JSON file")
    parser.add_argument("army_b", help="Player B army JSON file")
    parser.add_argument("-n", "--num-games", type=int, default=100, help="Number of games (default: 100)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Run single verbose game")
    
    args = parser.parse_args()
    
    # Load armies
    try:
        army_a = load_army_from_json(args.army_a)
    except ArmyNotFoundError:
        print(f"Error: Army file not found: {args.army_a}")
        sys.exit(1)
    
    try:
        army_b = load_army_from_json(args.army_b)
    except ArmyNotFoundError:
        print(f"Error: Army file not found: {args.army_b}")
        sys.exit(1)
    
    # Run
    if args.verbose:
        run_single_game(army_a, army_b)
    else:
        run_tournament(army_a, army_b, args.num_games)


if __name__ == "__main__":
    main()
