"""
Team: Daniel The Hammer
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

        # מעקב יריבים ומלאי
        self.opp_budgets = {opp: 60.0 for opp in opponent_teams}
        self.inventory = {'high': 6, 'low': 4, 'mixed': 10}
        self.market_prices = []

    def _update_available_budget(self, item_id: str, winning_team: str, price_paid: float):
        if winning_team == self.team_id:
            self.budget -= price_paid
            self.items_won.append(item_id)

    def update_after_each_round(self, item_id: str, winning_team: str, price_paid: float):
        self._update_available_budget(item_id, winning_team, price_paid)
        if winning_team == self.team_id:
            self.utility += (self.valuation_vector.get(item_id, 0) - price_paid)

        # עדכון תקציב יריבים (דיוק של 100%)
        if winning_team and winning_team != self.team_id:
            if winning_team in self.opp_budgets:
                self.opp_budgets[winning_team] -= price_paid

        # עדכון מלאי בייסיאני
        cat = 'high' if price_paid >= 11.0 else ('low' if price_paid <= 4.8 else 'mixed')
        if self.inventory[cat] > 0: self.inventory[cat] -= 1

        self.market_prices.append(price_paid)
        self.rounds_completed += 1
        return True

    # --- פונקציות עזר לחישובים מורכבים ---

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
        my_val = self.valuation_vector.get(item_id, 0)
        rounds_left = max(1, self.total_rounds - self.rounds_completed)

        if self.budget <= 0: return 0.0

        # --- שלב א: ניתוח עושר יחסי ---
        richest_opp_fund = max(self.opp_budgets.values()) if self.opp_budgets else 60.0
        wealth_ratio = self.budget / (richest_opp_fund + 1.0)

        # --- שלב ב: חישוב מחיר צל (Shadow Price) ---
        unseen_pool = max(1, 20 - self.rounds_completed)
        prob_high_future = self.inventory['high'] / unseen_pool
        # ככל שאנחנו עשירים יותר (wealth_ratio), ה-lambda יורדת -> אנחנו מרשים לעצמנו להוציא יותר
        shadow_lambda = (prob_high_future * 14.0) / (wealth_ratio * (self.budget / rounds_left) + 1.0)

        # --- שלב ג: קביעת הביד המנצח ---
        # ביד בסיסי עם Shading
        bid = my_val / (1 + shadow_lambda * 0.08)

        # אסטרטגיית הHammer (הפטיש):
        # אם אנחנו עשירים מהיריב וזה פריט בעל ערך, אנחנו לא עושים Shading.
        # אנחנו פשוט מציעים מחיר שינעל אותו בחוץ.
        if wealth_ratio > 1.3 and my_val > 10:
            pass
            bid = max(bid, richest_opp_fund + 0.11)

        # אסטרטגיית ה-Predator:
        # אם הפריט הוא בסיכוי גבוה High לכולם (לפי הערך שלנו), אנחנו "מטרילים"
        # את OPP2 ומציעים 92% מהערך שלנו כדי להכריח אותו לשלם ביוקר.
        if my_val > 15:
            bid = max(bid, my_val * 0.92)

        # Endgame: סיבובים 14-15
        if rounds_left <= 2:
            bid = max(bid, my_val * 0.98)

        # הגנות
        bid = min(bid, my_val, self.budget - 0.01)

        # Floor (מניעת מתנות): 1.62 ש"ח (עוקף את כולם)
        if my_val > 6.0:
            bid = max(bid, 1.62)

        return round(float(max(0.0, bid)), 2)


