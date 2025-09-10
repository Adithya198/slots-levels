## Analysis Results Summary

### Reel Mechanics Analysis
**Base Game Structure**
- 125 total outcomes (5³ combinations) each with 0.8% base probability  
- 3-of-a-kind combinations: 5 outcomes (A-A-A through E-E-E)  
- 2-of-a-kind combinations: 60 outcomes  
- No matches: 60 outcomes (zero bar fill)  

**Upgrade Effects**
- **Reel Bias**: Shifts probability mass toward D/E symbols (E-E-E jumps from 0.8% → 2.7%)  
- **Bonus Multiplier**: Increases bar fill by +1.0 for all symbol multipliers  
- **Extra Spins**: Provides +2 spins per round (20% more opportunities)  

---

### Strategy Performance Comparison
| Strategy | Theoretical ROI | Simulation ROI | Gap | Completion Rate |
|----------|-----------------|----------------|-----|-----------------|
| R2: reel_bias | 173.3% | 140.5% | -32.8pp | 41.33% |
| R2: reel_bias → R3: extra_spins | 189.6% | 134.1% | -55.5pp | 41.02% |
| R2: reel_bias → R3: bonus_mult | 182.1% | 127.5% | -54.6pp | 40.43% |
| No Upgrades | 121.2% | 120.4% | -0.8pp | 21.50% |

---

### Critical Inferences
1. **Theoretical vs Reality Gap**  
   - Simple strategies show minimal gaps (No Upgrades: 0.8pp difference)  
   - Complex strategies show massive overestimation (55+pp gaps)  
   - Compounding probability effects are more severe than models predict  

2. **Upgrade Timing Dominance**  
   - Round 2 purchases consistently outperform Round 3 purchases  
   - Early reel bias provides the highest single-upgrade impact (41.3% vs 21.2% completion)  
   - Sequential upgrades don’t deliver proportional returns due to failure risk  

3. **Game Balance Validation**  
   - Zero strategies exceed 50% success probability  
   - Completion rates cluster around 30–40% for viable strategies  
   - 68.4% Round 1 success rate creates meaningful initial challenge  
   - Progressive difficulty (68% → 52–60% → 27–57%) maintains tension  

4. **Economic Model**  
   - Positive expected returns (110–190% ROI) reward strategic play  
   - High variance prevents systematic exploitation  
   - Upgrade costs (50 credits each) create meaningful trade-offs against 100 credit start  

5. **Design Success Metrics**  
   - Strategic depth achieved: clear hierarchy (reel_bias > extra_spins > bonus_multiplier)  
   - Luck factor preserved: 30+pp theory-practice gaps ensure uncertainty remains  
   - While optimal strategies exist, they don’t guarantee outcomes  

---



