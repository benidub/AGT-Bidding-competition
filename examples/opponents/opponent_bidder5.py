from typing import Dict, List

class BiddingAgent:
    """
    Team: Daniel Aggressive Top-Value V1
    Strategy: Aggressive Top-Value Capture (Single Focus)
    """

    def __init__(self, team_id: str, valuation_vector: Dict[str, float],
                 budget: float, auction_items_sequence: List[str]):

        self.team_id = team_id
        self.valuation_vector = valuation_vector
        self.budget = budget
        self.initial_budget = budget
        self.auction_items_sequence = auction_items_sequence
        self.utility = 0.0
        self.items_won = []
        self.rounds_completed = 0
        self.total_rounds = len(auction_items_sequence)

    def _update_available_budget(self, item_id: str, winning_team: str, price_paid: float):
        if winning_team == self.team_id:
            self.budget -= price_paid
            self.items_won.append(item_id)

    def update_after_each_round(self, item_id: str,
                                winning_team: str,
                                price_paid: float):
        if winning_team == self.team_id:
            self.budget -= price_paid
            self.utility += (self.valuation_vector.get(item_id, 0) - price_paid)
            self.items_won.append(item_id)
        self.rounds_completed += 1
        return True

    def bidding_function(self, item_id: str) -> float:
        my_val = self.valuation_vector.get(item_id, 0)
        if my_val <= 0 or self.budget <= 0:
            return 0.0

        # ---------- Aggressive Top-Value Capture ----------
        top_value_threshold = 12.0
        aggression_factor = 0.9

        if my_val >= top_value_threshold:
            bid = my_val * aggression_factor
        else:
            # נמנע מהימור על פריטים נמוכי ערך
            bid = 0.0

        # הגבלות בטיחות
        bid = min(bid, my_val, self.budget - 0.01)
        bid = max(bid, 0.0)

        return round(bid, 2)