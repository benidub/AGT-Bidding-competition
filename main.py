"""
Main entry point for AGT Competition System
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
import os

from src.valuation_generator import ValuationGenerator
from src.results_manager import ResultsManager
from src.tournament_manager import TournamentManager
from src.utils import Team, generate_team_id
from src.config import BID_TIMEOUT_SECONDS, RANDOM_SEED
from typing import Dict, List, Optional
import json


def setup_logging(verbose: bool = True, log_file: str = None):
    """
    Setup logging configuration.
    
    Args:
        verbose: Enable verbose logging
        log_file: Optional log file path
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)


def load_team_registration(registration_file: str = None) -> Dict[str, List[str]]:
    """
    Load team registration mapping from JSON file.
    
    Args:
        registration_file: Path to team_registration.json
        
    Returns:
        Dictionary mapping team_name to list of member IDs
    """
    if registration_file is None:
        registration_file = Path("teams/team_registration.json")
    else:
        registration_file = Path(registration_file)
    
    if not registration_file.exists():
        logging.warning(f"Team registration file not found: {registration_file}")
        return {}
    
    try:
        with open(registration_file, 'r') as f:
            data = json.load(f)
            
        # Convert to dictionary for easy lookup
        team_members = {}
        for team in data.get("teams", []):
            team_name = team.get("team_name")
            members = team.get("members", [])
            if team_name:
                team_members[team_name] = members
        
        logging.info(f"Loaded registration for {len(team_members)} teams")
        return team_members
        
    except Exception as e:
        logging.error(f"Error loading team registration: {e}")
        return {}


def find_team_by_student_id(student_id: str, registration_file: str = None) -> Optional[str]:
    """
    Find team name for a given student ID.
    
    Args:
        student_id: Student ID to search for
        registration_file: Path to team_registration.json
        
    Returns:
        Team name if found, None otherwise
    """
    team_members = load_team_registration(registration_file)
    
    for team_name, members in team_members.items():
        if student_id in members:
            return team_name
    
    return None


def load_teams_from_directory(teams_dir: str, registration_file: str = None) -> list:
    """
    Load teams from directory structure.
    
    Expected structure:
    teams/
        team1/
            bidding_agent.py
        team2/
            bidding_agent.py
        team_registration.json
    
    Args:
        teams_dir: Path to teams directory
        registration_file: Optional path to team_registration.json (defaults to teams_dir/team_registration.json)
    
    Returns:
        List of Team objects
    """
    teams = []
    teams_path = Path(teams_dir)
    
    if not teams_path.exists():
        logging.error(f"Teams directory not found: {teams_dir}")
        return teams
    
    # Load team registration if available
    if registration_file is None:
        registration_file = teams_path / "team_registration.json"
    team_members_map = load_team_registration(str(registration_file))
    
    for team_dir in teams_path.iterdir():
        if not team_dir.is_dir():
            continue
        
        agent_file = team_dir / "bidding_agent.py"
        if not agent_file.exists():
            logging.warning(f"No bidding_agent.py found in {team_dir}")
            continue
        
        # Get member IDs from registration
        team_name = team_dir.name
        members = team_members_map.get(team_name, [])
        
        team = Team(
            team_id=team_dir.name,
            team_name=team_name,
            agent_file_path=str(agent_file.absolute()),
            registration_timestamp=datetime.fromtimestamp(team_dir.stat().st_ctime),
            members=members
        )
        
        teams.append(team)
        logging.info(f"Loaded team: {team.team_id} (members: {len(members)})")
    
    return teams


def run_full_tournament(teams_dir: str, output_dir: str, timeout: float, seed: int = None):
    """
    Run the complete tournament.
    
    Args:
        teams_dir: Directory containing team submissions
        output_dir: Directory for results output
        timeout: Timeout for bid execution
        seed: Random seed for reproducibility
    """
    logging.info("Loading teams...")
    teams = load_teams_from_directory(teams_dir)
    
    if len(teams) < 5:
        logging.error(f"Need at least 5 teams, found {len(teams)}")
        return
    
    logging.info(f"Loaded {len(teams)} teams")
    
    # Initialize components
    valuation_generator = ValuationGenerator(random_seed=seed)
    results_manager = ResultsManager(output_dir=output_dir)
    tournament_manager = TournamentManager(
        valuation_generator=valuation_generator,
        results_manager=results_manager,
        timeout_seconds=timeout
    )
    
    # Run tournament
    try:
        stage1_result, stage2_result = tournament_manager.run_full_tournament(teams)
        logging.info("Tournament completed successfully!")
    except Exception as e:
        logging.error(f"Tournament failed: {e}", exc_info=True)


