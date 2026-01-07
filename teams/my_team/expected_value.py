from typing import Dict, List
import math


class BiddingAgent:
    def __init__(self, team_id: str, valuation_vector: Dict[str, float], budget: float, opponent_teams: List[str]):
        # Required attributes
        self.team_id = team_id
        self.valuation_vector = valuation_vector
        self.budget = budget
        self.initial_budget = budget
        self.opponent_teams = opponent_teams
        self.utility = 0.0
        self.items_won = []

        # Game state tracking
        self.rounds_completed = 0
        self.total_rounds = 15

        # ===== Strategy state =====
        # Known pool composition (guesses about how many of each category remain)
        self.pool_total = 20
        self.R = {"L": 4.0, "H": 6.0, "M": 10.0}

        # Category supports
        self.support = {"L": (1.0, 10.0), "H": (10.0, 20.0), "M": (1.0, 20.0)}

        # Robustness parameters for likelihood updates
        self.eps_noise = 0.18
        self.uniform_price_density = 1.0 / 20.0
        self.price_eq_tol = 1e-9

        # Logging
        self.price_history = []
        self.winner_history = []
        self.last_bid_by_item = {}
        self.opp_spend = {opp: 0.0 for opp in opponent_teams}
        self.opp_wins = {opp: 0 for opp in opponent_teams}
        self.verbose = True

    def _update_available_budget(self, item_id: str, winning_team: str, price_paid: float):
        my_val = self.valuation_vector.get(item_id, 0.0)
        if winning_team == self.team_id:
            self.budget -= price_paid
            self.items_won.append(item_id)
            self.utility += (my_val - price_paid)
            if self.verbose and my_val < price_paid:
                print(f"My True Val: {my_val} | Price Paid: {price_paid} | Utility ratio: {my_val / price_paid}")
        elif winning_team:
            self.opp_spend[winning_team] += price_paid
            self.opp_wins[winning_team] += 1

    # ---------- Math helpers ----------
    def _clip01(self, x: float) -> float:
        return 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else x)

    def _F_uniform(self, x: float, a: float, b: float) -> float:
        if x <= a: return 0.0
        if x >= b: return 1.0
        return (x - a) / (b - a)

    def _pdf_M1(self, x: float, a: float, b: float) -> float:
        if x < a or x > b: return 0.0
        t = (x - a) / (b - a)
        return (4.0 * (t ** 3)) / (b - a)

    def _pdf_M2(self, x: float, a: float, b: float) -> float:
        if x < a or x > b: return 0.0
        t = (x - a) / (b - a)
        return (12.0 * (t ** 2) * (1.0 - t)) / (b - a)

    # ---------- Urn prior & value gating ----------
    def _lv(self, v: float, c: str) -> float:
        a, b = self.support[c]
        if v < a or v > b: return 0.0
        return 1.0 / (b - a)

    def _prior_category(self) -> Dict[str, float]:
        # Current probability based on remaining counts R
        remaining_goods = max(1.0, float(self.pool_total - self.rounds_completed))
        q = {c: max(0.0, self.R[c]) / remaining_goods for c in ["L", "H", "M"]}
        s = sum(q.values())
        if s <= 0.0: return {"L": 1 / 3, "H": 1 / 3, "M": 1 / 3}
        return {c: q[c] / s for c in q}

    # ---------- Likelihood ----------
    def _likelihood_obs(self, price_paid: float, won: bool, bid: float, c: str) -> float:
        a, b = self.support[c]
        L_model = 0.0
        if won:
            if price_paid < bid:
                L_model = self._pdf_M1(price_paid, a, b)
        else:
            if abs(price_paid - bid) <= self.price_eq_tol:
                u = self._F_uniform(bid, a, b)
                L_model = 4.0 * (1.0 - u) * (u ** 3)
            elif price_paid > bid:
                L_model = self._pdf_M2(price_paid, a, b)

        if abs(price_paid - bid) <= self.price_eq_tol and not won:
            return (1.0 - self.eps_noise) * L_model + self.eps_noise * 1e-3
        else:
            return (1.0 - self.eps_noise) * L_model + self.eps_noise * self.uniform_price_density

    # ---------- Update Loop ----------
    def update_after_each_round(self, item_id: str, winning_team: str, price_paid: float):
        self._update_available_budget(item_id, winning_team, price_paid)
        self.rounds_completed += 1

        if price_paid is not None:
            self.price_history.append(float(price_paid))
        self.winner_history.append(winning_team)

        # Bayesian update of beliefs
        v = float(self.valuation_vector.get(item_id, 0.0))
        bid = float(self.last_bid_by_item.get(item_id, 0.0))
        won = (winning_team == self.team_id)
        q_prior = self._prior_category()

        un = {}
        for c in ["L", "H", "M"]:
            lv = self._lv(v, c)
            if lv <= 0.0:
                un[c] = 0.0
                continue
            Lobs = self._likelihood_obs(float(price_paid), won, bid, c)
            un[c] = q_prior[c] * lv * Lobs

        s = sum(un.values())
        if s <= 0.0:
            q_post = {"L": 1 / 3, "H": 1 / 3, "M": 1 / 3}
        else:
            q_post = {c: un[c] / s for c in un}

        # Decrement the "guesses" (R) based on what we just saw
        for c in ["L", "H", "M"]:
            self.R[c] = max(0.0, self.R[c] - q_post[c])

        return True

    # ---------- Bidding Function (UPDATED) ----------
    def bidding_function(self, item_id: str) -> float:
        v = float(self.valuation_vector.get(item_id, 0.0))

        # Safety checks
        if v <= 0.0 or self.budget <= 0.0:
            self.last_bid_by_item[item_id] = 0.0
            return 0.0

        rounds_remaining = self.total_rounds - self.rounds_completed
        if rounds_remaining <= 0:
            self.last_bid_by_item[item_id] = 0.0
            return 0.0

        # Retrieve current agent guesses (remaining counts)
        L = max(0.0, self.R["L"])
        M = max(0.0, self.R["M"])
        H = max(0.0, self.R["H"])

        calculated_bid = 0.0
        l, m, h = 8.2,16.2,18
        if v < 10.0:
            # Case: Smaller than 10
            # Formula: (L/(M+L))*7 + (M/(L+M))*13.66
            denominator = L + M
            if denominator > 1e-9:
                calculated_bid = (L / denominator) * l + (M / denominator) * m
            else:
                # Fallback if beliefs for L and M are both 0 (unlikely given v < 10)
                calculated_bid = m
        else:
            # Case: Greater than or equal to 10
            # Formula: (H/(H+M))*16.7 + (M/(H+M))*13.66
            denominator = H + M
            if denominator > 1e-9:
                calculated_bid = (H / denominator) * h + (M / denominator) * m
            else:
                # Fallback if beliefs for H and M are both 0
                calculated_bid = m

        # Ensure we don't bid more than our remaining budget
        final_bid = max(0.0, min(calculated_bid, self.budget))

        self.last_bid_by_item[item_id] = float(final_bid)
        return float(final_bid)