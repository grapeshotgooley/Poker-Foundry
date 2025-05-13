import PokerPy
from PokerPy import Card, calculate_hand_frequency, get_best_hand
import eval7
from itertools import combinations

import eval7
from itertools import combinations

def best_possible_hole_cards(board_strs):
    """
    Returns the best 2-card villain combo given a board like ['QC', '5H', 'AC'].
    """
    def normalize(card_str):
        rank = card_str[:-1]
        suit = card_str[-1]
        rank = 'T' if rank == '10' else rank.upper()
        suit = suit.lower()  # Lowercase suits for eval7
        return eval7.Card(rank + suit)

    try:
        board = [normalize(s) for s in board_strs]
        deck = eval7.Deck()

        # Remove board cards using ascii_representation (e.g., 'Ah', 'Qc')
        board_ascii = {card.__str__() for card in board}
        deck.cards = [card for card in deck.cards if str(card) not in board_ascii]

        best_score = -1
        best_hole = None

        for h1, h2 in combinations(deck.cards, 2):
            score = eval7.evaluate(board + [h1, h2])
            if score > best_score:
                best_score = score
                best_hole = (h1, h2)

        return best_hole

    except Exception as e:
        import logging
        logging.warning(f"Error in best_possible_hole_cards: {e}")
        return None




def get_hero_win_rate(hero_hand, villain_hand, community_cards=[]):
    """
    Extracts and returns only the win probability for Hero as a precise decimal.

    :param hero_hand: List of two Card objects representing Hero's hole cards.
    :param villain_hand: List of two Card objects representing Villain's hole cards.
    :param community_cards: List of 0 to 5 Card objects representing the community cards.
    :return: Hero's win probability as a decimal.
    """
    if not (0 <= len(community_cards) <= 5):
        raise ValueError("Community cards must be between 0 and 5.")

    if len(community_cards) == 5:
        # Directly determine the best hand without simulation
        hero_best_hand = get_best_hand(hero_hand + community_cards)
        villain_best_hand = get_best_hand(villain_hand + community_cards)

        # Compare hand strength using heuristic value if available
        hero_strength = hero_best_hand.hand_heuristic()
        villain_strength = villain_best_hand.hand_heuristic()

        if hero_strength > villain_strength:
            return 1.0  # Hero wins outright
        elif hero_strength == villain_strength:
            return 0.0  # No outright win (tie handled separately)
        else:
            return 0.0  # Hero loses outright

    # If fewer than 5 community cards, use Monte Carlo simulation
    player_hands = [
        [*hero_hand, *community_cards],
        [*villain_hand, *community_cards]
    ]

    frequencies = calculate_hand_frequency(player_hands)
    total_simulations = frequencies[0].get("Total Cases", 1)

    hero_win = frequencies[0].get("Win", 0) / total_simulations
    return hero_win


def get_hero_tie_rate(hero_hand, villain_hand, community_cards=[]):
    """
    Extracts and returns only the tie probability for Hero as a precise decimal.

    :param hero_hand: List of two Card objects representing Hero's hole cards.
    :param villain_hand: List of two Card objects representing Villain's hole cards.
    :param community_cards: List of 0 to 5 Card objects representing the community cards.
    :return: Hero's tie probability as a decimal.
    """
    if not (0 <= len(community_cards) <= 5):
        raise ValueError("Community cards must be between 0 and 5.")

    if len(community_cards) == 5:
        # Directly determine if it's a tie
        hero_best_hand = get_best_hand(hero_hand + community_cards)
        villain_best_hand = get_best_hand(villain_hand + community_cards)

        hero_strength = hero_best_hand.hand_heuristic()
        villain_strength = villain_best_hand.hand_heuristic()

        if hero_strength == villain_strength:
            return 1.0  # 100% tie
        else:
            return 0.0  # No tie

    # If fewer than 5 community cards, use Monte Carlo simulation
    player_hands = [
        [*hero_hand, *community_cards],
        [*villain_hand, *community_cards]
    ]

    frequencies = calculate_hand_frequency(player_hands)
    total_simulations = frequencies[0].get("Total Cases", 1)

    hero_tie = frequencies[0].get("Draw", 0) / total_simulations
    return hero_tie


# Example usage
if __name__ == "__main__":
    hero = [Card("AC"), Card("7C")]
    villain = [Card("KC"), Card("10H")]
    board = []  # Full 5 community cards

    print(f"Hero Win Rate: {get_hero_win_rate(hero, villain, board)}")
    print(f"Hero Tie Rate: {get_hero_tie_rate(hero, villain, board)}")
