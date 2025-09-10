import os
import pandas as pd
from tqdm import tqdm
from engine import config, OUTPUT_DIR
from utils import generate_upgrade_strategies
from stats import generate_strategy_summary, generate_reel_spin_stats
from simulate import simulate_strategy

import warnings
warnings.filterwarnings('ignore')


if __name__ == "__main__":
    # Run analysis
    print("Running complete slot game analysis...")
    strategies = generate_upgrade_strategies()

    # Theoretical analysis
    print("1. Theoretical analysis...")
    theoretical_df = generate_strategy_summary(config)

    # Simulations
    print("2. Monte Carlo simulations...")
    all_simulation_results = []
    all_detailed_results = []

    for i, strategy_tuple in enumerate(tqdm(strategies, desc="Simulating")):
        summary_stats, detailed_df = simulate_strategy(config, strategy_tuple, num_runs=10000, seed=42 + i)
        all_simulation_results.append(summary_stats)
        detailed_df["strategy"] = summary_stats["strategy"]
        detailed_df["strategy_tuple"] = str(strategy_tuple)
        all_detailed_results.append(detailed_df)

    simulation_df = pd.DataFrame(all_simulation_results)
    detailed_simulation_df = pd.concat(all_detailed_results, ignore_index=True)

    # Create comparison dataframe
    print("3. Creating comparison analysis...")
    comparison_df = theoretical_df.merge(
        simulation_df[['strategy', 'completion_rate', 'roi', 'avg_final_credits', 'avg_rounds_played']], 
        left_on='Strategy', 
        right_on='strategy', 
        how='left'
    ).drop('strategy', axis=1)

    # Add RTP calculations for easier comparison
    comparison_df['Theoretical_RTP'] = comparison_df['Expected_ROI'].fillna(0)
    comparison_df['Simulation_RTP'] = comparison_df['roi'].fillna(0)

    # Save results
    print("4. Saving results...")
    with pd.ExcelWriter(os.path.join(OUTPUT_DIR, "analysis_results.xlsx"), engine="openpyxl") as writer:
        theoretical_df.to_excel(writer, sheet_name="Theoretical", index=False)
        simulation_df.to_excel(writer, sheet_name="Simulation", index=False)
        comparison_df.to_excel(writer, sheet_name="Comparison", index=False)

    # Generate reel spin stats 
    print("5. Generating reel spin statistics...")
    reel_stats_df = generate_reel_spin_stats(config)
    reel_stats_df.to_excel(os.path.join(OUTPUT_DIR, "reel_spin_stats.xlsx"), index=False)
    print(f"Reel spin stats saved to: {OUTPUT_DIR}/reel_spin_stats.xlsx")

    # Summary
    print(f"\nResults saved to: {OUTPUT_DIR}/analysis_results.xlsx")
    print(f"Total strategies: {len(comparison_df)}")
    print(f"Strategies with >50% overall success: {(comparison_df['Overall_Success_Probability'] > 0.5).sum()}")
    print(f"Average simulation completion rate: {comparison_df['completion_rate'].mean():.1%}")
    print(f"Best strategy (by simulation): {comparison_df.loc[comparison_df['completion_rate'].idxmax(), 'Strategy']}")
    print(f"Best completion rate: {comparison_df['completion_rate'].max():.1%}")

    # Display top results with comparison
    print("\nTop 5 strategies by simulation completion rate:")
    top_strategies = comparison_df.nlargest(5, 'completion_rate')[
        ['Strategy', 'completion_rate', 'Simulation_RTP', 'Theoretical_RTP']
    ]
    print(top_strategies.to_string(index=False))

    print("\nTop 5 strategies by theoretical RTP:")
    top_theoretical = comparison_df.nlargest(5, 'Theoretical_RTP')[
        ['Strategy', 'Theoretical_RTP', 'Simulation_RTP', 'completion_rate'] 
    ]
    print(top_theoretical.to_string(index=False))

    print("\nAnalysis complete")
