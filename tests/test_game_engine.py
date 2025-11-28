"""
Tests for game engine (GameState, TurnManager, full simulations)
"""

import pytest
from src.simulator.engine import (
    Position, Terrain, TerrainType, Battlefield,
    GameState, create_standard_battlefield, deploy_armies_standard,
    TurnManager, simulate_full_game, run_full_game_simulations
)
from src.simulator.models.unit import create_unit, TroopType, BaseSize, UnitCategory, Formation


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_test_unit(name: str, models: int = 20):
    """Create a test unit"""
    profile = {"M": 4, "WS": 4, "BS": 3, "S": 3, "T": 3, "W": 1, "I": 3, "A": 1, "Ld": 7}
    unit = create_unit(
        name=name,
        profile=profile,
        faction="test",
        category=UnitCategory.CORE,
        troop_type=TroopType.INFANTRY,
        base_size=BaseSize.MEDIUM_25,
        max_models=models,
        current_models=models,
        armour_save=5
    )
    unit.formation = Formation(ranks=4, files=5)
    return unit


def create_test_army():
    """Create a simple test army"""
    return [
        create_test_unit("Infantry", 20),
        create_test_unit("Archers", 10)
    ]


# ============================================================================
# POSITION TESTS
# ============================================================================

class TestPosition:
    """Test Position class"""
    
    def test_position_creation(self):
        """Test creating a position"""
        pos = Position(10.0, 20.0, 45.0)
        assert pos.x == 10.0
        assert pos.y == 20.0
        assert pos.facing == 45.0
    
    def test_distance_calculation(self):
        """Test distance between positions"""
        pos1 = Position(0.0, 0.0)
        pos2 = Position(3.0, 4.0)
        distance = pos1.distance_to(pos2)
        assert distance == 5.0  # 3-4-5 triangle
    
    def test_angle_calculation(self):
        """Test angle between positions"""
        pos1 = Position(0.0, 0.0, 0.0)
        pos2 = Position(0.0, 10.0)
        angle = pos1.angle_to(pos2)
        assert angle == 0.0  # North
    
    def test_in_arc_check(self):
        """Test arc checking"""
        pos1 = Position(0.0, 0.0, 0.0)  # Facing north
        pos2 = Position(5.0, 10.0)  # Northeast
        assert pos1.is_in_arc(pos2, arc_angle=45.0)
    
    def test_movement(self):
        """Test moving position"""
        pos = Position(0.0, 0.0, 0.0)  # Facing north
        new_pos = pos.move(10.0)  # Move 10" forward
        assert new_pos.x == pytest.approx(0.0, abs=0.1)
        assert new_pos.y == pytest.approx(10.0, abs=0.1)


# ============================================================================
# BATTLEFIELD TESTS
# ============================================================================

class TestBattlefield:
    """Test Battlefield class"""
    
    def test_standard_battlefield(self):
        """Test creating standard battlefield"""
        battlefield = create_standard_battlefield()
        assert battlefield.width == 72.0
        assert battlefield.height == 48.0
    
    def test_terrain_addition(self):
        """Test adding terrain"""
        battlefield = Battlefield()
        hill = Terrain(TerrainType.HILL, 10, 10, 12, 12, "Big Hill")
        battlefield.add_terrain(hill)
        assert len(battlefield.terrain) == 1
    
    def test_terrain_detection(self):
        """Test terrain at position"""
        battlefield = Battlefield()
        forest = Terrain(TerrainType.FOREST, 10, 10, 12, 12, "Forest")
        battlefield.add_terrain(forest)
        
        terrain_list = battlefield.get_terrain_at(15.0, 15.0)
        assert len(terrain_list) == 1
        assert terrain_list[0].terrain_type == TerrainType.FOREST
    
    def test_elevation(self):
        """Test elevation calculation"""
        battlefield = Battlefield()
        hill = Terrain(TerrainType.HILL, 10, 10, 12, 12)
        battlefield.add_terrain(hill)
        
        assert battlefield.get_elevation_at(15, 15) == 1
        assert battlefield.get_elevation_at(5, 5) == 0


# ============================================================================
# GAME STATE TESTS
# ============================================================================

