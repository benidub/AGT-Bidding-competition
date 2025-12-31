from typing import Dict, List

class BiddingAgent:
    """
    Strategy: Simple Win-the-group (Consistent)
    """

    def __init__(self, team_id: str, valuation_vector: Dict[str, float],
                 budget: float, auction_items_sequence: List[str]):

        # ----- Required by skeleton -----
        self.team_id = team_id
        self.valuation_vector = valuation_vector
        self.budget = budget
        self.initial_budget = budget
        self.auction_items_sequence = auction_items_sequence
        self.utility = 0.0
        self.items_won = []

        # ----- Game structure -----
        self.rounds_completed = 0
        self.total_rounds = len(auction_items_sequence)

    # --------------------------------------------------
    # Mandatory system update
    # --------------------------------------------------
    def _update_available_budget(self, item_id: str,
                                 winning_team: str,
                                 price_paid: float):
        if winning_team == self.team_id:
            self.budget -= price_paid
            self.items_won.append(item_id)

    # --------------------------------------------------
    # After each round
    # --------------------------------------------------
    def update_after_each_round(self, item_id: str,
                                winning_team: str,
                                price_paid: float):
        self._update_available_budget(item_id, winning_team, price_paid)

        if winning_team == self.team_id:
            self.utility += (self.valuation_vector[item_id] - price_paid)

        self.rounds_completed += 1
        return True

    # --------------------------------------------------
    # Main bidding logic
    # --------------------------------------------------
    def bidding_function(self, item_id: str) -> float:
        my_v = self.valuation_vector.get(item_id, 0.0)
        rounds_left = max(1, self.total_rounds - self.rounds_completed)

        if my_v <= 0 or self.budget <= 0:
            return 0.0

        # ---------- Simple Win-the-group ----------
        # מחלקים את התקציב שנותר שווה בין כל הפריטים שנותרו
        base_bid = self.budget / rounds_left

        # לא להמר יותר מהערך שלנו
        bid = min(base_bid, my_v, self.budget - 0.01)

        # מקטינים סיכון קטן למספר עשרוני
        return round(max(0.0, bid), 2)
