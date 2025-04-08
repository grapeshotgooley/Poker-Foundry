from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
from datetime import datetime
import re

# Setup Chrome
service = Service("C:\\Users\\goole\\PycharmProjects\\PokerFoundry\\chromedriver-win64\\chromedriver.exe")
options = Options()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=service, options=options)

#driver.get("https://www.pokernow.club/start-game")
driver.get("https://www.pokernow.club/games/pglz6eNyqWKKcqKI1f2dMw-sV")

time.sleep(5)

last_state = ""
last_actions = {}
last_turn = None
last_turn_element = None
last_dealer_seat = None
hand_number = 1
player_bets = {}
previous_bets = {}
last_board = []
current_street = "Preflop"
last_better = None
last_action = None
current_turn = None

def get_texts(selector):
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        return [e.text.strip() for e in elements if e.is_displayed() and e.text.strip()]
    except:
        return []

def get_single(selector):
    try:
        e = driver.find_element(By.CSS_SELECTOR, selector)
        return e.text.strip()
    except:
        return None

def get_table_players():
    return driver.find_elements(By.CSS_SELECTOR, ".table-player")

def get_player_name(player):
    try:
        return player.find_element(By.CSS_SELECTOR, ".table-player-name").text.strip()
    except:
        return None

def get_player_bet(player):
    try:
        return player.find_element(By.CSS_SELECTOR, ".table-player-bet-value .chips-value").text.strip()
    except:
        return "0"

def get_player_action(player, highest_bet):
    try:
        name = get_player_name(player)
        class_attr = player.get_attribute("class")

        if "fold" in class_attr:
            return "Fold"

        try:
            bet_text = player.find_element(By.CSS_SELECTOR, ".table-player-bet-value .chips-value").text.strip()
            bet = int(bet_text.replace(",", "")) if bet_text else 0
        except:
            bet = 0

        if bet == 0:
            if highest_bet > 0:
                return "Fold"
            else:
                return "Check"
        elif bet < highest_bet:
            return f"Call {bet}"
        elif bet == highest_bet:
            return f"Call {bet}"
        else:
            return f"Raise to {bet}"
    except:
        return "Check"

# Persistent variable to store the last dealer's seat index
last_dealer_seat = None


def get_dealer_seat_and_name():
    global last_dealer_seat  # Access the global variable to track the dealer seat
    try:
        dealer_els = driver.find_elements(By.CSS_SELECTOR, ".dealer-button-ctn")
        if not dealer_els:
            print("❌ Game Hasn't Started.")
            return None, None

        for el in dealer_els:
            class_attr = el.get_attribute("class")
            match = re.search(r"dealer-position-(\d+)", class_attr)
            if not match:
                continue

            seat_index = int(match.group(1))
            player_els = driver.find_elements(By.CSS_SELECTOR, ".table-player")
            for player in player_els:
                player_class = player.get_attribute("class")
                if f"table-player-{seat_index}" in player_class:
                    try:
                        name_el = player.find_element(By.CSS_SELECTOR, ".table-player-name")
                        name = name_el.text.strip()
                        if not name:
                            name = name_el.find_element(By.CSS_SELECTOR, "a").text.strip()

                        # Check for dealer change
                        if last_dealer_seat != seat_index:
                            print(f"🔄 New dealer for the hand: {name} (Seat {seat_index})")
                            last_dealer_seat = seat_index  # Update the last dealer seat

                        return seat_index, name
                    except:
                        if last_dealer_seat != seat_index:
                            print(f"🔄 New dealer for the hand: (no name) (Seat {seat_index})")
                            last_dealer_seat = seat_index  # Update the last dealer seat
                        return seat_index, "(no name)"
        return None, None
    except Exception as e:
        print(f"[!] Dealer detection error: {e}")
        return None, None

