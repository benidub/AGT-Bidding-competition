# """
# Team Name: CardCounter
# Strategy: Shadow Pacing + Item Category Inference (Card Counting)
# """
# from typing import Dict, List
#
#
# class BiddingAgent:
#     def __init__(self, team_id: str, valuation_vector: Dict[str, float],
#                  budget: float, opponent_teams: List[str]):
#         # Standard Setup
#         self.team_id = team_id
#         self.valuation_vector = valuation_vector
#         self.budget = budget
#         self.initial_budget = budget
#         self.utility = 0
#         self.items_won = []
#         self.rounds_completed = 0
#         self.total_rounds = 15
#
#         # --- STRATEGY: SHADOW PACER ---
#         self.total_value_remaining = sum(valuation_vector.values())
#         self.shadow_price = 0.5
#         self.alpha = 0.2
#
#         # --- STRATEGY: CARD COUNTING ---
#         # We track the "Deck" of items
#         self.remaining_deck = {
#             "High": 6,  # Competitive items (Everyone > 10)
#             "Low": 4,  # Junk items (Everyone < 10)
#             "Mixed": 10  # Random items
#         }
#
#     def _update_available_budget(self, item_id: str, winning_team: str, price_paid: float):
#         if winning_team == self.team_id:
#             self.budget -= price_paid
#             self.items_won.append(item_id)
#
#     def _infer_category(self, my_val: float, price_paid: float):
#         """
#         Guess the category of the item just sold based on My Value vs Market Price.
#         """
#         # Heuristic Logic:
#
#         # 1. If Price is high (>10), it implies at least 2 people bid high.
#         # It's likely High Value or Mixed.
#         if price_paid > 10.5:
#             # If I also valued it high, it's very likely a Common High Value item
#             if my_val > 10:
#                 return "High"
#             # If I valued it low, but price is high, it's a Mixed item
#             # (opponents got high values, I got low)
#             else:
#                 return "Mixed"
#
#         # 2. If Price is low (<9), it implies the 2nd highest bidder was low.
#         elif price_paid < 9.0:
#             # If I valued it low too, likely Common Low Value
#             if my_val < 10:
#                 return "Low"
#             # If I valued it HIGH, but price is LOW -> Mixed item (I was lucky)
#             else:
#                 return "Mixed"
#
#         # 3. Grey area (Price 9-10.5), default to Mixed to be safe
#         return "Mixed"
#
#     def update_after_each_round(self, item_id: str, winning_team: str, price_paid: float):
#         # 1. Standard Updates
#         self._update_available_budget(item_id, winning_team, price_paid)
#         if winning_team == self.team_id:
#             self.utility += (self.valuation_vector[item_id] - price_paid)
#
#         my_val = self.valuation_vector.get(item_id, 0)
#         self.total_value_remaining -= my_val
#         self.rounds_completed += 1
#
#         # 2. INFERENCE: Update the Deck
#         inferred_category = self._infer_category(my_val, price_paid)
#
#         # Decrement count (don't go below zero)
#         if self.remaining_deck[inferred_category] > 0:
#             self.remaining_deck[inferred_category] -= 1
#         else:
#             # Fallback: if we thought we were out of 'High', but saw another,
#             # decrement 'Mixed' instead as our fallback bucket.
#             if self.remaining_deck["Mixed"] > 0:
#                 self.remaining_deck["Mixed"] -= 1
#
#         # 3. Shadow Price Logic (Standard Adaptive Pacer)
#         rounds_remaining = self.total_rounds - self.rounds_completed
#         if rounds_remaining > 0:
#             safe_val = max(1.0, self.total_value_remaining)
#             wealth_ratio = self.budget / safe_val
#             target = 0.24
#
#             if wealth_ratio < target:
#                 self.shadow_price *= (1 + self.alpha)
#             else:
#                 self.shadow_price *= (1 - self.alpha)
#             self.shadow_price = max(0.0, min(self.shadow_price, 5.0))
#
#         return True
#
#     def bidding_function(self, item_id: str) -> float:
#         my_valuation = self.valuation_vector.get(item_id, 0)
#         rounds_remaining = self.total_rounds - self.rounds_completed
#
#         if my_valuation <= 0 or self.budget <= 0: return 0.0
#         if rounds_remaining <= 1: return min(my_valuation, self.budget)
#
#         # --- EXPLOITATION LOGIC ---
#
#         # Calculate Base Bid (Shadow Pacing)
#         optimal_bid = my_valuation / (1.0 + self.shadow_price)
#
#         # Adjustment: "Am I facing a shark tank?"
#         # Calculate probability that this current item is a "High Value Common" item
#         total_items_left = sum(self.remaining_deck.values())
#         if total_items_left > 0:
#             prob_high_competition = self.remaining_deck["High"] / total_items_left
#         else:
#             prob_high_competition = 0
#
#         # CASE 1: High Competition Likely
#         # If I have a high value, and there are many 'Common High' items left,
#         # I must bid aggressive to win against others who also have high value.
#         if my_valuation > 12 and prob_high_competition > 0.4:
#             # Boost the bid slightly (reduce shading)
#             optimal_bid = optimal_bid * 1.15
#
#         # CASE 2: Low Competition Likely (The "Snipe")
#         # If 'Common High' items are mostly gone (prob < 0.1),
#         # but I have a high value, it means this is likely a 'Mixed' item
#         # that I value highly but others might not.
#         # I can afford to stick to my shaded bid or even shade more.
#         elif my_valuation > 12 and prob_high_competition < 0.1:
#             # No need to change anything, standard shading works great here.
#             # We will win cheaply because others likely drew low values.
#             pass
#
#         # Safety Cap (Budget Aware)
#         budget_per_round = self.budget / rounds_remaining
#         safety_cap = budget_per_round * 3.0
#
#         final_bid = min(optimal_bid, safety_cap)
#
#         # End game dump
#         if rounds_remaining <= 3 and self.budget > 15:
#             final_bid = max(final_bid, my_valuation * 0.9)
#
#         return float(max(0.0, min(final_bid, self.budget)))

