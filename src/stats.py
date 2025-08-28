# stats.py - Updated for final game configuration
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


def determine_strategy_viability(expected_per_round, bar_targets=[1.0, 1.5, 2.0]):
    """
    Determine if a strategy is viable based on expected bar fill per round.
    
    A strategy is viable if it can beat ALL round targets.
    Since the same expected value applies to all rounds in our analysis,
    the strategy must beat the highest target (Round 3 = 2.0).
    
    Args:
        expected_per_round: Expected bar fill per round for the strategy
        bar_targets: List of bar targets for each round
    
    Returns:
        dict: Viability analysis
    """
    can_beat_r1 = expected_per_round >= bar_targets[0]
    can_beat_r2 = expected_per_round >= bar_targets[1]
    can_beat_r3 = expected_per_round >= bar_targets[2]
    
    is_viable = can_beat_r1 and can_beat_r2 and can_beat_r3
    
    # Calculate safety margins (buffer above targets)
    r1_buffer = expected_per_round - bar_targets[0]
    r2_buffer = expected_per_round - bar_targets[1]
    r3_buffer = expected_per_round - bar_targets[2]
    
    # Determine risk level based on minimum buffer
    min_buffer = min(r1_buffer, r2_buffer, r3_buffer)
    if min_buffer >= 0.2:
        risk_level = "LOW"
    elif min_buffer >= 0.1:
        risk_level = "MEDIUM"
    elif min_buffer >= 0.0:
        risk_level = "HIGH"
    else:
        risk_level = "IMPOSSIBLE"
    
    return {
        "is_viable": is_viable,
        "can_beat_r1": can_beat_r1,
        "can_beat_r2": can_beat_r2,
        "can_beat_r3": can_beat_r3,
        "r1_buffer": r1_buffer,
        "r2_buffer": r2_buffer,
        "r3_buffer": r3_buffer,
        "min_buffer": min_buffer,
        "risk_level": risk_level
    }


def generate_strategy_summary(config):
    """
    Generate summary statistics for all upgrade strategies.
    """
    strategies = generate_upgrade_strategies()
    summary_rows = []
    bar_targets = [1.0, 1.5, 2.0]  # +0.5 progression per round

    print(f"Analyzing {len(strategies)} strategies")

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
        expected_per_round = exp_fill * spins_per_round
        
        # Determine viability
        viability = determine_strategy_viability(expected_per_round, bar_targets)
        
        # Calculate upgrade costs
        upgrade_cost = 0
        if round2_upgrade != "skip":
            upgrade_cost += config.get("upgrades", {}).get(round2_upgrade, {}).get("cost", 0)
        if round3_upgrade != "skip":
            upgrade_cost += config.get("upgrades", {}).get(round3_upgrade, {}).get("cost", 0)
        
        summary_rows.append({
            "Strategy": format_strategy_name(strategy_tuple),
            "Round_2_Upgrade": round2_upgrade,
            "Round_3_Upgrade": round3_upgrade,
            "Upgrade_Combination": format_upgrade_combo_name(list(strategy_tuple)),
            "Expected_Fill_per_Spin": exp_fill,
            "Std_Dev_Fill": std_fill,
            "Expected_Bonus_Contribution": exp_bonus_contrib,
            "Spins_per_Round": spins_per_round,
            "Expected_Fill_per_Round": expected_per_round,
            "Is_Viable": viability["is_viable"],
            "Can_Beat_R1": viability["can_beat_r1"],
            "Can_Beat_R2": viability["can_beat_r2"],
            "Can_Beat_R3": viability["can_beat_r3"],
            "R1_Buffer": viability["r1_buffer"],
            "R2_Buffer": viability["r2_buffer"],
            "R3_Buffer": viability["r3_buffer"],
            "Min_Buffer": viability["min_buffer"],
            "Risk_Level": viability["risk_level"],
            "Total_Upgrade_Cost": upgrade_cost,
            "Has_Reel_Bias": game.upgrades["reel_bias"],
            "Has_Extra_Spins": game.upgrades["extra_spins"],
            "Has_Bonus_Multiplier": game.upgrades["bonus_multiplier_upgrade"],
            "Avg_Symbol_Multiplier": sum(multipliers.values()) / len(multipliers),
            "High_Value_Prob_Sum": current_probs.get("D", 0) + current_probs.get("E", 0),
            "Expected_ROI": None,  # Will be calculated if viable
            "Expected_Final_Credits": None  # Will be calculated if viable
        })

    df = pd.DataFrame(summary_rows)
    
    # Calculate expected ROI and final credits for viable strategies
    starting_credits = config.get("credits_start", 100)
    for idx, row in df.iterrows():
        if row["Is_Viable"]:
            # Simple calculation: start -> R1 success -> R2 success -> R3 success
            # Round 1: base credits -> 2x
            # Round 2: (credits - upgrade_cost) -> 2x  
            # Round 3: (credits - upgrade_cost) -> 2x
            
            credits = starting_credits
            # Round 1: no upgrade cost, just multiply by 2
            credits *= 2
            
            # For rounds 2 and 3, subtract upgrade cost then multiply
            if row["Round_2_Upgrade"] != "skip":
                upgrade_cost = config.get("upgrades", {}).get(row["Round_2_Upgrade"], {}).get("cost", 0)
                credits -= upgrade_cost
            credits *= 2
            
            if row["Round_3_Upgrade"] != "skip":
                upgrade_cost = config.get("upgrades", {}).get(row["Round_3_Upgrade"], {}).get("cost", 0)
                credits -= upgrade_cost
            credits *= 2
            
            expected_final_credits = credits
            expected_roi = (expected_final_credits - starting_credits) / starting_credits
            
            df.at[idx, "Expected_ROI"] = expected_roi
            df.at[idx, "Expected_Final_Credits"] = expected_final_credits
    
    return df


