from typing import Dict, List

class BiddingAgent:
    """
    Team: Daniel Even Spread
    Strategy: Even Spread Bidding (Single Focus)
    """

    def __init__(self, team_id: str, valuation_vector: Dict[str, float],
                 budget: float, opponent_teams: List[str]):
        self.team_id = team_id
        self.valuation_vector = valuation_vector
        self.budget = budget
        self.initial_budget = budget
        self.opponent_teams = opponent_teams
        self.utility = 0
        self.items_won = []
        self.rounds_completed = 0
        self.total_rounds = 15

    def _update_available_budget(self, item_id: str, winning_team: str, price_paid: float):
        if winning_team == self.team_id:
            self.budget -= price_paid
            self.items_won.append(item_id)

    def update_after_each_round(self, item_id: str, winning_team: str, price_paid: float):
        if winning_team == self.team_id:
            self.budget -= price_paid
            self.utility += (self.valuation_vector.get(item_id, 0) - price_paid)
            self.items_won.append(item_id)
        self.rounds_completed += 1
        return True

    def get_expected_competition(self, my_val: float) -> float:
        """מעריך כמה היריב הכי חזק יציע על הפריט הזה"""
        total_items_left = sum(self.inventory.values())
        if total_items_left == 0: return 5.0

        # הסתברות שהפריט הוא High-Value לכולם
        p_high = 0.1 if 10 <= my_val <= 20 else 0.001
        prior_h = self.inventory['high'] / total_items_left
        prob_is_high = (p_high * prior_h) / (p_high * prior_h + 0.05 * (1-prior_h))

        richest_opp = max(self.opp_budgets.values())
        # אם הפריט High, היריב יציע הרבה. אם לא, הוא יציע לפי ה-Burn Rate שלו.
        expected_bid = (prob_is_high * 15.0) + ((1 - prob_is_high) * (richest_opp / 10.0))
        return min(expected_bid, richest_opp)

    def bidding_function(self, item_id: str) -> float:
        rounds_left = max(1, self.total_rounds - self.rounds_completed)
        if self.budget <= 0:
            return 0.0

        # ---------- Even Spread ----------
        # מחלקים את התקציב שנותר באופן שווה בין הסיבובים שנותרו
        bid = self.budget / rounds_left

        # לא להמר יותר מהערך של הפריט
        my_val = self.valuation_vector.get(item_id, 0)
        bid = min(bid, my_val, self.budget - 0.01)

        return round(max(0.0, bid), 2)