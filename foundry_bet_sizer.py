import random
import numpy as np


def truncated_normal(mean, lower, upper):
    """Generate a sample from a truncated normal distribution."""
    std_dev = (upper - lower) / 6  # Approximate to keep most values within bounds
    sample = np.random.normal(mean, std_dev)
    return min(max(sample, lower), upper)


def calculate_spr_and_bet(street, hero_stack, villain_stack, pot_size, raises, last_villain_bet=0, big_blind=1,
                          multiway=False, postflop_street='flop', hero_position=1, in_position=True):
    """
    Calculate SPR and determine bet size based on poker bet sizing rules.

    Parameters:
    street (str): 'preflop' or 'postflop'
    hero_stack (float): Hero's current stack size
    villain_stack (float): Villain's current stack size
    pot_size (float): Current pot size
    raises (int): Number of raises on this street
    last_villain_bet (float): The last bet made by the villain
    big_blind (float): The size of the big blind
    multiway (bool): Whether multiple opponents are in the hand
    postflop_street (str): 'flop', 'turn', or 'river' to differentiate postflop bet sizing ranges
    hero_position (int): Hero's position (1-10) to determine preflop range
    in_position (bool): Whether hero is in position or out of position

    Returns:
    tuple: (SPR, bet size)
    """
    # Calculate SPR (Stack-to-Pot Ratio)
    spr = min(hero_stack, villain_stack) / pot_size if pot_size > 0 else 0

    # Jam conditions
    if spr <= 1 or hero_stack <= (12*big_blind):
        return spr, round(hero_stack)  # All-in

    bet_size = 0  # Initialize bet size

    if street == 'preflop':
        if raises == 0:
            preflop_ranges = {
                1: (2.5, 4.5),
                2: (2.5, 4),
                3: (2, 2.5),
                4: (2, 3),
                5: (2, 3.5),
                6: (2, 3.5),
                7: (2, 4),
                8: (2, 4.5),
                9: (2, 4.5),
                10: (2, 4.5)
            }
            lower, upper = preflop_ranges.get(hero_position, (2.5, 4.5))
            bet_size = big_blind * truncated_normal((lower + upper) / 2, lower, upper)
        else:
            if raises >= 3:  # 5-bet
                return spr, round(min(hero_stack, pot_size))  # Min-click or jam
            elif raises == 2:  # 4-bet
                lower, upper = (2.2, 3.2)
                if not in_position:
                    lower += 0.75
                    upper += 0.75
                mean = (lower + upper) / 2  # Adjust mean based on position shift
                bet_size = last_villain_bet * truncated_normal(mean, lower, upper)
            elif raises == 1:  # 3-bet
                lower, upper = (2.5, 3.5)
                if not in_position:
                    lower += 0.75
                    upper += 0.75
                mean = (lower + upper) / 2  # Adjust mean based on position shift
                bet_size = last_villain_bet * truncated_normal(mean, lower, upper)

    else:  # Postflop
        postflop_ranges = {
            'flop': (1 / 3, 2, 0.5),  # Flop bet centers at 1/2 pot
            'turn': (1 / 3, 2, 0.75),  # Turn bet centers at 3/4 pot
            'river': (1 / 3, 2, 1)  # River bet centers at 1 pot
        }
        lower, upper, center = postflop_ranges.get(postflop_street, (1 / 3, 2, 0.5))

        if raises > 0:
            bet_size = (pot_size + 2 * last_villain_bet) * truncated_normal(1, 0.75,
                                                                            1.25)  # Adjusted for reraise formula
        else:
            bet_size = pot_size * truncated_normal(center, lower, upper)

    # Multiway adjustment
    if multiway and street == 'postflop':
        bet_size *= 0.75  # Reduce by 25%

    # Ensure bet sizes conform to rounding rules
    if bet_size >= 0.85 * hero_stack or bet_size >= hero_stack:
        bet_size = hero_stack  # Convert to jam

    return spr, round(bet_size)


# Example usage
spr, bet = calculate_spr_and_bet('preflop', hero_stack=620, villain_stack=480, pot_size=27, raises=1,
                                 last_villain_bet=20, big_blind=5, multiway=False, postflop_street='N/A',
                                 hero_position=1, in_position=False)
print(f'SPR: {spr:.2f}, Bet Size: {bet}')