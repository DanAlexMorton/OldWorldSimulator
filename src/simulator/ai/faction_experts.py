#!/usr/bin/env python3
"""
Faction Expert AI System

Specialized AI agents for each faction, coordinated by a Rule Shark Orchestrator.

Architecture:
                    +-------------------+
                    |   RULE SHARK      |
                    |   ORCHESTRATOR    |
                    | (Rules Validator) |
                    +-------------------+
                            |
            +---------------+---------------+
            |               |               |
    +-------v------+ +------v-------+ +-----v--------+
    | EMPIRE       | | ORC/GOBLIN   | | GENERIC      |
    | EXPERT       | | EXPERT       | | TACTICIAN    |
    | - Gunlines   | | - Waaagh!    | | - Flanking   |
    | - Knights    | | - Mobs       | | - Terrain    |
    | - Combined   | | - Animosity  | | - CR Math    |
    +--------------+ +--------------+ +--------------+
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum


class ExpertType(Enum):
    """Types of expert AI"""
    EMPIRE = "empire"
    ORCS = "orcs"
    GENERIC = "generic"
    RULE_SHARK = "rule_shark"


@dataclass
class TacticalAdvice:
    """Advice from an expert AI"""
    action: str  # "hold", "advance", "march", "flank_left", "flank_right", "charge", "shoot", "refuse"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    expert: ExpertType
    priority: int = 5  # 1 (critical) to 10 (suggestion)


@dataclass
class RuleCheck:
    """Result of a rules validation"""
    is_legal: bool
    rule_reference: str
    explanation: str
    modifier: float = 0.0  # Bonus/penalty from special rules


class EmpireExpert:
    """
    Expert AI for The Empire of Man
    
    Strengths:
    - Combined arms (infantry + cavalry + artillery)
    - Shooting (handguns, crossbows, cannons)
    - State Troop detachments
    - Knights and cavalry charges
    - Magic (Lore of Light, Heavens, Life)
    
    Weaknesses:
    - Average stats (WS3, T3)
    - Relies on synergy
    - Morale can break
    """
    
    def __init__(self):
        self.expert_type = ExpertType.EMPIRE
        
        # Empire tactical knowledge
        self.preferred_tactics = {
            "handgunners": ["shoot", "refuse", "hold"],
            "knights": ["charge", "flank_left", "flank_right"],
            "halberdiers": ["hold", "advance", "flank_left"],
            "greatswords": ["advance", "charge", "hold"],
            "cannon": ["shoot", "hold", "refuse"],
        }
        
        # Optimal ranges for Empire units
        self.optimal_ranges = {
            "handgun": (12, 24),  # 24" range, -1 at long
            "crossbow": (12, 30),
            "cannon": (24, 48),
            "mortar": (12, 48),
        }
    
    def get_advice(
        self,
        unit_name: str,
        unit_type: str,
        distance: float,
        our_models: int,
        enemy_models: int,
        enemy_faction: str,
        has_los: bool = True,
        terrain: str = "open"
    ) -> TacticalAdvice:
        """Get Empire-specific tactical advice"""
        
        # Identify unit role
        is_shooter = any(x in unit_name.lower() for x in ["handgun", "crossbow", "archer", "cannon", "mortar"])
        is_cavalry = any(x in unit_name.lower() for x in ["knight", "pistolier", "outrider"])
        is_elite = any(x in unit_name.lower() for x in ["greatsword", "reiksguard", "demigryph"])
        
        # Empire shooting doctrine: stay at optimal range
        if is_shooter:
            if distance > 24:
                return TacticalAdvice(
                    action="advance",
                    confidence=0.8,
                    reasoning=f"Close to optimal shooting range (current: {distance:.0f}\")",
                    expert=self.expert_type,
                    priority=3
                )
            elif 12 <= distance <= 24:
                return TacticalAdvice(
                    action="shoot" if has_los else "hold",
                    confidence=0.95,
                    reasoning="At optimal range - FIRE!",
                    expert=self.expert_type,
                    priority=2
                )
            elif distance < 12:
                return TacticalAdvice(
                    action="refuse",
                    confidence=0.7,
                    reasoning="Too close! Fall back to shooting range",
                    expert=self.expert_type,
                    priority=3
                )
        
        # Empire cavalry doctrine: setup flanks, devastating charge
        if is_cavalry:
            if distance > 20:
                return TacticalAdvice(
                    action="flank_right",
                    confidence=0.85,
                    reasoning="Position for flank charge - Knights hit hardest on the charge!",
                    expert=self.expert_type,
                    priority=2
                )
            elif 8 <= distance <= 16:
                return TacticalAdvice(
                    action="charge",
                    confidence=0.9,
                    reasoning="CHARGE! Lance bonus + Impact hits!",
                    expert=self.expert_type,
                    priority=1
                )
            elif distance < 8:
                return TacticalAdvice(
                    action="charge",
                    confidence=0.95,
                    reasoning="In charge range - GO!",
                    expert=self.expert_type,
                    priority=1
                )
        
        # Empire infantry doctrine: steady advance with support
        if enemy_models > our_models * 1.3:
            return TacticalAdvice(
                action="hold",
                confidence=0.7,
                reasoning="Outnumbered - hold position, let shooting thin them",
                expert=self.expert_type,
                priority=4
            )
        
        # Default: steady advance
        return TacticalAdvice(
            action="advance",
            confidence=0.6,
            reasoning="Advance steadily, maintain formation",
            expert=self.expert_type,
            priority=5
        )


class OrcExpert:
    """
    Expert AI for Orcs & Goblins
    
    Strengths:
    - High Toughness (T4)
    - Numbers (cheap troops)
    - Choppa bonus (S4 first round)
    - Waaagh! (extra movement)
    - Boar Boyz (fast and tough)
    
    Weaknesses:
    - Low Initiative
    - Animosity (random)
    - Lower Leadership
    """
    
    def __init__(self):
        self.expert_type = ExpertType.ORCS
        
        # Orc tactical knowledge
        self.preferred_tactics = {
            "boyz": ["march", "charge", "advance"],
            "goblins": ["shoot", "flank_left", "refuse"],
            "boar_boyz": ["charge", "march", "flank_right"],
            "black_orcs": ["advance", "charge", "hold"],
            "trolls": ["charge", "advance", "march"],
        }
    
    def get_advice(
        self,
        unit_name: str,
        unit_type: str,
        distance: float,
        our_models: int,
        enemy_models: int,
        enemy_faction: str,
        has_los: bool = True,
        terrain: str = "open"
    ) -> TacticalAdvice:
        """Get Orc-specific tactical advice"""
        
        # Identify unit role
        is_goblin = "goblin" in unit_name.lower()
        is_cavalry = any(x in unit_name.lower() for x in ["boar", "wolf", "spider"])
        is_big = any(x in unit_name.lower() for x in ["troll", "giant", "black orc"])
        
        # Goblin doctrine: sneaky, avoid combat
        if is_goblin:
            if "archer" in unit_name.lower():
                if 12 <= distance <= 24:
                    return TacticalAdvice(
                        action="shoot",
                        confidence=0.8,
                        reasoning="Plink away with arrows, stay out of combat!",
                        expert=self.expert_type,
                        priority=4
                    )
                elif distance < 12:
                    return TacticalAdvice(
                        action="refuse",
                        confidence=0.85,
                        reasoning="Run away! Gobbos don't want to fight!",
                        expert=self.expert_type,
                        priority=2
                    )
            return TacticalAdvice(
                action="flank_left",
                confidence=0.7,
                reasoning="Sneak around for flank attack",
                expert=self.expert_type,
                priority=5
            )
        
        # Orc cavalry doctrine: CHARGE!
        if is_cavalry:
            if distance <= 14:  # Boar movement + charge
                return TacticalAdvice(
                    action="charge",
                    confidence=0.95,
                    reasoning="WAAAGH! Boar Boyz smash!",
                    expert=self.expert_type,
                    priority=1
                )
            else:
                return TacticalAdvice(
                    action="march",
                    confidence=0.85,
                    reasoning="Get stuck in faster!",
                    expert=self.expert_type,
                    priority=2
                )
        
        # Big stuff doctrine: SMASH
        if is_big:
            return TacticalAdvice(
                action="charge" if distance <= 12 else "march",
                confidence=0.9,
                reasoning="Big 'uns go first! SMASH!",
                expert=self.expert_type,
                priority=2
            )
        
        # Standard Orc Boyz doctrine: GET STUCK IN!
        if distance > 16:
            return TacticalAdvice(
                action="march",
                confidence=0.9,
                reasoning="WAAAGH! Get to da fight!",
                expert=self.expert_type,
                priority=2
            )
        elif 8 < distance <= 16:
            return TacticalAdvice(
                action="advance",
                confidence=0.8,
                reasoning="Almost dere! Ready to charge!",
                expert=self.expert_type,
                priority=3
            )
        else:
            return TacticalAdvice(
                action="charge",
                confidence=0.95,
                reasoning="WAAAGH!!! CHARGE!!!",
                expert=self.expert_type,
                priority=1
            )


class GenericTactician:
    """
    Generic tactical expert - faction-agnostic tactics
    
    Focuses on:
    - Combat Resolution math
    - Flanking and positioning
    - Terrain usage
    - Morale/Leadership
    """
    
    def __init__(self):
        self.expert_type = ExpertType.GENERIC
    
    def get_advice(
        self,
        unit_name: str,
        unit_type: str,
        distance: float,
        our_models: int,
        enemy_models: int,
        our_strength: int,
        enemy_strength: int,
        can_flank: bool = False,
        has_cover: bool = False
    ) -> TacticalAdvice:
        """Get generic tactical advice based on game theory"""
        
        # Combat Resolution calculation
        cr_advantage = (our_models - enemy_models) / 10
        strength_advantage = (our_strength - enemy_strength) / 50
        total_advantage = cr_advantage + strength_advantage
        
        # Flanking is always +1 CR - huge value!
        if can_flank:
            return TacticalAdvice(
                action="flank_left",
                confidence=0.85,
                reasoning=f"Flanking gives +1 CR and denies rank bonus! Critical tactical advantage.",
                expert=self.expert_type,
                priority=2
            )
        
        # If we have significant advantage, engage
        if total_advantage > 0.5:
            if distance <= 12:
                return TacticalAdvice(
                    action="charge",
                    confidence=0.8,
                    reasoning=f"We have advantage (CR: {cr_advantage:+.1f}, Str: {strength_advantage:+.1f}). Engage!",
                    expert=self.expert_type,
                    priority=3
                )
            else:
                return TacticalAdvice(
                    action="advance",
                    confidence=0.7,
                    reasoning="We have advantage. Close the distance.",
                    expert=self.expert_type,
                    priority=4
                )
        
        # If disadvantaged, be cautious
        if total_advantage < -0.3:
            if has_cover:
                return TacticalAdvice(
                    action="hold",
                    confidence=0.75,
                    reasoning="Disadvantaged but in cover. Hold position.",
                    expert=self.expert_type,
                    priority=3
                )
            else:
                return TacticalAdvice(
                    action="refuse",
                    confidence=0.6,
                    reasoning="Disadvantaged. Consider repositioning.",
                    expert=self.expert_type,
                    priority=5
                )
        
        # Neutral - default to steady advance
        return TacticalAdvice(
            action="advance",
            confidence=0.5,
            reasoning="Balanced matchup. Steady advance.",
            expert=self.expert_type,
            priority=6
        )


class RuleSharkOrchestrator:
    """
    THE RULE SHARK - Master of Rules, Coordinator of Experts
    
    Responsibilities:
    1. Validate all moves against TOW rules
    2. Check special rule interactions
    3. Weigh expert advice
    4. Make final decision
    5. Exploit rules advantages
    
    Rules Knowledge:
    - Movement rules (march, charge, reform)
    - Combat rules (supporting attacks, CR, break tests)
    - Special rules (Hatred, Fear, Frenzy, Stubborn, etc.)
    - Army-specific rules (Detachments, Animosity, etc.)
    """
    
    def __init__(self):
        self.empire_expert = EmpireExpert()
        self.orc_expert = OrcExpert()
        self.generic_expert = GenericTactician()
        
        # Rule knowledge base
        self.rules = self._load_rules_knowledge()
    
    def _load_rules_knowledge(self) -> Dict:
        """Load comprehensive rules knowledge"""
        return {
            # Movement rules
            "march": {
                "description": "Move 2x M value",
                "restrictions": ["Cannot march within 8\" of enemy", "Cannot march if rallying"],
                "benefit": "Double movement"
            },
            "charge": {
                "description": "Declare charge, 2D6\" + M charge range",
                "bonuses": ["Lance: +2S on charge", "Impact Hits", "Devastating Charge: +1S"],
                "restrictions": ["Must have LOS", "Cannot be fleeing"]
            },
            "reform": {
                "description": "Change formation",
                "cost": "Cannot move after reforming",
                "benefit": "Better formation for combat"
            },
            
            # Combat rules
            "supporting_attacks": {
                "description": "2nd rank fights with 1 attack each",
                "spears": "3rd rank also fights with spears",
                "horde": "4th rank fights if 10+ wide"
            },
            "combat_resolution": {
                "wounds": "+1 per wound caused",
                "ranks": "+1 per rank after first (max +3)",
                "standard": "+1 for standard bearer",
                "flank": "+1 for flank attack, enemy loses rank bonus",
                "rear": "+2 for rear attack, enemy loses rank bonus"
            },
            
            # Special rules effects
            "special_rules": {
                "hatred": {"effect": "Reroll missed hits (first round)", "phase": "combat"},
                "fear": {"effect": "Fear test or WS1", "phase": "combat"},
                "terror": {"effect": "Fear + panic test on charge", "phase": "charge"},
                "frenzy": {"effect": "+1A, must charge if able", "phase": "movement"},
                "stubborn": {"effect": "Use unmodified Ld for break tests", "phase": "combat"},
                "unbreakable": {"effect": "Never flees", "phase": "combat"},
                "killing_blow": {"effect": "6 to wound = instant death", "phase": "combat"},
                "poisoned_attacks": {"effect": "6 to hit = auto-wound", "phase": "combat"},
                "regeneration": {"effect": "4+ save after other saves", "phase": "combat"},
            }
        }
    
    def validate_action(
        self, 
        action: str, 
        unit_state: Any,
        target_state: Optional[Any] = None,
        distance: float = 0
    ) -> RuleCheck:
        """Validate if action is legal under TOW rules"""
        
        # March validation
        if action == "march":
            if distance < 8:
                return RuleCheck(
                    is_legal=False,
                    rule_reference="Movement Rules - March",
                    explanation="Cannot march within 8\" of enemy"
                )
            return RuleCheck(
                is_legal=True,
                rule_reference="Movement Rules - March",
                explanation="March allowed - no enemies within 8\""
            )
        
        # Charge validation
        if action == "charge":
            max_charge = 12 + 6  # Assuming M4 + 2D6 average
            if distance > max_charge:
                return RuleCheck(
                    is_legal=False,
                    rule_reference="Movement Rules - Charge",
                    explanation=f"Target too far ({distance:.0f}\" > {max_charge}\" max charge)"
                )
            return RuleCheck(
                is_legal=True,
                rule_reference="Movement Rules - Charge",
                explanation="Charge range valid",
                modifier=0.1 if distance < 8 else 0  # Easy charge bonus
            )
        
        # Shooting validation
        if action == "shoot":
            return RuleCheck(
                is_legal=True,
                rule_reference="Shooting Rules",
                explanation="Shooting allowed",
                modifier=-0.1 if distance > 24 else 0  # Long range penalty
            )
        
        # All other actions are generally legal
        return RuleCheck(
            is_legal=True,
            rule_reference="Movement Rules",
            explanation=f"{action} is a valid action"
        )
    
    def check_special_rules(
        self,
        our_rules: List[str],
        enemy_rules: List[str]
    ) -> List[Tuple[str, float]]:
        """Check for special rule interactions and bonuses"""
        
        modifiers = []
        
        # Check our advantages
        if "Hatred" in our_rules:
            modifiers.append(("Hatred: Reroll misses round 1", +0.15))
        
        if "Fear" in our_rules and "Immune to Psychology" not in enemy_rules:
            modifiers.append(("Fear: Enemy may be WS1", +0.1))
        
        if "Killing Blow" in our_rules:
            modifiers.append(("Killing Blow: Instant death on 6", +0.1))
        
        if "Stubborn" in our_rules:
            modifiers.append(("Stubborn: Use unmodified Ld", +0.1))
        
        # Check enemy threats
        if "Fear" in enemy_rules and "Immune to Psychology" not in our_rules:
            modifiers.append(("Enemy Fear: We may be WS1", -0.1))
        
        if "Regeneration" in enemy_rules:
            modifiers.append(("Enemy Regeneration: Harder to kill", -0.1))
        
        return modifiers
    
    def orchestrate_decision(
        self,
        faction: str,
        unit_name: str,
        unit_type: str,
        distance: float,
        our_models: int,
        enemy_models: int,
        our_strength: int,
        enemy_strength: int,
        our_rules: List[str] = None,
        enemy_rules: List[str] = None,
        verbose: bool = False
    ) -> Tuple[str, float, str]:
        """
        Orchestrate the final decision using all experts.
        
        Returns: (action, confidence, reasoning)
        """
        our_rules = our_rules or []
        enemy_rules = enemy_rules or []
        
        advice_list: List[TacticalAdvice] = []
        
        # 1. Get faction-specific advice
        if faction.lower() in ["empire", "the empire"]:
            faction_advice = self.empire_expert.get_advice(
                unit_name, unit_type, distance, our_models, enemy_models,
                enemy_faction="unknown"
            )
            advice_list.append(faction_advice)
        elif faction.lower() in ["orcs", "orcs & goblins", "greenskins"]:
            faction_advice = self.orc_expert.get_advice(
                unit_name, unit_type, distance, our_models, enemy_models,
                enemy_faction="unknown"
            )
            advice_list.append(faction_advice)
        
        # 2. Get generic tactical advice
        generic_advice = self.generic_expert.get_advice(
            unit_name, unit_type, distance, our_models, enemy_models,
            our_strength, enemy_strength
        )
        advice_list.append(generic_advice)
        
        # 3. Check special rules
        rule_modifiers = self.check_special_rules(our_rules, enemy_rules)
        
        # 4. Validate all suggestions against rules
        valid_advice = []
        for advice in advice_list:
            rule_check = self.validate_action(advice.action, None, None, distance)
            if rule_check.is_legal:
                # Adjust confidence based on rule modifiers
                adjusted_confidence = advice.confidence + rule_check.modifier
                for rule_name, mod in rule_modifiers:
                    adjusted_confidence += mod
                
                valid_advice.append((advice, adjusted_confidence))
            elif verbose:
                print(f"  [RULE SHARK] Rejected {advice.action}: {rule_check.explanation}")
        
        # 5. Weight and select best action
        if not valid_advice:
            return ("hold", 0.5, "No valid actions - holding position")
        
        # Sort by priority (lower is better) then confidence
        valid_advice.sort(key=lambda x: (x[0].priority, -x[1]))
        
        best_advice, best_confidence = valid_advice[0]
        
        # Build reasoning
        reasoning_parts = [best_advice.reasoning]
        for rule_name, mod in rule_modifiers:
            reasoning_parts.append(f"[{rule_name}]")
        
        full_reasoning = " | ".join(reasoning_parts)
        
        if verbose:
            print(f"\n  [RULE SHARK] Decision Analysis:")
            print(f"  Faction Expert: {faction.upper()}")
            for advice, conf in valid_advice[:3]:
                print(f"    - {advice.action}: {conf:.2f} ({advice.expert.value})")
            print(f"  Special Rules: {[r[0] for r in rule_modifiers]}")
            print(f"  FINAL: {best_advice.action.upper()} ({best_confidence:.2f})")
        
        return (best_advice.action, best_confidence, full_reasoning)


# Convenience function
def create_rule_shark() -> RuleSharkOrchestrator:
    """Create a fully configured Rule Shark orchestrator"""
    return RuleSharkOrchestrator()


if __name__ == "__main__":
    # Demo
    print("""