def get_game_state():
    state = {}
    pot = get_single(".table-pot-size") or get_single(".chips-value")
    state['pot'] = pot

    player_names = get_texts(".table-player-name")
    player_stacks = get_texts(".table-player-stack")
    state['players'] = list(zip(player_names, player_stacks))

    cards = get_texts(".you-player .card-container .card .value")
    suits = get_texts(".you-player .card-container .card .suit")
    state['your_hand'] = [f"{v}{s}" for v, s in zip(cards, suits)] if cards else []

    community_values = get_texts(".card-container .card .value")
    community_suits = get_texts(".card-container .card .suit")
    full_board = [f"{v}{s}" for v, s in zip(community_values, community_suits)]
    state['board'] = full_board[2:]
    state['game_type'] = get_single(".game-type-ctn") or get_single(".table-game-type")

    board_len = len(state['board'])
    if board_len == 0:
        state['street'] = "Preflop"
    elif 1 <= board_len <= 3:
        state['street'] = "Flop"
    elif board_len == 4:
        state['street'] = "Turn"
    else:
        state['street'] = "River"

    action_elements = driver.find_elements(By.CSS_SELECTOR, ".table-player-infos-ctn")
    player_actions = {}
    for el in action_elements:
        try:
            name_el = el.find_element(By.CSS_SELECTOR, ".table-player-name")
            signal_els = el.find_elements(By.CSS_SELECTOR, ".signal")
            if name_el and signal_els:
                name = name_el.text.strip()
                action = signal_els[-1].text.strip() if signal_els else ""
                if name and action:
                    player_actions[name] = action
        except:
            continue
    state['player_actions'] = player_actions
    state['last_action'] = last_action
    state['current_turn'] = current_turn
    return state

def state_to_str(state, dealer_seat=None, dealer_name=None):
    return (
        f"[Game Type] {state.get('game_type')}\n"
        f"[Pot Size] {state.get('pot')}\n"
        f"[Your Hand] {' '.join(state.get('your_hand', []))}\n"
        f"[Board ({state.get('street')})] {' '.join(state.get('board', []))}\n"
        f"[Players]\n" +
        "\n".join([f" - {name}: {stack}, Bet: {player_bets.get(name, '0')}" for name, stack in state.get('players', [])]) +
        f"\n[Dealer Seat] {dealer_seat}, Dealer Name: {dealer_name}\n"
        f"[Last Better] {last_better if last_better else 'None'}\n"
        f"[Last Action] {state.get('last_action') if state.get('last_action') else 'None'}\n"
        f"[Current Turn] {state.get('current_turn') if state.get('current_turn') else 'None'}\n"
    )

def log_action_updates(current_actions):
    global last_actions, last_better, previous_bets
    for player, action in current_actions.items():
        if player not in last_actions or last_actions[player] != action:
            (f"[{datetime.now().strftime('%H:%M:%S')}] {player} -> {action}")

    for name, current_bet in player_bets.items():
        prev_bet = previous_bets.get(name, "0")
        try:
            if int(current_bet.replace(",", "")) > int(prev_bet.replace(",", "")):
                last_better = f"{name} ({current_bet})"
        except ValueError:
            continue

    previous_bets = player_bets.copy()
    last_actions = current_actions.copy()

while True:
    try:
        dealer_seat, dealer_name = get_dealer_seat_and_name()
        if dealer_seat is not None and dealer_seat != last_dealer_seat:
            print(f"\n[New Hand #{hand_number}] Dealer Seat: {dealer_seat}, Dealer: {dealer_name}")
            last_dealer_seat = dealer_seat
            hand_number += 1
            player_bets.clear()
            previous_bets.clear()
            last_board = []
            current_street = "Preflop"

        raw_bets = []
        for el in get_table_players():
            try:
                bet_el = el.find_element(By.CSS_SELECTOR, ".table-player-bet-value .chips-value")
                bet = int(bet_el.text.replace(",", "")) if bet_el.text else 0
                raw_bets.append(bet)
            except:
                continue
        highest_bet_value = max(raw_bets or [0])

        for player_el in get_table_players():
            name = get_player_name(player_el)
            if name:
                player_bets[name] = get_player_bet(player_el)

        players = get_table_players()
        next_turn = None
        current_element = None

        for player in players:
            if "decision-current" in player.get_attribute("class"):
                next_turn = get_player_name(player)
                current_element = player
                break

        if next_turn and next_turn != last_turn:
            if last_turn and last_turn_element:
                last_action = get_player_action(last_turn_element, highest_bet_value)
                #print(f"[Action] {last_turn} -> {last_action}")
            #print(f"[Turn] It's now {next_turn}'s turn")
            last_turn = next_turn
            last_turn_element = current_element
            current_turn = next_turn

        state = get_game_state()

        if state['board'] != last_board:
            if state['street'] != current_street:
                print(f"[New Street] {state['street']}")
                player_bets.clear()
                previous_bets.clear()
                current_street = state['street']
            last_board = state['board']

        state_str = state_to_str(state, dealer_seat, dealer_name)
        if state_str != last_state:
            print("\n" + "=" * 50)
            print(state_str)
            last_state = state_str

        log_action_updates(state.get("player_actions", {}))

        time.sleep(1)

    except KeyboardInterrupt:
        print("[Stopped by user]")
        break
    except Exception as e:
        print("[Error]", e)
        time.sleep(1)
