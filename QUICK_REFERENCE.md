# Quick Reference Guide - AGT Competition

## 🚀 Quick Start (5 minutes)

### 1. Create Your Agent
```bash
# Create your team directory
mkdir teams/my_team

# Copy template
cp AGENT_TEMPLATE.py teams/my_team/bidding_agent.py
```

### 2. Implement Your Strategy
Edit `teams/my_team/bidding_agent.py` - focus on the `bidding_function` method:

```python
def bidding_function(self, item_id: str) -> float:
    # Get your valuation
    my_value = self.valuation_vector[item_id]
    
    # YOUR STRATEGY HERE (improve this!)
    bid = my_value * 0.8  # Bid 80% of value
    
    # Ensure valid
    return min(bid, self.budget)
```

### 3. Test Your Agent
```bash
# Validate interface
python main.py --mode validate --validate teams/my_team/bidding_agent.py

# Simulate 10 games
python simulator.py --your-agent teams/my_team/bidding_agent.py --num-games 10
```

---

## 📋 Essential Information

### Agent Interface (3 Required Methods)

```python
class BiddingAgent:
    def __init__(self, team_id, valuation_vector, budget, opponent_teams):
        # Initialize your state
        # opponent_teams = list of opponent IDs
        
    def bidding_function(self, item_id) -> float:
        # Return your bid (0 to budget)
        
    def update_after_each_round(self, item_id, winning_team, price_paid):
        # Learn from each round
```

### Key Constraints

| Constraint | Value | Consequence if Violated |
|------------|-------|------------------------|
| Execution Time | 3 seconds | Bid = 0 |
| Budget | 60 per game | Bids capped automatically |
| Return Type | float | Bid = 0 |
| Dependencies | stdlib, numpy, scipy | Import error |

### What You Know

**At Game Start:**
- ✓ Your valuations for all 20 items
- ✓ Your budget (60)
- ✓ Opponent team IDs
- ✗ Which 15 items will be auctioned (learned online)
- ✗ Order of auctions
- ✗ Other teams' valuations

**After Each Round:**
- ✓ Which item was auctioned
- ✓ Who won
- ✓ Price paid (second-highest bid)
- ✗ All individual bids

### Scoring

```
Utility = Σ(Values of Items Won) - Σ(Prices Paid)

Stage Score = Sum of utilities across 5 games
Competition Score = Stage 1 + Stage 2 scores
```

**Tiebreakers:**
1. Highest single item utility
2. Most items won
3. Registration time (earliest)

---

## 💡 Strategy Patterns

### Pattern 1: Truthful Bidding (Baseline)
```python
def bidding_function(self, item_id):
    return min(self.valuation_vector[item_id], self.budget)
```
**Pros:** Optimal in standard auctions  
**Cons:** Ignores budget constraints

### Pattern 2: Budget Pacing
```python
def bidding_function(self, item_id):
    rounds_left = 15 - self.rounds_completed
    budget_per_round = self.budget / rounds_left
    
    value = self.valuation_vector[item_id]
    bid = min(value, budget_per_round * 1.5)  # Allow 1.5x per round
    return bid
```
**Pros:** Avoids budget exhaustion  
**Cons:** May lose valuable items

### Pattern 3: Value-Based Shading
```python
def bidding_function(self, item_id):
    value = self.valuation_vector[item_id]
    
    # High-value items: bid 90%
    # Medium-value items: bid 70%
    # Low-value items: bid 50%
    if value > 12:
        fraction = 0.9
    elif value > 8:
        fraction = 0.7
    else:
        fraction = 0.5
    
    return min(value * fraction, self.budget)
```
**Pros:** Balances winning vs spending  
**Cons:** May miss competitive items

### Pattern 4: Adaptive Learning
```python
def __init__(self, ...):
    # ... other init ...
    self.price_history = []

def update_after_each_round(self, item_id, winning_team, price_paid):
    # ... system update ...
    if price_paid > 0:
        self.price_history.append(price_paid)

def bidding_function(self, item_id):
    value = self.valuation_vector[item_id]
    
    # Learn from market
    if self.price_history:
        avg_price = sum(self.price_history) / len(self.price_history)
        
        # If item value > average market price, it's competitive
        if value > avg_price * 1.2:
            bid = value * 0.85  # Competitive item
        else:
            bid = value * 0.6   # Less competitive
    else:
        bid = value * 0.7
    
    return min(bid, self.budget)
```
**Pros:** Adapts to competition  
**Cons:** More complex

