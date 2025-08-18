# engine.py
import json
import random


class SlotGame:
    def __init__(self, config_path=None, config_dict=None):
        if config_dict is not None:
            self.config = config_dict
        elif config_path is not None:
            with open(config_path, "r") as f:
                self.config = json.load(f)
        else:
            raise ValueError("Must provide either config_path or config_dict")

        self._validate_config()
        self.credits = float(self.config.get("credits_start", 100))
        self.spins_per_round = int(self.config.get("spins_per_round", 10))

        reels_config = self.config["reels"]
        self.rows = int(reels_config.get("rows", 1))
        self.cols = int(reels_config.get("cols", 3))
        self.symbols = list(reels_config["symbols"])
        self.base_multipliers = {s: float(v) for s, v in reels_config["multipliers"].items()}
        
        # Create normalized base probabilities
        raw_probs = {s: float(reels_config["probabilities"].get(s, 0.0)) for s in self.symbols}
        self.base_symbol_probs = self._normalize_probabilities(raw_probs)

        self.bar_fill_per_match = self.config.get(
            "bar_fill_per_match",
            {"3_same": 0.1, "2_same": 0.05, "1_same": 0}
        )
        self.base_bar_bonus_multiplier = float(self.config.get("bar_bonus_multiplier", 2.0))

        # Game state
        self.bar_progress = 0.0
        self.bar_target = float(self.config.get("initial_bar_target", 1.0))
        self.round = 1
        self.max_rounds = int(self.config.get("max_rounds", 3))

        # upgrades (all single-purchase)
        self.upgrades = {
            "reel_bias": False,
            "extra_spins": False,               # one-time +2 spins when True
            "bonus_multiplier_upgrade": False,  # one-time +0.5 to multipliers
        }

        # Track per-round upgrade purchase restriction
        self.upgrade_bought_this_round = False

    def _validate_config(self):
        """Validate that config has all required keys and consistent data"""
        required_keys = ["reels"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")
        
        reels_config = self.config["reels"]
        required_reel_keys = ["symbols", "multipliers", "probabilities"]
        for key in required_reel_keys:
            if key not in reels_config:
                raise ValueError(f"Missing required reels config key: {key}")
        
        # Check that all symbols have multipliers and probabilities
        symbols = set(reels_config["symbols"])
        mult_symbols = set(reels_config["multipliers"].keys())
        prob_symbols = set(reels_config["probabilities"].keys())
        
        if symbols != mult_symbols:
            raise ValueError(f"Symbol mismatch between symbols and multipliers: {symbols} vs {mult_symbols}")
        if not prob_symbols.issubset(symbols):
            raise ValueError(f"Probability symbols not subset of main symbols: {prob_symbols} vs {symbols}")

    def _normalize_probabilities(self, prob_dict):
        """Normalize probabilities to sum to 1.0"""
        total_prob = sum(prob_dict.values())
        if total_prob <= 0:
            raise ValueError("Symbol probabilities must sum to a positive number")
        return {s: prob_dict[s] / total_prob for s in prob_dict}

    def get_current_probabilities(self):
        """
        Unified method to get current symbol probabilities with all adjustments applied.
        Returns normalized probabilities.
        """
        probs = self.base_symbol_probs.copy()
        
        # Apply reel_bias if active
        if self.upgrades.get("reel_bias"):
            if "D" in probs:
                probs["D"] += 0.05
            if "E" in probs:
                probs["E"] += 0.10
            if "A" in probs:
                probs["A"] = max(0.0, probs["A"] - 0.10)
            if "B" in probs:
                probs["B"] = max(0.0, probs["B"] - 0.05)
            
            # Renormalize after adjustments
            probs = self._normalize_probabilities(probs)
        
        return probs

    def get_effective_multipliers(self):
        """Get current multipliers with all upgrades applied"""
        if self.upgrades["bonus_multiplier_upgrade"]:
            return {s: val + 0.5 for s, val in self.base_multipliers.items()}
        return dict(self.base_multipliers)

    def spin_reels(self):
        """
        Spins each column independently using current probabilities.
        """
        current_probs = self.get_current_probabilities()
        symbols = list(current_probs.keys())
        weights = list(current_probs.values())
        return [random.choices(symbols, weights=weights, k=1)[0] for _ in range(self.cols)]

    def classify_outcome(self, row):
        """Classify a spin outcome as 1_same, 2_same, or 3_same"""
        symbol_counts = {s: row.count(s) for s in self.symbols}
        
        # Check for 3 of a kind first
        for symbol, count in symbol_counts.items():
            if count == 3:
                return "3_same"
        
        # Check for 2 of a kind
        for symbol, count in symbol_counts.items():
            if count == 2:
                return "2_same"
        
        # All different (or no matches worth counting)
        return "1_same"

    def evaluate_spin(self, row):
        """
        Update the bar progress according to matches in this spin.
        Returns (payout, bar_filled_this_spin) tuple.
        Note: Currently payout is 0 as this game only has bar progression.
        """
        symbol_counts = {s: row.count(s) for s in self.symbols}
        bar_filled_this_spin = 0.0
        payout = 0.0  # This game doesn't have direct payouts, only bar progression
        matched = False

        multipliers = self.get_effective_multipliers()

        for symbol, count in symbol_counts.items():
            if count == 3:
                increment = multipliers[symbol] * float(self.bar_fill_per_match.get("3_same", 0.0))
                self.bar_progress += increment
                bar_filled_this_spin += increment
                matched = True
            elif count == 2:
                increment = multipliers[symbol] * float(self.bar_fill_per_match.get("2_same", 0.0))
                self.bar_progress += increment
                bar_filled_this_spin += increment
                matched = True

        if not matched:
            singles = [s for s, c in symbol_counts.items() if c == 1]
            if singles and float(self.bar_fill_per_match.get("1_same", 0.0)) > 0:
                best_symbol = max(singles, key=lambda s: multipliers[s])
                increment = multipliers[best_symbol] * float(self.bar_fill_per_match.get("1_same", 0.0))
                self.bar_progress += increment
                bar_filled_this_spin += increment

        if self.bar_progress > self.bar_target:
            self.bar_progress = self.bar_target

        return payout, bar_filled_this_spin

    def play_round(self):
        """
        Plays one round and returns True if bonus triggered.
        """
        self.bar_progress = 0.0
        self.upgrade_bought_this_round = False  # reset restriction at start of round

        spins_this_round = self.spins_per_round + (2 if self.upgrades["extra_spins"] else 0)
        print(f"\nRound {self.round} | Bar target: {self.bar_target:.2f} | Spins this round: {spins_this_round} | Credits: {self.credits:.2f}")

        # Prompt for upgrade at the start of round 2 and 3
        if self.round in (2, 3):
            self.prompt_for_upgrade()

        for spin_num in range(1, spins_this_round + 1):
            row = self.spin_reels()
            payout, filled = self.evaluate_spin(row)
            print(f"Spin {spin_num}: {row} | Bar filled this spin: {filled:.4f} | Total bar progress: {self.bar_progress:.4f}")

        bonus_triggered = False
        if self.bar_progress >= self.bar_target:
            multiplier = float(self.base_bar_bonus_multiplier)
            self.credits *= multiplier
            bonus_triggered = True
            print(f"Bonus triggered! Credits multiplied by {multiplier}. New credits: {self.credits:.2f}")
        else:
            print("No bonus this round.")

        return bonus_triggered

    def prompt_for_upgrade(self):
        """
        Ask player if they want to buy an upgrade at the start of round 2 or 3.
        """
        upgrade_config = self.config.get("upgrades", {})
        print("\n--- Upgrade Shop ---")
        print(f"Credits available: {self.credits:.2f}")
        for name, data in upgrade_config.items():
            status = "Purchased" if self.upgrades.get(name) else f"Cost: {data['cost']}"
            print(f"- {name}: {status}")

        choice = input("Do you want to buy an upgrade? (yes/no): ").strip().lower()
        if choice == "yes":
            upgrade_name = input("Enter the upgrade name: ").strip()
            result = self.buy_upgrade(upgrade_name)
            print(result)
        else:
            print("No upgrade purchased.")

    def buy_upgrade(self, upgrade_name):
        # Restrict upgrade availability only to rounds 2 and 3
        if self.round not in (2, 3):
            return "Upgrades can only be purchased in rounds 2 and 3."

        # Restrict to one upgrade per round
        if self.upgrade_bought_this_round:
            return "You can only buy one upgrade per round."

        upgrade_config = self.config.get("upgrades", {})
        if upgrade_name not in upgrade_config:
            return f"Upgrade '{upgrade_name}' does not exist."
        if self.upgrades.get(upgrade_name):
            return f"Upgrade '{upgrade_name}' already purchased."

        cost = float(upgrade_config[upgrade_name]["cost"])
        if self.credits < cost:
            return f"Not enough credits to buy {upgrade_name} (cost: {cost}, credits: {self.credits:.2f})"

        self.credits -= cost
        self.upgrades[upgrade_name] = True
        self.upgrade_bought_this_round = True  # mark upgrade as purchased this round
        return f"Upgrade {upgrade_name} purchased successfully."

    def play_game(self):
        """
        Top-level game loop. Handles round progression and difficulty scaling.
        """
        while self.round <= self.max_rounds:
            bonus = self.play_round()
            if not bonus:
                print("Bar not filled — game ends.")
                break

            if self.round < self.max_rounds:
                self.bar_target += 0.5
                self.round += 1
                print(f"Proceeding to round {self.round} with bar target now {self.bar_target:.2f}")
            else:
                print("Max rounds reached. Game ends.")
                break

        print(f"Game over. Final credits: {self.credits:.2f}")