# from typing import Dict, List
# import math
#
#
# class BiddingAgent:
#     def __init__(self, team_id: str, valuation_vector: Dict[str, float],
#                  budget: float, opponent_teams: List[str]):
#         self.team_id = team_id
#         self.valuation_vector = valuation_vector
#         self.budget = budget
#         self.initial_budget = budget
#         self.opponent_teams = opponent_teams
#         self.utility = 0
#         self.items_won = []
#
#         # Game state tracking
#         self.rounds_completed = 0
#         self.total_rounds = 15
#
#         # Bayesian Tracking: Expected total items in each category
#         # Since we don't know the exact count, we assume a prior of 5 each.
#         self.category_counts = {"high": 5, "mixed": 5, "low": 5}
#         self.price_history = []
#
#     def update_after_each_round(self, item_id: str, winning_team: str, price_paid: float):
#         # System updates
#         if winning_team == self.team_id:
#             self.budget -= price_paid
#             self.items_won.append(item_id)
#             self.utility += (self.valuation_vector[item_id] - price_paid)
#
#         # 1. Infer Category from Posterior Price
#         # Thresholds: High > 14, Low < 7, else Mixed
#         if price_paid >= 14.0:
#             inferred = "high"
#         elif price_paid <= 7.0:
#             inferred = "low"
#         else:
#             inferred = "mixed"
#
#         # Update our inventory tracker (decrement what we think just sold)
#         if self.category_counts[inferred] > 0:
#             self.category_counts[inferred] -= 1
#
#         self.price_history.append(price_paid)
#         self.rounds_completed += 1
#         return True
#
#     def bidding_function(self, item_id: str) -> float:
#         my_val = self.valuation_vector.get(item_id, 0)
#         rounds_left = self.total_rounds - self.rounds_completed
#
#         if my_val <= 0 or self.budget <= 0 or rounds_left <= 0:
#             return 0.0
#
#         # 1. Budget Health Check
#         # If we have more than 4 coins per remaining round, we are "Rich"
#         budget_per_round = self.budget / rounds_left
#         is_rich = budget_per_round > 4.5
#
#         # 2. Probability Inference (Simplified for performance)
#         prob_mixed = 0.0
#         remaining_sum = sum(self.category_counts.values())
#         if remaining_sum > 0:
#             prob_mixed = self.category_counts["mixed"] / remaining_sum
#
#         # 3. Dynamic Shading Factor
#         # In the last 4 rounds, or if we are rich, stop shading (Bid Truthfully)
#         if rounds_left <= 4 or is_rich:
#             shade = 1.0
#         else:
#             # If it's likely a Mixed item, bid high to capture utility
#             # If it's High category, shade slightly to avoid the "Winner's Curse"
#             shade = 0.95 if prob_mixed > 0.4 else 0.85
#
#         # 4. Remove the aggressive bid_cap
#         # We only cap at the actual budget
#         bid = my_val * shade
#         final_bid = min(bid, self.budget)
#
#         return float(final_bid)

