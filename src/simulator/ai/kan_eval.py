"""
Kolmogorov-Arnold Network (KAN) for TOW Position Evaluation

Replaces MCTS rollouts with learned evaluation function.
Uses spline-based networks for interpretability and sample efficiency.

Based on: "KAN: Kolmogorov-Arnold Networks" (Liu et al., 2024)
and "KANs in Online RL" (arXiv 2408.04841, 2024)

Key advantages over MLPs:
1. Sample efficient (2x in RL experiments)
2. Interpretable (visualize spline functions)
3. Adaptive (learnable activation functions)
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class KANConfig:
    """Configuration for KAN network"""
    input_features: int = 20
    hidden_layers: List[int] = None
    output_size: int = 1
    spline_order: int = 3  # Cubic splines
    num_knots: int = 10  # Knots per spline
    learning_rate: float = 0.001
    
    def __post_init__(self):
        if self.hidden_layers is None:
            self.hidden_layers = [64, 32]


class KANLayer(nn.Module):
    """
    Single KAN layer with learnable univariate spline functions.
    
    Instead of w*x + b (MLP), uses learnable splines φ(x).
    Output[j] = Σ φ_ij(x_i) where φ are B-splines.
    """
    
    def __init__(
        self,
        in_features: int,
        out_features: int,
        num_knots: int = 10,
        spline_order: int = 3
    ):
        """
        Initialize KAN layer.
        
        Args:
            in_features: Input dimension
            out_features: Output dimension
            num_knots: Number of knots for B-splines
            spline_order: Spline polynomial order (3 = cubic)
        """
        super().__init__()
        
        self.in_features = in_features
        self.out_features = out_features
        self.num_knots = num_knots
        self.spline_order = spline_order
        
        # Learnable spline coefficients
        # Shape: (out_features, in_features, num_knots + spline_order)
        self.spline_coeffs = nn.Parameter(
            torch.randn(out_features, in_features, num_knots + spline_order) * 0.1
        )
        
        # Fixed knot positions (uniform)
        self.register_buffer(
            'knots',
            torch.linspace(-1, 1, num_knots + 2 * spline_order)
        )
    
    def basis_functions(self, x: torch.Tensor) -> torch.Tensor:
        """
        Compute B-spline basis functions.
        
        Args:
            x: Input tensor (batch_size, in_features)
        
        Returns:
            Basis values (batch_size, in_features, num_basis)
        """
        # Clamp input to knot range
        x = torch.clamp(x, -1, 1)
        
        # Expand dims for broadcasting
        x = x.unsqueeze(-1)  # (batch, in_features, 1)
        knots = self.knots.unsqueeze(0).unsqueeze(0)  # (1, 1, num_knots)
        
        # Simplified basis (triangular for speed)
        # Full B-spline would use recursive definition
        num_basis = self.num_knots + self.spline_order
        basis = torch.zeros(x.shape[0], self.in_features, num_basis, device=x.device)
        
        for i in range(num_basis - 1):
            # Triangular basis function
            left = knots[:, :, i]
            center = knots[:, :, i + 1]
            right = knots[:, :, i + 2] if i + 2 < len(self.knots) else knots[:, :, -1]
            
            # Left side of triangle
            mask_left = (x >= left) & (x < center)
            basis[:, :, i] += mask_left.squeeze(-1).float() * (x.squeeze(-1) - left.squeeze(-1)) / (center - left + 1e-8).squeeze(-1)
            
            # Right side of triangle
            mask_right = (x >= center) & (x < right)
            basis[:, :, i] += mask_right.squeeze(-1).float() * (right.squeeze(-1) - x.squeeze(-1)) / (right - center + 1e-8).squeeze(-1)
        
        return basis
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through KAN layer.
        
        Args:
            x: Input (batch_size, in_features)
        
        Returns:
            Output (batch_size, out_features)
        """
        # Normalize input to [-1, 1]
        x_norm = torch.tanh(x)
        
        # Compute basis functions
        basis = self.basis_functions(x_norm)  # (batch, in_features, num_basis)
        
        # Apply spline transformation
        # output[j] = Σ_i (basis_i · coeffs_ji)
        output = torch.zeros(x.shape[0], self.out_features, device=x.device)
        
        for j in range(self.out_features):
            for i in range(self.in_features):
                # Dot product: basis[batch, i, :] · coeffs[j, i, :]
                output[:, j] += torch.sum(basis[:, i, :] * self.spline_coeffs[j, i, :], dim=-1)
        
        return output


