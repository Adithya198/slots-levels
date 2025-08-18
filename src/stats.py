# stats.py
import json
import numpy as np
import pandas as pd
import itertools
import os
from engine import SlotGame
from utils import generate_upgrade_strategies, format_strategy_name, format_upgrade_combo_name


def bar_fill_distribution(game: SlotGame):
    """
    Returns probability distribution of bar fill increments per spin
    given current upgrades.
    """
    symbols = game.symbols
    multipliers = game.get_effective_multipliers()
    current_probs = game.get_current_probabilities()

    values = []
    probs = []

    for row in itertools.product(symbols, repeat=game.cols):
        # probability of this row
        p_row = 1.0
        for sym in row:
            p_row *= current_probs[sym]

        symbol_counts = {s: row.count(s) for s in symbols}
        increment = 0.0

        for symbol, count in symbol_counts.items():
            if count == 3:
                increment += multipliers[symbol] * game.bar_fill_per_match.get("3_same", 0.0)
            elif count == 2:
                increment += multipliers[symbol] * game.bar_fill_per_match.get("2_same", 0.0)

        if increment == 0.0 and game.bar_fill_per_match.get("1_same", 0.0) > 0:
            singles = [s for s, c in symbol_counts.items() if c == 1]
            if singles:
                best_symbol = max(singles, key=lambda s: multipliers[s])
                increment = multipliers[best_symbol] * game.bar_fill_per_match.get("1_same", 0.0)

        values.append(increment)
        probs.append(p_row)

    return np.array(values), np.array(probs)


def expected_stats(game: SlotGame):
    """
    Compute expected bar fill and its stddev per spin.
    Expected Bonus Contribution = expected fill * bar_bonus_multiplier.
    """
    values, probs = bar_fill_distribution(game)
    exp = np.sum(values * probs)
    exp_sq = np.sum((values ** 2) * probs)
    var = exp_sq - exp ** 2
    std = np.sqrt(max(var, 0.0))

    expected_bonus_contribution = exp * game.base_bar_bonus_multiplier
    return exp, std, expected_bonus_contribution


def generate_spin_outcomes(game: SlotGame, strategy_tuple):
    """
    Generate all possible spin outcomes with their probabilities and bar fills
    for a given game configuration and upgrade strategy.
    """
    symbols = game.symbols
    multipliers = game.get_effective_multipliers()
    current_probs = game.get_current_probabilities()
    
    # Generate all possible outcomes
    all_outcomes = list(itertools.product(symbols, repeat=game.cols))
    
    results = []
    for outcome in all_outcomes:
        outcome_str = "".join(outcome)
        
        # Calculate probability of this outcome
        prob = 1.0
        for symbol in outcome:
            prob *= current_probs[symbol]
        
        # Classify the outcome
        classification = game.classify_outcome(list(outcome))
        
        # Calculate bar fill for this outcome
        symbol_counts = {s: outcome.count(s) for s in symbols}
        bar_fill = 0.0
        
        for symbol, count in symbol_counts.items():
            if count == 3:
                bar_fill += multipliers[symbol] * game.bar_fill_per_match.get("3_same", 0.0)
            elif count == 2:
                bar_fill += multipliers[symbol] * game.bar_fill_per_match.get("2_same", 0.0)
        
        # Handle 1_same case if no matches found
        if bar_fill == 0.0 and game.bar_fill_per_match.get("1_same", 0.0) > 0:
            singles = [s for s, c in symbol_counts.items() if c == 1]
            if singles:
                best_symbol = max(singles, key=lambda s: multipliers[s])
                bar_fill = multipliers[best_symbol] * game.bar_fill_per_match.get("1_same", 0.0)
        
        results.append({
            "Outcome": outcome_str,
            "Classification": classification,
            "Barfill": bar_fill,
            "Probability": prob,
            "Strategy": format_strategy_name(strategy_tuple),
            "Upgrade_Combination": format_upgrade_combo_name(list(strategy_tuple))
        })
    
    return pd.DataFrame(results)


