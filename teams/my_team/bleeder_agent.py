"""
AGT Competition - Student Agent Template
========================================

Team Name: [YOUR TEAM NAME]
Members:
  - [Student 1 Name and ID]
  - [Student 2 Name and ID]
  - [Student 3 Name and ID]

Strategy Description:
Threshold-based bidding strategy:
- For items valued under 10, bid just under 7.
- For items valued between 10 and 20, bid a flat 13.66.
- For items valued over 20, bid 80% of valuation (default).

Key Features:
- Low-value price capping
- Fixed-point bidding for medium-value items
- Budget-aware bid clipping
"""

from typing import Dict, List


class BiddingAgent:
    def __init__(self, team_id: str, valuation_vector: Dict[str, float],
                 budget: float, opponent_teams: List[str]):
        # Required attributes
        self.team_id = team_id
        self.valuation_vector = valuation_vector
        self.budget = budget
        self.initial_budget = budget
        self.opponent_teams = opponent_teams
        self.utility = 0
        self.items_won = []

        # Game state tracking
        self.rounds_completed = 0
        self.total_rounds = 15

    def _update_available_budget(self, item_id: str, winning_team: str,
                                 price_paid: float):
        if winning_team == self.team_id:
            self.budget -= price_paid
            self.items_won.append(item_id)

    def update_after_each_round(self, item_id: str, winning_team: str,
                                price_paid: float):
        self._update_available_budget(item_id, winning_team, price_paid)
        if winning_team == self.team_id:
            self.utility += (self.valuation_vector[item_id] - price_paid)
        self.rounds_completed += 1
        return True

    def bidding_function(self, item_id: str) -> float:
        """
        Modified bidding function based on specific valuation thresholds.
        """
        # Get your valuation for this item
        my_valuation = self.valuation_vector.get(item_id, 0)

        # Basic sanity checks
        if my_valuation <= 0 or self.budget <= 0:
            return 0.0

        # Define epsilon for "7 - eps"
        epsilon = 0.01

        # ============================================================
        # IMPLEMENTED STRATEGY
        # ============================================================

        if my_valuation < 10:
            # If valuation < 10, propose 7 - eps
            bid = 7.0 - epsilon

        elif 10 <= my_valuation <= 20:
            # If valuation is between 10-20, propose 13.66
            bid = 13.66

        else:
            # Default behavior for high valuation items (> 20)
            # Maintaining the 80% shading from the template
            bid = my_valuation * 0.8

        # ============================================================

        # Ensure bid is valid (non-negative and within budget)
        # Note: If budget is less than the calculated bid,
        # min() will cap it to the remaining budget automatically.
        bid = max(0.0, min(bid, self.budget))

        return float(bid)