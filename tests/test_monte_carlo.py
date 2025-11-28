"""
Monte Carlo simulation tests
"""

import pytest
from src.simulator.models.unit import create_unit, TroopType, BaseSize, UnitCategory, Formation
from src.simulator.combat.monte_carlo import run_simulations, run_quick_test


def create_empire_halberdiers():
    """Create Empire Halberdiers unit"""
    profile = {"M": 4, "WS": 3, "BS": 3, "S": 3, "T": 3, "W": 1, "I": 3, "A": 1, "Ld": 7}
    unit = create_unit(
        "Halberdiers",
        profile,
        faction="Empire",
        category=UnitCategory.CORE,
        troop_type=TroopType.INFANTRY,
        base_size=BaseSize.MEDIUM_25,
        max_models=30,
        current_models=30,
        armour_save=5,
        special_rules=["Halberd"]
    )
    unit.formation = Formation(ranks=3, files=10)
    return [unit]


def create_orc_boyz():
    """Create Orc Boyz unit"""
    profile = {"M": 4, "WS": 3, "BS": 3, "S": 3, "T": 4, "W": 1, "I": 2, "A": 1, "Ld": 7}
    unit = create_unit(
        "Orc Boyz",
        profile,
        faction="Orcs & Goblins",
        category=UnitCategory.CORE,
        troop_type=TroopType.INFANTRY,
        base_size=BaseSize.MEDIUM_25,
        max_models=25,
        current_models=25,
        armour_save=6,
        special_rules=["Choppa"]
    )
    unit.formation = Formation(ranks=5, files=5)
    return [unit]


def create_high_elf_spearmen():
    """Create High Elf Spearmen"""
    profile = {"M": 5, "WS": 4, "BS": 4, "S": 3, "T": 3, "W": 1, "I": 5, "A": 1, "Ld": 8}
    unit = create_unit(
        "High Elf Spearmen",
        profile,
        faction="High Elves",
        category=UnitCategory.CORE,
        troop_type=TroopType.INFANTRY,
        base_size=BaseSize.MEDIUM_25,
        max_models=20,
        current_models=20,
        armour_save=5,
        special_rules=["Spear", "Always Strikes First"]
    )
    unit.formation = Formation(ranks=4, files=5)
    return [unit]


class TestMonteCarloSimulations:
    """Test Monte Carlo simulation system"""
    
    def test_quick_simulation_100_battles(self):
        """Test quick simulation with 100 battles"""
        result = run_quick_test(
            create_empire_halberdiers,
            create_orc_boyz,
            num_tests=100
        )
        
        # Should have results
        assert result['total_simulations'] == 100
        assert 'results' in result
        assert 'win_rates' in result
        
        # Win rates should sum to ~100%
        army_a_wins = result['results']['army_a_wins']
        army_b_wins = result['results']['army_b_wins']
        draws = result['results']['draws']
        assert army_a_wins + army_b_wins + draws == 100
    
    def test_simulation_reproducibility(self):
        """Test that simulations with same seed are reproducible"""
        result1 = run_simulations(
            create_empire_halberdiers,
            create_orc_boyz,
            num_simulations=100,
            seed=42
        )
        
        result2 = run_simulations(
            create_empire_halberdiers,
            create_orc_boyz,
            num_simulations=100,
            seed=42
        )
        
        # Same seed should give same results
        assert result1.army_a_wins == result2.army_a_wins
        assert result1.army_b_wins == result2.army_b_wins
        assert result1.draws == result2.draws
    
    def test_simulation_statistics(self):
        """Test that simulation statistics are calculated correctly"""
        result = run_simulations(
            create_empire_halberdiers,
            create_orc_boyz,
            num_simulations=100,
            verbose=False
        )
        
        # Check statistics
        assert result.total_simulations == 100
        assert 0 <= result.army_a_win_rate <= 100
        assert 0 <= result.army_b_win_rate <= 100
        assert 0 <= result.draw_rate <= 100
        
        # Win rates should sum to ~100%
        total_rate = result.army_a_win_rate + result.army_b_win_rate + result.draw_rate
        assert 99.0 <= total_rate <= 101.0  # Allow for rounding
        
        # Averages should be reasonable
        assert result.average_rounds > 0
        assert result.average_a_survivors >= 0
        assert result.average_b_survivors >= 0
        
        # Execution time should be reasonable
        assert result.execution_time > 0
        assert result.execution_time < 60  # Should complete in under a minute
    
    def test_large_simulation_1000_battles(self):
        """Test larger simulation with 1000 battles"""
        result = run_simulations(
            create_empire_halberdiers,
            create_orc_boyz,
            num_simulations=1000,
            verbose=False
        )
        
        # Should complete successfully
        assert result.total_simulations == 1000
        assert result.execution_time < 120  # Should be fast
        
        # Check that both sides win at least some battles
        # (unless one side completely dominates)
        # This is a reasonableness check
        assert result.army_a_wins > 0 or result.army_b_wins > 0
    
    def test_balanced_matchup(self):
        """Test that similar units produce balanced results"""
        def create_unit_a():
            return create_empire_halberdiers()
        
        def create_unit_b():
            return create_empire_halberdiers()
        
        result = run_simulations(
            create_unit_a,
            create_unit_b,
            num_simulations=500,
            verbose=False
        )
        
        # Identical units should have ~50/50 win rate (±10%)
        # Or many draws
        assert 30 <= result.army_a_win_rate <= 70 or result.draw_rate > 20
    
    def test_simulation_to_dict(self):
        """Test that result can be exported to dict"""
        result = run_simulations(
            create_empire_halberdiers,
            create_orc_boyz,
            num_simulations=100,
            verbose=False
        )
        
        result_dict = result.to_dict()
        
        # Check dict structure
        assert 'total_simulations' in result_dict
        assert 'results' in result_dict
        assert 'win_rates' in result_dict
        assert 'averages' in result_dict
        assert 'execution_time' in result_dict


class TestPerformance:
    """Test simulation performance"""
    
    def test_100_simulations_speed(self):
        """Test that 100 simulations complete quickly"""
        import time
        
        start = time.time()
        result = run_simulations(
            create_empire_halberdiers,
            create_orc_boyz,
            num_simulations=100,
            verbose=False
        )
        elapsed = time.time() - start
        
        # Should complete in under 10 seconds
        assert elapsed < 10.0
        
        # Should be at least 10 battles/second
        battles_per_second = 100 / elapsed
        assert battles_per_second >= 10
    
    def test_1000_simulations_speed(self):
        """Test that 1000 simulations complete in reasonable time"""
        import time
        
        start = time.time()
        result = run_simulations(
            create_empire_halberdiers,
            create_orc_boyz,
            num_simulations=1000,
            verbose=False
        )
        elapsed = time.time() - start
        
        # Should complete in under 60 seconds
        assert elapsed < 60.0
        
        # Report speed
        battles_per_second = 1000 / elapsed
        print(f"\n1000 simulations: {elapsed:.2f}s ({battles_per_second:.0f} battles/s)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

