"""
Team: ShadowPacer
Strategy: Adaptive Lagrangian Multiplier (Shadow Pricing) with End-Game Budget Dump.
"""

from typing import Dict, List
import math


class BiddingAgent:
    def __init__(self, team_id: str, valuation_vector: Dict[str, float],
                 budget: float, opponent_teams: List[str]):
        self.team_id = team_id
        self.valuation_vector = valuation_vector
        self.budget = budget
        self.initial_budget = budget
        self.opponent_teams = opponent_teams
        self.utility = 0
        self.items_won = []

        # --- STRATEGY STATE ---
        self.rounds_completed = 0
        self.total_rounds = 15

        # Calculate total potential value in our vector (all 20 items)
        # We use this to estimate how 'valuable' the remaining game is.
        self.total_value_remaining = sum(valuation_vector.values())

        # The Shadow Price (Lambda).
        # 0.0 = Truthful bidding. 1.0 = Bid half value.
        # Start conservative (assuming high competition).
        self.shadow_price = 0.5

        # Alpha is our learning rate for updating the shadow price
        self.alpha = 0.2

    def _update_available_budget(self, item_id: str, winning_team: str,
                                 price_paid: float):
        """System method - DO NOT CHANGE"""
        if winning_team == self.team_id:
            self.budget -= price_paid
            self.items_won.append(item_id)

    def update_after_each_round(self, item_id: str, winning_team: str,
                                price_paid: float):
        """
        Adjusts the Shadow Price based on whether we are over/under spending.
        """
        # 1. Standard system update
        self._update_available_budget(item_id, winning_team, price_paid)
        if winning_team == self.team_id:
            self.utility += (self.valuation_vector[item_id] - price_paid)

        # 2. Remove the item's value from our 'remaining potential'
        # (Even if we didn't win it, it's gone from the auction pool)
        if item_id in self.valuation_vector:
            self.total_value_remaining -= self.valuation_vector[item_id]

        # 3. Update Rounds
        self.rounds_completed += 1
        rounds_remaining = self.total_rounds - self.rounds_completed

        if rounds_remaining <= 0:
            return True

        # 4. Strategic Update: Re-calculate Shadow Price
        # Ideal spend ratio: Budget / Remaining Value
        # If we have lots of budget and little value left, we should spend FREELY.
        # If we have little budget and lots of value left, we should be STINGY.

        # Protect against divide by zero
        safe_value_remaining = max(1.0, self.total_value_remaining)

        # This ratio represents "How much budget do I have per unit of value left?"
        wealth_ratio = self.budget / safe_value_remaining

        # Target wealth ratio is roughly Initial_Budget / Initial_Total_Value (~60 / ~250 = ~0.24)
        target_ratio = 0.24

        if wealth_ratio < target_ratio:
            # We are poor relative to the value left -> Increase shadow price (Bid Less)
            self.shadow_price *= (1 + self.alpha)
        else:
            # We are rich relative to value left -> Decrease shadow price (Bid More)
            self.shadow_price *= (1 - self.alpha)

        # Clamp shadow price to sane limits
        self.shadow_price = max(0.0, min(self.shadow_price, 3.0))

        return True

    def bidding_function(self, item_id: str) -> float:
        """
        Bids based on Value / (1 + Lambda), switching to truthful at the end.
        """
        my_valuation = self.valuation_vector.get(item_id, 0)
        rounds_remaining = self.total_rounds - self.rounds_completed

        # --- END GAME LOGIC ---
        # If it's the very last round, BID EVERYTHING (capped at value)
        # Because unused budget has 0 utility.
        if rounds_remaining <= 1:
            return min(my_valuation, self.budget)

        # If we are near the end (last 3 rounds) and rich, drop shading
        if rounds_remaining <= 3 and self.budget > 10:
            return min(my_valuation, self.budget)

        # --- NORMAL GAME LOGIC (PACING) ---

        # Standard Pacing Formula: Bid = Value / (1 + lambda)
        # If lambda is high (saving money), bid is low.
        shaded_bid = my_valuation / (1.0 + self.shadow_price)

        # --- SANITY CHECKS ---

        # 1. Never bid more than budget
        final_bid = min(shaded_bid, self.budget)

        # 2. Never bid negative
        final_bid = max(0.0, final_bid)

        return final_bid