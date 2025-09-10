import json
import os
import random

class SlotGame:
    def __init__(self, config_dict):
        self.config = config_dict
        self.credits = float(self.config.get("credits_start", 100))
        self.spins_per_round = int(self.config.get("spins_per_round", 8))
        
        reels_config = self.config["reels"]
        self.cols = int(reels_config.get("cols", 3))
        self.symbols = list(reels_config["symbols"])
        self.base_multipliers = {s: float(v) for s, v in reels_config["multipliers"].items()}
        
        raw_probs = {s: float(reels_config["probabilities"].get(s, 0.0)) for s in self.symbols}
        total_prob = sum(raw_probs.values())
        self.base_symbol_probs = {s: raw_probs[s] / total_prob for s in raw_probs}
        
        self.bar_fill_per_match = self.config.get("bar_fill_per_match", {"3_same": 0.1, "2_same": 0.05, "1_same": 0})
        self.base_bar_bonus_multiplier = float(self.config.get("bar_bonus_multiplier", 2.0))
        
        self.bar_progress = 0.0
        self.bar_target = float(self.config.get("initial_bar_target", 1.0))
        self.round = 1
        self.max_rounds = int(self.config.get("max_rounds", 3))
        
        self.upgrades = {"reel_bias": False, "extra_spins": False, "bonus_multiplier_upgrade": False}
        self.upgrade_bought_this_round = False
    
    def get_current_probabilities(self):
        probs = self.base_symbol_probs.copy()
        if self.upgrades.get("reel_bias"):
            if "D" in probs: probs["D"] += 0.05
            if "E" in probs: probs["E"] += 0.10
            if "A" in probs: probs["A"] = max(0.0, probs["A"] - 0.10)
            if "B" in probs: probs["B"] = max(0.0, probs["B"] - 0.05)
            total_prob = sum(probs.values())
            probs = {s: probs[s] / total_prob for s in probs}
        return probs
    
    def get_effective_multipliers(self):
        if self.upgrades["bonus_multiplier_upgrade"]:
            return {s: val + 1.0 for s, val in self.base_multipliers.items()}
        return dict(self.base_multipliers)
    
    def spin_reels(self):
        current_probs = self.get_current_probabilities()
        symbols = list(current_probs.keys())
        weights = list(current_probs.values())
        return [random.choices(symbols, weights=weights, k=1)[0] for _ in range(self.cols)]
    
    def evaluate_spin(self, row):
        symbol_counts = {s: row.count(s) for s in self.symbols}
        bar_filled_this_spin = 0.0
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
        
        return 0.0, bar_filled_this_spin
    
    def buy_upgrade(self, upgrade_name):
        if self.upgrade_bought_this_round:
            return "You can only buy one upgrade per round."
        upgrade_config = self.config.get("upgrades", {})
        if upgrade_name not in upgrade_config:
            return f"Upgrade '{upgrade_name}' does not exist."
        if self.upgrades.get(upgrade_name):
            return f"Upgrade '{upgrade_name}' already purchased."
        cost = float(upgrade_config[upgrade_name]["cost"])
        if self.credits < cost:
            return f"Not enough credits to buy {upgrade_name}"
        self.credits -= cost
        self.upgrades[upgrade_name] = True
        self.upgrade_bought_this_round = True
        return f"Upgrade {upgrade_name} purchased successfully."
    
    def play_round_silent(self):
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

# Configuration
CONFIG_PATH = "data/config.json"
OUTPUT_DIR = "outputs"
NUM_RUNS = 10000
RANDOM_SEED = 42

# Create sample config if needed
def create_sample_config():
    return {
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
            "reel_bias": {"cost": 50, "effect": "increase the probability of D by 5% and E by 10%, decrease the probability of A by 10% and B by 5%"},
            "extra_spins": {"cost": 50, "effect": "+2 spins per round"},
            "bonus_multiplier_upgrade": {"cost": 50, "effect": "increase all symbol multipliers by 1.0"}
        }
    }

# Load or create config
try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
except FileNotFoundError:
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    config = create_sample_config()
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

os.makedirs(OUTPUT_DIR, exist_ok=True)