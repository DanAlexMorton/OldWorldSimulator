#!/usr/bin/env python3
"""
Quick KAN Training - 10K samples, 20 epochs

Fast training for demonstration and testing.
Full training (100K, 100 epochs) available via train_kan.py
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
import time

from src.simulator.ai.kan_eval import KANEvaluator, KANConfig, TOWPositionEncoder


def generate_data_fast(num_samples: int = 10000):
    """Generate training data quickly"""
    print(f"Generating {num_samples:,} samples...")
    
    encoder = TOWPositionEncoder()
    features = []
    labels = []
    
    for i in range(num_samples):
        # Random state
        our_models = random.randint(5, 40)
        enemy_models = random.randint(5, 40)
        distance = random.uniform(4, 60)
        our_strength = our_models * random.randint(2, 5)
        enemy_strength = enemy_models * random.randint(2, 5)
        
        feat = encoder.encode_state(
            our_models=our_models,
            enemy_models=enemy_models,
            distance=distance,
            our_strength=our_strength,
            enemy_strength=enemy_strength,
            our_leadership=random.randint(6, 9),
            enemy_leadership=random.randint(5, 8),
            unit_type=random.choice(["infantry", "cavalry", "ranged"]),
            has_flank=random.random() < 0.3,
            has_cover=random.random() < 0.2
        )
        
        # Heuristic label
        str_ratio = our_strength / max(enemy_strength, 1)
        value = np.clip((str_ratio - 1.0) * 0.5, -1, 1)
        
        features.append(feat)
        labels.append(value)
    
    return np.array(features, dtype=np.float32), np.array(labels, dtype=np.float32)


def train_fast(features, labels, epochs=20):
    """Quick training loop"""
    print(f"Training KAN (20 epochs)...")
    
    config = KANConfig(input_features=20, hidden_layers=[32, 16])
    evaluator = KANEvaluator(config=config)
    model = evaluator.model
    model.train()
    
    optimizer = optim.Adam(model.parameters(), lr=0.01)
    criterion = nn.MSELoss()
    
    X = torch.from_numpy(features)
    y = torch.from_numpy(labels).unsqueeze(1)
    
    for epoch in range(epochs):
        optimizer.zero_grad()
        predictions = model(X)
        loss = criterion(predictions, y)
        loss.backward()
        optimizer.step()
        
        if (epoch + 1) % 5 == 0:
            print(f"  Epoch {epoch+1}/{epochs}: Loss = {loss.item():.4f}")
    
    evaluator.save("data/kan_model_quick.pt")
    return evaluator


def demo_evaluation(evaluator):
    """Demonstrate KAN evaluation"""
    print("\n" + "="*60)
    print("KAN EVALUATION DEMO")
    print("="*60)
    
    scenarios = [
        {"name": "Empire Gunline (20 Handgunners, 30\" from 30 Orcs)",
         "our_models": 20, "enemy_models": 30, "distance": 30.0,
         "our_strength": 60, "enemy_strength": 90,
         "our_leadership": 7, "enemy_leadership": 7,
         "unit_type": "ranged", "has_flank": False, "has_cover": False},
        
        {"name": "Knights Charging (8 Knights, 10\" from 20 Goblins)",
         "our_models": 8, "enemy_models": 20, "distance": 10.0,
         "our_strength": 40, "enemy_strength": 60,
         "our_leadership": 8, "enemy_leadership": 5,
         "unit_type": "cavalry", "has_flank": True, "has_cover": False},
        
        {"name": "Outnumbered Infantry (15 Spears vs 30 Black Orcs, 6\")",
         "our_models": 15, "enemy_models": 30, "distance": 6.0,
         "our_strength": 45, "enemy_strength": 120,
         "our_leadership": 7, "enemy_leadership": 8,
         "unit_type": "infantry", "has_flank": False, "has_cover": True}
    ]
    
    for scenario in scenarios:
        name = scenario.pop("name")
        value = evaluator.evaluate(scenario)
        
        verdict = "WINNING" if value > 0.2 else ("LOSING" if value < -0.2 else "EVEN")
        print(f"\n{name}")
        print(f"  KAN Value: {value:+.3f} -> {verdict}")


def main():
    print("""
================================================================================
QUICK KAN TRAINING - 10K Samples, 20 Epochs
================================================================================
""")
    
    start = time.time()
    
    features, labels = generate_data_fast(10000)
    evaluator = train_fast(features, labels, epochs=20)
    
    elapsed = time.time() - start
    print(f"\nTraining complete in {elapsed:.1f}s")
    print(f"Saved: data/kan_model_quick.pt")
    
    demo_evaluation(evaluator)
    
    print("""
================================================================================
KAN TRAINING COMPLETE
================================================================================

The KAN network is now trained and can evaluate positions instantly.

Usage:
  >>> from src.simulator.ai import KANEvaluator
  >>> kan = KANEvaluator(model_path="data/kan_model_quick.pt")
  >>> value = kan.evaluate({'our_models': 20, ...})

Next: Integrate with MCTS to reduce rollouts (50 -> 20)

================================================================================
""")


if __name__ == "__main__":
    main()