# from typing import Dict, List, Tuple
# from enum import Enum
#
#
# class ItemType(Enum):
#     LOW_VALUE = "low"  # U[1, 10] for all
#     HIGH_VALUE = "high"  # U[10, 20] for all
#     WILDCARD = "mixed"  # U[1, 20] for all (Mixed/Wildcard)
#
#
# class BiddingAgent:
#     def __init__(self, team_id: str, valuation_vector: Dict[str, float],
#                  budget: float, opponent_teams: List[str]):
#         self.team_id = team_id
#         self.valuation_vector = valuation_vector
#         self.budget = budget
#         self.opponent_teams = opponent_teams
#         self.total_rounds = 15
#         self.rounds_completed = 0
#         self.utility = 0
#
#         # 1. Corrected Inventory Prior (Based on 20 total goods distribution)
#         # Note: We only play 15 rounds out of 20 possible goods.
#         self.inventory = {
#             ItemType.LOW_VALUE: 4,
#             ItemType.HIGH_VALUE: 6,
#             ItemType.WILDCARD: 10
#         }
#
#         # 2. Opponent Budget Tracking
#         self.opp_budgets = {opp: 60.0 for opp in opponent_teams}
#
#         # 3. Categorization Matrix Setup
#         # We store the mapping as (valuation_range, price_range) -> ItemType
#         # Ranges are: 0: (0-5.5), 1: (5.5-10), 2: (10-15), 3: (15-20)
#         self.cat_matrix = self._init_cat_matrix()
#
#     def _get_range_idx(self, val: float) -> int:
#         if val < 5.5: return 0
#         if val < 10:  return 1
#         if val < 15:  return 2
#         return 3
#
#     def _init_cat_matrix(self):
#         # Implementation of your provided logic
#         matrix = {}
#         for v in range(4):
#             for p in range(4):
#                 # Default to WILDCARD as it's 50% of the pool
#                 res = ItemType.WILDCARD
#                 if v <= 1 and p <= 1: res = ItemType.LOW_VALUE
#                 if v == 3 and p >= 2: res = ItemType.HIGH_VALUE
#                 matrix[(v, p)] = res
#         return matrix
#
#     def update_after_each_round(self, item_id: str, winning_team: str, price_paid: float):
#         # Update your own budget and utility
#         my_val = self.valuation_vector.get(item_id, 0)
#         if winning_team == self.team_id:
#             self.budget -= price_paid
#             self.utility += (my_val - price_paid)
#         elif winning_team in self.opp_budgets:
#             # Conservative estimate of opponent spend
#             self.opp_budgets[winning_team] -= price_paid
#
#         # Update Inventory based on Matrix
#         v_idx = self._get_range_idx(my_val)
#         p_idx = self._get_range_idx(price_paid)
#         inferred_type = self.cat_matrix.get((v_idx, p_idx), ItemType.WILDCARD)
#
#         if self.inventory[inferred_type] > 0:
#             self.inventory[inferred_type] -= 1
#
#         self.rounds_completed += 1
#         return True
#
#     def bidding_function(self, item_id: str) -> float:
#         my_val = self.valuation_vector.get(item_id, 0)
#         rounds_left = self.total_rounds - self.rounds_completed
#
#         if my_val <= 0 or self.budget <= 0:
#             return 0.0
#
#         # Bayesian Probability: What is the likelihood the current item is a "Wildcard"?
#         total_left = sum(self.inventory.values())
#         prob_mixed = self.inventory[ItemType.WILDCARD] / total_left if total_left > 0 else 0.5
#
#         # Room state
#         avg_opp_budget = sum(self.opp_budgets.values()) / len(self.opp_budgets)
#
#         # Bidding Logic:
#         # If it's a Mixed item and we have high valuation, this is our "Utility Goldmine"
#         # We bid aggressively because others might have very low valuations.
#         if prob_mixed > 0.6 and my_val > 14:
#             shade = 0.95
#         elif rounds_left <= 2 or avg_opp_budget < 10:
#             # End game or broke opponents: Take control.
#             shade = 1.0
#         else:
#             # General case: Shade slightly to maintain budget health
#             shade = 0.88
#
#         # Ensure we don't under-bid like the previous simulation
#         # If we have much more money than the average opponent, push the price up.
#         if self.budget > avg_opp_budget * 1.3:
#             shade = max(shade, 0.92)
#
#         return float(min(my_val * shade, self.budget)) #win rate 26.3% (bidding_agent = 24.1% in the same coalition)

