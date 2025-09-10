# Slots Levels — Quantitative Slot Machine Simulation and Strategy Analysis
A Python-based simulation framework for analyzing upgrade strategies in a slot-machine style game with progressive rounds and purchasable upgrades. Unlike typical slot games, this design incorporates:
- **Dynamic bar-fill mechanics** based on matching symbol combinations
- **Upgradable player strategies** affecting spins, probabilities, and rewards
- **Robust statistical analysis** with export of spin probabilities, expected returns, and game balance metrics  
The game is an attempt to balance challenge and reward by ensuring that the first level can be cleared more often than not, leaving players with a sense of accomplishment, while consecutive levels get progressively more challenging, with the third level having a much lower success rate so that there is a real sense of achievement whenever it is completed. The upgrades are balanced and not game-breaking, while ensuring that the benefits are felt across multiple runs but come at a cost. The overall RTP/ROI spread does favor certain upgrade combinations over others, so an optimal strategy does exist, but the variance between observed and theoretical results ensures that strategies do not necessarily guarantee a better outcome and the luck factor — the core of any slots game — is preserved.
## Files Overview
### Core Game Logic
- **`engine.py`** - Main game engine implementing slot mechanics, upgrade system, and round progression
- **`utils.py`** - Helper functions for generating upgrade strategies and formatting names
### Analysis Tools
- **`simulate.py`** - Monte Carlo simulation runner that tests all upgrade strategies across multiple game runs
- **`stats.py`** - Statistical analysis tool that calculates theoretical expected values, probabilities, ROI, RTP, and spin outcomes
### Configuration
- **`config.json`** - Game parameters including symbols, probabilities, multipliers, and upgrade costs
## Game Mechanics
- Players start with **100 credits** and must fill a **progress bar** each round to advance
- The bar target increases each round:
  - `Round 1 -> Target 1.0`
  - `Round 2 -> Target 1.5`
  - `Round 3 -> Target 2.0`
- Three upgrades are available for purchase in **Rounds 2-3** (each costing 50 credits):
  1. **Reel Bias** - Increases probability of high-value symbols
  2. **Extra Spins** - +2 spins per round
  3. **Bonus Multiplier** - +1 to all symbol multipliers
## Features
- Monte Carlo simulation of different upgrade strategies
- Theoretical EV (expected value) calculation for spins and rounds
- Export of outcome distributions, probabilities, ROI, and RTP for game balance testing
- Strategy optimization and comparison