def generate_detailed_spin_stats(config):
    """
    Generate detailed spin outcome statistics for all strategies.
    """
    strategies = generate_upgrade_strategies()
    all_spin_data = []

    print(f"Generating detailed spin statistics for {len(strategies)} strategies...")

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


def save_statistics_to_excel(config, output_path="outputs/statistics.xlsx"):
    """
    Generate and save statistics to Excel with multiple sheets:
    1. Strategy Summary: Aggregate numbers per strategy
    2. Spin Stats: Outcome-by-outcome table
    3. Viable Strategies Only: Filtered summary of viable strategies
    """
    try:
        # Generate both datasets
        print("Generating strategy summary...")
        strategy_summary = generate_strategy_summary(config)
        
        print("Generating detailed spin statistics...")
        spin_stats = generate_detailed_spin_stats(config)
        
        # Create viable strategies subset
        viable_strategies = strategy_summary[strategy_summary["Is_Viable"]].copy()
        viable_strategies = viable_strategies.sort_values("Expected_Fill_per_Round", ascending=False)
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        
        # Save to Excel with multiple sheets
        print(f"Saving results to {output_path}...")
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            # Sheet 1: Strategy Summary (all strategies)
            strategy_summary.to_excel(writer, sheet_name="Strategy Summary", index=False)
            
            # Sheet 2: Viable Strategies Only
            viable_strategies.to_excel(writer, sheet_name="Viable Strategies", index=False)
            
            # Sheet 3: Detailed Spin Stats (sample to avoid huge files)
            sample_spin_stats = spin_stats.sample(min(10000, len(spin_stats))) if len(spin_stats) > 10000 else spin_stats
            sample_spin_stats.to_excel(writer, sheet_name="Spin Stats Sample", index=False)
        
        print(f"Successfully saved statistics to {output_path}")
        print(f"Strategy Summary: {len(strategy_summary)} strategies")
        print(f"Viable Strategies: {len(viable_strategies)} strategies")
        print(f"Spin Stats: {len(spin_stats)} outcome records")
        
        # Print analysis summary
        print("\n" + "="*60)
        print("STATISTICAL ANALYSIS SUMMARY")
        print("="*60)
        
        print(f"Total strategies analyzed: {len(strategy_summary)}")
        print(f"Viable strategies: {len(viable_strategies)} ({len(viable_strategies)/len(strategy_summary)*100:.1f}%)")
        
        if len(viable_strategies) > 0:
            print(f"\nViability criteria: Expected bar fill per round >= 2.0")
            print("(Must beat Round 3 target to be considered viable)")
            
            print(f"\nTop 5 viable strategies by expected performance:")
            top_5 = viable_strategies.head(5)[["Strategy", "Expected_Fill_per_Round", "Risk_Level", "Expected_Final_Credits"]]
            print(top_5.to_string(index=False))
            
            print(f"\nRisk level distribution among viable strategies:")
            risk_counts = viable_strategies["Risk_Level"].value_counts()
            for risk_level, count in risk_counts.items():
                print(f"  {risk_level}: {count} strategies")
        
        return strategy_summary, viable_strategies, spin_stats
        
    except Exception as e:
        print(f"Error generating statistics: {str(e)}")
        raise


