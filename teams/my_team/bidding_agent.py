"""
AGT Competition - Student Agent Template
========================================

Team Name: [YOUR TEAM NAME]
Members: 
  - [Student 1 Name and ID]
  - [Student 2 Name and ID]
  - [Student 3 Name and ID]

Strategy Description:
[Brief description of your bidding strategy]

Key Features:
- [Feature 1]
- [Feature 2]
- [Feature 3]
"""
import math
from enum import StrEnum
from typing import Dict, List


class ItemType(StrEnum):
    HIGH_VALUE = "high_value"
    WILDCARD = "wildcard"
    LOW_VALUE = "low_value"


class PriceRange:
    def __init__(self, low: float, high: float):
        self.low = low
        self.high = high

    def is_in(self, f: float) -> bool:
        return self.low <= f <= self.high


class BiddingAgent:
    """
    Your bidding agent for the AGT Auto-Bidding Competition.
    
    This template provides the required interface and helpful structure.
    Replace the TODO sections with your own strategy implementation.
    """

    def __init__(self, team_id: str, valuation_vector: Dict[str, float],
                 budget: float, opponent_teams: List[str]):
        """
        Initialize your agent at the start of each game.
        
        Args:
            team_id: Your unique team identifier (UUID string)
            valuation_vector: Dict mapping item_id to your valuation
                Example: {"item_0": 15.3, "item_1": 8.2, ..., "item_19": 12.7}
            budget: Initial budget (always 60)
            opponent_teams: List of opponent team IDs competing in the same arena
                Example: ["Team_A", "Team_B", "Team_C", "Team_D"]
                This helps you track and model each opponent's behavior separately
        
        Important:
            - This is called once at the start of each game
            - You can initialize any state variables here
            - Pre-compute anything that doesn't change during the game
            - Use opponent_teams to set up per-opponent tracking/modeling
        """
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

        # TODO: Add your custom state variables here
        # Examples:
        self.price_history = []  # Track observed prices
        self.my_seen_evaluations = []  # Track valuations of items seen so far
        self.my_unseen_evaluations: Dict[str, float] = {k: v for k, v in valuation_vector.items()}  # Track valuations of items that have not been seen yet
        self.remaining_opponents_budgets = {opp: budget for opp in opponent_teams}  # Estimate opponent budgets
        self.opponent_wins = {opp: [] for opp in opponent_teams}  # Track which opponents win what

        self.items_type_mapping: dict[ItemType, int] = {
            ItemType.HIGH_VALUE: 6,
            ItemType.WILDCARD: 10,
            ItemType.LOW_VALUE: 4
        }

        self.acceptable_ratio = 1 / 8

        self.evaluation_and_price_to_item_category: dict[tuple[PriceRange, PriceRange], ItemType] = {
            (PriceRange(0, 5.5), PriceRange(0, 5.5)): ItemType.LOW_VALUE,
            (PriceRange(0, 5.5), PriceRange(5.5, 10)): ItemType.LOW_VALUE,
            (PriceRange(0, 5.5), PriceRange(10, 15)): ItemType.WILDCARD,
            (PriceRange(0, 5.5), PriceRange(15, 20)): ItemType.WILDCARD,
            (PriceRange(5.5, 10), PriceRange(0, 5.5)): ItemType.LOW_VALUE,
            (PriceRange(5.5, 10), PriceRange(5.5, 10)): ItemType.LOW_VALUE,  # TODO: think about make this 0.5 0.5
            (PriceRange(5.5, 10), PriceRange(10, 15)): ItemType.WILDCARD,
            (PriceRange(5.5, 10), PriceRange(15, 20)): ItemType.WILDCARD,
            (PriceRange(10, 15), PriceRange(0, 5.5)): ItemType.WILDCARD,
            (PriceRange(10, 15), PriceRange(5.5, 10)): ItemType.WILDCARD,
            (PriceRange(10, 15), PriceRange(10, 15)): ItemType.WILDCARD,
            (PriceRange(10, 15), PriceRange(15, 20)): ItemType.WILDCARD,
            (PriceRange(15, 20), PriceRange(0, 5.5)): ItemType.WILDCARD,
            (PriceRange(15, 20), PriceRange(5.5, 10)): ItemType.WILDCARD,
            (PriceRange(15, 20), PriceRange(10, 15)): ItemType.HIGH_VALUE,
            (PriceRange(15, 20), PriceRange(15, 20)): ItemType.HIGH_VALUE,
        }

        # self.opponent_bids = {opp: [] for opp in opponent_teams}  # Infer opponent bidding patterns
        # self.beliefs = {opp: {} for opp in opponent_teams}        # Bayesian beliefs per opponent
        # self.high_value_threshold = 12.0  # Classify items
        # self.low_value_threshold = 8.0

        # TODO: Pre-compute any strategy parameters
        # Examples:
        self.avg_valuation = sum(valuation_vector.values()) / len(valuation_vector)
        self.max_valuation = max(valuation_vector.values())
        self.min_valuation = min(valuation_vector.values())

    def _update_available_budget(self, item_id: str, winning_team: str,
                                 price_paid: float):
        """
        Internal method to update budget after auction.
        DO NOT MODIFY - This is called automatically by the system.
        
        Args:
            item_id: ID of the auctioned item
            winning_team: ID of the winning team
            price_paid: Price paid by winner
        """
        if winning_team == self.team_id:
            self.budget -= price_paid
            self.items_won.append(item_id)

    def update_after_each_round(self, item_id: str, winning_team: str,
                                price_paid: float):
        """
        Called after each auction round with public information.
        Use this to update your beliefs, opponent models, and strategy.
        
        Args:
            item_id: The item that was just auctioned
            winning_team: Team ID of the winner (empty string if no winner)
            price_paid: Price the winner paid (second-highest bid)
        
        What you learn:
            - Which item was sold
            - Who won it
            - What price they paid (second-highest bid)
        
        What you DON'T learn:
            - All individual bids
            - Other teams' valuations
        
        Returns:
            True if update successful (required by system)
        """
        # System updates (DO NOT REMOVE)
        self._update_available_budget(item_id, winning_team, price_paid)

        if winning_team == self.team_id:
            self.utility += (self.valuation_vector[item_id] - price_paid)

        self._update_items_type_table(item_id, winning_team, price_paid)

        self.rounds_completed += 1

        # TODO: Implement your learning/adaptation logic here

        # Update remaining opponent budgets
        if winning_team and winning_team in self.remaining_opponents_budgets:
            self.remaining_opponents_budgets[winning_team] -= price_paid
            if self.remaining_opponents_budgets[winning_team] < 0:
                self.remaining_opponents_budgets[winning_team] = 0.0

        # Track price history
        if price_paid > 0:
            self.price_history.append(price_paid)

        # Track seen valuations
        self.my_seen_evaluations.append(self.valuation_vector.get(item_id, 0))

        self.my_unseen_evaluations.pop(item_id)


        # Track opponent performance
        # if winning_team and winning_team != self.team_id:
        #     self.opponent_wins[winning_team] = \
        #         self.opponent_wins.get(winning_team, 0) + 1

        # Update beliefs about market competitiveness
        # if self.price_history:
        #     self.avg_market_price = sum(self.price_history) / len(self.price_history)

        # Bayesian belief updates
        # if winning_team and price_paid > 0:
        #     # Update beliefs about winner's valuation
        #     # They bid at least price_paid + epsilon
        #     pass

        return True

    def bidding_function(self, item_id: str) -> float:
        """
        MAIN METHOD: Decide how much to bid for the current item.
        This is called once per auction round.
        
        Args:
            item_id: The item being auctioned (e.g., "item_7")
        
        Returns:
            float: Your bid amount
                - Must be >= 0
                - Should be <= your current budget
                - Bids over budget are automatically capped
                - Return 0 to not bid
        
        Important:
            - You have 2 seconds maximum to return
            - Timeout or error = bid of 0
            - This is a SECOND-PRICE auction: winner pays second-highest bid
            - Budget does NOT carry over between games
        
        Strategy Considerations:
            1. Budget Management: How much to spend now vs save for later?
            2. Item Value: Is this item worth competing for?
            3. Competition: How competitive will this auction be?
            4. Game Progress: Are we early or late in the game?
        """
        # Get your valuation for this item
        my_valuation = self.valuation_vector.get(item_id, 0)

        # Early exit if no value or no budget
        if my_valuation <= 0 or self.budget <= 0:
            return 0.0

        # Calculate rounds remaining
        rounds_remaining = self.total_rounds - self.rounds_completed
        if rounds_remaining <= 0:
            return 0.0

        # ============================================================
        # TODO: IMPLEMENT YOUR BIDDING STRATEGY HERE
        # ============================================================

        # In first round we want to be truthful
        if self.rounds_completed == 0:
            return self._validate_bid(my_valuation)

        # TODO: CONSIDER what we should do in the last round
        if self.rounds_completed == self.total_rounds - 1:
            return self._validate_bid(my_valuation)

        # See if we can beat opponents in case that they have no budget left
        biggest_opponent_budget = self._get_biggest_remaining_opponent_budget()
        if my_valuation > biggest_opponent_budget and self.budget >= biggest_opponent_budget:
            # Bid aggressively if we can outbid everyone
            bid = self.budget
        else:
            bid = my_valuation

        # if my_valuation < 5.5:
        #     return self._validate_bid(5.5)
        # if my_valuation > 10.0:
        #     return self._validate_bid(my_valuation - 1.0)
        # return self._validate_bid(my_valuation)

        updated_unseen_evaluations = {k: v for k, v in self.my_unseen_evaluations.items() if k != item_id}
        expected_max_item_that_would_be_seen = self._calculate_expected_remaining_max_item(updated_unseen_evaluations)
        print(f"{expected_max_item_that_would_be_seen=}")


        # if my_valuation >= max_unseen_evaluation / 2:
            # current item is not worth even half of the max we can get

        return self._validate_bid(bid)

        # ============================================================
        # END OF STRATEGY IMPLEMENTATION
        # ============================================================

    # ================================================================
    # OPTIONAL: Helper methods for your strategy
    # ================================================================

    # TODO: Add any helper methods you
    def _calculate_expected_remaining_max_item(self, unseen_items_valuations: Dict[str, float]) -> float:
        number_of_items = len(unseen_items_valuations)
        number_of_items_that_will_be_known = number_of_items - 5
        items_values = list(unseen_items_valuations.values())
        sorted_items_values = sorted(items_values)
        denominator = math.comb(number_of_items, number_of_items_that_will_be_known)
        expectation = 0
        for k in range(number_of_items_that_will_be_known, number_of_items + 1):
            prob = math.comb(k - 1, number_of_items_that_will_be_known - 1) / denominator
            expectation += sorted_items_values[k - 1] * prob
        return expectation



    def _update_items_type_table(self, item_id, winning_team, price_paid):
        my_valuation = self.valuation_vector.get(item_id, 0)
        for (eval_range, price_range), item_type in self.evaluation_and_price_to_item_category.items():
            if eval_range.is_in(my_valuation) and price_range.is_in(price_paid):
                self.items_type_mapping[item_type] -= 1
            break

    def _validate_bid(self, bid: float) -> float:
        """
        Ensure the bid is valid: non-negative and within budget.
        """
        bid = max(0.0, min(bid, self.budget))
        return float(bid)

    def _get_biggest_remaining_opponent_budget(self) -> float:
        """
        Return the largest estimated remaining budget among opponents.
        """
        if not self.remaining_opponents_budgets:
            return 0.0
        return max(self.remaining_opponents_budgets.values())

