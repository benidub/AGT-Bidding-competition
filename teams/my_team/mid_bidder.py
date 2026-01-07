from typing import Dict, List
import math


class BiddingAgent:
    """
    Strategy Summary (what this code implements)
    --------------------------------------------
    - Online Bayesian classification of each item as {High, Low, Mixed} using:
        (a) your value v(item) (hard gate) and
        (b) the public clearing price p (2nd-highest bid ~ 2nd-highest value)
      Model: with 5 players, clearing price ~ 2nd-highest among 5 i.i.d. values
             => 4th order statistic => Beta(4,2) on normalized support.

    - Budget-aware bidding via Lagrangian shading:
        bid = v / (1 + lambda)
      lambda is chosen by quick binary search to pace expected spend:
        expected_payment(bid) ≈ budget_remaining / rounds_remaining
      plus:
        - do not bid if expected utility <= 0
        - spend-down more aggressively in last few rounds

    Notes:
    - This uses a Dirichlet learner for mixture weights of {H,L,M} over the 20 goods.
    - No knowledge of true counts is assumed. If counts are known, you can swap to a
      "remaining-counts" model easily.
    """

    def __init__(self, team_id: str, valuation_vector: Dict[str, float], budget: float, opponent_teams: List[str]):
        # Required attributes (DO NOT REMOVE)
        self.team_id = team_id
        self.valuation_vector = valuation_vector
        self.budget = budget
        self.initial_budget = budget
        self.opponent_teams = opponent_teams
        self.utility = 0
        self.items_won = []

        # Game state tracking
        self.rounds_completed = 0
        self.total_rounds = 15  # Always 15 rounds per game

        # -----------------------------
        # Custom state (strategy)
        # -----------------------------
        self.eps_price_noise = 0.15  # robustify price likelihood
        self.price_history: List[float] = []
        self.win_history: List[bool] = []

        # Dirichlet over mixture weights of categories among goods
        # (H, L, M) == (High, Low, Mixed)
        self.alpha_H = 1.0
        self.alpha_L = 1.0
        self.alpha_M = 1.0

        # Cache what we believed *before* the round, so update_after_each_round can do posterior correctly
        self._last_item_id = None
        self._last_v = None
        self._last_prior = None  # dict C->prob before observing price

        # Precompute Beta(4,2) normalization: pdf(z)=20*z^3*(1-z) on [0,1]
        self._beta42_const = 20.0

    def _update_available_budget(self, item_id: str, winning_team: str, price_paid: float):
        if winning_team == self.team_id:
            self.budget -= price_paid
            self.items_won.append(item_id)

    # -----------------------------
    # Category model helpers
    # -----------------------------
    def _support(self, C: str):
        if C == "H":
            return 10.0, 20.0
        if C == "L":
            return 1.0, 10.0
        return 1.0, 20.0  # "M"

    def _dirichlet_prior(self):
        s = self.alpha_H + self.alpha_L + self.alpha_M
        return {"H": self.alpha_H / s, "L": self.alpha_L / s, "M": self.alpha_M / s}

    def _likelihood_v(self, v: float, C: str):
        a, b = self._support(C)
        if v < a or v > b:
            return 0.0
        return 1.0 / (b - a)

    def _beta42_pdf(self, z: float):
        if z <= 0.0 or z >= 1.0:
            return 0.0
        return self._beta42_const * (z ** 3) * (1.0 - z)

    def _likelihood_price(self, p: float, C: str):
        a, b = self._support(C)
        if p <= 0:
            # If the simulator can output 0 for "no meaningful second-highest",
            # treat as weak evidence; keep it non-zero to avoid killing beliefs.
            return 1e-6

        if p < a or p > b:
            base = 0.0
        else:
            L = b - a
            z = (p - a) / L
            base = (1.0 / L) * self._beta42_pdf(z)

        # Robust mixture with a uniform noise component over [0,20]
        noise = 1.0 / 20.0
        return (1.0 - self.eps_price_noise) * base + self.eps_price_noise * noise

    def _posterior_category(self, v: float, p: float, prior: Dict[str, float]):
        unnorm = {}
        total = 0.0
        for C in ("H", "L", "M"):
            lv = self._likelihood_v(v, C)
            if lv == 0.0:
                unnorm[C] = 0.0
                continue
            lp = self._likelihood_price(p, C)
            val = prior.get(C, 0.0) * lv * lp
            unnorm[C] = val
            total += val

        if total <= 0.0:
            # Fallback: gate by value only
            gated = {}
            tot2 = 0.0
            for C in ("H", "L", "M"):
                val = prior.get(C, 0.0) * self._likelihood_v(v, C)
                gated[C] = val
                tot2 += val
            if tot2 <= 0.0:
                return {"H": 1/3, "L": 1/3, "M": 1/3}
            return {C: gated[C] / tot2 for C in gated}

        return {C: unnorm[C] / total for C in unnorm}

    def _prior_for_current_item(self, v: float):
        base = self._dirichlet_prior()
        # Hard gate by your value
        gated = {}
        total = 0.0
        for C in ("H", "L", "M"):
            lv = self._likelihood_v(v, C)
            val = base[C] * (1.0 if lv > 0.0 else 0.0)
            gated[C] = val
            total += val
        if total <= 0.0:
            return base
        return {C: gated[C] / total for C in gated}

    # -----------------------------
    # Vickrey-with-4-opponents spend/utility model (fast closed forms)
    # -----------------------------
    def _t_for_bid(self, bid: float, a: float, b: float):
        if bid <= a:
            return 0.0
        if bid >= b:
            return 1.0
        return (bid - a) / (b - a)

    def _pwin_under_C(self, bid: float, C: str):
        a, b = self._support(C)
        t = self._t_for_bid(bid, a, b)
        # max of 4 opponents: P(max < bid) = t^4
        return t ** 4

    def _expected_payment_under_C(self, bid: float, C: str):
        # Expected payment in 2nd-price ~ max opponent value when you win,
        # unconditional expectation of payment: E[max * 1{max<bid}]
        a, b = self._support(C)
        L = b - a
        t = self._t_for_bid(bid, a, b)
        if t <= 0.0:
            return 0.0
        # ∫ m f_M(m) dm with M=max of 4 uniforms on [a,b]
        # Using normalized x in [0,t]: Epay = a*t^4 + (4L/5)*t^5
        return a * (t ** 4) + (4.0 * L / 5.0) * (t ** 5)

    def _expected_utility_mixture(self, v: float, bid: float, qpre: Dict[str, float]):
        # E[utility] = sum_C q(C) * ( v*Pwin - Epay )
        eu = 0.0
        for C in ("H", "L", "M"):
            pwin = self._pwin_under_C(bid, C)
            epay = self._expected_payment_under_C(bid, C)
            eu += qpre[C] * (v * pwin - epay)
        return eu

    def _expected_payment_mixture(self, bid: float, qpre: Dict[str, float]):
        ep = 0.0
        for C in ("H", "L", "M"):
            ep += qpre[C] * self._expected_payment_under_C(bid, C)
        return ep

    def _choose_lambda(self, v: float, qpre: Dict[str, float], budget_rem: float, rounds_rem: int):
        # Target spend per remaining round
        target = budget_rem / max(1, rounds_rem)

        # Endgame spend-down: reduce shading
        if rounds_rem <= 3:
            return 0.0

        # If value is tiny, no need to search hard
        if v <= 0.0:
            return 1e6

        # Binary search lambda in [0, lam_hi] so that expected payment matches target
        # bid(lambda) = v/(1+lambda), capped by budget_rem
        lam_lo = 0.0
        lam_hi = 50.0  # plenty

        for _ in range(10):  # 10 iterations is fast and accurate enough
            lam_mid = 0.5 * (lam_lo + lam_hi)
            bid = min(budget_rem, v / (1.0 + lam_mid))
            ep = self._expected_payment_mixture(bid, qpre)

            # If spending too much, increase lambda (shade more)
            if ep > target:
                lam_lo = lam_mid
            else:
                lam_hi = lam_mid

        return lam_hi

    # -----------------------------
    # Main update hook
    # -----------------------------
    def update_after_each_round(self, item_id: str, winning_team: str, price_paid: float):
        # System updates (DO NOT REMOVE)
        self._update_available_budget(item_id, winning_team, price_paid)
        if winning_team == self.team_id:
            self.utility += (self.valuation_vector[item_id] - price_paid)

        self.rounds_completed += 1

        # Track history
        if price_paid is not None:
            self.price_history.append(float(price_paid))
        self.win_history.append(winning_team == self.team_id)

        # Bayesian posterior update for mixture weights, if we have the cached prior/value for this item
        v = self.valuation_vector.get(item_id, 0.0)
        if self._last_item_id == item_id and self._last_prior is not None and self._last_v is not None:
            post = self._posterior_category(self._last_v, float(price_paid), self._last_prior)

            # Dirichlet soft update
            self.alpha_H += post["H"]
            self.alpha_L += post["L"]
            self.alpha_M += post["M"]

        # Clear cache
        self._last_item_id = None
        self._last_v = None
        self._last_prior = None

        return True

    # -----------------------------
    # Bidding decision
    # -----------------------------
    def bidding_function(self, item_id: str) -> float:
        v = float(self.valuation_vector.get(item_id, 0.0))
        if v <= 0.0 or self.budget <= 0.0:
            return 0.0

        rounds_remaining = self.total_rounds - self.rounds_completed
        if rounds_remaining <= 0:
            return 0.0

        # Pre-bid category belief for this item (history + hard gate by v)
        qpre = self._prior_for_current_item(v)

        # Choose lambda to pace spending
        lam = self._choose_lambda(v, qpre, self.budget, rounds_remaining)
        bid = min(self.budget, v / (1.0 + lam))

        # Optional: skip negative expected value bids (important with budget constraints)
        eu = self._expected_utility_mixture(v, bid, qpre)
        if eu <= 1e-9:
            bid = 0.0

        # Cache what we believed before seeing the price, for posterior update in update_after_each_round
        self._last_item_id = item_id
        self._last_v = v
        self._last_prior = qpre

        return float(max(0.0, min(bid, self.budget))) #27%!
