import pandas as pd
import numpy as np
import random
from engine import SlotGame, config
from utils import format_strategy_name, format_upgrade_combo_name


def run_single_game(config_dict, strategy_tuple):
    game = SlotGame(config_dict=config_dict)
    total_spins = 0
    rounds_played = 0
    upgrade_costs_paid = 0
    upgrades_purchased = []
    
    while game.round <= game.max_rounds:
        spins_this_round = game.spins_per_round + (2 if game.upgrades["extra_spins"] else 0)
        
        # Handle upgrade purchase decisions in rounds 2 and 3
        if game.round in (2, 3):
            choice = strategy_tuple[game.round - 2]
            if choice != "skip" and not game.upgrades.get(choice, False):
                upgrade_config = config_dict.get("upgrades", {})
                if choice in upgrade_config:
                    cost = float(upgrade_config[choice]["cost"])
                    if game.credits >= cost:
                        result = game.buy_upgrade(choice)
                        if "purchased successfully" in result:
                            upgrade_costs_paid += cost
                            upgrades_purchased.append(choice)
        
        # Play round
        bonus = game.play_round_silent()
        total_spins += spins_this_round
        rounds_played = game.round
        
        if not bonus:
            break
        
        if game.round < game.max_rounds:
            game.bar_target += 0.5
            game.round += 1
        else:
            break
    
    return {
        "final_credits": game.credits,
        "rounds_played": rounds_played,
        "total_spins": total_spins,
        "upgrade_costs_paid": upgrade_costs_paid,
        "upgrades_purchased": upgrades_purchased,
        "strategy": format_strategy_name(strategy_tuple)
    }


def simulate_strategy(config_dict, strategy_tuple, num_runs=10000, seed=None):
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
    
    results = []
    for i in range(num_runs):
        res = run_single_game(config_dict, strategy_tuple)
        results.append(res)
    
    df = pd.DataFrame(results)
    stats = {
        "strategy": format_strategy_name(strategy_tuple),
        "round2_upgrade": strategy_tuple[0],
        "round3_upgrade": strategy_tuple[1], 
        "upgrade_combination": format_upgrade_combo_name(list(strategy_tuple)),
        "num_runs": num_runs,
        "avg_final_credits": df["final_credits"].mean(),
        "std_final_credits": df["final_credits"].std(),
        "median_final_credits": df["final_credits"].median(),
        "min_final_credits": df["final_credits"].min(),
        "max_final_credits": df["final_credits"].max(),
        "avg_rounds_played": df["rounds_played"].mean(),
        "completion_rate": (df["rounds_played"] == 3).mean(),
        "avg_upgrade_costs": df["upgrade_costs_paid"].mean(),
        "net_credits_gained": df["final_credits"].mean() - 100,
        "roi": (df["final_credits"].mean() - 100) / 100,
    }
    return stats, df

