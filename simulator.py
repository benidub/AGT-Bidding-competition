"""
AGT Competition Simulator
Test your bidding agent against example strategies locally

This simulator allows students to test their agents before submission.
"""

import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime
import random

from src.valuation_generator import ValuationGenerator
from src.auction_engine import AuctionEngine
from src.agent_manager import AgentManager
from src.game_manager import GameManager
from src.utils import Team, format_utility
from src.config import BID_TIMEOUT_SECONDS


def setup_logging(verbose: bool = False):
    """Setup logging for simulator"""
    log_level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


class Simulator:
    """
    Local simulator for testing bidding agents.
    Students can use this to test against example strategies.
    """
    
    def __init__(self, seed: int = None, timeout: float = BID_TIMEOUT_SECONDS, print_log=False):
        self.seed = seed
        self.timeout = timeout
        self.valuation_generator = ValuationGenerator(random_seed=seed)
        self.print_log = print_log

        
    def load_example_opponents(self) -> list:
        """Load all example agents as opponents"""
        examples_dir = Path("examples")
        opponents = []
        
        if not examples_dir.exists():
            logging.warning("Examples directory not found")
            return opponents
        
        for agent_file in examples_dir.glob("*.py"):
            opponents.append({
                'team_id': agent_file.stem,
                'team_name': agent_file.stem,
                'agent_file': str(agent_file.absolute())
            })
        
        return opponents
    
    def simulate_game(self, your_agent_path: str, opponent_agents: list, 
                     game_num: int) -> dict:
        """
        Simulate a single game with your agent and opponents.
        
        Args:
            your_agent_path: Path to your agent file
            opponent_agents: List of opponent agent dicts
            game_num: Game number (for logging)
        
        Returns:
            Dictionary with game results
        """
        # Prepare team agents
        team_agents = {
            'your_agent': your_agent_path
        }
        
        for opp in opponent_agents:
            team_agents[opp['team_id']] = opp['agent_file']
        
        # Create game manager
        auction_engine = AuctionEngine()
        agent_manager = AgentManager(timeout_seconds=self.timeout)
        
        game_manager = GameManager(
            stage=1,
            arena_id="simulator",
            game_number=game_num,
            valuation_generator=self.valuation_generator,
            auction_engine=auction_engine,
            agent_manager=agent_manager
        )
        
        # Run game
        try:
            game_result = game_manager.run_game(team_agents)
            return game_result
        except Exception as e:
            logging.error(f"Error in game {game_num}: {e}", exc_info=True)
            return None
    
    def run_simulation(self, your_agent_path: str, opponents: list = None,
                      num_games: int = 10) -> dict:
        """
        Run multiple games and collect statistics.
        
        Args:
            your_agent_path: Path to your agent file
            opponents: List of opponent agents (uses examples if None)
            num_games: Number of games to simulate
        
        Returns:
            Dictionary with aggregate statistics
        """
        if opponents is None:
            opponents = self.load_example_opponents()
        
        if not opponents:
            logging.error("No opponents found!")
            return None
        
        print(f"\n{'='*80}")
        print(f"AGT COMPETITION SIMULATOR")
        print(f"{'='*80}")
        print(f"Your Agent: {your_agent_path}")
        print(f"Opponents: {', '.join([o['team_id'] for o in opponents])}")
        print(f"Games: {num_games}")
        print(f"Random Seed: {self.seed if self.seed else 'Random'}")
        print(f"{'='*80}\n")
        
        # Statistics tracking
        stats = {
            'your_agent': {
                'total_utility': 0,
                'games_won': 0,
                'total_items': 0,
                'total_spent': 0,
                'utilities': [],
                'ranks': []
            }
        }
        
        for opp in opponents:
            stats[opp['team_id']] = {
                'total_utility': 0,
                'games_won': 0,
                'total_items': 0,
                'total_spent': 0,
                'utilities': []
            }
        
        # Run games
        for game_num in range(1, num_games + 1):
            if self.print_log:
                print(f"\n--- Game {game_num}/{num_games} ---")
            
            game_result = self.simulate_game(your_agent_path, opponents, game_num)
            
            if game_result is None:
                continue
            
            # Collect statistics
            results_list = []
            for team_id, team_result in game_result.team_results.items():
                results_list.append((team_id, team_result))
                
                if team_id in stats:
                    stats[team_id]['total_utility'] += team_result.utility
                    stats[team_id]['total_items'] += len(team_result.items_won)
                    stats[team_id]['total_spent'] += team_result.budget_spent
                    stats[team_id]['utilities'].append(team_result.utility)
            
            # Sort by utility to find winner
            results_list.sort(key=lambda x: x[1].utility, reverse=True)
            
            winner_id = results_list[0][0]
            if winner_id in stats:
                stats[winner_id]['games_won'] += 1
            
            # Track your agent's rank
            for rank, (team_id, _) in enumerate(results_list, 1):
                if team_id == 'your_agent':
                    stats['your_agent']['ranks'].append(rank)
                    break

            if self.print_log:
                # Print game summary
                print(f"  Winner: {winner_id} (Utility: {results_list[0][1].utility:.2f})")
            
            your_result = game_result.team_results.get('your_agent')
            if your_result:
                your_rank = next(i for i, (tid, _) in enumerate(results_list, 1) 
                               if tid == 'your_agent')
                print(f"  Your Rank: {your_rank}/{len(results_list)} "
                      f"(Utility: {your_result.utility:.2f}, "
                      f"Items: {len(your_result.items_won)}, "
                      f"Spent: {your_result.budget_spent:.2f})")
        
        return stats
    
    def print_summary(self, stats: dict, num_games: int):
        """Print summary statistics"""
        print(f"\n\n{'='*80}")
        print(f"SIMULATION SUMMARY ({num_games} games)")
        print(f"{'='*80}\n")
        
        # Your agent statistics
        your_stats = stats['your_agent']
        avg_utility = your_stats['total_utility'] / num_games
        avg_items = your_stats['total_items'] / num_games
        avg_spent = your_stats['total_spent'] / num_games
        win_rate = (your_stats['games_won'] / num_games) * 100
        
        if your_stats['ranks']:
            avg_rank = sum(your_stats['ranks']) / len(your_stats['ranks'])
        else:
            avg_rank = 0
        
        print(f"YOUR AGENT PERFORMANCE:")
        print(f"  Win Rate: {win_rate:.1f}% ({your_stats['games_won']}/{num_games})")
        print(f"  Average Rank: {avg_rank:.2f}")
        print(f"  Average Utility: {format_utility(avg_utility)}")
        print(f"  Average Items Won: {avg_items:.1f}")
        print(f"  Average Budget Spent: {avg_spent:.2f}")
        
        if your_stats['utilities']:
            min_util = min(your_stats['utilities'])
            max_util = max(your_stats['utilities'])
            print(f"  Utility Range: [{format_utility(min_util)}, {format_utility(max_util)}]")
        
        print(f"\n{'─'*80}\n")
        
        # Opponent comparison
        print("OPPONENT COMPARISON:")
        print(f"{'Agent':<25} {'Avg Utility':>12} {'Wins':>8} {'Win Rate':>10}")
        print(f"{'-'*25} {'-'*12} {'-'*8} {'-'*10}")
        
        # Sort by average utility
        opponent_stats = []
        for team_id, team_stats in stats.items():
            if team_id == 'your_agent':
                continue
            
            avg_util = team_stats['total_utility'] / num_games
            win_rate = (team_stats['games_won'] / num_games) * 100
            opponent_stats.append((team_id, avg_util, team_stats['games_won'], win_rate))
        
        opponent_stats.sort(key=lambda x: x[1], reverse=True)
        
        for team_id, avg_util, wins, win_rate in opponent_stats:
            print(f"{team_id:<25} {format_utility(avg_util):>12} {wins:>8} {win_rate:>9.1f}%")
        
        print(f"\n{'='*80}")
        
        # Performance assessment
        print("\nPERFORMANCE ASSESSMENT:")
        if win_rate >= 50:
            print("  ✓ Excellent! Your agent is competitive")
        elif win_rate >= 30:
            print("  ✓ Good performance, room for improvement")
        elif win_rate >= 15:
            print("  ⚠ Needs improvement - try optimizing your strategy")
        else:
            print("  ⚠ Performance below baseline - review your approach")
        
        if avg_utility > 15:
            print("  ✓ Strong utility generation")
        elif avg_utility > 5:
            print("  ○ Moderate utility generation")
        else:
            print("  ⚠ Low utility - consider budget management")
        
        print(f"\n{'='*80}\n")