# ====================================================================
# NOTES AND TIPS
# ====================================================================

# 1. Second-Price Auction Theory:
#    - In standard Vickrey auctions, truthful bidding is optimal
#    - With budget constraints, this changes! You need strategy
#    - Winner pays second-highest bid, not their own bid

# 2. Budget Management:
#    - You have 60 units for 15 rounds
#    - Budget does NOT carry between games
#    - Spending all budget early is risky
#    - Saving too much budget is wasteful

# 3. Information Use:
#    - Learn from observed prices
#    - Track which opponents are winning
#    - Identify competitive vs non-competitive items
#    - Update your strategy as game progresses

# 4. Common Strategies:
#    - Truthful: Bid your valuation (baseline)
#    - Shading: Bid less than valuation to save budget
#    - Pacing: Limit spending per round
#    - Adaptive: Learn from observations and adjust

# 5. Testing:
#    - Use the simulator extensively: python simulator.py --your-agent ...
#    - Test with different seeds for consistency
#    - Aim for >20% win rate against examples
#    - Aim for >10 average utility

# 6. Performance:
#    - Keep computations fast (< 1 second per bid)
#    - Pre-compute what you can in __init__
#    - Avoid complex loops in bidding_function
#    - Test execution time regularly

# 7. Debugging:
#    - Add print statements (captured in logs)
#    - Use simulator with --verbose flag
#    - Check that bids are reasonable (0 to budget)
#    - Verify budget doesn't go negative (system prevents this)

# Good luck! 🏆