def generate_strategy_summary(config):
    """
    Generate summary statistics for all upgrade strategies.
    """
    strategies = generate_upgrade_strategies()
    summary_rows = []

    for strategy_tuple in strategies:
        # Create fresh game for each strategy
        game = SlotGame(config_dict=config)
        
        # Apply upgrades (ignoring costs for theoretical analysis)
        round2_upgrade, round3_upgrade = strategy_tuple
        if round2_upgrade != "skip":
            game.upgrades[round2_upgrade] = True
        if round3_upgrade != "skip":
            game.upgrades[round3_upgrade] = True

        # Calculate statistics
        exp_fill, std_fill, exp_bonus_contrib = expected_stats(game)
        
        # Get additional info
        current_probs = game.get_current_probabilities()
        multipliers = game.get_effective_multipliers()
        
        # Calculate spins per round with upgrades
        spins_per_round = game.spins_per_round + (2 if game.upgrades["extra_spins"] else 0)
        
        summary_rows.append({
            "Strategy": format_strategy_name(strategy_tuple),
            "Round_2_Upgrade": round2_upgrade,
            "Round_3_Upgrade": round3_upgrade,
            "Upgrade_Combination": format_upgrade_combo_name(list(strategy_tuple)),
            "Expected_Fill_per_Spin": exp_fill,
            "Std_Dev_Fill": std_fill,
            "Expected_Bonus_Contribution": exp_bonus_contrib,
            "Spins_per_Round": spins_per_round,
            "Expected_Fill_per_Round": exp_fill * spins_per_round,
            "Has_Reel_Bias": game.upgrades["reel_bias"],
            "Has_Extra_Spins": game.upgrades["extra_spins"],
            "Has_Bonus_Multiplier": game.upgrades["bonus_multiplier_upgrade"],
            "Avg_Symbol_Multiplier": sum(multipliers.values()) / len(multipliers),
            "High_Value_Prob_Sum": current_probs.get("D", 0) + current_probs.get("E", 0)
        })

    return pd.DataFrame(summary_rows)


def generate_detailed_spin_stats(config):
    """
    Generate detailed spin outcome statistics for all strategies.
    """
    strategies = generate_upgrade_strategies()
    all_spin_data = []

    for strategy_tuple in strategies:
        # Create fresh game for each strategy
        game = SlotGame(config_dict=config)
        
        # Apply upgrades
        round2_upgrade, round3_upgrade = strategy_tuple
        if round2_upgrade != "skip":
            game.upgrades[round2_upgrade] = True
        if round3_upgrade != "skip":
            game.upgrades[round3_upgrade] = True

        # Generate spin outcomes for this strategy
        spin_data = generate_spin_outcomes(game, strategy_tuple)
        all_spin_data.append(spin_data)

    return pd.concat(all_spin_data, ignore_index=True)


def save_statistics_to_excel(config, output_path="statistics.xlsx"):
    """
    Generate and save statistics to Excel with two sheets:
    1. Strategy Summary: Aggregate numbers per strategy
    2. Spin Stats: Outcome-by-outcome table
    """
    try:
        # Generate both datasets
        print("Generating strategy summary...")
        strategy_summary = generate_strategy_summary(config)
        
        print("Generating detailed spin statistics...")
        spin_stats = generate_detailed_spin_stats(config)
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        
        # Save to Excel with multiple sheets
        print(f"Saving results to {output_path}...")
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            # Sheet 1: Strategy Summary
            strategy_summary.to_excel(
                writer, 
                sheet_name="Strategy Summary", 
                index=False
            )
            
            # Sheet 2: Detailed Spin Stats
            spin_stats.to_excel(
                writer, 
                sheet_name="Spin Stats", 
                index=False
            )
        
        print(f"Successfully saved statistics to {output_path}")
        print(f"Strategy Summary: {len(strategy_summary)} strategies")
        print(f"Spin Stats: {len(spin_stats)} outcome records")
        
        # Print a quick preview
        print("\nTop 5 strategies by expected fill per round:")
        top_strategies = strategy_summary.nlargest(5, "Expected_Fill_per_Round")[
            ["Strategy", "Expected_Fill_per_Round", "Expected_Bonus_Contribution"]
        ]
        print(top_strategies.to_string(index=False))
        
    except Exception as e:
        print(f"Error generating statistics: {str(e)}")
        raise


def main():
    # Use relative path for config file
    config_path = os.path.join("data", "example_config.json")
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Config file not found at {config_path}")
        print("Please ensure the config file exists or update the path")
        return
    except json.JSONDecodeError as e:
        print(f"Error parsing config file: {e}")
        return

    # Create output path
    output_path = os.path.join("outputs", "statistics.xlsx")
    
    # Generate and save statistics
    save_statistics_to_excel(config, output_path)


if __name__ == "__main__":
    main()

