"""
Game state management for Warhammer: The Old World
Battlefield, unit positioning, terrain, and victory conditions
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Set
from enum import Enum
import math

from ..models.unit import Unit
from ..models.character import Character


class TerrainType(Enum):
    """Types of terrain"""
    OPEN = "open"
    HILL = "hill"
    FOREST = "forest"
    BUILDING = "building"
    RIVER = "river"
    IMPASSABLE = "impassable"
    OBSTACLE = "obstacle"


@dataclass
class Position:
    """
    Position on battlefield in inches.
    
    Origin (0,0) is bottom-left corner.
    x: horizontal (0-72")
    y: vertical (0-48")
    facing: angle in degrees (0=north, 90=east, 180=south, 270=west)
    """
    x: float
    y: float
    facing: float = 0.0  # Degrees
    
    def distance_to(self, other: 'Position') -> float:
        """Calculate distance to another position in inches"""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)
    
    def angle_to(self, other: 'Position') -> float:
        """Calculate angle to another position in degrees"""
        dx = other.x - self.x
        dy = other.y - self.y
        angle = math.degrees(math.atan2(dx, dy))
        return angle % 360
    
    def is_in_arc(self, target: 'Position', arc_angle: float = 45.0) -> bool:
        """
        Check if target is in front arc.
        
        Args:
            target: Target position
            arc_angle: Half-angle of arc (default 45° = 90° total front arc)
        
        Returns:
            True if target in arc
        """
        angle_to_target = self.angle_to(target)
        angle_diff = abs(angle_to_target - self.facing)
        # Normalize to 0-180
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        return angle_diff <= arc_angle
    
    def move(self, distance: float, angle: Optional[float] = None) -> 'Position':
        """
        Create new position by moving distance in direction.
        
        Args:
            distance: Distance to move in inches
            angle: Direction to move (default: current facing)
        
        Returns:
            New Position
        """
        if angle is None:
            angle = self.facing
        
        angle_rad = math.radians(angle)
        new_x = self.x + distance * math.sin(angle_rad)
        new_y = self.y + distance * math.cos(angle_rad)
        
        return Position(new_x, new_y, self.facing)
    
    def to_dict(self) -> Dict:
        """Export to dictionary"""
        return {
            "x": self.x,
            "y": self.y,
            "facing": self.facing
        }


@dataclass
class Terrain:
    """
    Terrain feature on battlefield.
    
    Represented as rectangular area for simplicity.
    """
    terrain_type: TerrainType
    x: float  # Bottom-left corner
    y: float
    width: float  # Inches
    height: float
    name: str = "Terrain"
    
    # Terrain properties
    blocks_line_of_sight: bool = False
    difficult_terrain_level: int = 0  # 0=normal, 1=DT1, 2=DT2
    provides_cover: bool = False
    impassable: bool = False
    elevation: int = 0  # Height levels (hills)
    
    def __post_init__(self):
        """Set properties based on terrain type"""
        if self.terrain_type == TerrainType.HILL:
            self.elevation = 1
            self.difficult_terrain_level = 1
        elif self.terrain_type == TerrainType.FOREST:
            self.difficult_terrain_level = 1
            self.provides_cover = True
            self.blocks_line_of_sight = True
        elif self.terrain_type == TerrainType.BUILDING:
            self.blocks_line_of_sight = True
            self.impassable = True
        elif self.terrain_type == TerrainType.RIVER:
            self.difficult_terrain_level = 2
        elif self.terrain_type == TerrainType.IMPASSABLE:
            self.impassable = True
        elif self.terrain_type == TerrainType.OBSTACLE:
            self.difficult_terrain_level = 1
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if point is within terrain"""
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)
    
    def overlaps_with(self, other: 'Terrain') -> bool:
        """Check if this terrain overlaps with another"""
        return not (self.x + self.width < other.x or
                   other.x + other.width < self.x or
                   self.y + self.height < other.y or
                   other.y + other.height < self.y)


@dataclass
class Battlefield:
    """
    The game battlefield (standard 48" x 72").
    
    Coordinates:
    - (0,0) = bottom-left corner
    - (72, 48) = top-right corner
    """
    width: float = 72.0  # Inches (6 feet)
    height: float = 48.0  # Inches (4 feet)
    terrain: List[Terrain] = field(default_factory=list)
    
    def add_terrain(self, terrain: Terrain) -> None:
        """Add terrain feature to battlefield"""
        self.terrain.append(terrain)
    
    def get_terrain_at(self, x: float, y: float) -> List[Terrain]:
        """Get all terrain features at position"""
        return [t for t in self.terrain if t.contains_point(x, y)]
    
    def is_valid_position(self, x: float, y: float) -> bool:
        """Check if position is on battlefield"""
        return 0 <= x <= self.width and 0 <= y <= self.height
    
    def get_elevation_at(self, x: float, y: float) -> int:
        """Get elevation level at position (0 = ground level)"""
        terrain_list = self.get_terrain_at(x, y)
        if not terrain_list:
            return 0
        return max(t.elevation for t in terrain_list)
    
    def has_line_of_sight(self, pos_a: Position, pos_b: Position) -> bool:
        """
        Check if there's line of sight between two positions.
        
        Simplified: blocked if terrain with LOS blocking is between them.
        """
        # Get midpoint
        mid_x = (pos_a.x + pos_b.x) / 2
        mid_y = (pos_a.y + pos_b.y) / 2
        
        # Check for blocking terrain at midpoint
        terrain_list = self.get_terrain_at(mid_x, mid_y)
        for terrain in terrain_list:
            if terrain.blocks_line_of_sight:
                # Simple check - could be more sophisticated
                elev_a = self.get_elevation_at(pos_a.x, pos_a.y)
                elev_b = self.get_elevation_at(pos_b.x, pos_b.y)
                # If both units on higher ground, they can see over
                if elev_a > terrain.elevation and elev_b > terrain.elevation:
                    continue
                return False
        
        return True


@dataclass
class UnitState:
    """
    Runtime state for a unit in game.
    
    Links Unit model to battlefield position and game state.
    """
    unit: Unit
    position: Position
    owner: str  # "player_a" or "player_b"
    
    # Movement state
    has_moved: bool = False
    has_marched: bool = False
    has_charged: bool = False
    has_fled: bool = False
    
    # Combat state
    in_combat: bool = False
    engaged_with: List['UnitState'] = field(default_factory=list)
    
    # Status effects
    is_fleeing: bool = False
    is_rallying: bool = False
    has_failed_terror: bool = False
    
    # Turn tracking
    last_moved_turn: int = 0
    
    def distance_to(self, other: 'UnitState') -> float:
        """Calculate distance to another unit"""
        return self.position.distance_to(other.position)
    
    def is_in_charge_arc(self, target: 'UnitState') -> bool:
        """Check if target is in front 45° arc for charging"""
        return self.position.is_in_arc(target.position, arc_angle=45.0)
    
    def can_move(self) -> bool:
        """Check if unit can move this turn"""
        return not self.has_moved and not self.in_combat and not self.is_fleeing
    
    def can_charge(self) -> bool:
        """Check if unit can charge this turn"""
        return not self.has_moved and not self.in_combat
    
    def can_shoot(self) -> bool:
        """Check if unit can shoot this turn"""
        return not self.in_combat and not self.has_marched
    
    def reset_turn_state(self) -> None:
        """Reset per-turn flags at start of turn"""
        self.has_moved = False
        self.has_marched = False
        self.has_charged = False
        self.has_fled = False


@dataclass
class GameState:
    """
    Complete game state for a TOW battle.
    
    Tracks battlefield, units, turn number, and victory conditions.
    """
    battlefield: Battlefield
    player_a_units: List[UnitState] = field(default_factory=list)
    player_b_units: List[UnitState] = field(default_factory=list)
    
    # Turn tracking
    current_turn: int = 1
    current_phase: str = "deployment"
    active_player: str = "player_a"
    
    # Victory tracking
    player_a_points_destroyed: int = 0
    player_b_points_destroyed: int = 0
    max_turns: int = 6
    
    # Game state
    game_over: bool = False
    winner: Optional[str] = None
    
    def add_unit(self, unit: Unit, position: Position, owner: str) -> UnitState:
        """
        Add unit to game at position.
        
        Args:
            unit: Unit to add
            position: Starting position
            owner: "player_a" or "player_b"
        
        Returns:
            UnitState for tracking
        """
        unit_state = UnitState(unit=unit, position=position, owner=owner)
        
        if owner == "player_a":
            self.player_a_units.append(unit_state)
        else:
            self.player_b_units.append(unit_state)
        
        return unit_state
    
    def get_all_units(self, player: Optional[str] = None) -> List[UnitState]:
        """Get all units, optionally filtered by player"""
        if player == "player_a":
            return self.player_a_units
        elif player == "player_b":
            return self.player_b_units
        else:
            return self.player_a_units + self.player_b_units
    
    def get_enemy_units(self, player: str) -> List[UnitState]:
        """Get enemy units for specified player"""
        if player == "player_a":
            return self.player_b_units
        else:
            return self.player_a_units
    
    def get_unit_at(self, x: float, y: float, max_distance: float = 1.0) -> Optional[UnitState]:
        """Find unit at or near position"""
        for unit_state in self.get_all_units():
            distance = math.sqrt((unit_state.position.x - x)**2 + 
                               (unit_state.position.y - y)**2)
            if distance <= max_distance:
                return unit_state
        return None
    
    def units_in_range(self, position: Position, range_inches: float, 
                       owner: Optional[str] = None) -> List[UnitState]:
        """Get all units within range of position"""
        units = []
        for unit_state in self.get_all_units(owner):
            if position.distance_to(unit_state.position) <= range_inches:
                units.append(unit_state)
        return units
    
    def check_coherency(self, unit_state: UnitState) -> bool:
        """
        Check if unit is in coherency (all models within 1" of another).
        
        Simplified: just check position is valid.
        """
        return self.battlefield.is_valid_position(
            unit_state.position.x, 
            unit_state.position.y
        )
    
    def advance_turn(self) -> None:
        """Advance to next turn"""
        if self.active_player == "player_a":
            self.active_player = "player_b"
        else:
            self.active_player = "player_a"
            self.current_turn += 1
        
        # Reset turn state for active player
        for unit in self.get_all_units(self.active_player):
            unit.reset_turn_state()
        
        # Check victory conditions
        if self.current_turn > self.max_turns:
            self.check_victory()
    
    def check_victory(self) -> None:
        """
        Check victory conditions.
        
        Standard TOW: Units destroyed, army broken (>50% casualties)
        """
        # Count units remaining
        initial_a_units = len(self.player_a_units) + len([u for u in [] if not u.unit.is_alive])
        initial_b_units = len(self.player_b_units) + len([u for u in [] if not u.unit.is_alive])
        
        # Simple check: if all enemy units destroyed
        if len(self.player_a_units) == 0:
            self.game_over = True
            self.winner = "player_b"
            return
        
        if len(self.player_b_units) == 0:
            self.game_over = True
            self.winner = "player_a"
            return
        
        # Turn limit victory - who has more units surviving
        if self.current_turn >= self.max_turns:  # Changed to >= so turn 6 triggers
            self.game_over = True
            
            # Count surviving models
            a_models = sum(u.unit.current_models for u in self.player_a_units)
            b_models = sum(u.unit.current_models for u in self.player_b_units)
            
            if a_models > b_models * 1.1:  # Need 10% advantage to win
                self.winner = "player_a"
            elif b_models > a_models * 1.1:
                self.winner = "player_b"
            else:
                self.winner = "draw"
    
    def remove_destroyed_units(self) -> None:
        """Remove units with 0 models from game"""
        # Player A
        destroyed_a = [u for u in self.player_a_units if not u.unit.is_alive]
        for unit in destroyed_a:
            self.player_a_points_destroyed += unit.unit.total_points_cost
            self.player_a_units.remove(unit)
        
        # Player B
        destroyed_b = [u for u in self.player_b_units if not u.unit.is_alive]
        for unit in destroyed_b:
            self.player_b_points_destroyed += unit.unit.total_points_cost
            self.player_b_units.remove(unit)
    
    def to_dict(self) -> Dict:
        """Export game state to dictionary"""
        return {
            "turn": self.current_turn,
            "phase": self.current_phase,
            "active_player": self.active_player,
            "player_a": {
                "units": len(self.player_a_units),
                "points_destroyed": self.player_a_points_destroyed
            },
            "player_b": {
                "units": len(self.player_b_units),
                "points_destroyed": self.player_b_points_destroyed
            },
            "game_over": self.game_over,
            "winner": self.winner
        }


def create_standard_battlefield() -> Battlefield:
    """Create standard 4x6 ft battlefield"""
    return Battlefield(width=72.0, height=48.0)


def deploy_armies_standard(
    game_state: GameState,
    army_a: List[Unit],
    army_b: List[Unit],
    deployment_zone_depth: float = 12.0
) -> None:
    """
    Deploy armies in standard deployment zones.
    
    Army A: bottom 12"
    Army B: top 12"
    24" gap between armies
    
    Args:
        game_state: Game state to deploy into
        army_a: Player A's army
        army_b: Player B's army
        deployment_zone_depth: Depth of deployment zone in inches
    """
    # Deploy Army A (bottom)
    x_offset = 6.0
    for i, unit in enumerate(army_a):
        x = x_offset + (i * 8.0) % 60.0  # Spread across width
        y = 6.0 + ((i * 8.0) // 60.0) * 4.0  # Multiple rows if needed
        position = Position(x, y, facing=0.0)  # Facing north
        game_state.add_unit(unit, position, "player_a")
    
    # Deploy Army B (top)
    for i, unit in enumerate(army_b):
        x = x_offset + (i * 8.0) % 60.0
        y = 42.0 - ((i * 8.0) // 60.0) * 4.0  # From top
        position = Position(x, y, facing=180.0)  # Facing south
        game_state.add_unit(unit, position, "player_b")

