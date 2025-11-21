# TOW Simulator - The Old World Combat Simulator

A Python-based simulator for Warhammer: The Old World tabletop battles.

## Features

- Combat resolution (shooting, melee, magic)
- Army list management
- AI decision-making
- Battle simulations

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the simulator:
```bash
python simulator.py
```

## Project Structure

- `src/simulator/` - Main package (pip-installable)
  - `core/` - Base rules & calculations (pure functions)
  - `factions/` - Army book loaders (JSON parsers)
  - `models/` - Entities (Unit, Character, Terrain)
  - `board/` - GameState, positioning
  - `phases/` - Phase managers (move/shoot/magic/combat)
  - `ai/` - Bot decision trees
- `data/` - Rules data (JSON format)
- `tests/` - Test suite
- `examples/` - Sample armies and battle reports

## Usage

Coming soon...

