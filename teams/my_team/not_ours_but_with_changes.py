"""
Team:
Strategy: Relative Wealth Dominance & Inventory Choking.
Specifically engineered to crush aggressive pacing agents by forcing them
into bankruptcy early and dominating the second half of the auction.
"""

from typing import Dict, List
import numpy as np


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
        self.rounds_completed = 0
        self.total_rounds = 15

        # Tracking and Inventory
        self.opp_budgets = {opp: 60.0 for opp in opponent_teams}
        self.opp_utility_est = {opp: 0.0 for opp in opponent_teams}
        self.inventory = {'high': 6, 'low': 4, 'mixed': 10}

        # Manipulation State
        self.tax_floor = 10.1
        self.last_bid_was_tax = False
        self.last_bid_amount = 0.0

    def _update_available_budget(self, item_id: str, winning_team: str, price_paid: float):
        if winning_team == self.team_id:
            self.budget -= price_paid
            self.items_won.append(item_id)

    def update_after_each_round(self, item_id: str, winning_team: str, price_paid: float):
        self._update_available_budget(item_id, winning_team, price_paid)
        my_val = self.valuation_vector.get(item_id, 0)

        if winning_team == self.team_id:
            # Did we win a tax bid?
            if self.last_bid_was_tax and my_val < price_paid:
                # We paid more than our value for a trash item - reduce aggression
                self.tax_floor = max(6.5, self.tax_floor - 0.75)
            self.utility += (my_val - price_paid)

        elif winning_team:
            if winning_team in self.opp_budgets:
                self.opp_budgets[winning_team] -= price_paid
            # Vengeance Tracker: Estimate their utility gain
            # High price paid usually means lower utility gain
            self.opp_utility_est[winning_team] += np.maximum(0, 10.5 - price_paid)

        # Bayesian Inventory Update
        cat = 'high' if price_paid >= 13.67 else ('low' if price_paid <= 5 else 'mixed')
        if self.inventory[cat] > 0:
            self.inventory[cat] -= 1

        self.rounds_completed += 1
        self.last_bid_was_tax = False
        return True

    def bidding_function(self, item_id: str) -> float:
        my_val = self.valuation_vector.get(item_id, 0)
        rounds_left = max(1, self.total_rounds - self.rounds_completed)
        if self.budget <= 0: return 0.0

        # 1. Market Analysis
        total_inv = sum(self.inventory.values())
        p_wild = self.inventory['mixed'] / total_inv if total_inv > 0 else 0.5
        richest_opp_fund = max(self.opp_budgets.values()) if self.opp_budgets else 60.0
        wealth_ratio = self.budget / (richest_opp_fund + 1.0)

        # Identify the current threat (Vengeance Target)
        alpha_team = max(self.opp_utility_est, key=self.opp_utility_est.get)
        alpha_is_rich = self.opp_budgets[alpha_team] > 20.0

        # 2. STRATEGY: THE PREDATORY TAX (Vengeance Logic)
        # If it's a wildcard and our value is trash, force the leader to pay.
        if p_wild > 0.6 and my_val < 6.0 and wealth_ratio > 0.7:
            # If the alpha is rich, we increase the tax to hurt them more
            effective_tax = self.tax_floor + (2.0 if alpha_is_rich else 0.0)
            self.last_bid_was_tax = True
            self.last_bid_amount = min(effective_tax, self.budget * 0.15)
            return round(float(self.last_bid_amount), 2)

        # 3. STRATEGY: SAFE-GAP WILDCARD BIDDING
        # Focus on maximizing (Value - Price) on Mixed items
        if p_wild > 0.6 and my_val > 13.0:
            # We "ask for less" by capping the bid at 14.1
            # This beats the median second-price but protects the utility gap.
            bid = min(my_val * 0.88, 14.1)
        else:
            # Standard Shadow Lambda for High/Low categories
            unseen_pool = max(1, 20 - self.rounds_completed)
            prob_high_future = self.inventory['high'] / unseen_pool
            shadow_lambda = (prob_high_future * 14.0) / (wealth_ratio * (self.budget / rounds_left) + 1.0)
            bid = my_val / (1 + shadow_lambda * 0.08)

        # 4. WEALTH DOMINANCE (The Bully Phase)
        # If we have dominated the budget, outbid the richest opponent by a penny
        if wealth_ratio > 1.3 and my_val > 11:
            bid = max(bid, richest_opp_fund -0.5)

        if my_val > 15:
            bid = max(bid, my_val * 0.92)

        # Endgame Flush (Rounds 14-15)
        if rounds_left <= 2:
            bid = max(bid, my_val * 0.98)

        # Safeguards
        bid = min(bid, my_val, self.budget - 0.01)
        if my_val > 6.0: bid = max(bid, 1.62)

        self.last_bid_was_tax = False
        return round(float(max(0.0, bid)), 2)