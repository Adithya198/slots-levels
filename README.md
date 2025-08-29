Slots Levels — Quantitative Slot Machine Simulation and Strategy Analysis
A Python-based simulation framework for analyzing upgrade strategies in a slot-machine style game with progressive rounds and purchasable upgrades. Unlike typical slot games, this design incorporates:

Dynamic bar-fill mechanics based on matching symbol combinations

Upgradable player strategies affecting spins, probabilities, and rewards

Rich statistical analysis and export of spin probabilities, expected returns, and game balance metrics

The goal is to demonstrate quantitative modeling and simulation expertise applied to game math, showcasing skills in probabilistic modeling, strategy optimization, and data-driven decision making


Files Overview
Core Game Logic:

engine.py - Main game engine implementing slot mechanics, upgrade system, and round progression
utils.py - Helper functions for generating upgrade strategies and formatting names

Analysis Tools:

simulate.py - Monte Carlo simulation runner that tests all upgrade strategies across multiple game runs
stats.py - Statistical analysis tool that calculates theoretical expected values and outcome distributions

Configuration:

config.json - Game parameters including symbols, probabilities, multipliers, and upgrade costs

Game Mechanics
Players start with 100 credits and must fill a progress bar each round to advance. The bar target increases each round (1.0 → 1.5 → 2.0). Three upgrades are available for purchase in rounds 2-3:

Reel Bias (50 credits): Increases probability of high-value symbols
Extra Spins (50 credits): +2 spins per round
Bonus Multiplier (50 credits): +1 to all symbol multipliers
