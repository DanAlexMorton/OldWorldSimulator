# Warhammer: The Old World Battle Simulator
## Project Status & Roadmap

**Updated:** November 28, 2025  
**Status:** Core Complete, Balance Issues Identified

---

## Current Reality Check

| Component | Status | Working? |
|-----------|--------|----------|
| Core Engine | Complete | YES |
| AI System | Complete | YES |
| Army Validator | **NEW** | YES |
| Data (Points) | Official values | YES |
| Combat Balance | **NEEDS WORK** | NO |
| Shooting Phase | Basic | PARTIAL |
| Magic Phase | Stub only | NO |

---

## Tournament Results (Validated 2000pt Lists)

```
Empire (127 models, 1981 pts)  vs  Orcs (162 models, 1970 pts)

Result: ORCS WIN 100%
```

**Why?** The simulator currently:
- Orcs: T4 vs Empire T3 = 33% harder to wound
- Orcs: 35 more models = more attacks
- Simulator doesn't properly reward:
  - Empire shooting (handguns/crossbows)
  - Cavalry charge bonuses
  - Magic (not implemented)

---

## What We Just Built: Army Validator AI

```bash
python src/simulator/factions/validator_ai.py armies/empire_2000pts.json
```

**Output:**
```
ARMY VALIDATION: Empire
Valid: YES
Points: 1981/2000 (-19)

Composition:
  Lords     :   4.3%   (max 25%)
  Heroes    :  12.4%   (max 50%)
  Core      :  42.7%   (min 25%)
  Special   :  31.3%   (max 50%)
  Rare      :   9.4%   (max 25%)
```

**Features:**
- Official points from TOW rulebooks
- Composition validation (Core 25%+, Lords 25%-, etc.)
- Unit limits (1 Steam Tank, 1 Giant)
- AI optimizer suggestions

---

## Files Created Today

```
data/official_points.json       # Verified points (Empire + Orcs)
src/simulator/factions/validator_ai.py  # Validator AI
armies/empire_2000pts.json      # Valid 2000pt list
armies/orcs_2000pts.json        # Valid 2000pt list
```

---

## REVISED ROADMAP (Honest Assessment)

### Completed
| Phase | Status |
|-------|--------|
| 1. Core Math | DONE |
| 2. Unit System | DONE |
| 3. Combat Resolver | DONE |
| 4. Game Engine | DONE |
| 5. Tournament Mode | DONE |
| 6. AI Systems | DONE |
| 7. Army Validator | DONE |

### Needed for Balance

| Task | Effort | Impact |
|------|--------|--------|
| **Fix Shooting Phase** | 4 hrs | HIGH - Empire can't win without shooting |
| **Implement Cavalry Charge** | 2 hrs | HIGH - Knights should devastate on charge |
| **Add Magic Phase** | 1-2 days | MEDIUM - Some armies depend on it |
| **Terrain Effects** | 1 day | MEDIUM - Cover, obstacles |
| **Psychology** | 4 hrs | LOW - Fear, terror, panic |

### The Core Problem

```
CURRENT:  Both armies march forward and hit each other
          Orcs win because: More models + Higher toughness

NEEDED:   Empire shoots for 2-3 turns (killing ~30 Orcs)
          Knights charge (devastating impact)
          Magic adds mortal wounds
          THEN Orcs have fewer models when combat starts
```

---

## Recommended Next Steps

### Option A: Fix Shooting (Quick Win)
Make shooting actually meaningful:
- Currently: ~1-2 casualties per shooting phase
- Should be: ~5-10 casualties per shooting phase
- Add "stand and shoot" charge reaction

### Option B: Fix Cavalry
Knight charge should:
- +2 Strength on charge
- Impact hits
- Devastating charge (+1 to wound)

### Option C: Implement Magic
Empire wizards can:
- Deal mortal wounds
- Buff units
- Debuff enemies

---

## Honest Summary

| What Works | What Doesn't |
|------------|--------------|
| Army validation | Shooting phase underpowered |
| Combat math | No magic |
| AI decision-making | Cavalry charges weak |
| Tournament system | Empire has no way to win |

**The simulator correctly shows that in a pure melee brawl, Orcs beat Empire every time.**

**To make it realistic, Empire needs working ranged + magic + cavalry.**

---

## Quick Stats

| Metric | Value |
|--------|-------|
| Lines of Code | ~7,000 |
| Tests Passing | 146 |
| Factions | 2 |
| AI Types | 4 (MCTS, KAN, Utility, Council) |
| Speed | ~1 game/second |

---

## Usage

```bash
# Validate army
python src/simulator/factions/validator_ai.py armies/empire_2000pts.json

# Run tournament
python run_game.py armies/empire_2000pts.json armies/orcs_2000pts.json -n 100

# Single verbose game
python run_game.py armies/empire_2000pts.json armies/orcs_2000pts.json -v
```
