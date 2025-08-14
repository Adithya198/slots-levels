# stats.py
import itertools
import pandas as pd
from engine import SlotGame
from itertools import chain, combinations
import copy

def all_upgrade_combos():
    upgrades = ["reel_bias", "extra_spins", "bar_boost", "bonus_multiplier_upgrade"]
    return chain.from_iterable(combinations(upgrades, r) for r in range(len(upgrades)+1))

def compute_spin_probability(outcome, game):
    """
    Deterministic probability calculation for a spin given the current game state.
    """
    counts = {s: 0 for s in game.symbols}
    prob = 1.0
    adjusted_probs = copy.deepcopy(game.symbol_probs)

    for col, sym in enumerate(outcome):
        reel_probs = copy.deepcopy(adjusted_probs)
        if game.upgrades["reel_bias"] and game.reel_bias_symbol:
            reel_probs[game.reel_bias_symbol] *= 2

        total_prob = sum(reel_probs.values())
        norm_probs = {s: p / total_prob for s, p in reel_probs.items()}

        prob *= norm_probs[sym]
        counts[sym] += 1

        # Penalize repeated symbols
        if counts[sym] == 2:
            adjusted_probs[sym] /= 2
        elif counts[sym] >= 3:
            adjusted_probs[sym] /= 4

    return prob

def enumerate_round_outcomes(game, round_num=1, max_rounds=3, path=None, prob_path=1.0, upgrade_path=None):
    if path is None:
        path = []

    all_results = []

    # Apply upgrades for this branch
    for u in upgrade_path or []:
        game.buy_upgrade(u)

    for outcome in itertools.product(game.symbols, repeat=game.cols):
        g = SlotGame(config_dict=game.config)  # clone
        g.credits = game.credits
        g.bar_progress = game.bar_progress
        g.last_bar_progress = game.last_bar_progress
        g.round = game.round
        g.upgrades = game.upgrades.copy()

        # Spin outcome
        counts = {s: outcome.count(s) for s in g.symbols}
        filled = g.evaluate_spin(list(outcome))

        # Compute probability for this outcome
        prob = 1.0
        adjusted_probs = g.symbol_probs.copy()
        for s in outcome:
            total_prob = sum(adjusted_probs.values())
            norm_probs = {k: v / total_prob for k, v in adjusted_probs.items()}
            prob *= norm_probs[s]
            # adjust for repeats
            if counts[s] == 2:
                adjusted_probs[s] /= 2
            elif counts[s] >= 3:
                adjusted_probs[s] /= 4

        full_prob = prob_path * prob
        new_path = path + ["".join(outcome)]

        # Check if bonus triggered
        bonus = g.bar_progress >= g.bar_target

        if round_num < max_rounds and bonus:
            g.bar_target += 1.0
            g.round += 1
            # recurse
            all_results.extend(enumerate_round_outcomes(
                g,
                round_num=round_num + 1,
                max_rounds=max_rounds,
                path=new_path,
                prob_path=full_prob,
                upgrade_path=upgrade_path
            ))
        else:
            # end branch
            all_results.append({
                "path": new_path,
                "probability": full_prob,
                "round": round_num,
                "upgrades": upgrade_path,
                "bar_progress": g.bar_progress,
            })

    return all_results


def export_multi_round_stats(config_path, filename="D://pythonprojects/game_math/slot-game-project-1/outputs/multi_round_stats.xlsx"):
    all_results = []

    for upgrade_combo in all_upgrade_combos():
        game = SlotGame(config_path)
        results = enumerate_round_outcomes(game, round_num=1, max_rounds=3, path=None, prob_path=1.0, upgrade_path=list(upgrade_combo))
        all_results.extend(results)

    df = pd.DataFrame(all_results)
    df.sort_values("probability", ascending=False, inplace=True)
    df.to_excel(filename, index=False)
    print(f"Exported multi-round stats to {filename}")

