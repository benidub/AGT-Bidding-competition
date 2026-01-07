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
from random import random
from typing import Dict, List


class Item:
    def __init__(self, name: str, value: float):
        self.name = name
        self.value = value


class Classification:
    def __init__(self, high: list[Item], low: list[Item], wildcard: list[Item]):
        assert len(high) == 6
        assert len(low) == 4
        assert len(wildcard) == 10
        self.high = high
        self.low = low
        self.wildcard = wildcard

    def difference(self, other: 'Classification') -> int:
        correct = 0
        for item in self.high:
            if item in other.high:
                correct += 1
        for item in self.low:
            if item in other.low:
                correct += 1
        for item in self.wildcard:
            if item in other.wildcard:
                correct += 1
        return correct

    def __repr__(self):
        return f"Classification(high={[(item.name, item.value) for item in self.high]}, low={[(item.name, item.value) for item in self.low]}, wildcard={[(item.name, item.value) for item in self.wildcard]})"


class AbstractClassifier:
    def classify(self, items: list[Item]) -> Classification:
        raise NotImplementedError


class BayesOptimalClassifier(AbstractClassifier):
    def classify(self, items: list[Item]) -> Classification:
        high = [(i, x) for i, x in enumerate(items) if x.value > 10]
        low = [(i, x) for i, x in enumerate(items) if x.value <= 10]
        score_A = [(i, (1 / 10) / (1 / 19)) for i, _ in high]
        score_B = [(i, (1 / 9) / (1 / 19)) for i, _ in low]
        score_A.sort(key=lambda t: t[1], reverse=True)
        score_B.sort(key=lambda t: t[1], reverse=True)

        high_items = []
        low_items = []
        wildcard_items = []

        for i, _ in score_A[:6]:
            high_items.append(items[i])
        for i, _ in score_B[:4]:
            low_items.append(items[i])
        used_indices = {i for i, _ in score_A[:6]} | {i for i, _ in score_B[:4]}
        for i in range(len(items)):
            if i not in used_indices:
                wildcard_items.append(items[i])
        return Classification(high=high_items, low=low_items, wildcard=wildcard_items)


