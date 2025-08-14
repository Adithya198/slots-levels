import json
import numpy as np
import pandas as pd
from engine import SlotGame
from tqdm import tqdm

def baseline_policy(game: SlotGame):
    return None

def aggressive_policy(game: SlotGame):
    if game.round == 1 and game.credits >= game.config["upgrades"]["reel_bias"]["cost"]:
        return "reel_bias"
    return None

def conservative_policy(game: SlotGame):
    if game.round == 1 and game.credits >= game.config["upgrades"]["bar_boost"]["cost"]:
        return "bar_boost"
    if game.round > 1:
        return "cashout"
    return None

def adaptive_ai_policy(game: SlotGame):
    min_cost = min(u["cost"] for u in game.config["upgrades"].values())
    if game.credits < min_cost:
        if game.credits < 50:
            return "cashout"
        return None

    if game.round == 1 and game.credits >= game.config["upgrades"]["reel_bias"]["cost"]:
        return "reel_bias"

    if game.last_bar_progress < 0.5 and game.credits >= game.config["upgrades"]["extra_spins"]["cost"]:
        return "extra_spins"

    if game.round >= 2 and game.credits >= game.config["upgrades"]["bar_boost"]["cost"]:
        return "bar_boost"

    if game.credits >= game.config["upgrades"]["bonus_multiplier_upgrade"]["cost"]:
        return "bonus_multiplier_upgrade"

    if game.round >= 3 and game.credits >= 150:
        return "cashout"

    return None


def run_single_sim(config_path, policy_fn):
    game = SlotGame(config_path)
    results = {
        "final_credits": None,
        "rounds_played": 0,
        "bonuses_triggered": 0,
        "upgrades_bought": [],
    }
    while game.round <= game.max_rounds:
        bonus = game.play_round()
        results["rounds_played"] = game.round
        if bonus:
            results["bonuses_triggered"] += 1

        action = policy_fn(game)
        if action == "cashout":
            break
        elif action is not None and action in game.config["upgrades"]:
            game.buy_upgrade(action)
            results["upgrades_bought"].append(action)

    results["final_credits"] = game.credits
    return results


def batch_simulate(config_path, policy_fn, num_runs=1000):
    all_results = []
    for _ in tqdm(range(num_runs)):
        res = run_single_sim(config_path, policy_fn)
        all_results.append(res)
    return all_results


def summarize_results(results):
    final_credits = np.array([r["final_credits"] for r in results])
    rounds_played = np.array([r["rounds_played"] for r in results])
    bonuses = np.array([r["bonuses_triggered"] for r in results])

    return {
        "runs": len(results),
        "avg_final_credits": final_credits.mean(),
        "median_final_credits": np.median(final_credits),
        "std_final_credits": final_credits.std(),
        "avg_rounds_played": rounds_played.mean(),
        "avg_bonuses_triggered": bonuses.mean(),
    }


if __name__ == "__main__":
    config_path = "D://pythonprojects/game_math/slot-game-project-1/data/example_config.json"

    all_summary = []

    print("Running baseline policy...")
    baseline_results = batch_simulate(config_path, baseline_policy, num_runs=1000)
    summary = summarize_results(baseline_results)
    summary["policy"] = "baseline"
    all_summary.append(summary)
    print(summary)

    print("\nRunning aggressive policy...")
    aggressive_results = batch_simulate(config_path, aggressive_policy, num_runs=1000)
    summary = summarize_results(aggressive_results)
    summary["policy"] = "aggressive"
    all_summary.append(summary)
    print(summary)

    print("\nRunning conservative policy...")
    conservative_results = batch_simulate(config_path, conservative_policy, num_runs=1000)
    summary = summarize_results(conservative_results)
    summary["policy"] = "conservative"
    all_summary.append(summary)
    print(summary)

    print("\nRunning adaptive AI policy...")
    adaptive_results = batch_simulate(config_path, adaptive_ai_policy, num_runs=1000)
    summary = summarize_results(adaptive_results)
    summary["policy"] = "adaptive_ai"
    all_summary.append(summary)
    print(summary)

    # Export to CSV
    df = pd.DataFrame(all_summary)
    output_path = "D://pythonprojects/game_math/slot-game-project-1/sim_results.csv"
    df.to_csv(output_path, index=False)
    print(f"\nSimulation results saved to: {output_path}")


