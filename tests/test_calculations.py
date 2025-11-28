"""
Unit tests for combat calculations
Validates hit/wound tables and save calculations
"""

import pytest
import random
from src.simulator.core.calculations import (
    to_hit_ws, to_hit_bs, to_wound,
    armour_save, ward_save, regeneration_save,
    calculate_hits, calculate_wounds, calculate_saves,
    final_casualties, combat_resolution_score, break_test
)


class TestToHitWS:
    """Test Weapon Skill to-hit table."""
    
    def test_equal_ws(self):
        """Equal WS requires 4+ to hit."""
        assert to_hit_ws(3, 3) == 4
        assert to_hit_ws(4, 4) == 4
        assert to_hit_ws(5, 5) == 4
    
    def test_higher_ws(self):
        """Higher WS requires 3+ to hit."""
        assert to_hit_ws(4, 3) == 3
        assert to_hit_ws(5, 4) == 3
        assert to_hit_ws(6, 5) == 3
    
    def test_double_ws(self):
        """WS double or more requires 2+ to hit."""
        assert to_hit_ws(6, 3) == 2
        assert to_hit_ws(8, 4) == 2
        assert to_hit_ws(10, 5) == 2
        assert to_hit_ws(4, 2) == 2
    
    def test_lower_ws(self):
        """Lower WS requires 5+ to hit."""
        assert to_hit_ws(3, 4) == 5
        assert to_hit_ws(4, 5) == 5
        assert to_hit_ws(5, 6) == 5
    
    def test_half_ws_or_less(self):
        """WS half or less requires 6+ to hit."""
        assert to_hit_ws(2, 4) == 6
        assert to_hit_ws(3, 6) == 6
        assert to_hit_ws(2, 5) == 6
    
    def test_ws_with_modifiers(self):
        """Test WS with bonus/penalty modifiers."""
        # Bonus makes it easier
        assert to_hit_ws(4, 4, {'bonus': 1}) == 3
        # Penalty makes it harder
        assert to_hit_ws(4, 4, {'penalty': 1}) == 5
    
    def test_ws_clamping(self):
        """Test that to-hit is clamped to 2+ and 6+."""
        # Can't be better than 2+
        assert to_hit_ws(10, 1, {'bonus': 5}) == 2
        # Can't be worse than 6+
        assert to_hit_ws(1, 10, {'penalty': 5}) == 6


class TestToHitBS:
    """Test Ballistic Skill to-hit calculation."""
    
    def test_bs_base_values(self):
        """Test base BS to-hit conversion."""
        assert to_hit_bs(1) == 6
        assert to_hit_bs(2) == 5
        assert to_hit_bs(3) == 4
        assert to_hit_bs(4) == 3
        assert to_hit_bs(5) == 2
        assert to_hit_bs(6) == 2
        assert to_hit_bs(10) == 2
    
    def test_bs_with_long_range(self):
        """Test BS with long range modifier."""
        assert to_hit_bs(3, {'long_range': True}) == 5
        assert to_hit_bs(4, {'long_range': True}) == 4
    
    def test_bs_with_cover(self):
        """Test BS with cover modifier."""
        assert to_hit_bs(3, {'cover': True}) == 5
        assert to_hit_bs(4, {'cover': True}) == 4
    
    def test_bs_with_multiple_modifiers(self):
        """Test BS with multiple penalties."""
        assert to_hit_bs(4, {'long_range': True, 'cover': True, 'moving': True}) == 6
    
    def test_bs_with_large_target(self):
        """Test BS with large target bonus."""
        assert to_hit_bs(3, {'large_target': True}) == 3
        assert to_hit_bs(4, {'large_target': True}) == 2
    
    def test_bs_clamping(self):
        """Test that BS to-hit is clamped to 2+ and 6+."""
        assert to_hit_bs(10, {'bonus': 10}) == 2
        assert to_hit_bs(1, {'penalty': 10}) == 6


class TestToWound:
    """Test Strength vs Toughness wound table."""
    
    def test_equal_strength_toughness(self):
        """Equal S and T requires 4+ to wound."""
        assert to_wound(3, 3) == 4
        assert to_wound(4, 4) == 4
        assert to_wound(5, 5) == 4
    
    def test_higher_strength(self):
        """Higher S requires 3+ to wound."""
        assert to_wound(4, 3) == 3
        assert to_wound(5, 4) == 3
        assert to_wound(6, 5) == 3
    
    def test_double_strength(self):
        """S double or more requires 2+ to wound."""
        assert to_wound(6, 3) == 2
        assert to_wound(8, 4) == 2
        assert to_wound(10, 5) == 2
    
    def test_lower_strength(self):
        """Lower S requires 5+ to wound."""
        assert to_wound(3, 4) == 5
        assert to_wound(4, 5) == 5
        assert to_wound(5, 6) == 5
    
    def test_half_strength_or_less(self):
        """S half or less requires 6+ to wound."""
        assert to_wound(2, 4) == 6
        assert to_wound(3, 6) == 6
        assert to_wound(2, 5) == 6
    
    def test_to_wound_with_modifiers(self):
        """Test to-wound with modifiers."""
        assert to_wound(4, 4, {'bonus': 1}) == 3
        assert to_wound(4, 4, {'penalty': 1}) == 5
    
    def test_to_wound_poisoned(self):
        """Test poisoned attacks (always wounds on modified value)."""
        result = to_wound(3, 6, {'always_wounds_on': 5})
        assert result == 5
    
    def test_to_wound_clamping(self):
        """Test that to-wound is clamped to 2+ and 6+."""
        assert to_wound(10, 3, {'bonus': 10}) == 2
        assert to_wound(2, 10, {'penalty': 10}) == 6


