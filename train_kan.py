#!/usr/bin/env python3
"""
Train KAN Evaluation Network

Generates 100K training states from TOW simulations.
Trains KAN to predict position value from board features.

Target: 65% Empire win rate when integrated with MCTS.
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
import time
from pathlib import Path

from src.simulator.ai.kan_eval import KANEvaluator, KANConfig, TOWPositionEncoder


def generate_training_data(num_samples: int = 100000, verbose: bool = True):
    """
    Generate training data from simulated TOW positions.
    
    Args:
        num_samples: Number of samples to generate
        verbose: Print progress
    
    Returns:
        features (num_samples, 20), labels (num_samples,)
    """
    if verbose:
        print(f"\nGenerating {num_samples:,} training samples...")
        print("Simulating TOW battle positions...\n")
    
    encoder = TOWPositionEncoder()
    features = []
    labels = []
    
    start_time = time.time()
    
    for i in range(num_samples):
        # Generate random battle state
        our_models = random.randint(5, 40)
        enemy_models = random.randint(5, 40)
        distance = random.uniform(4, 60)
        our_strength = our_models * random.randint(2, 5)
        enemy_strength = enemy_models * random.randint(2, 5)
        our_ld = random.randint(6, 9)
        enemy_ld = random.randint(5, 8)
        
        unit_type = random.choice(["infantry", "cavalry", "ranged"])
        has_flank = random.random() < 0.3
        has_cover = random.random() < 0.2
        
        # Encode features
        feat = encoder.encode_state(
            our_models=our_models,
            enemy_models=enemy_models,
            distance=distance,
            our_strength=our_strength,
            enemy_strength=enemy_strength,
            our_leadership=our_ld,
            enemy_leadership=enemy_ld,
            unit_type=unit_type,
            has_flank=has_flank,
            has_cover=has_cover
        )
        
        # Simulate outcome (heuristic labels)
        # Positive = good for us, Negative = bad
        
        # Base value from strength ratio
        str_ratio = our_strength / max(enemy_strength, 1)
        value = (str_ratio - 1.0) * 0.5  # -0.5 to +0.5
        
        # Distance modifiers
        if unit_type in ["ranged", "artillery"]:
            # Ranged units prefer 12-24" range
            if 12 <= distance <= 24:
                value += 0.2
            elif distance < 8:
                value -= 0.3  # Too close!
        else:
            # Melee units prefer close range
            if distance < 12:
                value += 0.2
            elif distance > 30:
                value -= 0.2
        
        # Flanking bonus
        if has_flank:
            value += 0.15
        
        # Cover bonus
        if has_cover:
            value += 0.1
        
        # Leadership affects morale
        ld_diff = our_ld - enemy_ld
        value += ld_diff * 0.05
        
        # Model count matters
        if our_models > enemy_models * 1.5:
            value += 0.2
        elif our_models < enemy_models * 0.7:
            value -= 0.2
        
        # Clamp to [-1, 1]
        value = np.clip(value, -1, 1)
        
        features.append(feat)
        labels.append(value)
        
        if verbose and (i + 1) % 10000 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            print(f"  Generated {i+1:,}/{num_samples:,} samples... ({rate:.0f} samples/s)")
    
    features = np.array(features, dtype=np.float32)
    labels = np.array(labels, dtype=np.float32)
    
    if verbose:
        elapsed = time.time() - start_time
        print(f"\nGeneration complete! ({num_samples/elapsed:.0f} samples/s)")
        print(f"  Features shape: {features.shape}")
        print(f"  Labels shape: {labels.shape}")
        print(f"  Label range: [{labels.min():.3f}, {labels.max():.3f}]")
        print(f"  Label mean: {labels.mean():.3f}")
    
    return features, labels


def train_kan_model(
    features: np.ndarray,
    labels: np.ndarray,
    epochs: int = 100,
    batch_size: int = 256,
    learning_rate: float = 0.001,
    verbose: bool = True
):
    """
    Train KAN model.
    
    Args:
        features: Training features (N, 20)
        labels: Training labels (N,)
        epochs: Training epochs
        batch_size: Batch size
        learning_rate: Learning rate
        verbose: Print progress
    
    Returns:
        Trained KANEvaluator
    """
    if verbose:
        print(f"\nTraining KAN model...")
        print(f"  Epochs: {epochs}")
        print(f"  Batch size: {batch_size}")
        print(f"  Learning rate: {learning_rate}")
        print(f"  Samples: {len(features):,}\n")
    
    # Create model
    config = KANConfig(
        input_features=20,
        hidden_layers=[64, 32],
        output_size=1,
        num_knots=10,
        spline_order=3,
        learning_rate=learning_rate
    )
    
    evaluator = KANEvaluator(config=config)
    model = evaluator.model
    model.train()
    
    # Optimizer
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.MSELoss()
    
    # Convert to tensors
    X = torch.from_numpy(features)
    y = torch.from_numpy(labels).unsqueeze(1)
    
    # Split train/val
    val_split = 0.1
    val_size = int(len(X) * val_split)
    indices = torch.randperm(len(X))
    
    X_train = X[indices[val_size:]]
    y_train = y[indices[val_size:]]
    X_val = X[indices[:val_size]]
    y_val = y[indices[:val_size]]
    
    if verbose:
        print(f"Train: {len(X_train):,} | Val: {len(X_val):,}\n")
    
    # Training loop
    best_val_loss = float('inf')
    
    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0
        num_batches = 0
        
        # Shuffle training data
        perm = torch.randperm(len(X_train))
        X_train = X_train[perm]
        y_train = y_train[perm]
        
        # Batch training
        for i in range(0, len(X_train), batch_size):
            batch_X = X_train[i:i+batch_size]
            batch_y = y_train[i:i+batch_size]
            
            # Forward
            optimizer.zero_grad()
            predictions = model(batch_X)
            loss = criterion(predictions, batch_y)
            
            # Backward
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            num_batches += 1
        
        # Validation
        model.eval()
        with torch.no_grad():
            val_predictions = model(X_val)
            val_loss = criterion(val_predictions, y_val)
        
        # Print progress
        if verbose and (epoch + 1) % 10 == 0:
            train_loss = epoch_loss / num_batches
            print(f"Epoch {epoch+1}/{epochs}: "
                  f"Train Loss = {train_loss:.4f}, "
                  f"Val Loss = {val_loss.item():.4f}")
        
        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            evaluator.save("data/kan_model_best.pt")
    
    if verbose:
        print(f"\nTraining complete!")
        print(f"  Best val loss: {best_val_loss:.4f}")
    
    # Load best model
    evaluator.load("data/kan_model_best.pt")
    
    return evaluator


def main():
    """Main training pipeline"""
    print("""