from typing import Dict, List
from enum import Enum


class ItemType(Enum):
    LOW_VALUE = "low"
    HIGH_VALUE = "high"
    WILDCARD = "mixed"


from typing import Dict, List
from enum import Enum


class ItemType(Enum):
    LOW_VALUE = "low"
    HIGH_VALUE = "high"
    WILDCARD = "mixed"


class BiddingAgent:
    def __init__(self, team_id: str, valuation_vector: Dict[str, float],
                 budget: float, opponent_teams: List[str]):
        self.team_id = team_id
        self.valuation_vector = valuation_vector
        self.budget = budget
        self.opponent_teams = opponent_teams
        self.total_rounds = 15
        self.rounds_completed = 0
        self.utility = 0
        self.verbose = True

        # Distribution: 10 Wildcards, 6 High, 4 Low
        self.inventory = {ItemType.LOW_VALUE: 4, ItemType.HIGH_VALUE: 6, ItemType.WILDCARD: 10}
        self.opp_budgets = {opp: 60.0 for opp in opponent_teams}
        self.opp_utility_est = {opp: 0.0 for opp in opponent_teams}

        # --- Tracking Variables ---
        self.last_bid_was_spite = False
        self.last_bid_amount = 0.0

    def update_after_each_round(self, item_id: str, winning_team: str, price_paid: float):
        my_val = self.valuation_vector.get(item_id, 0)

        # 1. ACCIDENTAL WIN DETECTION
        if winning_team == self.team_id:
            if self.verbose and self.last_bid_was_spite:
                # We tried to push the price but ended up winning the item
                print(f"--- [!] ACCIDENTAL WIN on {item_id} ---")
                print(f"My True Val: {my_val} | Spite Bid: {self.last_bid_amount} | Price Paid: {price_paid} | Utility Loss/Cost: {my_val - price_paid}")
            if self.verbose:
                print(f"My True Val: {my_val} | Price Paid: {price_paid} | Utility ratio: {my_val / price_paid}")

            self.budget -= price_paid
            self.utility += (my_val - price_paid)

        elif winning_team in self.opp_budgets:
            self.opp_budgets[winning_team] -= price_paid
            # Update Grudge utility estimate
            # (Assumes standard median utility if category is unknown)
            self.opp_utility_est[winning_team] += max(0, 10.5 - price_paid)

        # Update Inventory using matrix-like inference
        inferred = ItemType.WILDCARD
        if my_val > 15 and price_paid > 12:
            inferred = ItemType.HIGH_VALUE
        elif my_val < 10 and price_paid < 6:
            inferred = ItemType.LOW_VALUE

        if self.inventory[inferred] > 0: self.inventory[inferred] -= 1
        self.rounds_completed += 1

        # Reset spite flag for next round
        self.last_bid_was_spite = False
        return True

    def bidding_function(self, item_id: str) -> float:
        my_val = self.valuation_vector.get(item_id, 0)
        rounds_left = self.total_rounds - self.rounds_completed
        if my_val <= 0 or self.budget <= 0: return 0.0

        # 1. Manipulation Metrics
        total_inv = sum(self.inventory.values())
        p_wild = self.inventory[ItemType.WILDCARD] / total_inv if total_inv > 0 else 0.5

        # 2. STRATEGIC PRICE PUSHING (Spite Bids)
        # Identify the current leader to target them
        leader = max(self.opp_utility_est, key=self.opp_utility_est.get)

        if p_wild > 0.6 and my_val < 5.0 and self.budget > 30:
            tax_amount = 10.0
            self.last_bid_amount = float(min(tax_amount, self.budget * 0.15))
            self.last_bid_was_spite = True
            return self.last_bid_amount

        # 3. THE PRICE RULE: MANIPULATIVE SHADING
        if p_wild > 0.7:
            base_shade = 0.80
        elif p_wild > 0.4:
            base_shade = 0.90
        else:
            base_shade = 0.95

        # 4. OPPORTUNISTIC STEALING
        avg_opp_budget = sum(self.opp_budgets.values()) / len(self.opp_budgets)
        if avg_opp_budget < 15:
            base_shade *= 0.85

        if rounds_left <= 2:
            base_shade = 1.0

        final_bid = my_val * base_shade
        self.last_bid_amount = float(min(final_bid, self.budget))
        self.last_bid_was_spite = False  # This was a legitimate utility bid

        return self.last_bid_amount