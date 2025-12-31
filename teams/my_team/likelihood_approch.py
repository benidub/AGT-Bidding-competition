
# from typing import Dict, List
# import math
#
#
# class BiddingAgent:
#     def __init__(self, team_id: str, valuation_vector: Dict[str, float], budget: float, opponent_teams: List[str]):
#         # Required attributes (DO NOT REMOVE)
#         self.team_id = team_id
#         self.valuation_vector = valuation_vector
#         self.budget = budget
#         self.initial_budget = budget
#         self.opponent_teams = opponent_teams
#         self.utility = 0.0
#         self.items_won = []
#
#         # Game state tracking
#         self.rounds_completed = 0
#         self.total_rounds = 15  # Always 15 rounds per game
#
#         # ===== Strategy state =====
#         # Known pool composition across all 20 goods (without replacement)
#         self.pool_total = 20
#         self.R = {"L": 4.0, "H": 6.0, "M": 10.0}  # expected remaining counts (soft)
#
#         # Category supports
#         self.support = {"L": (1.0, 10.0), "H": (10.0, 20.0), "M": (1.0, 20.0)}
#
#         # Robustness (opponents may shade due to budgets)
#         self.eps_noise = 0.18  # mix likelihood with uniform noise
#         self.uniform_price_density = 1.0 / 20.0  # over [0,20]
#
#         # Runner-up detection tolerance (when we lose and paid price equals our bid)
#         self.price_eq_tol = 1e-9
#
#         # Pacing / selection parameters
#         self.kappa_grid = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
#         self.spend_slack = 1.08  # allow mild overshoot vs target spend
#         self.endgame_rounds = 3  # last N rounds spend-down
#
#         # Logging / optional tracking
#         self.price_history = []
#         self.winner_history = []
#
#         # Store our own last bid per item so we can use it in the likelihood update
#         self.last_bid_by_item = {}
#
#         # Opponent modeling
#         self.opp_spend = {opp: 0.0 for opp in opponent_teams}
#         self.opp_wins = {opp: 0 for opp in opponent_teams}
#         self.allow_pressure_mode =True
#
#         self.verbose= True
#
#     def _update_available_budget(self, item_id: str, winning_team: str, price_paid: float):
#         my_val = self.valuation_vector.get(item_id, 0.0)
#         if winning_team == self.team_id:
#             self.budget -= price_paid
#             self.items_won.append(item_id)
#             self.utility += (my_val - price_paid)
#             if self.verbose and my_val < price_paid:
#                 print(f"My True Val: {my_val} | Price Paid: {price_paid} | Utility ratio: {my_val / price_paid}")
#
#         elif winning_team:
#             self.opp_spend[winning_team] += price_paid
#             self.opp_wins[winning_team] += 1
#
#
#     # ---------- Math helpers (closed form, fast) ----------
#
#     def _clip01(self, x: float) -> float:
#         return 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else x)
#
#     def _F_uniform(self, x: float, a: float, b: float) -> float:
#         if x <= a:
#             return 0.0
#         if x >= b:
#             return 1.0
#         return (x - a) / (b - a)
#
#     # Opponents: 4 draws i.i.d. U[a,b]
#     # M1 = max (normalized ~ Beta(4,1))
#     def _pdf_M1(self, x: float, a: float, b: float) -> float:
#         """ the kth maximal value (Mk) among n i.i.d. U[a,b] has pdf of
#                 n!/(k-1)!(n-k)! * ((x-a)/(b-a))^(k-1) * (1-(x-a)/(b-a))^(n-k) * 1/(b-a)
#         Here: n=4, k=4 => pdf_M1(x) = 4 * ((x-a)/(b-a))^3 * 1/(b-a)"""
#         if x < a or x > b:
#             return 0.0
#         t = (x - a) / (b - a)
#         return (4.0 * (t ** 3)) / (b - a)
#
#     # M2 = 2nd-highest among 4 (normalized ~ Beta(3,2))
#     def _pdf_M2(self, x: float, a: float, b: float) -> float:
#         """ the kth maximal value (Mk) among n i.i.d. U[a,b] has pdf of
#                         n!/(k-1)!(n-k)! * ((x-a)/(b-a))^(k-1) * (1-(x-a)/(b-a))^(n-k) * 1/(b-a)
#         """
#         if x < a or x > b:
#             return 0.0
#         t = (x - a) / (b - a)
#         return (12.0 * (t ** 2) * (1.0 - t)) / (b - a)
#
#     def _expected_spend_uncond(self, bid: float, a: float, b: float) -> float:
#         """
#         Unconditional expected payment if we bid 'bid' against 4 opponents with values ~ U[a,b],
#         assuming bids ~ values, and payment when we win equals M1 (opponent max).
#         E[pay] = ∫_{a}^{min(bid,b)} x f_M1(x) dx
#
#         Closed form with t0 = clip((bid-a)/(b-a), 0, 1):
#         E[pay] = a*t0^4 + (4/5) *(b-a)*t0^5
#         """
#         if bid <= a:
#             return 0.0
#         t0 = self._clip01((min(bid, b) - a) / (b - a))
#         return a * (t0 ** 4) + (4.0/5.0) * (b - a) * (t0 ** 5)
#
#
#     # ---------- Urn prior & value gating ----------
#     def _lv(self, v: float, c: str) -> float:
#         a, b = self.support[c]
#         if v < a or v > b:
#             return 0.0
#         return 1.0 / (b - a)
#
#     def _prior_category(self) -> Dict[str, float]:
#         remaining_goods = max(1.0, float(self.pool_total - self.rounds_completed))
#         q = {c: max(0.0, self.R[c]) / remaining_goods for c in ["L", "H", "M"]}
#         s = q["L"] + q["H"] + q["M"]
#         if s <= 0.0:
#             return {"L": 1/3, "H": 1/3, "M": 1/3}
#         return {c: q[c] / s for c in q}
#
#     def _predictive_category_given_value(self, v: float) -> Dict[str, float]:
#         q0 = self._prior_category()
#         un = {c: q0[c] * self._lv(v, c) for c in q0}
#         s = un["L"] + un["H"] + un["M"]
#         if s <= 0.0:
#             return {"L": 1/3, "H": 1/3, "M": 1/3}
#         return {c: un[c] / s for c in un}
#
#
#     # ---------- Outcome-aware likelihood (uses our bid) ----------
#     def _likelihood_obs(self, price_paid: float, won: bool, bid: float, c: str) -> float:
#         a, b = self.support[c]
#
#         # Model likelihood (density or probability mass)
#         L_model = 0.0
#
#         if won:
#             if price_paid < bid:
#                 L_model = self._pdf_M1(price_paid, a, b) # If we won: price is opponent max M1 and must be < our bid
#             else:
#                 L_model = 0.0
#         else:
#             # If we lost:
#             # Second price p = max(our_bid, M2), with M1 > our_bid.
#             # Two subcases:
#             # (i) p == our_bid  (we are runner-up): exactly one opponent > bid, three <= bid
#             # (ii) p > our_bid  (we are not runner-up): p = M2, with M2 > bid
#             if abs(price_paid - bid) <= self.price_eq_tol:
#                 u = self._F_uniform(bid, a, b)
#                 # P(exactly one opponent above bid) = 4*(1-u)*u^3 (from beta)
#                 L_model = 4.0 * (1.0 - u) * (u ** 3)
#             elif price_paid > bid:
#                 L_model = self._pdf_M2(price_paid, a, b)
#             else:
#                 # Observing p < bid when we lost is inconsistent under this model
#                 L_model = 0.0
#
#         # Robustify with uniform noise on [0,20]
#         if abs(price_paid - bid) <= self.price_eq_tol and not won:
#             # mixture for a probability mass event: add small floor
#             L = (1.0 - self.eps_noise) * L_model + self.eps_noise * 1e-3
#         else:
#             L = (1.0 - self.eps_noise) * L_model + self.eps_noise * self.uniform_price_density
#
#         return L
#
#     # ---------- System callback ----------
#     def update_after_each_round(self, item_id: str, winning_team: str, price_paid: float):
#         self._update_available_budget(item_id, winning_team, price_paid)
#
#
#
#         self.rounds_completed += 1
#
#         # Track public history
#         if price_paid is not None:
#             self.price_history.append(float(price_paid))
#         self.winner_history.append(winning_team)
#
#         # --- Bayesian posterior for this item category, then urn decrement ---
#         v = float(self.valuation_vector.get(item_id, 0.0))
#         bid = float(self.last_bid_by_item.get(item_id, 0.0))
#         won = (winning_team == self.team_id)
#
#         q_prior = self._prior_category()
#
#         un = {}
#         for c in ["L", "H", "M"]:
#             lv = self._lv(v, c)
#             if lv <= 0.0:
#                 un[c] = 0.0
#                 continue
#             Lobs = self._likelihood_obs(float(price_paid), won, bid, c)
#             un[c] = q_prior[c] * lv * Lobs # unnormalized posterior: prior * likelihood * value-likelihood
#
#         s = un["L"] + un["H"] + un["M"]
#         if s <= 0.0:
#             q_post = {"L": 1/3, "H": 1/3, "M": 1/3}
#         else:
#             q_post = {c: un[c] / s for c in un}
#
#         # Soft decrement of remaining counts (without replacement)
#         for c in ["L", "H", "M"]:
#             self.R[c] = max(0.0, self.R[c] - q_post[c])
#
#         return True
#
#
#     # --------- Opponent budget estimation -------------
#
#     def _avg_opp_budget(self):
#         return sum(max(0.0, 60.0 - s) for s in self.opp_spend.values()) / len(self.opp_spend)
#
#     def _competition_is_weak(self):
#         return self._avg_opp_budget() < 15.0
#
#
#     # ---------- Bidding ----------
#     def bidding_function(self, item_id: str) -> float:
#         v = float(self.valuation_vector.get(item_id, 0.0))
#
#         if v <= 0.0 or self.budget <= 0.0:
#             self.last_bid_by_item[item_id] = 0.0
#             return 0.0
#
#         rounds_remaining = self.total_rounds - self.rounds_completed
#         if rounds_remaining <= 0:
#             self.last_bid_by_item[item_id] = 0.0
#             return 0.0
#
#         # Predictive belief for this item's category given urn + our value gating
#         q_pre = self._predictive_category_given_value(v)
#
#         # Budget pacing target
#         target_spend = self.budget / max(1, int(rounds_remaining/2))
#
#         # -------------------------------
#         # PRESSURE MODE (selective)
#         # -------------------------------
#         pressure_mode = False
#
#         # Conditions for pressure bidding
#         if (
#                 q_pre["M"] >= 0.6 and  # Mixed likely
#                 v <= 10.0 and  # low value for us
#                 rounds_remaining > 4 and  # not endgame
#                 self.budget >= 1.2 * target_spend  # budget slack
#         ):
#             pressure_mode = True
#
#         if pressure_mode:
#             # Win-risk control
#             rho = 0.02  # 5% accidental win probability
#             u = rho ** 0.25
#             pressure_bid = 1.0 + 19.0 * u  # Mixed U[1,20]
#
#             # Loss cap: never risk big negative utility
#             L = 2 if rounds_remaining >=10 else 1
#
#
#             bid = min(pressure_bid,v + L,self.budget)
#
#             bid = max(0.0, bid)
#             self.last_bid_by_item[item_id] = float(bid)
#             return float(bid)
#
#         # -------------------------------
#         # VALUE MODE (default)
#         # -------------------------------
#         in_endgame = (rounds_remaining <= self.endgame_rounds)
#         best_bid = 0.0
#         # Choose kappa to keep expected spend near target_spend
#         for kappa in self.kappa_grid:
#             # Endgame: forbid overly conservative bids
#             if in_endgame:
#                 # In the endgame, disallow very conservative kappas
#                 if rounds_remaining == 3 and kappa < 0.50:
#                     continue
#                 if rounds_remaining == 2 and kappa < 0.70:
#                     continue
#                 if rounds_remaining == 1 and kappa < 0.90:
#                     continue
#
#             bid = min(self.budget, kappa * v)
#
#             # Expected spend under mixture
#             exp_spend = 0.0
#             for c in ["L", "H", "M"]:
#                 a, b = self.support[c]
#                 exp_spend += q_pre[c] * self._expected_spend_uncond(bid, a, b)
#
#             # Accept if within pacing; pick the largest kappa satisfying the constraint
#             if exp_spend <= self.spend_slack * target_spend + 1e-12:
#                 best_bid = bid
#
#         # If we couldn't fit pacing at all (e.g., very low target_spend), still place a minimal-but-not-zero bid
#         # only when value is strong, to avoid missing cheap low-competition wins.
#         if best_bid <= 0.0:
#             # Small exploratory bid: fraction of target spend, capped by value and budget.
#             best_bid = min(self.budget, min(v, 0.75 * target_spend))
#
#         best_bid = max(0.0, min(best_bid, self.budget))
#         self.last_bid_by_item[item_id] = float(best_bid)
#         return float(best_bid)     #bidding function with pressure mode: 31.0%, avg_item: 3.7, avg_budget: 47.99