class KANNetwork(nn.Module):
    """
    Full KAN network for position evaluation.
    
    Architecture: Input → KAN layers → Output value
    """
    
    def __init__(self, config: KANConfig):
        """
        Initialize KAN network.
        
        Args:
            config: Network configuration
        """
        super().__init__()
        
        self.config = config
        
        # Build layers
        layers = []
        in_dim = config.input_features
        
        for hidden_dim in config.hidden_layers:
            layers.append(KANLayer(
                in_dim,
                hidden_dim,
                num_knots=config.num_knots,
                spline_order=config.spline_order
            ))
            in_dim = hidden_dim
        
        # Output layer
        layers.append(KANLayer(
            in_dim,
            config.output_size,
            num_knots=config.num_knots,
            spline_order=config.spline_order
        ))
        
        self.layers = nn.ModuleList(layers)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Input features (batch_size, input_features)
        
        Returns:
            Position value (batch_size, 1)
        """
        for layer in self.layers:
            x = layer(x)
        
        # Tanh to bound output to [-1, 1]
        return torch.tanh(x)
    
    def get_spline_parameters(self, layer_idx: int, feature_idx: int) -> np.ndarray:
        """
        Extract spline coefficients for visualization.
        
        Args:
            layer_idx: Which layer
            feature_idx: Which input feature
        
        Returns:
            Spline coefficients as numpy array
        """
        layer = self.layers[layer_idx]
        coeffs = layer.spline_coeffs[:, feature_idx, :].detach().cpu().numpy()
        return coeffs


class TOWPositionEncoder:
    """
    Encodes TOW game state into features for KAN.
    
    Features (20 total):
    - Model counts (ours, theirs, ratio)
    - Distance (bins)
    - Combat Resolution potential
    - Leadership difference
    - Special rules presence
    - Terrain effects
    - Formation quality
    - Unit type indicators
    """
    
    @staticmethod
    def encode_state(
        our_models: int,
        enemy_models: int,
        distance: float,
        our_strength: int,
        enemy_strength: int,
        our_leadership: int,
        enemy_leadership: int,
        unit_type: str = "infantry",
        has_flank: bool = False,
        has_cover: bool = False,
        **kwargs
    ) -> np.ndarray:
        """
        Encode game state to feature vector.
        
        Returns:
            Feature vector (20,) normalized to ~[-1, 1]
        """
        features = np.zeros(20, dtype=np.float32)
        
        # Normalize helper
        def norm(val, max_val):
            return np.clip(val / max_val, -1, 1)
        
        # Model features (0-3)
        features[0] = norm(our_models, 50)
        features[1] = norm(enemy_models, 50)
        features[2] = norm(our_models - enemy_models, 50)  # Difference
        features[3] = norm(our_models / max(enemy_models, 1), 2)  # Ratio
        
        # Distance features (4-6)
        features[4] = norm(distance, 72)  # Raw distance
        features[5] = 1.0 if distance < 12 else -1.0  # Close range
        features[6] = 1.0 if 12 <= distance <= 24 else -1.0  # Optimal range
        
        # Combat features (7-11)
        features[7] = norm(our_strength, 150)
        features[8] = norm(enemy_strength, 150)
        features[9] = norm(our_strength - enemy_strength, 150)
        cr_potential = (our_models - enemy_models) + (1 if has_flank else 0)
        features[10] = norm(cr_potential, 10)
        features[11] = norm(our_leadership - enemy_leadership, 5)
        
        # Unit type (12-14, one-hot)
        features[12] = 1.0 if unit_type == "infantry" else 0.0
        features[13] = 1.0 if unit_type == "cavalry" else 0.0
        features[14] = 1.0 if unit_type in ["ranged", "artillery"] else 0.0
        
        # Tactical features (15-17)
        features[15] = 1.0 if has_flank else 0.0
        features[16] = 1.0 if has_cover else 0.0
        features[17] = norm(distance / max(our_models, 1), 3)  # Density
        
        # Threat assessment (18-19)
        features[18] = 1.0 if distance < 8 and enemy_models > our_models else 0.0  # Danger
        features[19] = 1.0 if our_strength > enemy_strength * 1.5 else 0.0  # Winning
        
        return features
    
    @staticmethod
    def feature_names() -> List[str]:
        """Get human-readable feature names"""
        return [
            "our_models", "enemy_models", "model_diff", "model_ratio",
            "distance", "is_close", "is_optimal_range",
            "our_strength", "enemy_strength", "strength_diff", "cr_potential", "ld_diff",
            "is_infantry", "is_cavalry", "is_ranged",
            "has_flank", "has_cover", "density",
            "in_danger", "is_winning"
        ]


class KANEvaluator:
    """
    KAN-based position evaluator for TOW.
    
    Replaces MCTS rollouts with instant learned evaluation.
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        config: Optional[KANConfig] = None
    ):
        """
        Initialize KAN evaluator.
        
        Args:
            model_path: Path to trained model (.pt)
            config: Network config (if training new model)
        """
        self.config = config or KANConfig()
        self.model = KANNetwork(self.config)
        self.encoder = TOWPositionEncoder()
        
        if model_path:
            self.load(model_path)
        
        self.model.eval()
    
    def evaluate(self, state_dict: Dict) -> float:
        """
        Evaluate position value.
        
        Args:
            state_dict: Game state features
        
        Returns:
            Position value in [-1, 1]
        """
        # Encode state
        features = self.encoder.encode_state(**state_dict)
        
        # Convert to tensor
        x = torch.from_numpy(features).unsqueeze(0)  # (1, 20)
        
        # Forward pass
        with torch.no_grad():
            value = self.model(x)
        
        return value.item()
    
    def save(self, filepath: str):
        """Save trained model"""
        torch.save({
            'model_state': self.model.state_dict(),
            'config': self.config
        }, filepath)
    
    def load(self, filepath: str):
        """Load trained model"""
        checkpoint = torch.load(filepath)
        self.config = checkpoint['config']
        self.model = KANNetwork(self.config)
        self.model.load_state_dict(checkpoint['model_state'])
        self.model.eval()