================================================================================
KAN EVALUATION NETWORK TRAINING - WARHAMMER: THE OLD WORLD
================================================================================

Training Kolmogorov-Arnold Network for position evaluation.

Architecture:
  - Input: 20 features (models, distance, strength, tactics)
  - Hidden: [64, 32] KAN layers (spline-based)
  - Output: Position value [-1, 1]

Training:
  - Samples: 100,000
  - Epochs: 100
  - Optimizer: Adam (lr=0.001)
  - Loss: MSE

Target: Replace MCTS rollouts (0.01s) with KAN eval (0.0001s)
Result: 65%+ Empire win rate

================================================================================
""")
    
    # Generate data
    features, labels = generate_training_data(num_samples=100000, verbose=True)
    
    # Save raw data
    np.savez("data/kan_training_data.npz", features=features, labels=labels)
    print("\nSaved training data: data/kan_training_data.npz")
    
    # Train model
    evaluator = train_kan_model(
        features, labels,
        epochs=100,
        batch_size=256,
        learning_rate=0.001,
        verbose=True
    )
    
    # Final save
    evaluator.save("data/kan_model.pt")
    
    print("""
================================================================================
TRAINING COMPLETE
================================================================================

Saved files:
  - data/kan_model.pt (Best model)
  - data/kan_model_best.pt (Checkpoint)
  - data/kan_training_data.npz (Training data)

To use in MCTS:
  >>> from src.simulator.ai.kan_eval import KANEvaluator
  >>> kan = KANEvaluator(model_path="data/kan_model.pt")
  >>> value = kan.evaluate({
  ...     'our_models': 20, 'enemy_models': 30,
  ...     'distance': 24.0, 'our_strength': 60,
  ...     'enemy_strength': 90, ...
  ... })

Next: Integrate with MCTS (reduce rollouts 50 -> 20)
Target: 65% Empire win rate!

================================================================================
""")


if __name__ == "__main__":
    main()

