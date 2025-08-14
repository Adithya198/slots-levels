import json
import numpy as np
import random
from tqdm import tqdm


class SlotGame:
    def __init__(self, config_path=None, config_dict=None):
        if config_dict is not None:
            self.config = config_dict
            self.config_path = None  # optional, since config is already loaded
        elif config_path is not None:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            self.config_path = config_path
        else:
            raise ValueError("Must provide either config_path or config_dict")

        self.credits = self.config["credits_start"]
        self.spins_per_round = self.config["spins_per_round"]

        reels_config = self.config["reels"]
        self.rows = reels_config["rows"]
        self.cols = reels_config["cols"]
        self.symbols = reels_config["symbols"]
        self.base_multipliers = reels_config["multipliers"]
        self.symbol_probs = reels_config["probabilities"]

        self.bar_fill_per_match = self.config["bar_fill_per_match"]
        self.base_bar_bonus_multiplier = self.config["bar_bonus_multiplier"]

        # State
        self.bar_progress = 0.0
        self.last_bar_progress = 0.0
        self.bar_target = 1.0
        self.round = 1
        self.max_rounds = 5
        self.upgrades = {
            "reel_bias": False,
            "extra_spins": 0,
            "bar_boost": 0,
            "bonus_multiplier_upgrade": False,
        }
        self.reel_bias_symbol = None


    def get_effective_multipliers(self):
        # If bonus_multiplier_upgrade is active, add 1 to all base multipliers
        if self.upgrades["bonus_multiplier_upgrade"]:
            return {s: val + 1 for s, val in self.base_multipliers.items()}
        else:
            return self.base_multipliers
        

    def spin_reels(self):
        base_probs = self.symbol_probs.copy()
        adjusted_probs = base_probs.copy()
        picks = []
        counts = {s: 0 for s in self.symbols}

        for col in range(self.cols):
            reel_probs = adjusted_probs.copy()

            # If reel_bias is active, double the probability for the target symbol only on this reel
            if self.upgrades["reel_bias"] and self.reel_bias_symbol is not None:
                reel_probs[self.reel_bias_symbol] *= 2

            total_prob = sum(reel_probs.values())
            norm_probs = {s: p / total_prob for s, p in reel_probs.items()}

            symbols = list(norm_probs.keys())
            weights = list(norm_probs.values())
            pick = random.choices(symbols, weights=weights, k=1)[0]
            picks.append(pick)
            counts[pick] += 1

            # Penalize repeated symbols in subsequent reels
            if counts[pick] == 2:
                adjusted_probs[pick] /= 2
            elif counts[pick] >= 3:
                adjusted_probs[pick] /= 4

        return picks




    def evaluate_spin(self, row):
        symbol_counts = {s: row.count(s) for s in self.symbols}
        bar_filled_this_spin = 0.0
        matched = False

        boost_factor = 1 + 0.5 * self.upgrades["bar_boost"]
        multipliers = self.get_effective_multipliers()

        for symbol, count in symbol_counts.items():
            if count == 3:
                increment = multipliers[symbol] * self.bar_fill_per_match["3_same"] * boost_factor
                self.bar_progress += increment
                bar_filled_this_spin += increment
                matched = True
            elif count == 2:
                increment = multipliers[symbol] * self.bar_fill_per_match["2_same"] * boost_factor
                self.bar_progress += increment
                bar_filled_this_spin += increment
                matched = True

        if not matched:
            singles = [s for s, c in symbol_counts.items() if c == 1]
            if singles:
                best_symbol = max(singles, key=lambda s: multipliers[s])
                increment = multipliers[best_symbol] * self.bar_fill_per_match["1_same"] * boost_factor
                self.bar_progress += increment
                bar_filled_this_spin += increment

        if self.bar_progress > self.bar_target:
            self.bar_progress = self.bar_target

        return bar_filled_this_spin

    def play_round(self):
        self.bar_progress = 0.0
        spins_this_round = self.spins_per_round + self.upgrades["extra_spins"]
        print(f"\nRound {self.round} | Bar target: {self.bar_target:.2f} | Spins this round: {spins_this_round} | Credits: {self.credits}")

        for spin_num in range(1, spins_this_round + 1):
            row = self.spin_reels()
            filled = self.evaluate_spin(row)
            print(f"Spin {spin_num}: {row} | Bar filled this spin: {filled:.4f} | Total bar progress: {self.bar_progress:.4f}")

        bonus_triggered = False
        if self.bar_progress >= self.bar_target:
            multiplier = self.base_bar_bonus_multiplier
            self.credits *= multiplier
            bonus_triggered = True
            print(f"Bonus triggered! Credits multiplied by {multiplier}. New credits: {self.credits}")
        else:
            print("No bonus this round.")

        self.last_bar_progress = self.bar_progress

        # Only progress to next round if bonus triggered and not max rounds
        if bonus_triggered and self.round < self.max_rounds:
            self.bar_target += 1.0
            self.round += 1
        else:
            self.round = self.max_rounds + 1  # end game flag

        return bonus_triggered


        return bonus_triggered
    
    def buy_upgrade(self, upgrade_name):
        upgrade_config = self.config["upgrades"]
        if upgrade_name not in upgrade_config:
            return f"Upgrade '{upgrade_name}' does not exist."
        cost = upgrade_config[upgrade_name]["cost"]
        if self.credits < cost:
            return f"Not enough credits to buy {upgrade_name} (cost: {cost}, credits: {self.credits})"
        self.credits -= cost

        if upgrade_name in ["extra_spins", "bar_boost"]:
            self.upgrades[upgrade_name] += 1
        elif upgrade_name == "reel_bias":
            self.upgrades[upgrade_name] = True
            # Choose symbol with highest multiplier by default
            self.reel_bias_symbol = max(self.symbols, key=lambda s: self.base_multipliers[s])
        else:
            self.upgrades[upgrade_name] = True

        return f"Upgrade {upgrade_name} purchased successfully."



    def play_game(self):
        while self.round <= self.max_rounds:
            bonus = self.play_round()
            if not bonus:
                print("Bar not filled — game ends.")
                break
            if self.round == self.max_rounds:
                print("Max rounds reached. Game ends.")
                break

            # For difficulty increase: add 1.0 to bar target per round
            self.bar_target += 1.0
            self.round += 1
            print(f"Proceeding to round {self.round} with bar target now {self.bar_target:.2f}")

        print(f"Game over. Final credits: {self.credits}")
