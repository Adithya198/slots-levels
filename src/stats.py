# stats.py
import itertools
import pandas as pd
from engine import SlotGame 

def export_spin_stats(config_path, filename="D://pythonprojects/game_math/slot-game-project-1/outputs/spin_stats.xlsx"):
    game = SlotGame(config_path)
    symbols = game.symbols
    cols = game.cols
    base_multipliers = game.base_multipliers
    bar_fill_per_match = game.bar_fill_per_match
    symbol_probs = game.symbol_probs

    all_combinations = list(itertools.product(symbols, repeat=cols))
    rows = []

    for outcome in all_combinations:
        adjusted_probs = dict(symbol_probs)  # fresh copy for each outcome
        prob = 1.0
        counts = {s: 0 for s in symbols}

        for sym in outcome:
            total_prob = sum(adjusted_probs.values())
            norm_probs = {s: p / total_prob for s, p in adjusted_probs.items()}
            prob *= norm_probs[sym]
            counts[sym] += 1
            if counts[sym] == 2:
                adjusted_probs[sym] /= 2
            elif counts[sym] >= 3:
                adjusted_probs[sym] /= 4

        # Calculate bar fill increment (no upgrades)
        bar_fill = 0.0
        matched = False

        for sym, count in counts.items():
            if count == 3:
                bar_fill = base_multipliers[sym] * bar_fill_per_match["3_same"]
                matched = True
                break

        if not matched:
            for sym, count in counts.items():
                if count == 2:
                    bar_fill = base_multipliers[sym] * bar_fill_per_match["2_same"]
                    matched = True
                    break

        if not matched:
            singles = [s for s, c in counts.items() if c == 1]
            if singles:
                best_sym = max(singles, key=lambda s: base_multipliers[s])
                bar_fill = base_multipliers[best_sym] * bar_fill_per_match["1_same"]

        rows.append({
            "Outcome": ''.join(outcome),
            "Probability": prob,
            "3_same": any(count == 3 for count in counts.values()),
            "2_same": any(count == 2 for count in counts.values()),
            "1_same": sum(1 for count in counts.values() if count == 1) > 0 and not any(count >= 2 for count in counts.values()),
            "Bar_fill_increment": bar_fill,
        })

    df = pd.DataFrame(rows)
    df.sort_values("Probability", ascending=False, inplace=True)
    df.to_excel(filename, index=False)
    print(f"Exported conditional spin stats to {filename}")
