#!/usr/bin/env python3
"""
KAN-MCTS Hybrid AI Demonstration

Shows the trained KAN model evaluating TOW positions instantly.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.simulator.ai.kan_mcts import demo_kan_mcts

if __name__ == "__main__":
    demo_kan_mcts()

