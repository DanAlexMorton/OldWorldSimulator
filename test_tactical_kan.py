#!/usr/bin/env python3
"""Test the tactical KAN integration."""

from src.simulator.ai.council_of_war import CouncilOfWar

# Create council
council = CouncilOfWar('player', 'Empire')

print('=== TACTICAL KAN TEST ===')
print(f'Tactical KAN loaded: {council.tactical_kan.loaded if council.tactical_kan else False}')

# Test different unit types
print()
test_cases = [
    ('Great Cannon', 'artillery', 40, True),   # Artillery CAN shoot
    ('Great Cannon close', 'artillery', 10, True),
    ('Handgunners', 'ranged', 20, True),
    ('Handgunners close', 'ranged', 8, True),
    ('Knights', 'cavalry', 12, False),
    ('Halberdiers', 'infantry', 12, False),
    ('Giant', 'monster', 10, False),
    ('General', 'character', 15, False),
]

print(f"{'Unit':20s} {'Dist':>5s} {'Action':12s} {'Conf':>6s}")
print("-" * 50)

for name, unit_type, dist, can_shoot in test_cases:
    decision = council.convene_council(
        unit_name=name,
        unit_type=unit_type,
        distance=dist,
        our_models=20,
        enemy_models=30,
        our_strength=60,
        enemy_strength=90,
        can_shoot=can_shoot,
        verbose=False
    )
    print(f'{name:20s} {dist:5d}" {decision.action:12s} {decision.confidence:.2f}')

print()
print("Expected behavior:")
print("  - Artillery should HOLD/SHOOT (not march)")
print("  - Ranged at 20\" should SHOOT")
print("  - Ranged at 8\" should prefer retreat")
print("  - Cavalry at 12\" should CHARGE")
print("  - Monster should CHARGE")

