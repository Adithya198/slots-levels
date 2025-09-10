import pandas as pd
import numpy as np
import itertools
from engine import SlotGame

def bar_fill_distribution(game):
    symbols = game.symbols
    multipliers = game.get_effective_multipliers()
    current_probs = game.get_current_probabilities()
    values, probs = [], []
    
    for row in itertools.product(symbols, repeat=game.cols):
        p_row = 1.0
        for sym in row:
            p_row *= current_probs[sym]
        
        symbol_counts = {s: row.count(s) for s in symbols}
        increment = 0.0
        
        for symbol, count in symbol_counts.items():
            if count == 3:
                increment += multipliers[symbol] * game.bar_fill_per_match.get("3_same", 0.0)
            elif count == 2:
                increment += multipliers[symbol] * game.bar_fill_per_match.get("2_same", 0.0)
        
        if increment == 0.0 and game.bar_fill_per_match.get("1_same", 0.0) > 0:
            singles = [s for s, c in symbol_counts.items() if c == 1]
            if singles:
                best_symbol = max(singles, key=lambda s: multipliers[s])
                increment = multipliers[best_symbol] * game.bar_fill_per_match.get("1_same", 0.0)
        
        values.append(increment)
        probs.append(p_row)
    
    return np.array(values), np.array(probs)

def expected_stats(game):
    values, probs = bar_fill_distribution(game)
    exp = np.sum(values * probs)
    exp_sq = np.sum((values ** 2) * probs)
    var = exp_sq - exp ** 2
    std = np.sqrt(max(var, 0.0))
    expected_bonus_contribution = exp * game.base_bar_bonus_multiplier
    return exp, std, expected_bonus_contribution

def calculate_round_success_probability(game, bar_target, num_spins):
    """
    Calculate the probability that bar_progress >= bar_target after num_spins
    using dynamic programming for efficiency.
    """
    values, probs = bar_fill_distribution(game)
    
    # dp[spin][progress] = probability of having exactly 'progress' after 'spin' spins
    # Discretize progress to avoid infinite states
    
    # Find maximum possible progress and discretize
    max_single_fill = max(values)
    max_total_fill = max_single_fill * num_spins
    
    # Use small step size for accuracy
    step_size = 0.001
    max_steps = int(max_total_fill / step_size) + 1
    
    # Initialize DP table
    # dp[progress_step] = probability of having exactly that progress
    current_dp = {0: 1.0}  # Start with 0 progress, probability 1
    
    for spin in range(num_spins):
        next_dp = {}
        
        for current_progress_step, current_prob in current_dp.items():
            if current_prob == 0:
                continue
                
            current_progress = current_progress_step * step_size
            
            for fill_value, fill_prob in zip(values, probs):
                new_progress = min(current_progress + fill_value, bar_target)
                new_progress_step = int(new_progress / step_size)
                
                if new_progress_step not in next_dp:
                    next_dp[new_progress_step] = 0.0
                next_dp[new_progress_step] += current_prob * fill_prob
        
        current_dp = next_dp
    
    # Sum probabilities for all states where progress >= bar_target
    success_prob = 0.0
    target_step = int(bar_target / step_size)
    
    for progress_step, prob in current_dp.items():
        if progress_step >= target_step:
            success_prob += prob
    
    return min(success_prob, 1.0)  # Ensure probability doesn't exceed 1

def calculate_strategy_success_probabilities(config, strategy_tuple):
    """
    Calculate success probabilities for all three rounds of a strategy.
    """
    round2_upgrade, round3_upgrade = strategy_tuple
    bar_targets = [1.0, 1.5, 2.0]
    base_spins = config.get("spins_per_round", 8)
    
    results = {}
    
    # Round 1: Base game only
    game_r1 = SlotGame(config_dict=config)
    spins_r1 = base_spins
    p1 = calculate_round_success_probability(game_r1, bar_targets[0], spins_r1)
    results['round_1'] = p1
    
    # Round 2: Base game + Round 2 upgrade
    game_r2 = SlotGame(config_dict=config)
    if round2_upgrade != "skip":
        game_r2.upgrades[round2_upgrade] = True
    spins_r2 = base_spins + (2 if game_r2.upgrades["extra_spins"] else 0)
    p2 = calculate_round_success_probability(game_r2, bar_targets[1], spins_r2)
    results['round_2'] = p2
    
    # Round 3: Base game + both upgrades
    game_r3 = SlotGame(config_dict=config)
    if round2_upgrade != "skip":
        game_r3.upgrades[round2_upgrade] = True
    if round3_upgrade != "skip":
        game_r3.upgrades[round3_upgrade] = True
    spins_r3 = base_spins + (2 if game_r3.upgrades["extra_spins"] else 0)
    p3 = calculate_round_success_probability(game_r3, bar_targets[2], spins_r3)
    results['round_3'] = p3
    
    return results