================================================================================
RULE SHARK ORCHESTRATOR - DEMO
================================================================================
""")
    
    shark = create_rule_shark()
    
    # Test scenarios
    scenarios = [
        {
            "faction": "Empire",
            "unit_name": "Empire Handgunners",
            "unit_type": "infantry",
            "distance": 20.0,
            "our_models": 15,
            "enemy_models": 25,
            "our_strength": 45,
            "enemy_strength": 75,
            "our_rules": [],
            "enemy_rules": []
        },
        {
            "faction": "Empire",
            "unit_name": "Empire Knights",
            "unit_type": "cavalry",
            "distance": 12.0,
            "our_models": 8,
            "enemy_models": 20,
            "our_strength": 24,
            "enemy_strength": 60,
            "our_rules": ["Lance", "Devastating Charge"],
            "enemy_rules": []
        },
        {
            "faction": "Orcs",
            "unit_name": "Orc Boyz",
            "unit_type": "infantry",
            "distance": 18.0,
            "our_models": 25,
            "enemy_models": 15,
            "our_strength": 75,
            "enemy_strength": 45,
            "our_rules": ["Choppa"],
            "enemy_rules": []
        },
        {
            "faction": "Orcs",
            "unit_name": "Goblin Archers",
            "unit_type": "infantry",
            "distance": 8.0,
            "our_models": 20,
            "enemy_models": 20,
            "our_strength": 60,
            "enemy_strength": 60,
            "our_rules": [],
            "enemy_rules": ["Fear"]
        },
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- Scenario {i}: {scenario['faction']} {scenario['unit_name']} ---")
        action, confidence, reasoning = shark.orchestrate_decision(
            verbose=True,
            **scenario
        )
        print(f"\n  >>> ACTION: {action.upper()}")
        print(f"  >>> Confidence: {confidence:.2f}")
        print(f"  >>> Reasoning: {reasoning}")
    
    print("\n" + "="*80)

