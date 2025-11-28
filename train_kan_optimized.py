#!/usr/bin/env python3
"""
OPTIMIZED KAN Training - Uses all 12 CPU cores, vectorized operations

Completes in ~3-5 minutes instead of 30+
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
import time

# USE ALL 12 CPU CORES!
torch.set_num_threads(12)
print(f"Using {torch.get_num_threads()} CPU threads")


class FastKANLayer(nn.Module):
    """Vectorized KAN layer - no Python loops!"""
    
    def __init__(self, in_features, out_features, num_basis=8):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.num_basis = num_basis
        
        # Learnable spline coefficients
        self.coeffs = nn.Parameter(torch.randn(out_features, in_features, num_basis) * 0.1)
        
        # Basis centers (fixed)
        self.register_buffer('centers', torch.linspace(-1, 1, num_basis))
        self.register_buffer('width', torch.tensor(2.0 / num_basis))
    
    def forward(self, x):
        # x: (batch, in_features)
        batch_size = x.shape[0]
        
        # Normalize to [-1, 1]
        x = torch.tanh(x)
        
        # Compute RBF basis (vectorized!)
        # x: (batch, in_features) -> (batch, in_features, 1)
        x_expanded = x.unsqueeze(-1)
        
        # centers: (num_basis,) -> (1, 1, num_basis)
        centers = self.centers.view(1, 1, -1)
        
        # Gaussian RBF basis: (batch, in_features, num_basis)
        basis = torch.exp(-((x_expanded - centers) ** 2) / (self.width ** 2))
        
        # Apply coefficients using einsum (FAST!)
        # basis: (batch, in_features, num_basis)
        # coeffs: (out_features, in_features, num_basis)
        # output: (batch, out_features)
        output = torch.einsum('bin,oin->bo', basis, self.coeffs)
        
        return output


class FastKAN(nn.Module):
    """Fast KAN network for position evaluation"""
    
    def __init__(self, input_dim=20, hidden_dims=[64, 32], output_dim=1):
        super().__init__()
        
        layers = []
        in_dim = input_dim
        
        for hidden_dim in hidden_dims:
            layers.append(FastKANLayer(in_dim, hidden_dim))
            in_dim = hidden_dim
        
        layers.append(FastKANLayer(in_dim, output_dim))
        
        self.layers = nn.ModuleList(layers)
    
    def forward(self, x):
        for layer in self.layers:
            x = layer(x)
        return torch.tanh(x)  # Bound to [-1, 1]


def generate_data(num_samples=100000):
    """Generate training data (fast numpy version)"""
    print(f"\nGenerating {num_samples:,} samples...")
    start = time.time()
    
    # Vectorized generation (FAST!)
    our_models = np.random.randint(5, 41, num_samples)
    enemy_models = np.random.randint(5, 41, num_samples)
    distance = np.random.uniform(4, 60, num_samples)
    our_strength = our_models * np.random.randint(2, 6, num_samples)
    enemy_strength = enemy_models * np.random.randint(2, 6, num_samples)
    our_ld = np.random.randint(6, 10, num_samples)
    enemy_ld = np.random.randint(5, 9, num_samples)
    has_flank = np.random.random(num_samples) < 0.3
    has_cover = np.random.random(num_samples) < 0.2
    unit_types = np.random.choice([0, 1, 2], num_samples)  # inf, cav, ranged
    
    # Build features
    features = np.zeros((num_samples, 20), dtype=np.float32)
    features[:, 0] = our_models / 50
    features[:, 1] = enemy_models / 50
    features[:, 2] = (our_models - enemy_models) / 50
    features[:, 3] = np.clip(our_models / np.maximum(enemy_models, 1), 0, 2) / 2
    features[:, 4] = distance / 72
    features[:, 5] = (distance < 12).astype(float) * 2 - 1
    features[:, 6] = ((distance >= 12) & (distance <= 24)).astype(float) * 2 - 1
    features[:, 7] = our_strength / 150
    features[:, 8] = enemy_strength / 150
    features[:, 9] = (our_strength - enemy_strength) / 150
    features[:, 10] = ((our_models - enemy_models) + has_flank) / 10
    features[:, 11] = (our_ld - enemy_ld) / 5
    features[:, 12] = (unit_types == 0).astype(float)
    features[:, 13] = (unit_types == 1).astype(float)
    features[:, 14] = (unit_types == 2).astype(float)
    features[:, 15] = has_flank.astype(float)
    features[:, 16] = has_cover.astype(float)
    features[:, 17] = distance / np.maximum(our_models, 1) / 3
    features[:, 18] = ((distance < 8) & (enemy_models > our_models)).astype(float)
    features[:, 19] = (our_strength > enemy_strength * 1.5).astype(float)
    
    # Calculate labels (heuristic values)
    str_ratio = our_strength / np.maximum(enemy_strength, 1)
    labels = np.clip((str_ratio - 1.0) * 0.5, -1, 1)
    
    # Distance modifiers for ranged
    ranged_mask = unit_types == 2
    optimal_range = (distance >= 12) & (distance <= 24)
    too_close = distance < 8
    labels[ranged_mask & optimal_range] += 0.2
    labels[ranged_mask & too_close] -= 0.3
    
    # Flank/cover bonuses
    labels[has_flank] += 0.15
    labels[has_cover] += 0.1
    
    labels = np.clip(labels, -1, 1).astype(np.float32)
    
    elapsed = time.time() - start
    print(f"Generated in {elapsed:.1f}s ({num_samples/elapsed:.0f} samples/s)")
    print(f"  Features: {features.shape}, Labels: {labels.shape}")
    print(f"  Label range: [{labels.min():.3f}, {labels.max():.3f}]")
    
    return features, labels


def train(features, labels, epochs=100, batch_size=512):
    """Train with progress every epoch"""
    print(f"\nTraining FastKAN...")
    print(f"  Epochs: {epochs}")
    print(f"  Batch size: {batch_size}")
    print(f"  CPU threads: {torch.get_num_threads()}")
    
    # Create model
    model = FastKAN(input_dim=20, hidden_dims=[64, 32], output_dim=1)
    optimizer = optim.Adam(model.parameters(), lr=0.01)
    criterion = nn.MSELoss()
    
    # Convert to tensors
    X = torch.from_numpy(features)
    y = torch.from_numpy(labels).unsqueeze(1)
    
    # Train/val split
    val_size = int(len(X) * 0.1)
    X_train, X_val = X[val_size:], X[:val_size]
    y_train, y_val = y[val_size:], y[:val_size]
    
    print(f"\n  Train: {len(X_train):,} | Val: {len(X_val):,}\n")
    
    start_time = time.time()
    best_val_loss = float('inf')
    
    for epoch in range(epochs):
        model.train()
        
        # Shuffle
        perm = torch.randperm(len(X_train))
        X_train = X_train[perm]
        y_train = y_train[perm]
        
        epoch_loss = 0
        num_batches = 0
        
        for i in range(0, len(X_train), batch_size):
            batch_X = X_train[i:i+batch_size]
            batch_y = y_train[i:i+batch_size]
            
            optimizer.zero_grad()
            pred = model(batch_X)
            loss = criterion(pred, batch_y)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            num_batches += 1
        
        # Validation
        model.eval()
        with torch.no_grad():
            val_pred = model(X_val)
            val_loss = criterion(val_pred, y_val).item()
        
        # Print EVERY epoch
        train_loss = epoch_loss / num_batches
        elapsed = time.time() - start_time
        eta = (epochs - epoch - 1) * (elapsed / (epoch + 1))
        
        print(f"Epoch {epoch+1:2d}/{epochs}: "
              f"Train={train_loss:.4f} Val={val_loss:.4f} "
              f"[{elapsed:.0f}s elapsed, ~{eta:.0f}s remaining]")
        
        # Save best
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), "data/kan_model_best.pt")
    
    print(f"\nTraining complete in {time.time()-start_time:.1f}s!")
    print(f"Best val loss: {best_val_loss:.4f}")
    
    # Save final
    torch.save({
        'model_state': model.state_dict(),
        'config': {'input_dim': 20, 'hidden_dims': [64, 32]}
    }, "data/kan_model.pt")
    
    return model


def demo(model):
    """Quick demo of evaluations"""
    print("\n" + "="*60)
    print("KAN EVALUATION DEMO")
    print("="*60)
    
    model.eval()
    
    scenarios = [
        ("Empire Gunline (20 vs 30 Orcs, 30\")", 
         [0.4, 0.6, -0.2, 0.33, 0.42, -1, 1, 0.4, 0.6, -0.13, -0.1, 0, 0, 0, 1, 0, 0, 0.5, 0, 0]),
        ("Knights Flanking (8 vs 20 Goblins, 10\")",
         [0.16, 0.4, -0.24, 0.2, 0.14, 1, -1, 0.27, 0.4, -0.09, 0.1, 0.6, 0, 1, 0, 1, 0, 0.4, 0, 0]),
        ("Outnumbered Infantry (15 vs 30, 6\")",
         [0.3, 0.6, -0.3, 0.25, 0.08, 1, -1, 0.3, 0.8, -0.33, -0.15, -0.2, 1, 0, 0, 0, 1, 0.13, 1, 0]),
    ]
    
    for name, features in scenarios:
        x = torch.tensor([features], dtype=torch.float32)
        with torch.no_grad():
            value = model(x).item()
        
        verdict = "WINNING" if value > 0.15 else ("LOSING" if value < -0.15 else "EVEN")
        print(f"\n{name}")
        print(f"  KAN Value: {value:+.3f} -> {verdict}")
    
    print("\n" + "="*60)


def main():
    print("""
================================================================================
OPTIMIZED KAN TRAINING - 12 CPU CORES, VECTORIZED
================================================================================
""")
    
    # Generate data
    features, labels = generate_data(100000)
    
    # Save data
    np.savez("data/kan_training_data.npz", features=features, labels=labels)
    
    # Train
    model = train(features, labels, epochs=100, batch_size=512)
    
    # Demo
    demo(model)
    
    print("""
================================================================================
TRAINING COMPLETE!
================================================================================

Saved:
  - data/kan_model.pt (final model)
  - data/kan_model_best.pt (best checkpoint)
  - data/kan_training_data.npz (training data)

Usage:
  model = FastKAN()
  model.load_state_dict(torch.load("data/kan_model.pt")['model_state'])
  value = model(features_tensor)

================================================================================
""")


if __name__ == "__main__":
    main()