def generate_strategy_summary(config):
    from utils import generate_upgrade_strategies, format_strategy_name, format_upgrade_combo_name
    
    strategies = generate_upgrade_strategies()
    summary_rows = []
    
    for strategy_tuple in strategies:
        game = SlotGame(config_dict=config)
        round2_upgrade, round3_upgrade = strategy_tuple
        if round2_upgrade != "skip":
            game.upgrades[round2_upgrade] = True
        if round3_upgrade != "skip":
            game.upgrades[round3_upgrade] = True
        
        exp_fill, std_fill, exp_bonus_contrib = expected_stats(game)
        current_probs = game.get_current_probabilities()
        multipliers = game.get_effective_multipliers()
        spins_per_round = game.spins_per_round + (2 if game.upgrades["extra_spins"] else 0)
        expected_per_round = exp_fill * spins_per_round
        
        # Calculate actual success probabilities
        success_probs = calculate_strategy_success_probabilities(config, strategy_tuple)
        p1, p2, p3 = success_probs['round_1'], success_probs['round_2'], success_probs['round_3']
        
        # Calculate upgrade costs
        upgrade_costs = {}
        upgrade_costs['round_2'] = 0
        upgrade_costs['round_3'] = 0
        
        if round2_upgrade != "skip":
            upgrade_costs['round_2'] = float(config.get("upgrades", {}).get(round2_upgrade, {}).get("cost", 0))
        if round3_upgrade != "skip":
            upgrade_costs['round_3'] = float(config.get("upgrades", {}).get(round3_upgrade, {}).get("cost", 0))
        
        total_upgrade_cost = upgrade_costs['round_2'] + upgrade_costs['round_3']
        
        # Calculate expected final credits using probabilistic approach
        starting_credits = float(config.get("credits_start", 100))
        bar_multiplier = float(config.get("bar_bonus_multiplier", 2.0))
        
        # Expected credits calculation accounting for all possible outcomes
        # Outcome 1: Fail Round 1 (probability: 1-p1)
        # Credits: starting_credits
        outcome_1_prob = (1 - p1)
        outcome_1_credits = starting_credits
        
        # Outcome 2: Pass R1, Fail R2 (probability: p1 * (1-p2))
        # Credits: starting_credits * multiplier - r2_upgrade_cost
        outcome_2_prob = p1 * (1 - p2)
        outcome_2_credits = starting_credits * bar_multiplier - upgrade_costs['round_2']
        
        # Outcome 3: Pass R1&R2, Fail R3 (probability: p1 * p2 * (1-p3))
        # Credits: starting_credits * multiplier^2 - r2_cost - r3_cost
        outcome_3_prob = p1 * p2 * (1 - p3)
        outcome_3_credits = starting_credits * (bar_multiplier ** 2) - upgrade_costs['round_2'] - upgrade_costs['round_3']
        
        # Outcome 4: Pass All Rounds (probability: p1 * p2 * p3)
        # Credits: starting_credits * multiplier^3 - r2_cost - r3_cost
        outcome_4_prob = p1 * p2 * p3
        outcome_4_credits = starting_credits * (bar_multiplier ** 3) - upgrade_costs['round_2'] - upgrade_costs['round_3']
        
        # Expected final credits
        expected_final_credits = (
            outcome_1_prob * outcome_1_credits +
            outcome_2_prob * outcome_2_credits +
            outcome_3_prob * outcome_3_credits +
            outcome_4_prob * outcome_4_credits)
        
        # Expected ROI
        expected_roi = (expected_final_credits - starting_credits) / starting_credits if starting_credits > 0 else 0.0
        
        summary_rows.append({
            "Strategy": format_strategy_name(strategy_tuple),
            "Round_2_Upgrade": round2_upgrade,
            "Round_3_Upgrade": round3_upgrade,
            "Upgrade_Combination": format_upgrade_combo_name(list(strategy_tuple)),
            "Expected_Fill_per_Spin": exp_fill,
            "Std_Dev_Fill": std_fill,
            "Expected_Bonus_Contribution": exp_bonus_contrib,
            "Spins_per_Round": spins_per_round,
            "Expected_Fill_per_Round": expected_per_round,
            "R1_Success_Probability": p1,
            "R2_Success_Probability": p2,
            "R3_Success_Probability": p3,
            "Overall_Success_Probability": p1 * p2 * p3,
            "Total_Upgrade_Cost": total_upgrade_cost,
            "Avg_Symbol_Multiplier": sum(multipliers.values()) / len(multipliers),
            "Expected_ROI": expected_roi,
            "Expected_Final_Credits": expected_final_credits
        })
    
    return pd.DataFrame(summary_rows)