def main():
    """Main entry point for simulator"""
    parser = argparse.ArgumentParser(
        description="AGT Competition Simulator - Test your agent locally"
    )
    
    parser.add_argument(
        '--your-agent',
        required=True,
        help='Path to your bidding_agent.py file'
    )
    
    parser.add_argument(
        '--opponent',
        help='Path to specific opponent agent (uses all examples if not specified)'
    )
    
    parser.add_argument(
        '--num-games',
        type=int,
        default=10,
        help='Number of games to simulate (default: 10)'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        help='Random seed for reproducibility'
    )
    
    parser.add_argument(
        '--timeout',
        type=float,
        default=BID_TIMEOUT_SECONDS,
        help='Timeout for bid execution (seconds)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(verbose=args.verbose)
    
    # Validate your agent exists
    your_agent_path = Path(args.your_agent)
    if not your_agent_path.exists():
        print(f"Error: Agent file not found: {args.your_agent}")
        sys.exit(1)
    
    # Setup opponents
    opponents = None
    if args.opponent:
        opponent_path = Path(args.opponent)
        if not opponent_path.exists():
            print(f"Error: Opponent file not found: {args.opponent}")
            sys.exit(1)
        
        opponents = [{
            'team_id': opponent_path.stem,
            'team_name': opponent_path.stem,
            'agent_file': str(opponent_path.absolute())
        }]
    
    # Create simulator
    simulator = Simulator(seed=args.seed, timeout=args.timeout)
    
    # Run simulation
    try:
        stats = simulator.run_simulation(
            your_agent_path=str(your_agent_path.absolute()),
            opponents=opponents,
            num_games=args.num_games
        )
        
        if stats:
            simulator.print_summary(stats, args.num_games)
        else:
            print("Simulation failed!")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nSimulation error: {e}")
        logging.error("Simulation failed", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