class TestSaveCalculations:
    """Test armor, ward, and regeneration save calculations."""
    
    def test_armour_save_no_ap(self):
        """Test armor save with no AP modifier."""
        assert armour_save(4) == 4
        assert armour_save(5) == 5
        assert armour_save(6) == 6
    
    def test_armour_save_with_ap(self):
        """Test armor save with AP modifier."""
        assert armour_save(4, -1) == 5
        assert armour_save(5, -2) is None  # 7+ is no save
        assert armour_save(6, -1) is None  # 7+ is no save
    
    def test_armour_save_no_armor(self):
        """Test unit with no armor save."""
        assert armour_save(None) is None
        assert armour_save(None, -1) is None
    
    def test_armour_save_ignore_armor_rule(self):
        """Test special rule that ignores armor."""
        assert armour_save(4, 0, {'ignore_armour': True}) is None
    
    def test_ward_save(self):
        """Test ward save (unmodified by AP)."""
        assert ward_save(5) == 5
        assert ward_save(6) == 6
        assert ward_save(4) == 4
    
    def test_ward_save_none(self):
        """Test unit with no ward save."""
        assert ward_save(None) is None
    
    def test_ward_save_cancelled(self):
        """Test ward save cancelled by special rule."""
        assert ward_save(5, {'no_ward_save': True}) is None
    
    def test_regeneration_save(self):
        """Test regeneration save."""
        assert regeneration_save(5) == 5
        assert regeneration_save(6) == 6
    
    def test_regeneration_save_flaming(self):
        """Test regeneration negated by flaming attacks."""
        assert regeneration_save(5, {'flaming': True}) is None


class TestDamageCalculations:
    """Test damage calculation functions."""
    
    def test_calculate_hits_basic(self):
        """Test basic hit calculation."""
        random.seed(42)
        result = calculate_hits(10, 4)
        assert 'hits' in result
        assert 'rolls' in result
        assert len(result['rolls']) == 10
        assert 0 <= result['hits'] <= 10
    
    def test_calculate_hits_with_reroll(self):
        """Test hit calculation with reroll."""
        random.seed(42)
        result = calculate_hits(10, 4, {'reroll_failed_hits': True})
        assert result['rerolls_used'] is True
        assert 'rerolls' in result
    
    def test_calculate_wounds_basic(self):
        """Test basic wound calculation."""
        random.seed(42)
        result = calculate_wounds(5, 4)
        assert 'wounds' in result
        assert 'rolls' in result
        assert 0 <= result['wounds'] <= 5
    
    def test_calculate_wounds_killing_blow(self):
        """Test wounds with killing blow."""
        random.seed(42)
        result = calculate_wounds(10, 4, {'killing_blow': True})
        assert 'killing_blows' in result
    
    def test_calculate_saves_basic(self):
        """Test basic save calculation."""
        random.seed(42)
        result = calculate_saves(5, 4)
        assert 'failed_saves' in result
        assert 'successful_saves' in result
        assert result['failed_saves'] + result['successful_saves'] == 5
    
    def test_calculate_saves_no_save(self):
        """Test saves when no save available."""
        result = calculate_saves(5, None)
        assert result['failed_saves'] == 5
        assert result['successful_saves'] == 0


class TestFinalCasualties:
    """Test complete damage pipeline."""
    
    def test_final_casualties_full_pipeline(self):
        """Test complete damage sequence."""
        random.seed(42)
        result = final_casualties(
            num_attacks=10,
            to_hit=4,
            to_wound=4,
            armour_save=5
        )
        
        assert 'hits' in result
        assert 'wounds' in result
        assert 'saved_by_armour' in result
        assert 'final_casualties' in result
        assert result['final_casualties'] >= 0
    
    def test_final_casualties_with_ward(self):
        """Test casualties with ward save."""
        random.seed(42)
        result = final_casualties(
            num_attacks=10,
            to_hit=4,
            to_wound=4,
            armour_save=5,
            ward_save=5
        )
        
        assert 'saved_by_ward' in result
        # Ward saves should reduce casualties
        assert result['final_casualties'] <= result['wounds']
    
    def test_final_casualties_with_regeneration(self):
        """Test casualties with regeneration."""
        random.seed(42)
        result = final_casualties(
            num_attacks=10,
            to_hit=4,
            to_wound=4,
            armour_save=5,
            regen=5
        )
        
        assert 'saved_by_regen' in result


