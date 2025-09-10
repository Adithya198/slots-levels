import itertools

def generate_upgrade_strategies():
    upgrades = ["reel_bias", "extra_spins", "bonus_multiplier_upgrade"]
    strategies = [("skip", "skip")]
    for u in upgrades:
        strategies.append(("skip", u))
        strategies.append((u, "skip"))
    for u1 in upgrades:
        for u2 in upgrades:
            if u1 != u2:
                strategies.append((u1, u2))
    return strategies

def format_strategy_name(strategy_tuple):
    round2, round3 = strategy_tuple
    if round2 == "skip" and round3 == "skip":
        return "No Upgrades"
    elif round2 == "skip":
        return f"R3: {round3}"
    elif round3 == "skip":
        return f"R2: {round2}"
    else:
        return f"R2: {round2} → R3: {round3}"

def format_upgrade_combo_name(upgrade_list):
    if not upgrade_list or all(u == "skip" for u in upgrade_list):
        return "No Upgrades"
    active_upgrades = [u for u in upgrade_list if u != "skip"]
    if not active_upgrades:
        return "No Upgrades"
    return " + ".join(sorted(active_upgrades))