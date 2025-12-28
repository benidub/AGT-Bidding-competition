"""
Configuration and constants for AGT Competition System
"""

# Game Parameters
K_TOTAL_ITEMS = 20
T_AUCTION_ROUNDS = 15
INITIAL_BUDGET = 60

# Valuation Ranges
HIGH_VALUE_ITEMS = 6
LOW_VALUE_ITEMS = 4
MIXED_VALUE_ITEMS = 10

HIGH_VALUE_RANGE = (10, 20)
LOW_VALUE_RANGE = (1, 10)
MIXED_VALUE_RANGE = (1, 20)

# Competition Structure
STAGE1_GAMES = 5
STAGE2_GAMES = 5
ARENA_SIZE = 5

# Execution Limits
BID_TIMEOUT_SECONDS = 2.0
MEMORY_LIMIT_MB = 256

# Bid Precision
BID_DECIMAL_PLACES = 2  # Bids rounded to 2 decimal places

# Scoring
SCORING_WEIGHTS = {
    "utility": 1.0,
    "items_won": 0,
    "budget_remaining": 0
}

# File Paths
TEAMS_DIR = "teams"
RESULTS_DIR = "results"
LOGS_DIR = "logs"
EXAMPLES_DIR = "examples"

# Logging Levels
VERBOSE_LOGGING = True  # For course staff
TEAM_LOGGING = False    # Minimal logging for teams

# Item ID format
ITEM_ID_FORMAT = "item_{}"

# Random seed for reproducibility (optional)
RANDOM_SEED = 123  # Set to int for reproducible results
