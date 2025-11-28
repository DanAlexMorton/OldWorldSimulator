#!/usr/bin/env python3
"""
Tactical KAN Training

Trains the KAN neural network to understand unit-type-specific tactics:
- Artillery: Stay still, always shoot
- Ranged: Hold at range, shoot
- Cavalry: Flank and charge
- Infantry: Advance and engage
- Monsters: Charge aggressively
- Characters: Support units
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
import time
from pathlib import Path

# Set threads for CPU
torch.set_num_threads(12)

# Unit type encoding
UNIT_TYPES = {
    "artillery": 0,
    "ranged": 1,
    "cavalry": 2,
    "infantry": 3,
    "monster": 4,
    "character": 5
}


class TacticalKANLayer(nn.Module):
    """KAN layer with B-spline basis functions."""
    
    def __init__(self, in_dim, out_dim, num_splines=8):
        super().__init__()
        self.in_dim = in_dim
        self.out_dim = out_dim
        self.num_splines = num_splines
        
        # Spline control points
        self.control_points = nn.Parameter(
            torch.randn(in_dim, out_dim, num_splines) * 0.1
        )
        
        # Linear combination weights
        self.linear = nn.Linear(in_dim, out_dim)
        
    def forward(self, x):
        batch_size = x.shape[0]
        
        # Normalize input to [0, 1]
        x_norm = torch.sigmoid(x)
        
        # Create spline positions
        positions = torch.linspace(0, 1, self.num_splines, device=x.device)
        
        # Calculate basis function activations (Gaussian-like)
        x_expanded = x_norm.unsqueeze(-1)  # [B, in_dim, 1]
        distances = (x_expanded - positions) ** 2  # [B, in_dim, num_splines]
        basis = torch.exp(-10 * distances)  # [B, in_dim, num_splines]
        
        # Apply spline transformation
        # control_points: [in_dim, out_dim, num_splines]
        # basis: [B, in_dim, num_splines]
        spline_out = torch.einsum('bis,ios->bo', basis, self.control_points)
        
        # Add linear component
        linear_out = self.linear(x)
        
        return spline_out + linear_out


class TacticalKAN(nn.Module):
    """KAN network for tactical decision evaluation."""
    
    def __init__(self, input_dim=12, hidden_dims=[64, 32], output_dim=1):
        super().__init__()
        
        layers = []
        prev_dim = input_dim
        
        for hidden_dim in hidden_dims:
            layers.append(TacticalKANLayer(prev_dim, hidden_dim))
            layers.append(nn.SiLU())
            prev_dim = hidden_dim
        
        layers.append(TacticalKANLayer(prev_dim, output_dim))
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x)


def generate_tactical_scenario():
    """
    Generate a tactical scenario with correct action value.
    
    Returns:
        features: [unit_type, distance, our_models, enemy_models, 
                   our_strength, enemy_strength, in_range, can_charge,
                   enemy_flanked, has_support, terrain_bonus, turn]
        value: Expected outcome value for optimal play
    """
    unit_type = random.choice(list(UNIT_TYPES.keys()))
    unit_type_id = UNIT_TYPES[unit_type]
    
    distance = random.uniform(5, 48)
    our_models = random.randint(5, 40)
    enemy_models = random.randint(5, 40)
    our_strength = our_models * random.randint(3, 5)
    enemy_strength = enemy_models * random.randint(3, 5)
    
    # Tactical features
    in_range = 1.0 if distance <= 24 else 0.0
    can_charge = 1.0 if distance <= 15 else 0.0
    enemy_flanked = random.random() > 0.7
    has_support = random.random() > 0.5
    terrain_bonus = random.random() > 0.6
    turn = random.randint(1, 6)
    
    # Calculate value based on CORRECT tactical play for unit type
    value = 0.0
    
    if unit_type == "artillery":
        # Artillery value = shooting effectiveness
        # Best when: far from enemy, has clear shots
        if distance > 20:  # Safe distance
            value = 0.8 + (0.2 * in_range)  # High value for staying back and shooting
        else:
            value = 0.3  # Bad - too close to enemy
        
    elif unit_type == "ranged":
        # Ranged infantry value = in range but not in combat
        if 12 < distance <= 24:  # Sweet spot - in range but safe
            value = 0.9
        elif distance <= 12:  # Too close!
            value = 0.4
        elif distance > 24:  # Out of range
            value = 0.3 + (0.3 * (24 / distance))  # Value increases as we approach range
    
    elif unit_type == "cavalry":
        # Cavalry value = charge opportunities
        if can_charge and enemy_flanked:
            value = 1.0  # Perfect flank charge!
        elif can_charge:
            value = 0.8  # Good charge
        elif distance <= 20:
            value = 0.6  # In position
        else:
            value = 0.3  # Too far, need to move
    
    elif unit_type == "infantry":
        # Infantry value = solid combat position
        strength_ratio = our_strength / max(1, enemy_strength)
        if can_charge and strength_ratio > 1.0:
            value = 0.85
        elif can_charge:
            value = 0.7
        elif distance <= 20:
            value = 0.5 + (0.2 * has_support)
        else:
            value = 0.3
    
    elif unit_type == "monster":
        # Monsters = terror and destruction
        if can_charge:
            value = 0.95  # Monsters should always charge
        elif distance <= 20:
            value = 0.7
        else:
            value = 0.4
    
    elif unit_type == "character":
        # Characters = support and survival
        if has_support and distance > 8:  # With unit, safe distance
            value = 0.9
        elif has_support:
            value = 0.7
        elif distance <= 8:  # Alone and exposed!
            value = 0.2
        else:
            value = 0.5
    
    # Modifiers
    if terrain_bonus:
        value = min(1.0, value + 0.1)
    
    # Normalize
    value = max(0.0, min(1.0, value))
    
    features = [
        unit_type_id / 5.0,  # Normalized unit type
        distance / 48.0,     # Normalized distance
        our_models / 40.0,
        enemy_models / 40.0,
        our_strength / 200.0,
        enemy_strength / 200.0,
        in_range,
        can_charge,
        float(enemy_flanked),
        float(has_support),
        float(terrain_bonus),
        turn / 6.0
    ]
    
    return features, value


def generate_training_data(num_samples=100000):
    """Generate training dataset."""
    print(f"Generating {num_samples:,} tactical scenarios...")
    
    features = []
    values = []
    
    for _ in range(num_samples):
        f, v = generate_tactical_scenario()
        features.append(f)
        values.append(v)
    
    return np.array(features, dtype=np.float32), np.array(values, dtype=np.float32)


def train_tactical_kan(epochs=100, batch_size=512, lr=0.001):
    """Train the tactical KAN."""
    
    print("="*60)
    print("TACTICAL KAN TRAINING")
    print("="*60)
    print(f"Device: CPU ({torch.get_num_threads()} threads)")
    print(f"Epochs: {epochs}")
    print(f"Batch size: {batch_size}")
    print()
    
    # Generate data
    X_train, y_train = generate_training_data(90000)
    X_val, y_val = generate_training_data(10000)
    
    # Convert to tensors
    X_train = torch.tensor(X_train)
    y_train = torch.tensor(y_train).unsqueeze(1)
    X_val = torch.tensor(X_val)
    y_val = torch.tensor(y_val).unsqueeze(1)
    
    # Create model
    model = TacticalKAN(input_dim=12, hidden_dims=[64, 32], output_dim=1)
    
    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Model parameters: {total_params:,}")
    print()
    
    # Optimizer and loss
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.MSELoss()
    
    # Training loop
    best_val_loss = float('inf')
    start_time = time.time()
    
    print("Training...")
    print("-"*60)
    
    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0
        num_batches = 0
        
        # Shuffle training data
        perm = torch.randperm(len(X_train))
        X_train = X_train[perm]
        y_train = y_train[perm]
        
        for i in range(0, len(X_train), batch_size):
            batch_X = X_train[i:i+batch_size]
            batch_y = y_train[i:i+batch_size]
            
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            num_batches += 1
        
        scheduler.step()
        
        # Validation
        model.eval()
        with torch.no_grad():
            val_outputs = model(X_val)
            val_loss = criterion(val_outputs, y_val).item()
        
        avg_loss = epoch_loss / num_batches
        
        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save({
                'model_state': model.state_dict(),
                'epoch': epoch,
                'val_loss': val_loss,
                'unit_types': UNIT_TYPES
            }, 'data/tactical_kan_best.pt')
        
        # Print progress
        if (epoch + 1) % 10 == 0 or epoch == 0:
            elapsed = time.time() - start_time
            print(f"Epoch {epoch+1:3d}/{epochs} | "
                  f"Train: {avg_loss:.4f} | Val: {val_loss:.4f} | "
                  f"Best: {best_val_loss:.4f} | "
                  f"Time: {elapsed:.0f}s")
    
    # Save final model
    torch.save({
        'model_state': model.state_dict(),
        'epoch': epochs,
        'val_loss': val_loss,
        'unit_types': UNIT_TYPES
    }, 'data/tactical_kan.pt')
    
    elapsed = time.time() - start_time
    
    print("-"*60)
    print(f"Training complete in {elapsed:.1f}s")
    print(f"Best validation loss: {best_val_loss:.4f}")
    print(f"Models saved to data/tactical_kan.pt")
    print()
    
    # Test the model
    print("Testing tactical understanding...")
    print("-"*60)
    
    model.eval()
    test_scenarios = [
        ("Artillery at 40\" range", [0/5, 40/48, 0.5, 0.5, 0.5, 0.5, 0, 0, 0, 0, 0, 0.5]),
        ("Artillery at 10\" range", [0/5, 10/48, 0.5, 0.5, 0.5, 0.5, 1, 0, 0, 0, 0, 0.5]),
        ("Ranged at 20\" (in range)", [1/5, 20/48, 0.5, 0.5, 0.5, 0.5, 1, 0, 0, 0, 0, 0.5]),
        ("Ranged at 8\" (too close)", [1/5, 8/48, 0.5, 0.5, 0.5, 0.5, 1, 1, 0, 0, 0, 0.5]),
        ("Cavalry flanking charge", [2/5, 12/48, 0.5, 0.5, 0.5, 0.5, 1, 1, 1, 0, 0, 0.5]),
        ("Cavalry no flank", [2/5, 12/48, 0.5, 0.5, 0.5, 0.5, 1, 1, 0, 0, 0, 0.5]),
        ("Infantry can charge", [3/5, 12/48, 0.5, 0.5, 0.6, 0.4, 1, 1, 0, 1, 0, 0.5]),
        ("Monster charging", [4/5, 10/48, 0.5, 0.5, 0.5, 0.5, 1, 1, 0, 0, 0, 0.5]),
        ("Character with support", [5/5, 15/48, 0.5, 0.5, 0.5, 0.5, 1, 1, 0, 1, 0, 0.5]),
        ("Character alone", [5/5, 5/48, 0.5, 0.5, 0.5, 0.5, 1, 1, 0, 0, 0, 0.5]),
    ]
    
    with torch.no_grad():
        for name, features in test_scenarios:
            x = torch.tensor([features], dtype=torch.float32)
            value = model(x).item()
            status = "GOOD" if value > 0.6 else "BAD" if value < 0.4 else "OK"
            print(f"  {name:30s} -> {value:.2f} [{status}]")
    
    print()
    print("="*60)
    print("TACTICAL KAN READY!")
    print("="*60)
    
    return model


if __name__ == "__main__":
    train_tactical_kan(epochs=100)