def run_single_stage(stage: int, teams_dir: str, output_dir: str, timeout: float, seed: int = None):
    """
    Run a single stage only.
    
    Args:
        stage: Stage number (1 or 2)
        teams_dir: Directory containing team submissions
        output_dir: Directory for results output
        timeout: Timeout for bid execution
        seed: Random seed for reproducibility
    """
    logging.info(f"Loading teams for Stage {stage}...")
    teams = load_teams_from_directory(teams_dir)
    
    if len(teams) < 2:
        logging.error(f"Need at least 2 teams, found {len(teams)}")
        return
    
    logging.info(f"Loaded {len(teams)} teams")
    
    # Initialize components
    valuation_generator = ValuationGenerator(random_seed=seed)
    results_manager = ResultsManager(output_dir=output_dir)
    tournament_manager = TournamentManager(
        valuation_generator=valuation_generator,
        results_manager=results_manager,
        timeout_seconds=timeout
    )
    
    # Run stage
    try:
        if stage == 1:
            stage_result, qualified = tournament_manager.run_stage1(teams)
            logging.info(f"Stage 1 complete. {len(qualified)} teams qualified.")
        elif stage == 2:
            stage_result = tournament_manager.run_stage2(teams)
            logging.info("Stage 2 complete.")
        else:
            logging.error(f"Invalid stage: {stage}")
    except Exception as e:
        logging.error(f"Stage {stage} failed: {e}", exc_info=True)


def validate_agent(agent_file: str):
    """
    Validate a single agent file.
    
    Args:
        agent_file: Path to agent file
    """
    from src.agent_manager import AgentManager
    from src.config import INITIAL_BUDGET, T_AUCTION_ROUNDS, ITEM_ID_FORMAT
    
    logging.info(f"Validating agent: {agent_file}")
    
    # Create dummy data
    team_id = "test_team"
    valuation_vector = {ITEM_ID_FORMAT.format(i): 10.0 for i in range(20)}
    auction_sequence = [ITEM_ID_FORMAT.format(i) for i in range(T_AUCTION_ROUNDS)]
    
    # Try to load agent
    agent_manager = AgentManager()
    opponent_teams = []  # Empty for validation since no actual opponents
    agent = agent_manager.load_agent(
        file_path=agent_file,
        team_id=team_id,
        valuation_vector=valuation_vector,
        budget=INITIAL_BUDGET,
        opponent_teams=opponent_teams
    )
    
    if agent is None:
        logging.error("❌ Agent validation FAILED")
        return False
    
    # Try to execute a bid
    try:
        bid, exec_time, error = agent_manager.execute_bid_with_timeout(agent, auction_sequence[0])
        if error:
            logging.warning(f"Bid execution warning: {error}")
        else:
            logging.info(f"Test bid successful: {bid:.2f} (took {exec_time:.3f}s)")
    except Exception as e:
        logging.error(f"Bid execution failed: {e}")
        return False
    
    logging.info("Agent validation PASSED")
    return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="AGT Auto-Bidding Competition System")
    
    parser.add_argument(
        '--mode',
        choices=['tournament', 'stage', 'validate'],
        default='tournament',
        help='Execution mode'
    )
    
    parser.add_argument(
        '--teams-dir',
        default='teams',
        help='Directory containing team submissions'
    )
    
    parser.add_argument(
        '--output-dir',
        default='results',
        help='Directory for results output'
    )
    
    parser.add_argument(
        '--stage',
        type=int,
        choices=[1, 2],
        help='Stage number (for stage mode)'
    )
    
    parser.add_argument(
        '--validate',
        help='Path to agent file to validate'
    )
    
    parser.add_argument(
        '--timeout',
        type=float,
        default=BID_TIMEOUT_SECONDS,
        help='Timeout for bid execution (seconds)'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        default=RANDOM_SEED,
        help='Random seed for reproducibility'
    )
    
    parser.add_argument(
        '--log-file',
        help='Log file path'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = args.log_file if args.log_file else f"logs/competition_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    setup_logging(verbose=args.verbose, log_file=log_file)
    
    # Execute based on mode
    if args.mode == 'tournament':
        run_full_tournament(args.teams_dir, args.output_dir, args.timeout, args.seed)
    
    elif args.mode == 'stage':
        if args.stage is None:
            logging.error("--stage required for stage mode")
            return
        run_single_stage(args.stage, args.teams_dir, args.output_dir, args.timeout, args.seed)
    
    elif args.mode == 'validate':
        if args.validate is None:
            logging.error("--validate required for validate mode")
            return
        validate_agent(args.validate)


if __name__ == '__main__':
    main()
