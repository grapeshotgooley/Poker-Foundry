import time
import os
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging


class PokerDataExtractor:
    def __init__(self, options=None):
        """Initialize the PokerDataExtractor with browser options."""
        self.options = options if options else webdriver.ChromeOptions()
        self.driver = None
        self.last_state = None
        self.last_actions = {}
        self.last_turn = None
        self.last_turn_element = None
        self.last_dealer_seat = None
        self.hand_number = 0
        self.player_bets = {}
        self.previous_bets = {}
        self.last_board = []
        self.current_street = "preflop"
        self.last_better = None
        self.last_action = None
        self.current_turn = None
        self.hero_name = None  # Hero's name to track
        self.stats = {}  # Player stats
        self.pot_size = 0
        self.raises_on_street = 0
        self.big_blind = 0
        self.hero_position = 0
        self.in_position = False
        self.multiway = False
        self.last_villain_bet = 0
        self.hero_hand = []
        self.stats_file = "poker_stats.json"

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("poker_extractor.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("PokerDataExtractor")

        # Load stats if file exists
        self.load_stats()

    def load_stats(self):
        """Load player stats from file if it exists."""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    self.stats = json.load(f)
                self.logger.info(f"Loaded stats for {len(self.stats)} players.")
            except Exception as e:
                self.logger.error(f"Error loading stats file: {str(e)}")
                self.stats = {}

    def save_stats(self):
        """Save player stats to file."""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=4)
            self.logger.info(f"Saved stats for {len(self.stats)} players.")
        except Exception as e:
            self.logger.error(f"Error saving stats file: {str(e)}")

    def initialize(self):
        """Initialize the WebDriver and set up wait conditions."""
        try:
            self.driver = webdriver.Chrome(options=self.options)
            self.wait = WebDriverWait(self.driver, 10)
            self.logger.info("WebDriver initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {str(e)}")
            return False

    def navigate_to(self, url):
        """Navigate to the poker room URL."""
        try:
            self.driver.get(url)
            self.logger.info(f"Navigated to {url}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to navigate to {url}: {str(e)}")
            return False

    def set_hero_name(self, name):
        """Set the hero's name to track stats and actions."""
        self.hero_name = name
        # Initialize stats for hero if not already present
        if name and name not in self.stats:
            self.stats[name] = {
                "VPIP": {"count": 0, "total": 0},
                "PFR": {"count": 0, "total": 0},
                "3B": {"count": 0, "total": 0},
                "F3B": {"count": 0, "total": 0},
                "CBF": {"count": 0, "total": 0},
                "WTSD": {"count": 0, "total": 0}
            }
        self.logger.info(f"Hero set to: {name}")

    def get_texts(self, elements):
        """Extract text from a list of elements."""
        return [el.text if el else "" for el in elements]

    def get_single(self, xpath, default=None):
        """Get a single element by XPath."""
        try:
            return self.driver.find_element(By.XPATH, xpath)
        except NoSuchElementException:
            return default

    def get_table_players(self):
        """Get all players at the table."""
        try:
            player_elements = self.driver.find_elements(By.CSS_SELECTOR, ".player-box")
            players = {}

            for el in player_elements:
                name_el = el.find_element(By.CSS_SELECTOR, ".player-name")
                name = name_el.text if name_el else "Unknown"

                stack_el = el.find_element(By.CSS_SELECTOR, ".player-stack")
                stack = stack_el.text.replace('$', '').replace(',', '') if stack_el else "0"

                seat = el.get_attribute("data-seat-idx")

                players[seat] = {
                    "name": name,
                    "stack": float(stack) if stack.replace('.', '', 1).isdigit() else 0,
                    "element": el
                }

                # Initialize stats for this player if not already present
                if name not in self.stats and name != "Unknown":
                    self.stats[name] = {
                        "VPIP": {"count": 0, "total": 0},
                        "PFR": {"count": 0, "total": 0},
                        "3B": {"count": 0, "total": 0},
                        "F3B": {"count": 0, "total": 0},
                        "CBF": {"count": 0, "total": 0},
                        "WTSD": {"count": 0, "total": 0}
                    }

            return players
        except Exception as e:
            self.logger.error(f"Error getting table players: {str(e)}")
            return {}

    def get_player_cards(self, player_element):
        """Get a player's cards if revealed."""
        try:
            card_elements = player_element.find_elements(By.CSS_SELECTOR, ".card")
            return [card.get_attribute("alt") for card in card_elements]
        except Exception:
            return []

    def get_hero_cards(self):
        """Get the hero's cards."""
        try:
            if not self.hero_name:
                return []

            players = self.get_table_players()
            for seat, player_data in players.items():
                if player_data["name"] == self.hero_name:
                    return self.get_player_cards(player_data["element"])
            return []
        except Exception as e:
            self.logger.error(f"Error getting hero cards: {str(e)}")
            return []

    def get_board_cards(self):
        """Get the community cards on the board."""
        try:
            board_cards_el = self.driver.find_elements(By.CSS_SELECTOR, ".board-card")
            return [card.get_attribute("alt") for card in board_cards_el if card.get_attribute("alt")]
        except Exception as e:
            self.logger.error(f"Error getting board cards: {str(e)}")
            return []

    def get_pot_size(self):
        """Get the current pot size."""
        try:
            pot_el = self.get_single("//div[contains(@class, 'pot-size')]")
            if pot_el and pot_el.text:
                pot_text = pot_el.text.replace('$', '').replace(',', '')
                return float(pot_text) if pot_text.replace('.', '', 1).isdigit() else 0
            return 0
        except Exception as e:
            self.logger.error(f"Error getting pot size: {str(e)}")
            return 0

    def get_player_position(self, player_name):
        """Calculate player's position (1-6 from early to late)."""
        players = self.get_table_players()
        dealer_seat, dealer_name = self.get_dealer_seat_and_name()

        if not dealer_seat or len(players) <= 1:
            return 0

        # Sort players by seat
        sorted_seats = sorted([int(seat) for seat in players.keys()])
        dealer_index = sorted_seats.index(int(dealer_seat))

        # Find the player's seat
        player_seat = None
        for seat, player_data in players.items():
            if player_data["name"] == player_name:
                player_seat = int(seat)
                break

        if player_seat is None:
            return 0

        # Calculate position
        player_index = sorted_seats.index(player_seat)
        relative_position = (player_index - dealer_index) % len(sorted_seats)

        # Map to 1-6 scale (1 is earliest, 6 is latest)
        num_players = len(sorted_seats)
        normalized_position = int((relative_position / num_players) * 6) + 1

        return min(normalized_position, 6)  # Ensure max position is 6

    def is_in_position(self, hero_position, num_players):
        """Determine if hero is in position (late position)."""
        if num_players <= 2:
            # Heads-up, button is in position
            return hero_position >= 5  # Position 5-6 is late
        else:
            # Multiway, generally late positions are in position
            return hero_position >= 5  # Position 5-6 is late

    def is_multiway_pot(self):
        """Check if more than 2 players have put money in the pot."""
        try:
            active_players = 0
            for bet in self.player_bets.values():
                if bet > 0:
                    active_players += 1
            return active_players > 2
        except Exception as e:
            self.logger.error(f"Error checking if pot is multiway: {str(e)}")
            return False

    def get_game_state(self):
        """Get the current game state, including community cards and street."""
        board = self.get_board_cards()

        # Determine the current street based on the number of community cards
        if not board:
            street = "preflop"
        elif len(board) == 3:
            street = "flop"
        elif len(board) == 4:
            street = "turn"
        elif len(board) == 5:
            street = "river"
        else:
            street = "unknown"

        # Check if a new street has been reached
        if self.last_board != board and street != self.current_street:
            self.logger.info(f"New street: {street} with board: {board}")
            self.current_street = street
            self.raises_on_street = 0  # Reset raise counter for new street

        self.last_board = board

        return {
            "board": board,
            "street": street
        }

    def get_dealer_seat_and_name(self):
        """Get the dealer's seat and name."""
        try:
            dealer_button = self.get_single("//div[contains(@class, 'dealer-button')]")
            if dealer_button:
                dealer_seat = dealer_button.get_attribute("data-seat-idx")

                # Get dealer name
                players = self.get_table_players()
                dealer_name = players.get(dealer_seat, {}).get("name", "Unknown")

                if dealer_seat != self.last_dealer_seat:
                    self.logger.info(f"New dealer: {dealer_name} at seat {dealer_seat}")
                    self.last_dealer_seat = dealer_seat
                    self.hand_number += 1

                    # Reset tracking for new hand
                    self.player_bets = {}
                    self.previous_bets = {}
                    self.current_street = "preflop"
                    self.raises_on_street = 0

                    # Update stats for all players at the table
                    for player in players.values():
                        name = player["name"]
                        if name in self.stats:
                            self.stats[name]["VPIP"]["total"] += 1
                            self.stats[name]["PFR"]["total"] += 1
                            self.stats[name]["3B"]["total"] += 1

                return dealer_seat, dealer_name
            return None, None
        except Exception as e:
            self.logger.error(f"Error getting dealer info: {str(e)}")
            return None, None

    def get_big_blind_value(self):
        """Get the big blind value from the table."""
        try:
            bb_el = self.get_single("//div[contains(@class, 'table-stakes')]")
            if bb_el and bb_el.text:
                stakes_text = bb_el.text
                # Assuming format like "$0.50/$1"
                if '/' in stakes_text:
                    bb_text = stakes_text.split('/')[-1].replace('$', '').replace(',', '')
                    return float(bb_text) if bb_text.replace('.', '', 1).isdigit() else 0
            return 0
        except Exception as e:
            self.logger.error(f"Error getting big blind value: {str(e)}")
            return 0

    def get_player_actions(self):
        """Get the actions of all players."""
        try:
            action_elements = self.driver.find_elements(By.CSS_SELECTOR, ".player-action")
            current_actions = {}

            for el in action_elements:
                # Find the player element that contains this action
                player_el = el.find_element(By.XPATH, "./ancestor::div[contains(@class, 'player-box')]")
                if not player_el:
                    continue

                seat = player_el.get_attribute("data-seat-idx")
                name_el = player_el.find_element(By.CSS_SELECTOR, ".player-name")
                name = name_el.text if name_el else "Unknown"

                action_text = el.text.strip().lower()

                # Record the action
                current_actions[name] = {
                    "action": action_text,
                    "seat": seat
                }

                # Update stats based on actions
                if name in self.stats:
                    # Track VPIP - any money put in preflop
                    if self.current_street == "preflop" and any(
                            keyword in action_text for keyword in ["call", "raise", "all-in"]):
                        if not self.stats[name].get("vpip_counted_this_hand", False):
                            self.stats[name]["VPIP"]["count"] += 1
                            self.stats[name]["vpip_counted_this_hand"] = True

                    # Track PFR - raising preflop
                    if self.current_street == "preflop" and "raise" in action_text:
                        if not self.stats[name].get("pfr_counted_this_hand", False):
                            self.stats[name]["PFR"]["count"] += 1
                            self.stats[name]["pfr_counted_this_hand"] = True

                    # Track 3B - re-raising preflop
                    if self.current_street == "preflop" and "raise" in action_text and self.raises_on_street >= 1:
                        if not self.stats[name].get("3b_counted_this_hand", False):
                            self.stats[name]["3B"]["count"] += 1
                            self.stats[name]["3b_counted_this_hand"] = True

                            # Check if hero needs to track F3B (folding to 3bet)
                            if self.hero_name and self.hero_name != name and self.stats[self.hero_name].get(
                                    "pfr_counted_this_hand", False):
                                self.stats[self.hero_name]["F3B"]["total"] += 1

                    # Track F3B - folding to 3bet
                    if self.hero_name == name and action_text == "fold" and self.current_street == "preflop":
                        if self.stats[name].get("pfr_counted_this_hand", False) and not self.stats[name].get(
                                "f3b_counted_this_hand", False):
                            last_raiser = None
                            for player, action in current_actions.items():
                                if player != name and "raise" in action["action"]:
                                    last_raiser = player
                                    break

                            if last_raiser and self.raises_on_street >= 2:
                                self.stats[name]["F3B"]["count"] += 1
                                self.stats[name]["f3b_counted_this_hand"] = True

                    # Track CBF - continuation bet on flop
                    if self.current_street == "flop":
                        # Mark players who see the flop
                        if not self.stats[name].get("saw_flop_this_hand", False):
                            self.stats[name]["saw_flop_this_hand"] = True

                        # Track if they bet/raise (not check/fold)
                        if any(keyword in action_text for keyword in ["bet", "raise"]):
                            if not self.stats[name].get("cbf_counted_this_hand", False):
                                self.stats[name]["CBF"]["count"] += 1
                                self.stats[name]["cbf_counted_this_hand"] = True

                    # Track WTSD - went to showdown
                    if self.current_street == "river" and not self.stats[name].get("wtsd_counted_this_hand", False):
                        self.stats[name]["WTSD"]["count"] += 1
                        self.stats[name]["wtsd_counted_this_hand"] = True

                # Count raises on this street
                if "raise" in action_text and self.last_action != f"{name}: {action_text}":
                    self.raises_on_street += 1

                # Update last action
                self.last_action = f"{name}: {action_text}"

                # Update last villain bet (if this is not the hero)
                if name != self.hero_name and "raise" in action_text:
                    # Try to extract bet amount
                    try:
                        bet_el = player_el.find_element(By.CSS_SELECTOR, ".player-bet")
                        if bet_el and bet_el.text:
                            bet_text = bet_el.text.replace('$', '').replace(',', '')
                            self.last_villain_bet = float(bet_text) if bet_text.replace('.', '', 1).isdigit() else 0
                    except:
                        pass

            # Look for new actions
            for name, action_data in current_actions.items():
                action = action_data["action"]
                if name not in self.last_actions or self.last_actions[name] != action:
                    self.logger.info(f"Action: {name} {action}")

            self.last_actions = {name: action_data["action"] for name, action_data in current_actions.items()}
            return current_actions
        except Exception as e:
            self.logger.error(f"Error getting player actions: {str(e)}")
            return {}

    def get_current_data(self):
        """Collect all current data to be sent to modules."""
        # Get current game state
        state = self.get_game_state()
        players = self.get_table_players()
        actions = self.get_player_actions()

        # Get hero-specific data
        hero_stack = 0
        villain_stack = 0  # Using the stack of the most active opponent

        # Find hero stack and position
        if self.hero_name:
            for seat, player_data in players.items():
                if player_data["name"] == self.hero_name:
                    hero_stack = player_data["stack"]
                    break

            self.hero_position = self.get_player_position(self.hero_name)

        # Find the most active villain
        max_bet = 0
        for name, player_data in players.items():
            if name != self.hero_name:
                for action_name, action_data in actions.items():
                    if action_name == name and "raise" in action_data["action"]:
                        if player_data["stack"] > max_bet:
                            max_bet = player_data["stack"]
                            villain_stack = player_data["stack"]
                            break

        # If we didn't find an active villain, just use the first non-hero player
        if villain_stack == 0 and len(players) > 1:
            for name, player_data in players.items():
                if name != self.hero_name:
                    villain_stack = player_data["stack"]
                    break

        # Get other data
        pot_size = self.get_pot_size()
        big_blind = self.get_big_blind_value()
        hero_cards = self.get_hero_cards()
        board_cards = state["board"]
        street = state["street"]

        # Calculate multiway status
        self.multiway = self.is_multiway_pot()

        # Calculate in position status
        self.in_position = self.is_in_position(self.hero_position, len(players))

        return {
            "hero_name": self.hero_name,
            "hero_stack": hero_stack,
            "hero_position": self.hero_position,
            "in_position": self.in_position,
            "villain_stack": villain_stack,
            "pot_size": pot_size,
            "raises_this_street": self.raises_on_street,
            "last_villain_bet": self.last_villain_bet,
            "big_blind": big_blind,
            "multiway": self.multiway,
            "street": street,
            "hero_cards": hero_cards,
            "board_cards": board_cards,
            "players": players,
            "actions": actions,
            "hand_number": self.hand_number
        }

    def send_data_to_open_fold(self, data):
        """Send data to the Open-Fold module."""
        if data["hero_name"] and self.last_dealer_seat != data.get("dealer_seat"):
            message = {
                "module": "open-fold",
                "hand": data["hero_cards"],
                "options": {
                    "position": data["hero_position"],
                    "stack": data["hero_stack"],
                    "big_blind": data["big_blind"]
                }
            }
            self.logger.info(f"Sending to Open-Fold: {message}")
            # Implement actual sending mechanism here (e.g., API call, file write, etc.)

    def send_data_to_calculator(self, data):
        """Send data to the Calculator module."""
        # Check if it's a new street
        if self.current_street != data["street"]:
            message = {
                "module": "calculator",
                "hand": data["hero_cards"],
                "board": data["board_cards"]
            }

            # Check if opponent's hand is revealed
            for player_name, player_data in data["players"].items():
                if player_name != data["hero_name"]:
                    try:
                        opponent_cards = self.get_player_cards(player_data["element"])
                        if opponent_cards and len(opponent_cards) == 2:
                            message["opponent_hand"] = opponent_cards
                            break
                    except:
                        pass

            self.logger.info(f"Sending to Calculator: {message}")
            # Implement actual sending mechanism here

    def send_data_to_bet_sizer(self, data):
        """Send data to the Bet Sizer module."""
        message = {
            "module": "bet-sizer",
            "hero_stack": data["hero_stack"],
            "villain_stack": data["villain_stack"],
            "pot_size": data["pot_size"],
            "raises_on_street": data["raises_this_street"],
            "last_villain_bet": data["last_villain_bet"],
            "big_blind": data["big_blind"],
            "multiway": data["multiway"],
            "street": data["street"],
            "hero_position": data["hero_position"],
            "in_position": data["in_position"]
        }
        self.logger.info(f"Sending to Bet Sizer: {message}")
        # Implement actual sending mechanism here

    def send_data_to_stat_tracker(self):
        """Send data to the Stat Tracker module by saving stats to file."""
        # Clean up temporary tracking flags
        for player in self.stats:
            for temp_key in [
                "vpip_counted_this_hand",
                "pfr_counted_this_hand",
                "3b_counted_this_hand",
                "f3b_counted_this_hand",
                "cbf_counted_this_hand",
                "wtsd_counted_this_hand",
                "saw_flop_this_hand"
            ]:
                if temp_key in self.stats[player]:
                    del self.stats[player][temp_key]

        # Save stats to file
        self.save_stats()
        self.logger.info("Stats updated and saved to file")

    def process_data_and_send(self):
        """Process current poker data and send to appropriate modules."""
        # Get all current data
        data = self.get_current_data()

        # Send to Open-Fold when new dealer
        dealer_seat, _ = self.get_dealer_seat_and_name()
        if dealer_seat != self.last_dealer_seat:
            data["dealer_seat"] = dealer_seat
            self.send_data_to_open_fold(data)

        # Send to Calculator when new street
        if self.current_street != data["street"]:
            self.send_data_to_calculator(data)

        # Always send to Bet Sizer (it needs real-time updates)
        self.send_data_to_bet_sizer(data)

        # Send to Stat Tracker at the end of each hand
        if dealer_seat != self.last_dealer_seat:
            self.send_data_to_stat_tracker()

    def run_tracking_loop(self, interval=1):
        """Main loop for tracking poker data."""
        try:
            self.logger.info("Starting poker data tracking...")

            while True:
                # Get dealer information
                self.get_dealer_seat_and_name()

                # Process and send data
                self.process_data_and_send()

                # Wait before checking again
                time.sleep(interval)

        except KeyboardInterrupt:
            self.logger.info("Tracking stopped by user.")
        except Exception as e:
            self.logger.error(f"Error in tracking loop: {str(e)}")
        finally:
            self.save_stats()
            if self.driver:
                self.driver.quit()
            self.logger.info("Tracking ended, stats saved.")


if __name__ == "__main__":
    # Create options for Chrome
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")

    # Create the data extractor
    extractor = PokerDataExtractor(options=chrome_options)

    # Initialize the extractor
    if extractor.initialize():
        # Set the hero's name (can be changed through command-line args in a more complex version)
        extractor.set_hero_name("YourUsername")  # Replace with your actual username

        # Navigate to the poker room
        poker_url = "https://www.pokernow.club/games/pgl5AEiLfXPzHUOqt_ZJgp4kE"  # Replace with your actual game URL
        if extractor.navigate_to(poker_url):
            # Run the tracking loop
            extractor.run_tracking_loop(interval=1)
