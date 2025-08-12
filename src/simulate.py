import json
import numpy as np
from engine import SlotGame  # assuming engine.py is in src/
from tqdm import tqdm

def baseline_policy(game: SlotGame):
    # Never buy upgrades, always continue until max rounds or fail
    return None  # no upgrade purchase

def aggressive_policy(game: SlotGame):
    # Buy reel_bias if affordable on first round
    if game.round == 1 and game.credits >= game.config["upgrades"]["reel_bias"]["cost"]:
        return "reel_bias"
    return None

def conservative_policy(game: SlotGame):
    # Buy bar_boost if affordable on round 1, else cash out after first bonus
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

    # Use last round's bar progress now!
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
            msg = game.buy_upgrade(action)
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

    print(f"Runs: {len(results)}")
    print(f"Average final credits: {final_credits.mean():.2f}")
    print(f"Median final credits: {np.median(final_credits):.2f}")
    print(f"Std dev final credits: {final_credits.std():.2f}")
    print(f"Average rounds played: {rounds_played.mean():.2f}")
    print(f"Average bonuses triggered: {bonuses.mean():.2f}")

if __name__ == "__main__":
    config_path = "D://pythonprojects/game_math/slot-game-project-1/data/example_config.json"

    print("Running baseline policy...")
    baseline_results = batch_simulate(config_path, baseline_policy, num_runs=1000)
    summarize_results(baseline_results)

    print("\nRunning aggressive policy...")
    aggressive_results = batch_simulate(config_path, aggressive_policy, num_runs=1000)
    summarize_results(aggressive_results)

    print("\nRunning conservative policy...")
    conservative_results = batch_simulate(config_path, conservative_policy, num_runs=1000)
    summarize_results(conservative_results)

    print("\nRunning adaptive AI policy...")
    adaptive_results = batch_simulate(config_path, adaptive_ai_policy, num_runs=1000)
    summarize_results(adaptive_results)


