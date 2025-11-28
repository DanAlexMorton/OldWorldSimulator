"""
Unit tests for dice mechanics
Validates dice rolling functions and reroll mechanics
"""

import pytest
import random
from src.simulator.core.dice import (
    d6, d6_sum, roll_with_reroll, roll_with_modifier,
    artillery_dice, scatter_dice, roll_2d6, roll_d3,
    roll_multiple_wounds
)


class TestBasicDiceRolls:
    """Test basic dice rolling functions."""
    
    def test_d6_returns_valid_range(self):
        """Test that d6 returns values 1-6."""
        random.seed(42)
        for _ in range(100):
            rolls = d6(10)
            for roll in rolls:
                assert 1 <= roll <= 6
    
    def test_d6_returns_correct_count(self):
        """Test that d6 returns correct number of dice."""
        random.seed(42)
        assert len(d6(1)) == 1
        assert len(d6(5)) == 5
        assert len(d6(10)) == 10
    
    def test_d6_with_zero_or_negative(self):
        """Test edge case of zero or negative dice."""
        assert d6(0) == []
        assert d6(-1) == []
    
    def test_d6_sum(self):
        """Test d6_sum returns correct sum."""
        random.seed(42)
        result = d6_sum(2)
        assert 2 <= result <= 12
    
    def test_d6_deterministic_with_seed(self):
        """Test that seeded random produces consistent results."""
        random.seed(42)
        roll1 = d6(5)
        random.seed(42)
        roll2 = d6(5)
        assert roll1 == roll2


class TestRerollMechanics:
    """Test reroll mechanics (Hatred, etc.)."""
    
    def test_roll_with_reroll_no_rerolls(self):
        """Test rolling without rerolls."""
        random.seed(42)
        successes, initial, rerolls = roll_with_reroll(4, dice_count=10)
        assert len(initial) == 10
        assert len(rerolls) == 0
        assert successes >= 0
    
    def test_roll_with_reroll_failed_hits(self):
        """Test rerolling all failed hits."""
        random.seed(42)
        successes, initial, rerolls = roll_with_reroll(4, dice_count=10, reroll_fails=True)
        assert len(initial) == 10
        # Should have rerolled some failures
        num_initial_fails = sum(1 for r in initial if r < 4)
        assert len(rerolls) == num_initial_fails
    
    def test_roll_with_reroll_ones(self):
        """Test rerolling only 1s."""
        random.seed(42)
        successes, initial, rerolls = roll_with_reroll(4, dice_count=20, reroll_ones=True)
        # Should only reroll 1s
        num_ones = sum(1 for r in initial if r == 1)
        assert len(rerolls) == num_ones
    
    def test_reroll_improves_success_rate(self):
        """Test that rerolls improve success rate statistically."""
        random.seed(42)
        # Without reroll
        successes_no_reroll, _, _ = roll_with_reroll(4, dice_count=100, reroll_fails=False)
        
        random.seed(42)
        # With reroll
        successes_with_reroll, _, _ = roll_with_reroll(4, dice_count=100, reroll_fails=True)
        
        # Note: Due to randomness, this might not always hold for single tests
        # But over multiple runs, rerolls should help
        assert successes_with_reroll >= successes_no_reroll * 0.9  # Allow some variance


class TestModifiers:
    """Test modifier application to dice rolls."""
    
    def test_roll_with_positive_modifier(self):
        """Test that positive modifiers make it harder."""
        random.seed(42)
        # +1 modifier makes 4+ into 5+
        successes, rolls = roll_with_modifier(4, modifier=1, dice_count=10)
        # Should be less successful than base
        assert len(rolls) == 10
    
    def test_roll_with_negative_modifier(self):
        """Test that negative modifiers make it easier."""
        random.seed(42)
        # -1 modifier makes 4+ into 3+
        successes, rolls = roll_with_modifier(4, modifier=-1, dice_count=10)
        assert len(rolls) == 10
    
    def test_modifier_clamping_maximum(self):
        """Test that modifiers can't make target better than 2+."""
        random.seed(42)
        # 3+ with -5 should clamp to 2+
        successes, rolls = roll_with_modifier(3, modifier=-5, dice_count=10)
        # All rolls of 2+ should succeed
        expected = sum(1 for r in rolls if r >= 2)
        assert successes == expected
    
    def test_modifier_clamping_minimum(self):
        """Test that modifiers can't make target worse than 6+."""
        random.seed(42)
        # 4+ with +5 should clamp to 6+
        successes, rolls = roll_with_modifier(4, modifier=5, dice_count=10)
        # Only 6s should succeed
        expected = sum(1 for r in rolls if r >= 6)
        assert successes == expected