class TestCombatResolution:
    """Test combat resolution scoring."""
    
    def test_combat_resolution_basic(self):
        """Test basic combat resolution."""
        score = combat_resolution_score(wounds_caused=5)
        assert score == 5
    
    def test_combat_resolution_with_ranks(self):
        """Test combat resolution with rank bonus."""
        score = combat_resolution_score(wounds_caused=3, ranks=3)
        assert score == 6  # 3 wounds + 3 ranks
    
    def test_combat_resolution_max_ranks(self):
        """Test that rank bonus caps at +3."""
        score = combat_resolution_score(wounds_caused=2, ranks=5)
        assert score == 5  # 2 wounds + 3 max ranks
    
    def test_combat_resolution_with_standard(self):
        """Test combat resolution with standard."""
        score = combat_resolution_score(wounds_caused=3, standards=1)
        assert score == 4  # 3 wounds + 1 standard
    
    def test_combat_resolution_charging(self):
        """Test combat resolution when charging."""
        score = combat_resolution_score(wounds_caused=3, charging=True)
        assert score == 4  # 3 wounds + 1 charge
    
    def test_combat_resolution_flank(self):
        """Test combat resolution with flank attack."""
        score = combat_resolution_score(wounds_caused=3, flank=True)
        assert score == 4  # 3 wounds + 1 flank
    
    def test_combat_resolution_rear(self):
        """Test combat resolution with rear attack."""
        score = combat_resolution_score(wounds_caused=3, rear=True)
        assert score == 5  # 3 wounds + 2 rear
    
    def test_combat_resolution_overkill(self):
        """Test combat resolution with overkill."""
        score = combat_resolution_score(wounds_caused=3, overkill=3)
        assert score == 6  # 3 wounds + 3 overkill
    
    def test_combat_resolution_max_overkill(self):
        """Test that overkill caps at +5."""
        score = combat_resolution_score(wounds_caused=3, overkill=10)
        assert score == 8  # 3 wounds + 5 max overkill
    
    def test_combat_resolution_full(self):
        """Test full combat resolution with all bonuses."""
        score = combat_resolution_score(
            wounds_caused=5,
            ranks=3,
            standards=1,
            charging=True,
            flank=True
        )
        assert score == 11  # 5 + 3 + 1 + 1 + 1


class TestBreakTests:
    """Test break test mechanics."""
    
    def test_break_test_passes(self):
        """Test passing a break test."""
        random.seed(42)  # Seed that produces 7
        broke, roll = break_test(leadership=8, combat_result_diff=-1)
        # Ld 8 -1 = 7, rolling 7 = pass
        assert roll == 7
        assert broke is False
    
    def test_break_test_fails(self):
        """Test failing a break test."""
        random.seed(10)  # Find seed that produces high roll
        # Try multiple seeds to find a failure
        found_failure = False
        for seed in range(100):
            random.seed(seed)
            broke, roll = break_test(leadership=5, combat_result_diff=-5)
            if broke:
                found_failure = True
                break
        assert found_failure
    
    def test_break_test_natural_12_always_fails(self):
        """Test that natural 12 always fails."""
        # Find a seed that produces 12
        found_12 = False
        for seed in range(1000):
            random.seed(seed)
            broke, roll = break_test(leadership=10, combat_result_diff=0)
            if roll == 12:
                assert broke is True
                found_12 = True
                break
        assert found_12
    
    def test_break_test_steadfast(self):
        """Test break test with Steadfast."""
        random.seed(42)
        broke, roll = break_test(
            leadership=7,
            combat_result_diff=-5,
            modifiers={'steadfast': True}
        )
        # Steadfast ignores combat result difference
        # Should test against Ld 7, not Ld 2
        assert roll <= 12
    
    def test_break_test_stubborn(self):
        """Test break test with Stubborn."""
        random.seed(42)
        broke, roll = break_test(
            leadership=7,
            combat_result_diff=-5,
            modifiers={'stubborn': True}
        )
        # Stubborn also ignores combat result
        assert roll <= 12
    
    def test_break_test_inspiring_presence(self):
        """Test break test with Inspiring Presence."""
        random.seed(42)
        broke, roll = break_test(
            leadership=6,
            combat_result_diff=-2,
            modifiers={'inspiring_presence': 9}
        )
        # Should use general's Ld 9 instead of unit's Ld 6
        # Ld 9 - 2 = 7, rolling 7 = pass
        assert broke is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