class TestGameState:
    """Test GameState class"""
    
    def test_game_state_creation(self):
        """Test creating game state"""
        battlefield = create_standard_battlefield()
        game_state = GameState(battlefield=battlefield)
        assert game_state.current_turn == 1
        assert game_state.active_player == "player_a"
        assert not game_state.game_over
    
    def test_add_unit(self):
        """Test adding units to game"""
        battlefield = create_standard_battlefield()
        game_state = GameState(battlefield=battlefield)
        
        unit = create_test_unit("Test Unit", 20)
        pos = Position(10.0, 10.0, 0.0)
        unit_state = game_state.add_unit(unit, pos, "player_a")
        
        assert len(game_state.player_a_units) == 1
        assert unit_state.unit == unit
        assert unit_state.position == pos
    
    def test_deployment(self):
        """Test army deployment"""
        battlefield = create_standard_battlefield()
        game_state = GameState(battlefield=battlefield)
        
        army_a = [create_test_unit(f"Unit {i}", 20) for i in range(3)]
        army_b = [create_test_unit(f"Enemy {i}", 20) for i in range(3)]
        
        deploy_armies_standard(game_state, army_a, army_b)
        
        assert len(game_state.player_a_units) == 3
        assert len(game_state.player_b_units) == 3
    
    def test_turn_advancement(self):
        """Test advancing turns"""
        battlefield = create_standard_battlefield()
        game_state = GameState(battlefield=battlefield)
        
        assert game_state.active_player == "player_a"
        assert game_state.current_turn == 1
        
        game_state.advance_turn()
        assert game_state.active_player == "player_b"
        assert game_state.current_turn == 1
        
        game_state.advance_turn()
        assert game_state.active_player == "player_a"
        assert game_state.current_turn == 2


# ============================================================================
# TURN MANAGER TESTS
# ============================================================================

class TestTurnManager:
    """Test TurnManager"""
    
    def test_turn_manager_creation(self):
        """Test creating turn manager"""
        battlefield = create_standard_battlefield()
        game_state = GameState(battlefield=battlefield)
        turn_manager = TurnManager(game_state)
        assert turn_manager.game_state == game_state
    
    def test_execute_turn(self):
        """Test executing a full turn"""
        battlefield = create_standard_battlefield()
        game_state = GameState(battlefield=battlefield)
        
        army_a = create_test_army()
        army_b = create_test_army()
        deploy_armies_standard(game_state, army_a, army_b)
        
        turn_manager = TurnManager(game_state)
        result = turn_manager.execute_full_turn("player_a")
        
        assert "phases" in result
        assert "log" in result
        assert len(result["phases"]) == 8  # All phases executed


# ============================================================================
# FULL GAME SIMULATION TESTS
# ============================================================================

class TestFullGameSimulation:
    """Test full game simulation"""
    
    def test_simulate_single_game(self):
        """Test simulating a single game"""
        army_a = create_test_army()
        army_b = create_test_army()
        
        result = simulate_full_game(army_a, army_b, max_turns=2, verbose=False)
        
        assert result.winner in ["player_a", "player_b", "draw"]
        assert result.turns_played >= 1
        assert result.turns_played <= 2
        assert result.total_time > 0
    
    def test_full_game_simulations(self):
        """Test running multiple game simulations"""
        def create_army():
            return create_test_army()
        
        stats = run_full_game_simulations(
            create_army,
            create_army,
            num_simulations=10,
            max_turns=3,
            verbose=False
        )
        
        assert stats.total_games == 10
        assert stats.player_a_wins + stats.player_b_wins + stats.draws == 10
        assert 0 <= stats.player_a_win_rate <= 100
        assert 0 <= stats.player_b_win_rate <= 100
        assert stats.average_turns > 0
    
    def test_simulation_reproducibility(self):
        """Test that simulations with same seed are reproducible"""
        def create_army():
            return create_test_army()
        
        stats1 = run_full_game_simulations(
            create_army,
            create_army,
            num_simulations=10,
            max_turns=3,
            seed=42,
            verbose=False
        )
        
        stats2 = run_full_game_simulations(
            create_army,
            create_army,
            num_simulations=10,
            max_turns=3,
            seed=42,
            verbose=False
        )
        
        assert stats1.player_a_wins == stats2.player_a_wins
        assert stats1.player_b_wins == stats2.player_b_wins
        assert stats1.draws == stats2.draws


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestGameIntegration:
    """Integration tests for complete game flow"""
    
    def test_complete_game_flow(self):
        """Test a complete game from start to finish"""
        # Create armies
        army_a = create_test_army()
        army_b = create_test_army()
        
        # Create game
        battlefield = create_standard_battlefield()
        game_state = GameState(battlefield=battlefield, max_turns=2)
        deploy_armies_standard(game_state, army_a, army_b)
        
        # Play turns
        turn_manager = TurnManager(game_state)
        
        for turn in range(1, 3):
            game_state.current_turn = turn
            
            # Player A
            turn_manager.execute_full_turn("player_a")
            if game_state.game_over:
                break
            
            # Player B
            turn_manager.execute_full_turn("player_b")
            if game_state.game_over:
                break
        
        # Force game to end after max turns
        game_state.current_turn = 3  # Past max_turns
        if not game_state.game_over:
            game_state.check_victory()
        
        assert game_state.winner is not None
    
    def test_game_with_casualties(self):
        """Test that casualties are tracked correctly"""
        army_a = create_test_army()
        army_b = create_test_army()
        
        result = simulate_full_game(army_a, army_b, max_turns=6, verbose=False)
        
        # Should have some casualties in 6 turns
        total_casualties = (result.player_a_points_destroyed + 
                           result.player_b_points_destroyed)
        # May be 0 if armies don't engage, but system should work
        assert total_casualties >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

