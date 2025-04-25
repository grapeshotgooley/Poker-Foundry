import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class PlayerStats:
    vpip: float = 0.0
    pfr: float = 0.0
    three_bet: float = 0.0
    fold_to_three_bet: float = 0.0
    call_big_flop: float = 0.0
    went_to_showdown: float = 0.0


@dataclass
class HandAction:
    action_type: str  # 'call', 'raise', 'fold', 'check'
    amount: float
    street: str  # 'preflop', 'flop', 'turn', 'river'
    timestamp: str


@dataclass
class Hand:
    hand_id: str
    timestamp: str
    actions: List[HandAction]
    result: Optional[float] = None  # Amount won/lost
    went_to_showdown: bool = False


class StatsTracker:
    def __init__(self, data_dir: str = "player_data"):
        self.data_dir = data_dir
        self._ensure_data_directory()

    def _ensure_data_directory(self):
        """Create the data directory if it doesn't exist."""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def _get_player_file_path(self, player_name: str) -> str:
        """Get the file path for a player's data file."""
        return os.path.join(self.data_dir, f"{player_name}.json")

    def _load_player_data(self, player_name: str) -> Dict:
        """Load player data from JSON file."""
        file_path = self._get_player_file_path(player_name)
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return {
            "name": player_name,
            "hands": [],
            "stats": {
                "vpip": 0.0,
                "pfr": 0.0,
                "three_bet": 0.0,
                "fold_to_three_bet": 0.0,
                "call_big_flop": 0.0,
                "went_to_showdown": 0.0
            }
        }

    def _save_player_data(self, player_name: str, data: Dict):
        """Save player data to JSON file."""
        file_path = self._get_player_file_path(player_name)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

    def add_hand(self, player_name: str, hand: Hand):
        """Add a new hand to a player's history and update stats."""
        data = self._load_player_data(player_name)
        hand_dict = {
            "hand_id": hand.hand_id,
            "timestamp": hand.timestamp,
            "actions": [
                {
                    "action_type": action.action_type,
                    "amount": action.amount,
                    "street": action.street,
                    "timestamp": action.timestamp
                }
                for action in hand.actions
            ],
            "result": hand.result,
            "went_to_showdown": hand.went_to_showdown
        }
        data["hands"].append(hand_dict)
        self._update_stats(data)
        self._save_player_data(player_name, data)

    def _update_stats(self, data: Dict):
        """Update player statistics based on hand history."""
        hands = data["hands"]
        if not hands:
            return

        total_hands = len(hands)
        vpip_hands = 0
        pfr_hands = 0
        three_bet_hands = 0
        fold_to_three_bet_hands = 0
        call_big_flop_hands = 0
        went_to_showdown_hands = 0

        for hand in hands:
            actions = hand["actions"]

            # VPIP calculation
            if any(action["action_type"] in ["call", "raise"] for action in actions):
                vpip_hands += 1

            # PFR calculation
            if any(action["action_type"] == "raise" and action["street"] == "preflop" for action in actions):
                pfr_hands += 1

            # 3B calculation
            if any(action["action_type"] == "raise" and action["street"] == "preflop" and action["amount"] > 2.5 for
                   action in actions):
                three_bet_hands += 1

            # F3B calculation
            if any(action["action_type"] == "fold" and action["street"] == "preflop" for action in actions):
                fold_to_three_bet_hands += 1

            # CBF calculation
            if any(action["action_type"] == "call" and action["street"] == "flop" for action in actions):
                call_big_flop_hands += 1

            # WTSD calculation
            if hand["went_to_showdown"]:
                went_to_showdown_hands += 1

        data["stats"] = {
            "vpip": (vpip_hands / total_hands) * 100 if total_hands > 0 else 0,
            "pfr": (pfr_hands / total_hands) * 100 if total_hands > 0 else 0,
            "three_bet": (three_bet_hands / total_hands) * 100 if total_hands > 0 else 0,
            "fold_to_three_bet": (fold_to_three_bet_hands / total_hands) * 100 if total_hands > 0 else 0,
            "call_big_flop": (call_big_flop_hands / total_hands) * 100 if total_hands > 0 else 0,
            "went_to_showdown": (went_to_showdown_hands / total_hands) * 100 if total_hands > 0 else 0
        }

    def get_player_stats(self, player_name: str) -> PlayerStats:
        """Get current statistics for a player."""
        data = self._load_player_data(player_name)
        stats = data["stats"]
        return PlayerStats(
            vpip=stats["vpip"],
            pfr=stats["pfr"],
            three_bet=stats["three_bet"],
            fold_to_three_bet=stats["fold_to_three_bet"],
            call_big_flop=stats["call_big_flop"],
            went_to_showdown=stats["went_to_showdown"]
        )