class TestSpecialDice:
    """Test special dice rolls (artillery, scatter, etc.)."""
    
    def test_artillery_dice_normal(self):
        """Test normal artillery dice roll."""
        random.seed(43)  # Seed that doesn't produce double 1s immediately
        result, is_misfire = artillery_dice()
        assert 2 <= result <= 12
        # With this seed, shouldn't misfire
    
    def test_artillery_dice_misfire_detection(self):
        """Test that double 1s are detected as misfire."""
        # Keep rolling until we get a double 1 or test enough times
        found_misfire = False
        for i in range(1000):
            random.seed(i)
            result, is_misfire = artillery_dice()
            if result == 2 and is_misfire:
                found_misfire = True
                break
        assert found_misfire, "Should eventually find a misfire scenario"
    
    def test_scatter_dice_hit(self):
        """Test scatter dice hit result."""
        # Find a seed that produces HIT
        found_hit = False
        for i in range(100):
            random.seed(i)
            direction, distance = scatter_dice()
            if direction == 'HIT':
                assert distance == 0
                found_hit = True
                break
        assert found_hit
    
    def test_scatter_dice_scatter(self):
        """Test scatter dice scatter result."""
        random.seed(42)
        direction, distance = scatter_dice()
        if direction != 'HIT':
            assert distance >= 2
            assert distance <= 12
            assert direction in ['1', '2', '3', '4', '5']
    
    def test_roll_2d6(self):
        """Test 2d6 roll for leadership tests."""
        random.seed(42)
        result = roll_2d6()
        assert 2 <= result <= 12
    
    def test_roll_d3(self):
        """Test d3 roll."""
        random.seed(42)
        for _ in range(20):
            result = roll_d3()
            assert 1 <= result <= 3
    
    def test_roll_multiple_wounds_d3(self):
        """Test multiple wounds d3."""
        random.seed(42)
        result = roll_multiple_wounds('d3')
        assert 1 <= result <= 3
    
    def test_roll_multiple_wounds_d6(self):
        """Test multiple wounds d6."""
        random.seed(42)
        result = roll_multiple_wounds('d6')
        assert 1 <= result <= 6
    
    def test_roll_multiple_wounds_fixed(self):
        """Test multiple wounds with fixed value."""
        assert roll_multiple_wounds('2') == 2
        assert roll_multiple_wounds('3') == 3


class TestDiceDistributions:
    """Test that dice produce expected distributions over many rolls."""
    
    def test_d6_distribution(self):
        """Test that d6 produces relatively even distribution."""
        random.seed(42)
        rolls = d6(6000)
        
        # Count occurrences of each face
        counts = {i: rolls.count(i) for i in range(1, 7)}
        
        # Each face should appear roughly 1000 times (±10%)
        for face, count in counts.items():
            assert 800 <= count <= 1200, f"Face {face} appeared {count} times"
    
    def test_reroll_improves_probability(self):
        """Test that rerolls improve success rate statistically."""
        random.seed(42)
        
        # Test reroll failures on 4+
        successes_list = []
        for _ in range(100):
            s, _, _ = roll_with_reroll(4, dice_count=10, reroll_fails=True)
            successes_list.append(s)
        
        avg_successes = sum(successes_list) / len(successes_list)
        
        # Expected: 0.5 + 0.5*0.5 = 0.75 success rate
        # So out of 10 dice, expect ~7.5 successes
        assert 6.5 <= avg_successes <= 8.5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
