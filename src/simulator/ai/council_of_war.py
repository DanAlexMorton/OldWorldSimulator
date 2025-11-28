#!/usr/bin/env python3
"""
Council of War - Full Power AI with Trained Models

Uses:
- Tactical KAN (unit-type aware neural network)
- MCTS-style evaluation
- Faction expertise
- Weighted voting

Each player gets their own independent Council.
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum
from pathlib import Path

# Try to import torch for KAN
try:
    import torch
    torch.set_num_threads(4)
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class CouncilMember(Enum):
    """Types of advisors"""
    KAN = "kan"
    MCTS = "mcts"
    FACTION = "faction"


@dataclass
class Vote:
    """Advisor vote"""
    advisor: CouncilMember
    action: str
    score: float
    reason: str


@dataclass
class Decision:
    """Council decision"""
    action: str
    confidence: float
    votes: List[Vote]


# Unit type mapping
UNIT_TYPE_IDS = {
    "artillery": 0,
    "ranged": 1,
    "cavalry": 2,
    "infantry": 3,
    "monster": 4,
    "character": 5
}


class TacticalKAN:
    """
    Tactical KAN that understands unit-type-specific tactics.
    
    Trained on scenarios that reward:
    - Artillery: staying still and shooting
    - Ranged: holding at optimal range
    - Cavalry: flank charges
    - Infantry: combined arms
    - Monsters: aggressive charges
    - Characters: staying with support
    """
    
    def __init__(self, model_path: str = "data/tactical_kan.pt"):
        self.model = None
        self.loaded = False
        
        if not HAS_TORCH:
            return
        
        path = Path(model_path)
        if not path.exists():
            root = Path(__file__).parent.parent.parent.parent
            path = root / model_path
        
        if path.exists():
            try:
                self._load_model(path)
                self.loaded = True
            except Exception as e:
                pass  # Use fallback
    
    def _load_model(self, path: Path):
        """Load the trained tactical KAN model."""
        import torch.nn as nn
        
        class TacticalKANLayer(nn.Module):
            def __init__(self, in_dim, out_dim, num_splines=8):
                super().__init__()
                self.control_points = nn.Parameter(
                    torch.randn(in_dim, out_dim, num_splines) * 0.1
                )
                self.linear = nn.Linear(in_dim, out_dim)
                
            def forward(self, x):
                x_norm = torch.sigmoid(x)
                positions = torch.linspace(0, 1, 8, device=x.device)
                x_expanded = x_norm.unsqueeze(-1)
                distances = (x_expanded - positions) ** 2
                basis = torch.exp(-10 * distances)
                spline_out = torch.einsum('bis,ios->bo', basis, self.control_points)
                return spline_out + self.linear(x)
        
        class TacticalKANNetwork(nn.Module):
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
        
        self.model = TacticalKANNetwork(input_dim=12, hidden_dims=[64, 32], output_dim=1)
        checkpoint = torch.load(path, map_location='cpu', weights_only=False)
        if isinstance(checkpoint, dict) and 'model_state' in checkpoint:
            self.model.load_state_dict(checkpoint['model_state'])
        else:
            self.model.load_state_dict(checkpoint)
        self.model.eval()
    
    def evaluate(
        self,
        unit_type: str,
        distance: float,
        our_models: int,
        enemy_models: int,
        our_strength: int,
        enemy_strength: int,
        in_range: bool = False,
        can_charge: bool = False,
        enemy_flanked: bool = False,
        has_support: bool = False
    ) -> float:
        """Evaluate position using tactical KAN with unit type awareness."""
        if not self.loaded or self.model is None:
            return self._fallback_evaluate(unit_type, distance, in_range, can_charge)
        
        unit_type_id = UNIT_TYPE_IDS.get(unit_type.lower(), 3)
        
        features = torch.zeros(1, 12)
        features[0, 0] = unit_type_id / 5.0
        features[0, 1] = distance / 48.0
        features[0, 2] = our_models / 40.0
        features[0, 3] = enemy_models / 40.0
        features[0, 4] = our_strength / 200.0
        features[0, 5] = enemy_strength / 200.0
        features[0, 6] = 1.0 if in_range else 0.0
        features[0, 7] = 1.0 if can_charge else 0.0
        features[0, 8] = 1.0 if enemy_flanked else 0.0
        features[0, 9] = 1.0 if has_support else 0.0
        features[0, 10] = 0.0
        features[0, 11] = 0.5
        
        with torch.no_grad():
            value = self.model(features).item()
        
        return value
    
    def _fallback_evaluate(
        self,
        unit_type: str,
        distance: float,
        in_range: bool,
        can_charge: bool
    ) -> float:
        """Fallback heuristic if model not loaded."""
        unit_type = unit_type.lower()
        
        if unit_type == "artillery":
            return 0.8 if distance > 20 else 0.3
        elif unit_type == "ranged":
            return 0.9 if in_range and distance > 12 else 0.4
        elif unit_type == "cavalry":
            return 0.95 if can_charge else 0.5
        elif unit_type == "monster":
            return 0.9 if can_charge else 0.5
        elif unit_type == "character":
            return 0.8 if distance > 8 else 0.2
        else:
            return 0.8 if can_charge else 0.5


class CouncilOfWar:
    """
    Full-power AI Council with trained models.
    
    Each council is independent - no shared state.
    Uses TacticalKAN for unit-type-aware decisions.
    """
    
    _tactical_kan: Optional[TacticalKAN] = None
    
    def __init__(self, player_id: str, faction: str, council_id: int = None):
        self.player_id = player_id
        self.faction = faction
        self.council_id = council_id or random.randint(1000, 9999)
        
        if CouncilOfWar._tactical_kan is None:
            CouncilOfWar._tactical_kan = TacticalKAN()
        
        self.tactical_kan = CouncilOfWar._tactical_kan
        self.weights = self._get_weights(faction)
        self.doctrine = self._get_doctrine(faction)
        self.decision_count = 0
    
    def _get_weights(self, faction: str) -> Dict[CouncilMember, float]:
        """Advisor weights tuned per faction."""
        if "empire" in faction.lower():
            return {CouncilMember.KAN: 0.50, CouncilMember.MCTS: 0.25, CouncilMember.FACTION: 0.25}
        elif "orc" in faction.lower():
            return {CouncilMember.KAN: 0.40, CouncilMember.MCTS: 0.20, CouncilMember.FACTION: 0.40}
        return {CouncilMember.KAN: 0.45, CouncilMember.MCTS: 0.25, CouncilMember.FACTION: 0.30}
    
    def _get_doctrine(self, faction: str) -> Dict:
        """Faction tactical doctrine."""
        if "empire" in faction.lower():
            return {"style": "combined_arms", "preferred_range": (12, 24), "aggression": 0.5}
        elif "orc" in faction.lower():
            return {"style": "aggressive", "preferred_range": (0, 8), "aggression": 0.9}
        return {"style": "balanced", "preferred_range": (8, 16), "aggression": 0.6}
    
    def _kan_evaluate_action(
        self,
        action: str,
        unit_type: str,
        distance: float,
        our_models: int,
        enemy_models: int,
        our_strength: int,
        enemy_strength: int,
        can_shoot: bool = False
    ) -> Tuple[float, str]:
        """Use tactical KAN to evaluate an action with unit-type awareness."""
        
        new_distance = distance
        enemy_flanked = False
        
        if action == "march":
            new_distance = max(0, distance - 8)
        elif action == "advance":
            new_distance = max(0, distance - 4)
        elif action == "charge":
            new_distance = 0
        elif action.startswith("flank"):
            new_distance = max(0, distance - 3)
            enemy_flanked = True
        elif action == "refuse":
            new_distance = distance + 2
        
        in_range = new_distance <= 24
        can_charge = new_distance <= 15
        
        value = self.tactical_kan.evaluate(
            unit_type=unit_type,
            distance=new_distance,
            our_models=our_models,
            enemy_models=enemy_models,
            our_strength=our_strength,
            enemy_strength=enemy_strength,
            in_range=in_range,
            can_charge=can_charge,
            enemy_flanked=enemy_flanked,
            has_support=True
        )
        
        reason = f"TacticalKAN({unit_type}): {value:+.2f}"
        return value, reason
    
    def _mcts_evaluate_action(
        self,
        action: str,
        distance: float,
        our_models: int,
        enemy_models: int
    ) -> Tuple[float, str]:
        """MCTS-style tactical evaluation."""
        score = 0.5
        
        if action == "charge" and distance <= 15:
            score = 0.8
        elif action == "march" and distance > 20:
            score = 0.7
        elif action == "advance" and 10 < distance <= 20:
            score = 0.6
        elif action == "hold" and distance <= 24:
            score = 0.6 if our_models > enemy_models else 0.4
        elif action == "shoot":
            score = 0.85 if distance <= 24 else 0.3
        elif action.startswith("flank"):
            score = 0.7 if distance <= 20 else 0.4
        elif action == "refuse":
            score = 0.3
        
        return score, f"MCTS: {score:.2f}"
    
    def _faction_evaluate_action(
        self,
        action: str,
        unit_name: str,
        distance: float,
        can_shoot: bool
    ) -> Tuple[float, str]:
        """Faction-specific tactical evaluation."""
        score = 0.5
        style = self.doctrine["style"]
        aggression = self.doctrine["aggression"]
        
        if style == "combined_arms":
            if can_shoot and action in ["hold", "shoot"]:
                score = 0.9
            elif action == "charge" and distance <= 12:
                score = 0.8
            elif action == "advance":
                score = 0.6
        
        elif style == "aggressive":
            if action == "charge":
                score = 0.9
            elif action == "march":
                score = 0.8
            elif action in ["hold", "shoot"]:
                score = 0.3
        
        else:  # balanced
            if action == "advance":
                score = 0.7
            elif action == "charge" and distance <= 15:
                score = 0.8
        
        return score, f"Faction({style}): {score:.2f}"
    
    def convene_council(
        self,
        unit_name: str,
        unit_type: str,
        distance: float,
        our_models: int,
        enemy_models: int,
        our_strength: int,
        enemy_strength: int,
        can_shoot: bool = False,
        verbose: bool = False
    ) -> Decision:
        """
        Convene council and return best action.
        
        Uses Tactical KAN + MCTS + Faction expertise.
        """
        self.decision_count += 1
        
        actions = ["hold", "advance", "march", "charge"]
        if can_shoot:
            actions.append("shoot")
        
        action_scores: Dict[str, float] = {}
        action_votes: Dict[str, List[Vote]] = {a: [] for a in actions}
        
        for action in actions:
            total_score = 0.0
            
            # Tactical KAN evaluation (unit-type aware)
            kan_score, kan_reason = self._kan_evaluate_action(
                action, unit_type, distance, our_models, enemy_models,
                our_strength, enemy_strength, can_shoot
            )
            kan_weight = self.weights[CouncilMember.KAN]
            total_score += kan_score * kan_weight
            action_votes[action].append(Vote(CouncilMember.KAN, action, kan_score, kan_reason))
            
            # MCTS evaluation
            mcts_score, mcts_reason = self._mcts_evaluate_action(
                action, distance, our_models, enemy_models
            )
            mcts_weight = self.weights[CouncilMember.MCTS]
            total_score += mcts_score * mcts_weight
            action_votes[action].append(Vote(CouncilMember.MCTS, action, mcts_score, mcts_reason))
            
            # Faction evaluation
            faction_score, faction_reason = self._faction_evaluate_action(
                action, unit_name, distance, can_shoot
            )
            faction_weight = self.weights[CouncilMember.FACTION]
            total_score += faction_score * faction_weight
            action_votes[action].append(Vote(CouncilMember.FACTION, action, faction_score, faction_reason))
            
            action_scores[action] = total_score
        
        best_action = max(action_scores.items(), key=lambda x: x[1])
        
        if verbose:
            print(f"\n[Council {self.council_id}] {self.faction} - {unit_name}")
            print(f"  Tactical KAN loaded: {self.tactical_kan.loaded}")
            for action, score in sorted(action_scores.items(), key=lambda x: -x[1])[:3]:
                print(f"  {action:12s}: {score:.3f}")
            print(f"  >> {best_action[0].upper()} ({best_action[1]:.3f})")
        
        return Decision(
            action=best_action[0],
            confidence=best_action[1],
            votes=action_votes[best_action[0]]
        )


def create_independent_councils(faction_a: str, faction_b: str) -> Tuple[CouncilOfWar, CouncilOfWar]:
    """Create two independent councils."""
    council_a = CouncilOfWar("player_a", faction_a, council_id=1)
    council_b = CouncilOfWar("player_b", faction_b, council_id=2)
    return council_a, council_b