def generate_reel_spin_stats(config):
    """Generate detailed reel spin statistics"""
    
    # Create game instances for all combinations
    base_game = SlotGame(config_dict=config)
    
    reel_bias_game = SlotGame(config_dict=config)
    reel_bias_game.upgrades["reel_bias"] = True
    
    bonus_mult_game = SlotGame(config_dict=config)
    bonus_mult_game.upgrades["bonus_multiplier_upgrade"] = True
    
    both_upgrades_game = SlotGame(config_dict=config)
    both_upgrades_game.upgrades["reel_bias"] = True
    both_upgrades_game.upgrades["bonus_multiplier_upgrade"] = True
    
    symbols = base_game.symbols
    base_probs = base_game.get_current_probabilities()
    reel_bias_probs = reel_bias_game.get_current_probabilities()
    base_multipliers = base_game.get_effective_multipliers()
    bonus_multipliers = bonus_mult_game.get_effective_multipliers()
    
    results = []
    
    # Generate all possible combinations
    for row in itertools.product(symbols, repeat=base_game.cols):
        outcome_str = " ".join(row)
        
        # Calculate probabilities
        base_prob = 1.0
        for sym in row:
            base_prob *= base_probs[sym]
        
        bias_prob = 1.0
        for sym in row:
            bias_prob *= reel_bias_probs[sym]
        
        symbol_counts = {s: row.count(s) for s in symbols}
        
        # Classify outcome type
        outcome_type = "1_same"
        max_count = max(symbol_counts.values())
        if max_count == 3:
            outcome_type = "3_same"
        elif max_count == 2:
            outcome_type = "2_same"
        
        # Calculate base barfill (no upgrades)
        base_barfill = 0.0
        for symbol, count in symbol_counts.items():
            if count == 3:
                base_barfill += base_multipliers[symbol] * base_game.bar_fill_per_match.get("3_same", 0.0)
            elif count == 2:
                base_barfill += base_multipliers[symbol] * base_game.bar_fill_per_match.get("2_same", 0.0)
        
        if base_barfill == 0.0 and base_game.bar_fill_per_match.get("1_same", 0.0) > 0:
            singles = [s for s, c in symbol_counts.items() if c == 1]
            if singles:
                best_symbol = max(singles, key=lambda s: base_multipliers[s])
                base_barfill = base_multipliers[best_symbol] * base_game.bar_fill_per_match.get("1_same", 0.0)
        
        # Calculate barfill with bonus multiplier upgrade only
        bonus_barfill = 0.0
        for symbol, count in symbol_counts.items():
            if count == 3:
                bonus_barfill += bonus_multipliers[symbol] * base_game.bar_fill_per_match.get("3_same", 0.0)
            elif count == 2:
                bonus_barfill += bonus_multipliers[symbol] * base_game.bar_fill_per_match.get("2_same", 0.0)
        
        if bonus_barfill == 0.0 and base_game.bar_fill_per_match.get("1_same", 0.0) > 0:
            singles = [s for s, c in symbol_counts.items() if c == 1]
            if singles:
                best_symbol = max(singles, key=lambda s: bonus_multipliers[s])
                bonus_barfill = bonus_multipliers[best_symbol] * base_game.bar_fill_per_match.get("1_same", 0.0)
        
        # Calculate barfill with reel bias only (same multipliers as base, different probabilities)
        reel_bias_barfill = base_barfill
        
        # Calculate barfill with both upgrades
        both_barfill = bonus_barfill
        
        # Get base multiplier for the best symbol
        best_symbol_base_mult = 0
        if max_count == 3:
            for symbol, count in symbol_counts.items():
                if count == 3:
                    best_symbol_base_mult = base_multipliers[symbol]
                    break
        elif max_count == 2:
            for symbol, count in symbol_counts.items():
                if count == 2:
                    best_symbol_base_mult = base_multipliers[symbol]
                    break
        else:
            if singles:
                best_symbol_base_mult = base_multipliers[max(singles, key=lambda s: base_multipliers[s])]
        
        # Get bonus multiplier for the best symbol
        best_symbol_bonus_mult = 0
        if max_count == 3:
            for symbol, count in symbol_counts.items():
                if count == 3:
                    best_symbol_bonus_mult = bonus_multipliers[symbol]
                    break
        elif max_count == 2:
            for symbol, count in symbol_counts.items():
                if count == 2:
                    best_symbol_bonus_mult = bonus_multipliers[symbol]
                    break
        else:
            if singles:
                best_symbol_bonus_mult = bonus_multipliers[max(singles, key=lambda s: bonus_multipliers[s])]
        
        results.append({
            "Reel spin outcome": outcome_str,
            "Outcome type": outcome_type,
            "Probability": base_prob,
            "Probability with reel_bias upgrade": bias_prob,
            "Barfill": base_barfill,
            "Barfill with Bonus Multiplier upgrade": bonus_barfill,
            "Barfill with reel_bias upgrade": reel_bias_barfill,
            "Barfill with both upgrades": both_barfill,
            "Best symbol base multiplier": best_symbol_base_mult,
            "Best symbol bonus multiplier": best_symbol_bonus_mult
        })
    
    return pd.DataFrame(results)