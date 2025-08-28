# simulate.py
import itertools
import numpy as np
import pandas as pd
import os
import json
import random
from tqdm import tqdm
from engine import SlotGame
from utils import generate_upgrade_strategies, format_strategy_name, format_upgrade_combo_name


def run_single_game(config_dict, strategy_tuple, verbose=False):
    """
    Run a single game following a fixed strategy.
    
    Args:
        config_dict: Game configuration dictionary
        strategy_tuple: Tuple of (round2_upgrade, round3_upgrade)
        verbose: If True, print detailed game progress
    
    Returns:
        Dictionary with game results
    """
    game = SlotGame(config_dict=config_dict)
    total_spins = 0
    total_bar_progress = 0
    rounds_played = 0
    upgrade_costs_paid = 0
    upgrades_purchased = []
    round_results = []

    if verbose:
        print(f"\n Starting game with strategy: {format_strategy_name(strategy_tuple)} ---")

    while game.round <= game.max_rounds:
        round_start_credits = game.credits
        spins_this_round = game.spins_per_round + (2 if game.upgrades["extra_spins"] else 0)
        
        if verbose:
            print(f"\nRound {game.round} | Bar target: {game.bar_target:.2f} | Credits: {game.credits:.2f}")
        
        # Strategy purchase logic: BEFORE playing the round, on rounds 2 and 3
        upgrade_bought_this_round = None
        upgrade_cost_this_round = 0
        
        if game.round in (2, 3):
            choice = strategy_tuple[game.round - 2]  # 0 for round 2, 1 for round 3
            if choice != "skip" and not game.upgrades.get(choice, False):
                # Check if we can afford the upgrade
                upgrade_config = config_dict.get("upgrades", {})
                if choice in upgrade_config:
                    cost = float(upgrade_config[choice]["cost"])
                    if game.credits >= cost:
                        result = game.buy_upgrade(choice)
                        if "purchased successfully" in result:
                            upgrade_bought_this_round = choice
                            upgrade_cost_this_round = cost
                            upgrade_costs_paid += cost
                            upgrades_purchased.append(choice)
                            if verbose:
                                print(f"  Purchased upgrade: {choice} for {cost} credits")
                        elif verbose:
                            print(f"  Failed to buy upgrade: {result}")
                    elif verbose:
                        print(f"  Cannot afford upgrade {choice} (cost: {cost}, credits: {game.credits:.2f})")

        # Play the round
        round_bar_start = game.bar_progress
        bonus = game.play_round_silent()
        round_bar_end = game.bar_progress
        
        total_spins += spins_this_round
        total_bar_progress += round_bar_end
        rounds_played = game.round
        
        # Record round results
        round_results.append({
            "round": game.round,
            "bar_target": game.bar_target,
            "bar_progress": round_bar_end,
            "bonus_triggered": bonus,
            "spins": spins_this_round,
            "credits_start": round_start_credits,
            "credits_end": game.credits,
            "upgrade_bought": upgrade_bought_this_round,
            "upgrade_cost": upgrade_cost_this_round
        })

        if verbose:
            print(f"  Bar progress: {round_bar_end:.4f}/{game.bar_target:.2f}")
            print(f"  Bonus triggered: {bonus}")
            print(f"  Credits after round: {game.credits:.2f}")

        if not bonus:
            if verbose:
                print("  Game ended - bonus not triggered")
            break

        # Move to next round
        if game.round < game.max_rounds:
            game.bar_target += 0.5  # +0.5 progression per round
            game.round += 1
        else:
            if verbose:
                print("  Max rounds reached")
            break

    if verbose:
        print(f"\nGame completed")
        print(f"Final credits: {game.credits:.2f}")
        print(f"Rounds played: {rounds_played}")
        print(f"Total upgrade costs: {upgrade_costs_paid:.2f}")

    return {
        "final_credits": game.credits,
        "rounds_played": rounds_played,
        "total_spins": total_spins,
        "total_bar_progress": total_bar_progress,
        "avg_bar_progress_per_round": total_bar_progress / rounds_played if rounds_played > 0 else 0,
        "upgrade_costs_paid": upgrade_costs_paid,
        "upgrades_purchased": upgrades_purchased,
        "round_results": round_results,
        "strategy": format_strategy_name(strategy_tuple),
        "upgrade_combination": format_upgrade_combo_name(list(strategy_tuple)),
        "completed_all_rounds": rounds_played >= 3
    }