def analyze_upgrade_efficiency(config):
    """
    Analyze the efficiency of individual upgrades and combinations.
    """
    print("\n" + "="*60)
    print("UPGRADE EFFICIENCY ANALYSIS")
    print("="*60)
    
    # Test individual upgrades
    base_game = SlotGame(config_dict=config)
    base_expected, _, _ = expected_stats(base_game)
    base_per_round = base_expected * base_game.spins_per_round
    
    print(f"Base game expected bar fill per round: {base_per_round:.4f}")
    
    upgrades = ["reel_bias", "extra_spins", "bonus_multiplier_upgrade"]
    upgrade_effects = {}
    
    for upgrade in upgrades:
        game = SlotGame(config_dict=config)
        game.upgrades[upgrade] = True
        
        expected, _, _ = expected_stats(game)
        spins = game.spins_per_round + (2 if game.upgrades["extra_spins"] else 0)
        per_round = expected * spins
        
        improvement = per_round - base_per_round
        cost = config.get("upgrades", {}).get(upgrade, {}).get("cost", 0)
        efficiency = improvement / cost if cost > 0 else 0
        
        upgrade_effects[upgrade] = {
            "expected_per_round": per_round,
            "improvement": improvement,
            "cost": cost,
            "efficiency": efficiency
        }
        
        print(f"\n{upgrade.replace('_', ' ').title()}:")
        print(f"  Expected per round: {per_round:.4f}")
        print(f"  Improvement: +{improvement:.4f} ({improvement/base_per_round*100:.1f}%)")
        print(f"  Cost: {cost} credits")
        print(f"  Efficiency: {efficiency:.4f} improvement per credit")
    
    # Rank by efficiency
    print(f"\nUpgrade efficiency ranking:")
    sorted_upgrades = sorted(upgrade_effects.items(), key=lambda x: x[1]["efficiency"], reverse=True)
    for i, (upgrade, stats) in enumerate(sorted_upgrades, 1):
        print(f"  {i}. {upgrade.replace('_', ' ').title()}: {stats['efficiency']:.4f} per credit")
    
    return upgrade_effects


def main():
    # Load configuration
    config_path = os.path.join("data", "config.json")
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Config file not found at {config_path}")
        return
    except json.JSONDecodeError as e:
        print(f"Error parsing config file: {e}")
        return

    # Create output path
    output_path = os.path.join("outputs", "statistics.xlsx")
    
    # Generate and save statistics
    strategy_summary, viable_strategies, spin_stats = save_statistics_to_excel(config, output_path)
    
    # Analyze upgrade efficiency
    upgrade_effects = analyze_upgrade_efficiency(config)
    
    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()