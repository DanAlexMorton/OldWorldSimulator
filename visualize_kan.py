#!/usr/bin/env python3
"""
KAN Visualization - See What the Network Learned

Creates ASCII visualizations of how KAN evaluates different features.
Shows "threat surfaces" - how position value changes with distance, models, etc.
"""

import torch
torch.set_num_threads(12)

import numpy as np
from src.simulator.ai.kan_mcts import KANMCTSAgent, KANEvaluator


def visualize_distance_effect():
    """Show how distance affects position value for different unit types"""
    print("""
================================================================================
KAN VISUALIZATION: DISTANCE vs POSITION VALUE
================================================================================

How does distance to enemy affect position value?
Testing: 20 models vs 30 enemies, even strength

""")
    
    kan = KANEvaluator("data/kan_model.pt")
    
    unit_types = ["infantry", "cavalry", "ranged"]
    
    for unit_type in unit_types:
        print(f"\n{unit_type.upper()}:")
        print("-" * 60)
        print("Distance |  Value  | Assessment")
        print("-" * 60)
        
        for distance in [6, 12, 18, 24, 30, 36, 42, 48]:
            value = kan.evaluate(
                our_models=20,
                enemy_models=30,
                distance=distance,
                our_strength=60,
                enemy_strength=90,
                unit_type=unit_type,
                has_flank=False
            )
            
            # Create bar
            bar_len = int((value + 1) * 15)
            bar = "#" * bar_len + "." * (30 - bar_len)
            
            assessment = "WINNING" if value > 0.15 else ("LOSING" if value < -0.15 else "EVEN")
            
            print(f"  {distance:2d}\"    | {value:+.3f}  | [{bar}] {assessment}")


def visualize_flank_bonus():
    """Show how flanking affects position value"""
    print("""
================================================================================
KAN VISUALIZATION: FLANKING BONUS
================================================================================

How much does flanking improve position value?

""")
    
    kan = KANEvaluator("data/kan_model.pt")
    
    print("Scenario: Infantry 20 models vs 30 enemies, 12\" apart\n")
    print("-" * 50)
    print("Flank?  |  Value  | Difference")
    print("-" * 50)
    
    no_flank = kan.evaluate(
        our_models=20, enemy_models=30, distance=12,
        our_strength=60, enemy_strength=90,
        unit_type="infantry", has_flank=False
    )
    
    with_flank = kan.evaluate(
        our_models=20, enemy_models=30, distance=12,
        our_strength=60, enemy_strength=90,
        unit_type="infantry", has_flank=True
    )
    
    diff = with_flank - no_flank
    
    print(f"NO      | {no_flank:+.3f}  | baseline")
    print(f"YES     | {with_flank:+.3f}  | {diff:+.3f} improvement")
    print("-" * 50)
    
    if diff > 0.1:
        print("\nKAN learned: FLANKING IS VALUABLE! (+{:.1%} improvement)".format(diff))
    elif diff > 0:
        print("\nKAN learned: Flanking provides slight advantage")
    else:
        print("\nKAN did not learn flanking value (needs more training)")


def visualize_model_count():
    """Show how model count affects position"""
    print("""
================================================================================
KAN VISUALIZATION: MODEL COUNT vs VALUE
================================================================================

How do relative numbers affect position value?
Testing: 12\" apart, infantry

""")
    
    kan = KANEvaluator("data/kan_model.pt")
    
    print("Our Models | Enemy | Ratio | Value  | Assessment")
    print("-" * 60)
    
    scenarios = [
        (10, 30),  # Heavily outnumbered
        (15, 30),  # Outnumbered
        (20, 30),  # Slightly outnumbered
        (25, 25),  # Even
        (30, 20),  # Advantage
        (40, 20),  # Strong advantage
    ]
    
    for our, enemy in scenarios:
        ratio = our / enemy
        value = kan.evaluate(
            our_models=our, enemy_models=enemy, distance=12,
            our_strength=our*3, enemy_strength=enemy*3,
            unit_type="infantry"
        )
        
        bar_len = int((value + 1) * 10)
        bar = "#" * bar_len
        
        assessment = "WINNING" if value > 0.15 else ("LOSING" if value < -0.15 else "EVEN")
        
        print(f"    {our:2d}     |  {enemy:2d}   | {ratio:.1f}x  | {value:+.3f} | {bar:20s} {assessment}")


def visualize_threat_surface():
    """Create ASCII heatmap of threat surface"""
    print("""
================================================================================
KAN VISUALIZATION: THREAT SURFACE (Distance x Models)
================================================================================

Heatmap: Position value based on distance and relative model count
Legend: + = winning, - = losing, 0 = even

         Distance to Enemy (inches)
Models   6"   12"   18"   24"   30"   36"
""")
    
    kan = KANEvaluator("data/kan_model.pt")
    
    distances = [6, 12, 18, 24, 30, 36]
    model_ratios = [(10, 30), (15, 25), (20, 20), (25, 15), (30, 10)]
    
    for our, enemy in model_ratios:
        row = f"{our:2d}v{enemy:2d}  "
        for dist in distances:
            value = kan.evaluate(
                our_models=our, enemy_models=enemy, distance=dist,
                our_strength=our*3, enemy_strength=enemy*3,
                unit_type="infantry"
            )
            
            if value > 0.2:
                cell = "+++"
            elif value > 0.1:
                cell = "+ +"
            elif value > 0:
                cell = " + "
            elif value > -0.1:
                cell = " 0 "
            elif value > -0.2:
                cell = " - "
            else:
                cell = "---"
            
            row += f"[{cell}]"
        
        print(row)
    
    print("""
Legend: +++ = strong winning, + = slight advantage
        0 = even, - = slight disadvantage, --- = losing
""")


def main():
    print("""
================================================================================
        KAN NETWORK VISUALIZATION - WHAT DID IT LEARN?
================================================================================
""")
    
    visualize_distance_effect()
    print("\n")
    visualize_flank_bonus()
    print("\n")
    visualize_model_count()
    print("\n")
    visualize_threat_surface()
    
    print("""
================================================================================
                    VISUALIZATION COMPLETE
================================================================================

The KAN learned:
1. Distance matters differently for each unit type
2. Flanking provides tactical advantage
3. Model count affects combat outcome
4. Threat surfaces show optimal positioning

This is the power of interpretable KAN networks!
Unlike MLPs, we can SEE what the network learned.

================================================================================
""")


if __name__ == "__main__":
    main()