def simulate_strategy(config_dict, strategy_tuple, num_runs=1000, seed=None, verbose_sample=False):
    """
    Simulate a strategy multiple times and return summary statistics.
    
    Args:
        config_dict: Game configuration
        strategy_tuple: Strategy to simulate
        num_runs: Number of simulation runs
        seed: Random seed for reproducibility
        verbose_sample: If True, show verbose output for first run
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    results = []
    strategy_name = format_strategy_name(strategy_tuple)
    
    for i in tqdm(range(num_runs), desc=f"Simulating {strategy_name}", leave=False):
        verbose = verbose_sample and i == 0
        res = run_single_game(config_dict, strategy_tuple, verbose=verbose)
        results.append(res)

    df = pd.DataFrame(results)
    
    # Calculate statistics
    stats = {
        "strategy": strategy_name,
        "round2_upgrade": strategy_tuple[0],
        "round3_upgrade": strategy_tuple[1], 
        "upgrade_combination": format_upgrade_combo_name(list(strategy_tuple)),
        "num_runs": num_runs,
        
        # Credits statistics
        "avg_final_credits": df["final_credits"].mean(),
        "std_final_credits": df["final_credits"].std(),
        "median_final_credits": df["final_credits"].median(),
        "min_final_credits": df["final_credits"].min(),
        "max_final_credits": df["final_credits"].max(),
        
        # Performance statistics
        "avg_rounds_played": df["rounds_played"].mean(),
        "std_rounds_played": df["rounds_played"].std(),
        "completion_rate": df["completed_all_rounds"].mean(),
        "success_rate": df["completed_all_rounds"].mean(),  # Same as completion rate
        
        # Efficiency statistics
        "avg_total_spins": df["total_spins"].mean(),
        "std_total_spins": df["total_spins"].std(),
        "avg_spins_per_round": df["total_spins"].mean() / df["rounds_played"].mean() if df["rounds_played"].mean() > 0 else 0,
        
        # Bar progress statistics  
        "avg_total_bar_progress": df["total_bar_progress"].mean(),
        "avg_bar_progress_per_round": df["avg_bar_progress_per_round"].mean(),
        
        # Economic statistics
        "avg_upgrade_costs": df["upgrade_costs_paid"].mean(),
        "net_credits_gained": df["final_credits"].mean() - 100,  # Starting credits = 100
        "roi": (df["final_credits"].mean() - 100) / 100,  # Return on investment
        
        # Risk statistics
        "failure_rate": 1 - df["completed_all_rounds"].mean(),
        "credits_risk": df["final_credits"].std() / df["final_credits"].mean() if df["final_credits"].mean() > 0 else 0,
    }
    
    return stats, df


def run_comprehensive_simulation(config_dict, num_runs=1000, seed=42, output_dir="outputs"):
    """
    Run simulation for all strategies and save detailed results.
    """
    print("Starting comprehensive simulation...")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    strategies = generate_upgrade_strategies()
    all_summary_stats = []
    all_detailed_results = []
    
    print(f"Found {len(strategies)} strategies to simulate")
    
    for i, strategy_tuple in enumerate(strategies):
        print(f"\n--- Strategy {i+1}/{len(strategies)}: {format_strategy_name(strategy_tuple)} ---")
        
        # Run simulation
        summary_stats, detailed_df = simulate_strategy(
            config_dict, 
            strategy_tuple, 
            num_runs=num_runs, 
            seed=seed + i,  # Different seed for each strategy
            verbose_sample=(i == 0)  # Show verbose output for first strategy only
        )
        
        all_summary_stats.append(summary_stats)
        
        # Add strategy info to detailed results
        detailed_df["strategy"] = summary_stats["strategy"]
        detailed_df["strategy_tuple"] = str(strategy_tuple)
        all_detailed_results.append(detailed_df)
    
    # Create summary DataFrame
    summary_df = pd.DataFrame(all_summary_stats)
    
    # Combine all detailed results
    detailed_df = pd.concat(all_detailed_results, ignore_index=True)
    
    # Save results to Excel
    output_path = os.path.join(output_dir, "simulation_results.xlsx")
    print(f"\nSaving results to {output_path}...")
    
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # Summary sheet
        summary_df.to_excel(writer, sheet_name="Strategy Summary", index=False)
        
        # Detailed results sheet (sample to avoid huge files)
        sample_detailed = detailed_df.sample(min(10000, len(detailed_df))) if len(detailed_df) > 10000 else detailed_df
        sample_detailed.to_excel(writer, sheet_name="Sample Detailed Results", index=False)
    
    # Also save summary as CSV for easy reading
    csv_path = os.path.join(output_dir, "simulation_summary.csv")
    summary_df.to_csv(csv_path, index=False)
    
    print(f"Results saved to:")
    print(f"  - Excel: {output_path}")
    print(f"  - CSV: {csv_path}")
    
    # Print top performing strategies
    print("\n TOP 5 STRATEGIES BY AVERAGE FINAL CREDITS ")
    top_credits = summary_df.nlargest(5, "avg_final_credits")[
        ["strategy", "avg_final_credits", "completion_rate", "roi"]
    ]
    print(top_credits.to_string(index=False))
    
    print("\n TOP 5 STRATEGIES BY COMPLETION RATE")
    top_completion = summary_df.nlargest(5, "completion_rate")[
        ["strategy", "completion_rate", "avg_final_credits", "avg_rounds_played"]
    ]
    print(top_completion.to_string(index=False))
    
    print("\n TOP 5 STRATEGIES BY ROI ")
    top_roi = summary_df.nlargest(5, "roi")[
        ["strategy", "roi", "avg_final_credits", "net_credits_gained"]
    ]
    print(top_roi.to_string(index=False))
    
    return summary_df, detailed_df


# Add silent version of play_round to SlotGame class
def add_silent_play_round():
    """Add a silent version of play_round to SlotGame for simulation"""
    def play_round_silent(self):
        """
        Plays one round silently (no print output) and returns True if bonus triggered.
        """
        self.bar_progress = 0.0
        self.upgrade_bought_this_round = False

        spins_this_round = self.spins_per_round + (2 if self.upgrades["extra_spins"] else 0)

        for spin_num in range(1, spins_this_round + 1):
            row = self.spin_reels()
            payout, filled = self.evaluate_spin(row)

        bonus_triggered = False
        if self.bar_progress >= self.bar_target:
            multiplier = float(self.base_bar_bonus_multiplier)
            self.credits *= multiplier
            bonus_triggered = True

        return bonus_triggered
    
    # Add method to SlotGame class
    SlotGame.play_round_silent = play_round_silent


def main():
    # Add silent play_round method
    add_silent_play_round()
    
    # Load configuration
    config_path = os.path.join("data", "example_config.json")
    
    # If config file doesn't exist, create default config
    if not os.path.exists(config_path):
        os.makedirs("data", exist_ok=True)
        default_config = {
            "credits_start": 100,
            "spins_per_round": 8,
            "max_rounds": 3,
            "initial_bar_target": 1.0,
            "reels": {
                "rows": 1,
                "cols": 3,
                "symbols": ["A", "B", "C", "D", "E"],
                "multipliers": {"A": 2, "B": 3, "C": 4, "D": 5, "E": 6},
                "probabilities": {"A": 0.2, "B": 0.2, "C": 0.2, "D": 0.2, "E": 0.2}
            },
            "bar_fill_per_match": {"3_same": 0.20, "2_same": 0.067, "1_same": 0},
            "bar_bonus_multiplier": 2.0,
            "upgrades": {
                "reel_bias": {
                    "cost": 50,
                    "effect": "increase the probability of D by 5% and E by 10%, decrease the probability of A by 10% and B by 5%"
                },
                "extra_spins": {
                    "cost": 50,
                    "effect": "+2 spins per round"
                },
                "bonus_multiplier_upgrade": {
                    "cost": 50,
                    "effect": "increase all symbol multipliers by 1.0"
                }
            }
        }
        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=2)
        print(f"Created default config at {config_path}")
    
    try:
        with open(config_path, "r") as f:
            config_dict = json.load(f)
    except FileNotFoundError:
        print(f"Config file not found at {config_path}")
        return
    except json.JSONDecodeError as e:
        print(f"Error parsing config file: {e}")
        return

    # Run comprehensive simulation
    summary_df, detailed_df = run_comprehensive_simulation(
        config_dict, 
        num_runs=1000, 
        seed=42,
        output_dir="outputs"
    )
    
    print("\nSimulation completed successfully")
    print(f"Analyzed {len(summary_df)} strategies with {summary_df['num_runs'].iloc[0]} runs each")


if __name__ == "__main__":
    main()