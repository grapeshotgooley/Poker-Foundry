import json
import os
import random

RANGES_DIR = "ranges"
VALID_POSITIONS = {"utg", "utg+1", "utg+2", "lj", "hj", "co", "btn", "sb", "bb"}

POKER_RANK_ORDER = "AKQJT98765432"

def normalize_hand(hand: str) -> str:
    def rank_value(card):
        return POKER_RANK_ORDER.index(card)

    if len(hand) == 2:
        r1, r2 = hand[0], hand[1]
        if r1 == r2:
            return r1 + r2
        return r1 + r2 if rank_value(r1) < rank_value(r2) else r2 + r1

    if len(hand) == 3 and hand[2] in {'s', 'o'}:
        r1, r2, suitedness = hand[0], hand[1], hand[2]
        if r1 == r2:
            return r1 + r2
        return r1 + r2 + suitedness if rank_value(r1) > rank_value(r2) else r2 + r1 + suitedness

    raise ValueError(f"Invalid hand format: '{hand}'. Expected formats like 'AKs', 'QQ', 'JTo'.")

def get_range_action(hand: str, position: str) -> str:
    try:
        if position not in VALID_POSITIONS:
            raise ValueError(f"Invalid position '{position}'. Must be one of: {', '.join(sorted(VALID_POSITIONS))}")

        normalized_hand = normalize_hand(hand)
        filepath = os.path.join(RANGES_DIR, f"{position}.json")

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"No range file found for '{position}' at '{filepath}'.")

        with open(filepath, "r") as file:
            data = json.load(file)

        action = data.get(normalized_hand)
        if action is None:
            raise KeyError(f"Hand '{hand}' (normalized as '{normalized_hand}') not found in {position} ranges.")

        return action

    except Exception as e:
        return f"Error: {e}"

def should_play_hand(
    hand: str,
    position: str,
    special_hand_enabled: bool = False,
    special_hand: str = "",
    special_hand_suited: bool = False
) -> str:
    try:
        normalized_hand = normalize_hand(hand)

        # Big Blind pre-check: 15% open regardless of hand
        if position == "bb" and random.random() < 0.15:
            return "open"

        # Special hand override
        if special_hand_enabled:
            normalized_special = normalize_hand(special_hand + "s")
            hand_core = normalized_hand[:2]
            special_core = normalized_special[:2]

            if special_hand_suited:
                if normalized_hand == special_core + "s":
                    return "open"
            else:
                if hand_core == special_core:
                    return "open"

        # Get our hand's action
        action = get_range_action(hand, position)

        # ✳️ NEW: If special hand would raise and our hand is 's', allow 25% open
        if special_hand_enabled:
            normalized_special = normalize_hand(special_hand + "s")
            special_action = get_range_action(normalized_special, position)
            if special_action == "r" and action == "s":
                return "open" if random.random() < 0.25 else "fold"

        # Special frequency adjustment for 's'/'b'
        if action == "s" or action == "b":
            if special_hand_enabled and special_hand_suited:
                return "open" if random.random() < 0.125 else "fold"
            elif special_hand_enabled and not special_hand_suited:
                return "open" if random.random() < 0.05 else "fold"
            else:
                return "open" if random.random() < 0.25 else "fold"

        # SB r becomes call 60% of time
        if action == "r" and position == "sb":
            return "call" if random.random() < 0.60 else "open"

        # BB never folds → return check instead
        if action == "f" and position == "bb":
            return "check"

        if action == "r":
            return "open"
        elif action == "f":
            return "fold"
        else:
            raise ValueError(f"Unknown action value '{action}' for hand '{hand}' at position '{position}'.")

    except Exception as e:
        return f"Error: {e}"

# 🧪 Test
if __name__ == "__main__":
    test_cases = [
        ("78s", "utg", True, "72", False),     # from range
    ]

    for hand, pos, special_on, special_hand, suited_only in test_cases:
        result = should_play_hand(hand, pos, special_on, special_hand, suited_only)
        print(f"{hand} in {pos.upper()} → {result}")
