# utils.py
import itertools

def generate_upgrade_strategies():
    """
    Generate upgrade strategies where ORDER MATTERS but combination doesn't.
    This creates sequences of (round2_upgrade, round3_upgrade) where:
    - Each can be "skip" or one of the three upgrades
    - Same upgrade can't be bought twice (since they're one-time purchases)
    
    Total strategies: 1 (skip-skip) + 6 (skip-upgrade) + 6 (upgrade-skip) + 6 (upgrade1-upgrade2) = 19
    """
    upgrades = ["reel_bias", "extra_spins", "bonus_multiplier_upgrade"]
    strategies = []

    # Skip-Skip: no upgrades purchased
    strategies.append(("skip", "skip"))

    # Skip in round 2, then buy any upgrade in round 3
    for u in upgrades:
        strategies.append(("skip", u))

    # Buy upgrade in round 2, then skip round 3
    for u in upgrades:
        strategies.append((u, "skip"))

    # Buy one upgrade in round 2, then buy a DIFFERENT upgrade in round 3
    # (since each upgrade is one-time purchase)
    for u1 in upgrades:
        for u2 in upgrades:
            if u1 != u2:  # Can't buy the same upgrade twice
                strategies.append((u1, u2))

    return strategies

def format_strategy_name(strategy_tuple):
    """Convert strategy tuple to readable name"""
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
    """Convert upgrade list to readable combination name"""
    if not upgrade_list or all(u == "skip" for u in upgrade_list):
        return "No Upgrades"
    
    active_upgrades = [u for u in upgrade_list if u != "skip"]
    if not active_upgrades:
        return "No Upgrades"
    
    return " + ".join(sorted(active_upgrades))