"""
AGT Competition - Student Agent Template
========================================

Team Name: Bayesian-Urn Pacing
Members:
  - [Student 1 Name and ID]
  # - [Student 2 Name and ID]
  - [Student 3 Name and ID]

Strategy Description:
Bayesian inference of item category (Low/High/Mixed) using an urn model (known 4/6/10 composition, without replacement)
and second-price outcomes. Budget is managed via pacing: choose a shading factor kappa each round so expected spend
matches remaining-budget / remaining-rounds, with endgame spend-down.

Key Features:
- Urn prior with soft posterior decrement (sampling without replacement).
- Outcome-aware likelihood: if we win, price ~ max(opponents); if we lose, price ~ max(our_bid, opponents_2nd_highest).
- Budget pacing via closed-form expected spend under uniform order-statistics and a small kappa grid search.
"""

from typing import Dict, List
import math


class BiddingAgent:
    def __init__(self, team_id: str, valuation_vector: Dict[str, float], budget: float, opponent_teams: List[str]):
        # Required attributes (DO NOT REMOVE)
        self.team_id = team_id
        self.valuation_vector = valuation_vector
        self.budget = budget
        self.initial_budget = budget
        self.opponent_teams = opponent_teams
        self.utility = 0.0
        self.items_won = []

        # Game state tracking
        self.rounds_completed = 0
        self.total_rounds = 15  # Always 15 rounds per game

        # ===== Strategy state =====
        # Known pool composition across all 20 goods (without replacement)
        self.pool_total = 20
        self.R = {"L": 4.0, "H": 6.0, "M": 10.0}  # expected remaining counts (soft)

        # Category supports
        self.support = {"L": (1.0, 10.0), "H": (10.0, 20.0), "M": (1.0, 20.0)}

        # Robustness (opponents may shade due to budgets)
        self.eps_noise = 0.18  # mix likelihood with uniform noise
        self.uniform_price_density = 1.0 / 20.0  # over [0,20]

        # Runner-up detection tolerance (when we lose and paid price equals our bid)
        self.price_eq_tol = 1e-9

        # Pacing / selection parameters
        self.kappa_grid = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
        self.spend_slack = 1.08  # allow mild overshoot vs target spend
        self.endgame_rounds = 3  # last N rounds spend-down

        # Logging / optional tracking
        self.price_history = []
        self.winner_history = []

        # Store our own last bid per item so we can use it in the likelihood update
        self.last_bid_by_item = {}

        # Opponent modeling
        self.opp_spend = {opp: 0.0 for opp in opponent_teams}
        self.opp_wins = {opp: 0 for opp in opponent_teams}
        self.allow_pressure_mode =True

        self.verbose= True

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


    # ---------- Math helpers (closed form, fast) ----------

    def _clip01(self, x: float) -> float:
        return 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else x)

    def _F_uniform(self, x: float, a: float, b: float) -> float:
        if x <= a:
            return 0.0
        if x >= b:
            return 1.0
        return (x - a) / (b - a)

    # Opponents: 4 draws i.i.d. U[a,b]
    # M1 = max (normalized ~ Beta(4,1))
    def _pdf_M1(self, x: float, a: float, b: float) -> float:
        """ the kth maximal value (Mk) among n i.i.d. U[a,b] has pdf of
                n!/(k-1)!(n-k)! * ((x-a)/(b-a))^(k-1) * (1-(x-a)/(b-a))^(n-k) * 1/(b-a)
        Here: n=4, k=4 => pdf_M1(x) = 4 * ((x-a)/(b-a))^3 * 1/(b-a)"""
        if x < a or x > b:
            return 0.0
        t = (x - a) / (b - a)
        return (4.0 * (t ** 3)) / (b - a)

    # M2 = 2nd-highest among 4 (normalized ~ Beta(3,2))
    def _pdf_M2(self, x: float, a: float, b: float) -> float:
        """ the kth maximal value (Mk) among n i.i.d. U[a,b] has pdf of
                        n!/(k-1)!(n-k)! * ((x-a)/(b-a))^(k-1) * (1-(x-a)/(b-a))^(n-k) * 1/(b-a)
        """
        if x < a or x > b:
            return 0.0
        t = (x - a) / (b - a)
        return (12.0 * (t ** 2) * (1.0 - t)) / (b - a)

    def _expected_spend_uncond(self, bid: float, a: float, b: float) -> float:
        """
        Unconditional expected payment if we bid 'bid' against 4 opponents with values ~ U[a,b],
        assuming bids ~ values, and payment when we win equals M1 (opponent max).
        E[pay] = ∫_{a}^{min(bid,b)} x f_M1(x) dx

        Closed form with t0 = clip((bid-a)/(b-a), 0, 1):
        E[pay] = a*t0^4 + (4/5) *(b-a)*t0^5
        """
        if bid <= a:
            return 0.0
        t0 = self._clip01((min(bid, b) - a) / (b - a))
        return a * (t0 ** 4) + (4.0/5.0) * (b - a) * (t0 ** 5)


    # ---------- Urn prior & value gating ----------
    def _lv(self, v: float, c: str) -> float:
        a, b = self.support[c]
        if v < a or v > b:
            return 0.0
        return 1.0 / (b - a)

    def _prior_category(self) -> Dict[str, float]:
        remaining_goods = max(1.0, float(self.pool_total - self.rounds_completed))
        q = {c: max(0.0, self.R[c]) / remaining_goods for c in ["L", "H", "M"]}
        s = q["L"] + q["H"] + q["M"]
        if s <= 0.0:
            return {"L": 1/3, "H": 1/3, "M": 1/3}
        return {c: q[c] / s for c in q}

    def _predictive_category_given_value(self, v: float) -> Dict[str, float]:
        q0 = self._prior_category()
        un = {c: q0[c] * self._lv(v, c) for c in q0}
        s = un["L"] + un["H"] + un["M"]
        if s <= 0.0:
            return {"L": 1/3, "H": 1/3, "M": 1/3}
        return {c: un[c] / s for c in un}


    # ---------- Outcome-aware likelihood (uses our bid) ----------
    def _likelihood_obs(self, price_paid: float, won: bool, bid: float, c: str) -> float:
        a, b = self.support[c]

        # Model likelihood (density or probability mass)
        L_model = 0.0

        if won:
            if price_paid < bid:
                L_model = self._pdf_M1(price_paid, a, b) # If we won: price is opponent max M1 and must be < our bid
            else:
                L_model = 0.0
        else:
            # If we lost:
            # Second price p = max(our_bid, M2), with M1 > our_bid.
            # Two subcases:
            # (i) p == our_bid  (we are runner-up): exactly one opponent > bid, three <= bid
            # (ii) p > our_bid  (we are not runner-up): p = M2, with M2 > bid
            if abs(price_paid - bid) <= self.price_eq_tol:
                u = self._F_uniform(bid, a, b)
                # P(exactly one opponent above bid) = 4*(1-u)*u^3 (from beta)
                L_model = 4.0 * (1.0 - u) * (u ** 3)
            elif price_paid > bid:
                L_model = self._pdf_M2(price_paid, a, b)
            else:
                # Observing p < bid when we lost is inconsistent under this model
                L_model = 0.0

        # Robustify with uniform noise on [0,20]
        if abs(price_paid - bid) <= self.price_eq_tol and not won:
            # mixture for a probability mass event: add small floor
            L = (1.0 - self.eps_noise) * L_model + self.eps_noise * 1e-3
        else:
            L = (1.0 - self.eps_noise) * L_model + self.eps_noise * self.uniform_price_density

        return L

    # ---------- System callback ----------
    def update_after_each_round(self, item_id: str, winning_team: str, price_paid: float):
        self._update_available_budget(item_id, winning_team, price_paid)
        self.rounds_completed += 1

        # Track public history
        if price_paid is not None:
            self.price_history.append(float(price_paid))
        self.winner_history.append(winning_team)

        # --- Bayesian posterior for this item category, then urn decrement ---
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
            un[c] = q_prior[c] * lv * Lobs # unnormalized posterior: prior * likelihood * value-likelihood

        s = un["L"] + un["H"] + un["M"]
        if s <= 0.0:
            q_post = {"L": 1/3, "H": 1/3, "M": 1/3}
        else:
            q_post = {c: un[c] / s for c in un}

        # Soft decrement of remaining counts (without replacement)
        for c in ["L", "H", "M"]:
            self.R[c] = max(0.0, self.R[c] - q_post[c])

        return True


    # --------- Opponent budget estimation -------------

    def _avg_opp_budget(self):
        return sum(max(0.0, 60.0 - s) for s in self.opp_spend.values()) / len(self.opp_spend)

    def _competition_is_weak(self):
        return self._avg_opp_budget() < 15.0


    # ---------- Bidding ----------
    def bidding_function(self, item_id: str) -> float:
        v = float(self.valuation_vector.get(item_id, 0.0))

        if v <= 0.0 or self.budget <= 0.0:
            self.last_bid_by_item[item_id] = 0.0
            return 0.0

        rounds_remaining = self.total_rounds - self.rounds_completed
        if rounds_remaining <= 0:
            self.last_bid_by_item[item_id] = 0.0
            return 0.0

        # Predictive belief for this item's category given urn + our value gating
        q_pre = self._predictive_category_given_value(v)

        # Budget pacing target
        # target_spend = self.budget / max(1, int(rounds_remaining/2))
        expected_total_wins = 4
        wins_remaining = max(1.0, expected_total_wins - len(self.items_won))
        target_spend = self.budget / wins_remaining
        # -------------------------------
        # PRESSURE MODE (selective)
        # -------------------------------
        pressure_mode = False

        # Conditions for pressure bidding
        if (
                q_pre["M"] >= 0.6 and  # Mixed likely
                v <= 10 and  # low value for us
                rounds_remaining > 4 and  # not endgame
                self.budget >= 1.2 * target_spend  # budget slack
        ):
            pressure_mode = True

        if pressure_mode:
            # Win-risk control
            rho = 0.02  # 5% accidental win probability
            u = rho ** 0.25
            pressure_bid = 1.0 + 19.0 * u  # Mixed U[1,20]

            # Loss cap: never risk big negative utility
            L = 2 if rounds_remaining >=10 else 1


            bid = min(pressure_bid,v + L,self.budget)

            bid = max(0.0, bid)
            self.last_bid_by_item[item_id] = float(bid)
            return float(bid)

        # -------------------------------
        # VALUE MODE (default)
        # -------------------------------
        in_endgame = (rounds_remaining <= self.endgame_rounds)
        best_bid = 0.0
        # Choose kappa to keep expected spend near target_spend
        for kappa in self.kappa_grid:
            # Endgame: forbid overly conservative bids
            if in_endgame:
                # In the endgame, disallow very conservative kappas
                if rounds_remaining == 3 and kappa < 0.50:
                    continue
                if rounds_remaining == 2 and kappa < 0.70:
                    continue
                if rounds_remaining == 1 and kappa < 0.90:
                    continue

            bid = min(self.budget, kappa * v)

            # Expected spend under mixture
            exp_spend = 0.0
            for c in ["L", "H", "M"]:
                a, b = self.support[c]
                exp_spend += q_pre[c] * self._expected_spend_uncond(bid, a, b)

            # Accept if within pacing; pick the largest kappa satisfying the constraint
            if exp_spend <= self.spend_slack * target_spend + 1e-12:
                best_bid = bid

        # If we couldn't fit pacing at all (e.g., very low target_spend), still place a minimal-but-not-zero bid
        # only when value is strong, to avoid missing cheap low-competition wins.
        if best_bid <= 0.0:
            # Small exploratory bid: fraction of target spend, capped by value and budget.
            best_bid = min(self.budget, min(v, 0.75 * target_spend))

        best_bid = max(0.0, min(best_bid, self.budget))
        self.last_bid_by_item[item_id] = float(best_bid)
        return float(best_bid) #bidding function with pressure mode: 31.0%, avg_item: 4, avg_budget: 47.99, avg_utility: 12.27



