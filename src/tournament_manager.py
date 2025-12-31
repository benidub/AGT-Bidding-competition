"""
Tournament Manager for AGT Competition
Manages tournament stages and arenas
"""

import logging
from datetime import datetime
from typing import Dict, List, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import random

from src.config import STAGE1_GAMES, STAGE2_GAMES, ARENA_SIZE
from src.game_manager import GameManager
from src.valuation_generator import ValuationGenerator
from src.auction_engine import AuctionEngine
from src.agent_manager import AgentManager
from src.results_manager import ResultsManager
from src.utils import GameResult, StageResult, Team


logger = logging.getLogger(__name__)


class TournamentManager:
    """
    Manages the complete tournament including both stages.
    
    Stage 1: Qualification Round
    - Divide teams into 5-team arenas
    - Run 5 games per arena
    - Top scorer from each arena advances
    
    Stage 2: Championship Round
    - All qualified teams in single arena
    - Run 5 games
    - Determine final rankings
    """
    
    def __init__(self, valuation_generator: ValuationGenerator,
                 results_manager: ResultsManager,
                 timeout_seconds: float = 2.0):
        """
        Initialize tournament manager.
        
        Args:
            valuation_generator: Valuation generator instance
            results_manager: Results manager instance
            timeout_seconds: Timeout for agent bid execution
        """
        self.valuation_generator = valuation_generator
        self.results_manager = results_manager
        self.timeout_seconds = timeout_seconds
        
        self.stage1_results = None
        self.stage2_results = None
        self.stage1_valuations = None  # Fixed valuations for Stage 1
        self.stage2_valuations = None  # Fixed valuations for Stage 2
    
    def create_arenas(self, teams: List[Team], arena_size: int = None) -> Dict[str, List[Team]]:
        """
        Divide teams into arenas with random allocation.
        
        Teams are randomly shuffled before being divided into arenas to ensure
        fair and unpredictable groupings. Arena allocation is fixed within a stage.
        
        Args:
            teams: List of Team objects
            arena_size: Number of teams per arena (default: ARENA_SIZE from config)
        
        Returns:
            Dictionary mapping arena_id to list of teams
        """
        if arena_size is None:
            arena_size = ARENA_SIZE
            
        # Randomly shuffle teams for fair arena allocation
        shuffled_teams = teams.copy()
        random.shuffle(shuffled_teams)
        
        logger.info(f"Randomly allocating {len(shuffled_teams)} teams into arenas of size {arena_size}")
        
        arenas = {}
        for i in range(0, len(shuffled_teams), arena_size):
            arena_id = str(i // arena_size + 1)
            arena_teams = shuffled_teams[i:i + arena_size]
            arenas[arena_id] = arena_teams
            logger.info(f"Arena {arena_id}: {[t.team_id for t in arena_teams]}")
        
        return arenas
    
    def run_arena_games(self, arena_id: str, arena_teams: List[Team], 
                       stage: int, num_games: int, fixed_valuations: Dict = None) -> List[GameResult]:
        """
        Run all games for a single arena.
        
        Args:
            arena_id: Arena identifier
            arena_teams: List of teams in this arena
            stage: Competition stage (1 or 2)
            num_games: Number of games to run
            fixed_valuations: Optional pre-generated valuations to use for all games in this arena
        
        Returns:
            List of GameResult objects
        """
        logger.info(f"=== Running Arena {arena_id} (Stage {stage}) ===")
        
        game_results = []
        
        # Prepare team_agents mapping
        team_agents = {team.team_id: team.agent_file_path for team in arena_teams}
        
        # Generate valuations once for this arena if not provided
        if fixed_valuations is None:
            team_ids = [team.team_id for team in arena_teams]
            fixed_valuations, _ = self.valuation_generator.generate_arena_valuations(team_ids)
            logger.info(f"Generated fixed valuations for arena {arena_id}")
        else:
            logger.info(f"Using pre-generated fixed valuations for arena {arena_id}")
        
        for game_num in range(1, num_games + 1):
            try:
                # Create fresh instances for each game
                auction_engine = AuctionEngine()
                agent_manager = AgentManager(timeout_seconds=self.timeout_seconds)
                
                game_manager = GameManager(
                    stage=stage,
                    arena_id=arena_id,
                    game_number=game_num,
                    valuation_generator=self.valuation_generator,
                    auction_engine=auction_engine,
                    agent_manager=agent_manager,
                    fixed_valuations=fixed_valuations  # Pass fixed valuations to each game
                )
                
                # Run the game
                game_result = game_manager.run_game(team_agents)
                game_results.append(game_result)
                
                # Save game results
                self.results_manager.save_game_result(game_result)
                
            except Exception as e:
                logger.error(f"Error running game {game_num} in arena {arena_id}: {e}", exc_info=True)
        
        return game_results
    
    def determine_arena_winner(self, arena_teams: List[Team], game_results: List[GameResult]) -> Team:
        """
        Determine arena winner using new tiebreaker rules.
        
        Winner determination logic:
        1. Number of games won (most wins)
        2. If tied: Highest cumulative utility across all games (total value of items won, not net utility)
        3. If tied: Team with maximal single item utility won
        4. If tied: Highest cumulative utility gap (sum of utility differences from 2nd place in each game)
        
        Args:
            arena_teams: List of teams in the arena
            game_results: List of GameResult objects from all games in the arena
        
        Returns:
            Winning team
        """
        # Aggregate statistics for each team
        team_stats = {}
        
        for team in arena_teams:
            team_stats[team.team_id] = {
                'team': team,
                'games_won': 0,
                'cumulative_valuation': 0.0,  # Total value of items won (not net utility)
                'max_item_utility': 0.0,
                'cumulative_utility_gap': 0.0  # Sum of (my_utility - second_place_utility) per game
            }
        
        # Process each game
        for game in game_results:
            # Find winner and second place for this game
            game_rankings = sorted(
                game.team_results.items(),
                key=lambda x: x[1].utility,
                reverse=True
            )
            
            if game_rankings:
                winner_id = game_rankings[0][0]
                team_stats[winner_id]['games_won'] += 1
                
                # Calculate utility gap for each team
                for i, (team_id, team_result) in enumerate(game_rankings):
                    if i == 0 and len(game_rankings) > 1:
                        # Winner: gap is difference from second place
                        second_utility = game_rankings[1][1].utility
                        team_stats[team_id]['cumulative_utility_gap'] += (team_result.utility - second_utility)
                    elif i > 0:
                        # Non-winner: gap is negative (their utility - winner's utility)
                        winner_utility = game_rankings[0][1].utility
                        team_stats[team_id]['cumulative_utility_gap'] += (team_result.utility - winner_utility)
            
            # Accumulate total valuation won and max item utility
            for team_id, team_result in game.team_results.items():
                team_stats[team_id]['cumulative_valuation'] += team_result.total_valuation_won
                team_stats[team_id]['max_item_utility'] = max(
                    team_stats[team_id]['max_item_utility'],
                    team_result.max_single_item_utility
                )
        
        # Sort teams by tiebreaker rules
        sorted_teams = sorted(
            team_stats.values(),
            key=lambda x: (
                x['games_won'],                    # 1. Most games won
                x['cumulative_valuation'],         # 2. Highest cumulative valuation
                x['max_item_utility'],             # 3. Highest single item utility
                x['cumulative_utility_gap']        # 4. Highest utility gap
            ),
            reverse=True
        )
        
        winner = sorted_teams[0]['team']
        
        logger.info(f"Arena winner determined: {winner.team_id}")
        logger.info(f"  - Games won: {sorted_teams[0]['games_won']}")
        logger.info(f"  - Cumulative valuation: {sorted_teams[0]['cumulative_valuation']:.2f}")
        logger.info(f"  - Max item utility: {sorted_teams[0]['max_item_utility']:.2f}")
        logger.info(f"  - Cumulative utility gap: {sorted_teams[0]['cumulative_utility_gap']:.2f}")
        
        return winner
    
    def run_stage1(self, teams: List[Team]) -> Tuple[StageResult, List[Team]]:
        """
        Run Stage 1: Qualification Round.
        
        Teams are randomly allocated to arenas. Valuations are fixed for all games
        within this stage (same valuations used across all 5 games).
        
        Args:
            teams: List of all registered teams
        
        Returns:
            Tuple of (StageResult, qualified_teams)
        """
        logger.info("=" * 80)
        logger.info("STARTING STAGE 1: QUALIFICATION ROUND")
        logger.info("=" * 80)
        
        # Create arenas with random allocation (fixed for this stage)
        arenas = self.create_arenas(teams)
        
        # Generate fixed valuations for each arena in Stage 1
        # These valuations will be reused across all games in this stage
        logger.info("Generating fixed valuations for Stage 1 (same across all games)")
        self.stage1_valuations = {}
        for arena_id, arena_teams in arenas.items():
            team_ids = [team.team_id for team in arena_teams]
            valuations, _ = self.valuation_generator.generate_arena_valuations(team_ids)
            self.stage1_valuations[arena_id] = valuations
            logger.info(f"Generated fixed valuations for Arena {arena_id}")
        
        # Run games for each arena
        arena_results = {}
        arena_winners = []
        
        for arena_id, arena_teams in arenas.items():
            game_results = self.run_arena_games(
                arena_id=arena_id,
                arena_teams=arena_teams,
                stage=1,
                num_games=STAGE1_GAMES,
                fixed_valuations=self.stage1_valuations[arena_id]  # Pass fixed valuations
            )
            
            arena_results[arena_id] = game_results
            
            # Determine arena winner using new tiebreaker rules
            winner_team = self.determine_arena_winner(arena_teams, game_results)
            arena_winners.append(winner_team)
            logger.info(f"Arena {arena_id} Winner: {winner_team.team_id}")
        
        # Generate overall Stage 1 leaderboard
        all_games = [game for games in arena_results.values() for game in games]
        all_team_reg_times = {team.team_id: team.registration_timestamp for team in teams}
        overall_leaderboard = self.results_manager.generate_leaderboard(all_games, all_team_reg_times)
        
        # Create stage result
        stage_result = StageResult(
            stage=1,
            arena_results=arena_results,
            leaderboard=overall_leaderboard,
            timestamp=datetime.now()
        )
        
        # Save stage results
        self.results_manager.save_stage_result(stage_result)
        self.stage1_results = stage_result
        
        logger.info("=" * 80)
        logger.info(f"STAGE 1 COMPLETE - {len(arena_winners)} teams advance to Stage 2")
        logger.info("=" * 80)
        
        return stage_result, arena_winners
    
    def run_stage2(self, qualified_teams: List[Team]) -> StageResult:
        """
        Run Stage 2: Championship Round.
        
        Valuations are regenerated for Stage 2 (different from Stage 1) but
        remain fixed across all games within Stage 2.
        
        Args:
            qualified_teams: List of teams qualified from Stage 1
        
        Returns:
            StageResult with final rankings
        """
        logger.info("=" * 80)
        logger.info("STARTING STAGE 2: CHAMPIONSHIP ROUND")
        logger.info("=" * 80)
        
        # Regenerate valuations for Stage 2 (different from Stage 1)
        logger.info("Regenerating fixed valuations for Stage 2 (same across all games, different from Stage 1)")
        self.valuation_generator.reset_seed()  # New seed for Stage 2
        
        # All qualified teams in single arena
        arena_id = "championship"
        
        # Generate fixed valuations for Stage 2 championship
        team_ids = [team.team_id for team in qualified_teams]
        stage2_valuations, _ = self.valuation_generator.generate_arena_valuations(team_ids)
        self.stage2_valuations = {arena_id: stage2_valuations}
        logger.info(f"Generated fixed valuations for Stage 2 Championship")
        
        game_results = self.run_arena_games(
            arena_id=arena_id,
            arena_teams=qualified_teams,
            stage=2,
            num_games=STAGE2_GAMES,
            fixed_valuations=stage2_valuations  # Pass fixed valuations
        )
        
        # Generate final leaderboard
        team_reg_times = {team.team_id: team.registration_timestamp for team in qualified_teams}
        final_leaderboard = self.results_manager.generate_leaderboard(game_results, team_reg_times)
        
        # Create stage result
        stage_result = StageResult(
            stage=2,
            arena_results={arena_id: game_results},
            leaderboard=final_leaderboard,
            timestamp=datetime.now()
        )
        
        # Save stage results
        self.results_manager.save_stage_result(stage_result)
        self.stage2_results = stage_result
        
        # Display final results
        logger.info("=" * 80)
        logger.info("STAGE 2 COMPLETE - FINAL RANKINGS")
        logger.info("=" * 80)
        
        for rank, entry in enumerate(final_leaderboard, 1):
            logger.info(
                f"Rank {rank}: {entry['team_id']} | "
                f"Utility: {entry['total_utility']:.2f} | "
                f"Items: {entry['total_items_won']}"
            )
        
        return stage_result
    
    def run_full_tournament(self, teams: List[Team]) -> Tuple[StageResult, StageResult]:
        """
        Run complete tournament (both stages).
        
        Args:
            teams: List of all registered teams
        
        Returns:
            Tuple of (stage1_result, stage2_result)
        """
        logger.info("=" * 80)
        logger.info("AGT AUTO-BIDDING COMPETITION - STARTING TOURNAMENT")
        logger.info(f"Total Teams: {len(teams)}")
        logger.info("=" * 80)
        
        # Run Stage 1
        stage1_result, qualified_teams = self.run_stage1(teams)
        
        # Run Stage 2
        stage2_result = self.run_stage2(qualified_teams)
        
        # Generate final report
        self.results_manager.generate_final_report(stage1_result, stage2_result)
        
        logger.info("=" * 80)
        logger.info("🏆 TOURNAMENT COMPLETE 🏆")
        logger.info("=" * 80)
        
        return stage1_result, stage2_result