---

## 🧪 Testing Commands

```bash
# Basic validation
python main.py --mode validate --validate teams/my_team/bidding_agent.py

# Quick test (3 games)
python simulator.py --your-agent teams/my_team/bidding_agent.py --num-games 3

# Thorough test (50 games, reproducible)
python simulator.py --your-agent teams/my_team/bidding_agent.py --num-games 50 --seed 6431

# Test against specific opponent
python simulator.py --your-agent teams/my_team/bidding_agent.py \
                    --opponent examples/strategic_bidder.py --num-games 20

# Verbose debugging
python simulator.py --your-agent teams/my_team/bidding_agent.py \
                    --num-games 1 --verbose
```

---

## 🎯 Optimization Checklist

### Performance
- [ ] Bid computation < 1 second
- [ ] No infinite loops
- [ ] Minimal complex calculations

### Strategy
- [ ] Budget management implemented
- [ ] Handles edge cases (low budget, first/last rounds)
- [ ] Adapts to observations
- [ ] Differentiates high/low value items

### Testing
- [ ] Passes validation
- [ ] Tested 50+ games
- [ ] Win rate > 20% against examples
- [ ] Average utility > 10
- [ ] No timeout errors

### Code Quality
- [ ] Well-commented
- [ ] Team names in header
- [ ] No prohibited imports
- [ ] No file I/O or network access

---

## ⚠️ Common Mistakes

### 1. Budget Exhaustion
```python
# ❌ BAD: Always bid full value
return self.valuation_vector[item_id]

# ✅ GOOD: Pace your budget
rounds_left = 15 - self.rounds_completed
return min(value, self.budget / rounds_left * 2)
```

### 2. Ignoring State
```python
# ❌ BAD: Not tracking anything
def update_after_each_round(self, ...):
    pass

# ✅ GOOD: Learn from observations
def update_after_each_round(self, item_id, winner, price):
    self.price_history.append(price)
    self.rounds_completed += 1
```

### 3. Invalid Returns
```python
# ❌ BAD: Wrong types
return None           # Error!
return "10"           # String!
return -5             # Negative!

# ✅ GOOD: Valid float
return max(0.0, min(float(bid), self.budget))
```

### 4. Slow Execution
```python
# ❌ BAD: Complex nested loops
for i in range(1000000):
    for j in range(1000000):
        complex_calc()

# ✅ GOOD: Pre-compute in __init__ or update
def __init__(self, ...):
    self.precomputed = self._precompute_strategy()
```

---

## 📊 Interpreting Simulator Results

### Good Performance Indicators
- **Win Rate > 30%**: Competitive strategy
- **Average Utility > 15**: Efficient bidding
- **Average Rank ≤ 2.5**: Consistently strong
- **Utility Range**: Small variance = consistent

### Red Flags
- **Win Rate < 10%**: Strategy needs work
- **Average Utility < 5**: Poor budget use
- **Timeout errors**: Code too slow
- **Large utility variance**: Inconsistent strategy

---

## 🔗 Resources

- **Full Guide**: `STUDENT_GUIDE.md` - Comprehensive documentation
- **Rules**: `agt_competition_rules.md` - Official competition rules
- **Examples**: `examples/` - Sample strategies
- **Design**: `design.md` - System architecture

---

## 🆘 Getting Help

1. **Read Error Messages**: They usually tell you what's wrong
2. **Check Logs**: Use `--verbose` flag for detailed output
3. **Test Examples**: Verify system works with example agents
4. **Course Forum**: Ask questions and discuss strategies
5. **Office Hours**: Get personalized help from TAs

---

## 📤 Submission

```bash
# Final checklist before submission
python main.py --mode validate --validate teams/my_team/bidding_agent.py
python simulator.py --your-agent teams/my_team/bidding_agent.py --num-games 50

# Submit: teams/my_team/bidding_agent.py to Moodle
```

**Good luck! 🏆**


