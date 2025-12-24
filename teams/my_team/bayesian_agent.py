from typing import Dict, List


class BiddingAgent:
    """
    Bayesian 'Budget Sniper' Agent V2 - Aggressive Correction
    """

    def __init__(self, team_id: str, valuation_vector: Dict[str, float],
                 budget: float, opponent_teams: List[str]):

        self.team_id = team_id
        self.valuation_vector = valuation_vector
        self.budget = budget
        self.initial_budget = budget
        self.opponent_teams = opponent_teams
        self.utility = 0

        self.rounds_completed = 0
        self.total_rounds = 15

        # --- STRATEGY STATE ---
        self.counts = {'H': 6, 'M': 10, 'L': 4}

        # We need to track average prices to detect market shifts
        self.price_history = []

    def _update_available_budget(self, item_id: str, winning_team: str,
                                 price_paid: float):
        if winning_team == self.team_id:
            self.budget -= price_paid

    def _decrement_count(self, category: str):
        if self.counts[category] > 0:
            self.counts[category] -= 1
        else:
            # Fallback redistribution if counts go negative
            if category == 'H' and self.counts['M'] > 0:
                self.counts['M'] -= 1
            elif category == 'M' and self.counts['L'] > 0:
                self.counts['L'] -= 1

    def update_after_each_round(self, item_id: str, winning_team: str,
                                price_paid: float):
        # 1. System Updates
        self._update_available_budget(item_id, winning_team, price_paid)
        if winning_team == self.team_id:
            self.utility += (self.valuation_vector[item_id] - price_paid)

        self.rounds_completed += 1
        self.price_history.append(price_paid)

        # 2. Bayesian Inference (Identify what was sold)
        # We relax the thresholds slightly to account for opponent variance
        if price_paid < 9.0:
            if price_paid < 5.0:
                self._decrement_count('L')
            else:
                self._decrement_count('L')  # Heavily biased toward L removal
        elif 9.0 <= price_paid < 14.5:
            self._decrement_count('M')
        else:
            self._decrement_count('H')

        return True

    def bidding_function(self, item_id: str) -> float:
        my_valuation = self.valuation_vector.get(item_id, 0)
        rounds_remaining = self.total_rounds - self.rounds_completed

        # 1. Basic Exit
        if my_valuation <= 0 or self.budget <= 0 or rounds_remaining <= 0:
            return 0.0

        # 2. Calculate "Budget Surplus"
        # If we have 40 coins and 5 rounds left, we have 8 coins/round.
        # Average item cost is ~12. We can afford to be reckless.
        budget_per_round = self.budget / rounds_remaining
        is_rich = budget_per_round > 5.0  # We have excess cash
        is_poor = budget_per_round < 2.5  # We are starving

        # 3. Low Value Logic (< 10)
        # These are usually trash, but if we are rich, we might as well pick them up
        if my_valuation < 10:
            if is_rich: return my_valuation * 0.8  # Throw a bid out there
            return my_valuation * 0.2  # Low ball if poor

        # 4. High Value Logic (Bayesian Decision)
        # Calculate Odds
        count_m = max(0.1, self.counts['M'])
        # Adjusted multiplier: 1.5 instead of 1.9 to be slightly less "scared" of Highs
        score_high = self.counts['H'] * 1.5
        score_mixed = count_m * 1.0

        likely_category = 'H' if score_high > score_mixed else 'M'

        bid = 0.0

        if likely_category == 'M':
            # --- OPPORTUNITY ZONE ---
            # It's likely Mixed. We have High Value. Opponents likely have Low Value.
            # STRATEGY: TRUTHFUL.
            # Why? If opponents bid 5, we pay 5 (regardless if we bid 18 or 15).
            # But if an opponent bids 16, and we shaded to 15, we lose a profitable item.
            bid = my_valuation

        else:
            # --- DANGER ZONE (Likely High) ---
            # Everyone has High Value. Price will be high.
            if is_rich:
                # If we have money to burn, BUY IT.
                # Shading slightly (0.9) helps avoid the absolute worst-case peaks (paying 19 for 19).
                bid = my_valuation * 0.95
            elif is_poor:
                # We can't afford a bidding war.
                bid = my_valuation * 0.6
            else:
                # Normal state: Shade to target profit
                bid = my_valuation * 0.8

        # 5. End Game Panic
        # If it's the last 3 rounds and we have > 15 budget, DUMP IT.
        if rounds_remaining <= 3 and self.budget > 15:
            bid = my_valuation  # Go full truthful to secure wins

        # 6. Safety Cap
        bid = max(0.0, min(bid, self.budget))
        return float(bid)