class NaiveOptimalClassifier(AbstractClassifier):
    def classify(self, items: list[Item]) -> Classification:
        sorted_items = sorted(items, key=lambda item: item.value)
        low = sorted_items[:4]
        high = sorted_items[-6:]
        wildcard = sorted_items[4:-6]
        return Classification(high=high, low=low, wildcard=wildcard)


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
        self.my_unseen_evaluations: Dict[str, float] = {k: v for k, v in
                                                        valuation_vector.items()}  # Track valuations of items that have not been seen yet
        self.remaining_opponents_budgets = {opp: budget for opp in opponent_teams}  # Estimate opponent budgets
        self.opponent_wins = {opp: [] for opp in opponent_teams}  # Track which opponents win what

        self.remaining_items_classifications: dict[ItemType, int] = {
            ItemType.HIGH_VALUE: 6,
            ItemType.WILDCARD: 10,
            ItemType.LOW_VALUE: 4
        }

        self.wiled_expected_value = 16.20626335684833
        self.low_expected_value = 8.202508702990823
        self.high_expected_value = 18
        self.low_variance = 2.16
        self.wild_variance = 9.626666666666667
        self.high_variance = 2.666666666666667
        self.acceptable_ratio = 1 / 8

        self.init_items_classifications = self._build_items_classification_table(self.valuation_vector)

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

        if price_paid <= 10:
            item_classification = ItemType.LOW_VALUE
        elif price_paid >= 15:
            item_classification = ItemType.HIGH_VALUE
        else:
            item_classification = ItemType.WILDCARD
        self.remaining_items_classifications[item_classification] = max(
            0, self.remaining_items_classifications[item_classification] - 1)

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

        progress = 1 - (rounds_remaining / self.total_rounds)  # Goes from 0 -> 1

        # In first round we want to be truthful
        # if self.rounds_completed == 0:
        #     return self._validate_bid(my_valuation)

        # TODO: CONSIDER what we should do in the last round
        # if self.rounds_completed == self.total_rounds - 1:
        #     return self._validate_bid(my_valuation)

        # See if we can beat opponents in case that they have no budget left
        biggest_opponent_budget = self._get_biggest_remaining_opponent_budget()
        if my_valuation > biggest_opponent_budget and self.budget >= biggest_opponent_budget:
            # Bid aggressively if we can outbid everyone
            return self._validate_bid(my_valuation)

        item_classification = self._get_item_classification(item_id)

        bid = my_valuation * 0.95
        if my_valuation > 15:
            bid = my_valuation * 0.85

        if my_valuation < 6:
            bid = my_valuation * 1.1

        if my_valuation < 3:
            bid = my_valuation * 1.5

        if self.rounds_completed >= 12:
            bid = max(bid, my_valuation * 0.95)
        return self._validate_bid(bid)

        # match item_classification:
        #     case ItemType.HIGH_VALUE:
        #         if my_valuation > self.high_expected_value:
        #             return self._validate_bid((my_valuation + self.high_expected_value) / 2)
        #         else:
        #             return self._validate_bid(my_valuation + 0.5)
        #     case ItemType.WILDCARD:
        #         return self._validate_bid(my_valuation + 0.5)
        #     case ItemType.LOW_VALUE:
        #         return self._validate_bid(my_valuation)

        # if my_valuation < 5.5:
        #     return self._validate_bid(5.5)
        # if my_valuation > 10.0:
        #     return self._validate_bid(my_valuation - 1.0)
        # return self._validate_bid(my_valuation)

        # if self.rounds_completed >= 12:
        #     return self._validate_bid(my_valuation * 0.95)
        # #
        # updated_unseen_evaluations = {k: v for k, v in self.my_unseen_evaluations.items() if k != item_id}
        # expected_max_item_that_would_be_seen = self._calculate_expected_remaining_max_item(updated_unseen_evaluations)
        #
        # if my_valuation < expected_max_item_that_would_be_seen / 2:
        #     # This item is not worth half of the expected max, So we will not want to pay a lot for it.
        #     # Option 1: bid 0
        #     # Option 2: bid more than the valuation so others will pay more
        #
        #     return self._validate_bid(min(my_valuation, 6))
        # elif my_valuation >= expected_max_item_that_would_be_seen:
        #     return self._validate_bid(my_valuation - 1)
        # else:
        #     # max_expected / 2 <= my_valuation <= max_expected
        #     return self._validate_bid(my_valuation)
        #
        # return self._validate_bid(0)

        # ============================================================
        # END OF STRATEGY IMPLEMENTATION
        # ============================================================

    # ================================================================
    # OPTIONAL: Helper methods for your strategy
    # ================================================================

    # TODO: Add any helper methods you
    def _calculate_expected_remaining_max_item(self, unseen_items_valuations: Dict[str, float]) -> float:
        number_of_items = len(unseen_items_valuations)
        number_of_items_that_will_be_known = number_of_items - 4
        items_values = list(unseen_items_valuations.values())
        sorted_items_values = sorted(items_values)
        denominator = math.comb(number_of_items, number_of_items_that_will_be_known)
        expectation = 0
        for k in range(number_of_items_that_will_be_known, number_of_items + 1):
            prob = math.comb(k - 1, number_of_items_that_will_be_known - 1) / denominator
            expectation += sorted_items_values[k - 1] * prob
        return expectation

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

    def _build_items_classification_table(self, valuation_vector: Dict[str, float]) -> Dict[str, ItemType]:
        items = [Item(name=k, value=v) for k, v in valuation_vector.items()]
        classifier = BayesOptimalClassifier()
        classification = classifier.classify(items)
        items_type_mapping = {}
        for item in classification.high:
            items_type_mapping[item.name] = ItemType.HIGH_VALUE
        for item in classification.low:
            items_type_mapping[item.name] = ItemType.LOW_VALUE
        for item in classification.wildcard:
            items_type_mapping[item.name] = ItemType.WILDCARD
        return items_type_mapping

    def _get_item_classification(self, item_id):
        my_value = self.valuation_vector.get(item_id, 0)
        remaining_wildcard = self.remaining_items_classifications[ItemType.WILDCARD]
        remaining_high = self.remaining_items_classifications[ItemType.HIGH_VALUE]
        remaining_low = self.remaining_items_classifications[ItemType.LOW_VALUE]

        if my_value >= 10:
            if remaining_high == 0 and remaining_wildcard == 0:
                return ItemType.HIGH_VALUE
            high_classification_probability = remaining_high * 2 / (remaining_high * 2 + remaining_wildcard)
            random_between_0_and_1 = random()
            if random_between_0_and_1 <= high_classification_probability:
                return ItemType.HIGH_VALUE
            return ItemType.WILDCARD

        elif my_value < 10:
            if remaining_low == 0 and remaining_wildcard == 0:
                return ItemType.LOW_VALUE
            low_classification_probability = remaining_low * 2 / (remaining_low * 2 + remaining_wildcard)
            random_between_0_and_1 = random()
            if random_between_0_and_1 <= low_classification_probability:
                return ItemType.LOW_VALUE
            return ItemType.WILDCARD
        return ItemType.WILDCARD

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
