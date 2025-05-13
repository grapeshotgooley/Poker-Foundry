import sys
import logging
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QHBoxLayout, QLabel, QWidget, QVBoxLayout, QSizePolicy,
    QLineEdit, QCheckBox, QFrame, QPushButton, QComboBox
)
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from foundry_open_fold import *
from foundry_calculator import *
from foundry_bet_sizer import *
from foundry_tracker import *

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# Global storage
GLOBAL_STATE = {
    "url_input": "",
    "special_hand_enabled": False,
    "special_hand_value": "",
    "suited_only": False,
    "hero_hand": "",
    "raises": 0,
    "hero_position": "",
    "button_seat": None,
    "hero_stack": 0.0,
    "pot_size": 0.0,
    "big_blind": 0.0,
    "active_players": [],
    "calculator_input": "",
    "top_top": False,
    "nuts": False,
    "selected_player": "",
    "community_cards": "",
    "stats": {
        "VPIP": "0.0",
        "PFR": "0.0",
        "3B": "0.0",
        "F3B": "0.0",
        "CBF": "0.0",
        "WTSD": "0.0"
    },
    "win_percent": "0.00",
    "tie_percent": "0.00",
    "suggestion": "FOLD",
    "spr": "0.0",
    "bet_size": "0"
}

class FoundryOverlay(QMainWindow):
    def __init__(self):
        super().__init__()
        self.last_suggestion_args = None
        self.last_revealed_hands = {}
        self.last_villain_bet = 0
        self.last_board_length = 0
        self.last_button_seat = None
        self.last_total_bet = 0

        screen = QApplication.primaryScreen().geometry()
        screen_width, screen_height = screen.width(), screen.height()

        self.previous_hand = None

        self.light_theme = """
           QMainWindow { background-color: white; color: black; }
           QPushButton { background-color: lightgray; color: black; }
           QLineEdit, QComboBox { background-color: white; color: black; }
           QLabel { color: black; }
        """

        self.dark_theme = """
           QMainWindow { background-color: #2e2e2e; color: white; }
           QPushButton { background-color: #444444; color: white; }
           QCheckBox{ color: white; }
           QLineEdit{ background-color: #555555; color: white; }
           QComboBox { background-color: #555555; color: black; }
           QLabel { background-color: #555555; color: white; }
        """

        self.is_dark_theme = False
        self.setGeometry(screen_width // 10, screen_height // 10, int(screen_width * 0.8), int(screen_height * 0.8))
        self.setWindowTitle("Foundry Overlay")

        self.dynamic_labels = {}

        central_widget = QWidget()
        layout = QHBoxLayout()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        button_layout_left, button_layout_right, center_layout = QVBoxLayout(), QVBoxLayout(), QVBoxLayout()
        top_input_layout = QHBoxLayout()

        left_button = QPushButton("New Game")
        left_button.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")

        def handle_new_game_click():
            current_text = self.url_input.text().strip()
            if current_text:
                self.load_url()
            else:
                self.url_input.setText("https://www.pokernow.club/start-game")
                self.load_url()

        left_button.clicked.connect(handle_new_game_click)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter Poker Now link and Press Enter")
        self.url_input.setStyleSheet("font-size: 16px; padding: 10px; text-align: center;")
        self.url_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.url_input.returnPressed.connect(self.load_url)
        self.url_input.textChanged.connect(lambda text: GLOBAL_STATE.update({"url_input": text}))

        self.theme_button = QPushButton("Dark Theme")
        self.theme_button.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        self.theme_button.clicked.connect(self.toggle_theme)

        top_input_layout.addWidget(left_button)
        top_input_layout.addWidget(self.url_input)
        top_input_layout.addWidget(self.theme_button)

        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold; text-align: center;")
        self.warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.browser = QWebEngineView()
        self.browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        center_layout.addLayout(top_input_layout)
        center_layout.addWidget(self.warning_label)
        center_layout.addWidget(self.browser, 1)

        def create_section(title_text, tooltip_text):
            section_container = QFrame()
            section_container.setFrameShape(QFrame.Shape.Box)
            section_container.setStyleSheet("padding: 10px; border: 2px solid black;")
            section_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

            section_layout = QVBoxLayout()
            section_container.setLayout(section_layout)
            section_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            title_layout = QHBoxLayout()
            title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            title = QLabel(title_text)
            title.setStyleSheet("font-size: 20px; font-weight: bold; text-align: center;")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)

            info_label = QLabel(" ℹ️")
            info_label.setStyleSheet("font-size: 16px; color: blue; cursor: pointer;")
            info_label.setToolTip(tooltip_text)

            title_layout.addWidget(title)
            title_layout.addWidget(info_label)
            section_layout.addLayout(title_layout)
            return section_container, section_layout

        with open('./how_to_use/open_fold.txt', 'r', encoding='utf-8') as f:
            open_fold_text = f.read()

        open_fold_container, open_fold_layout = create_section("Open-Fold", open_fold_text)
        self.special_hand_checkbox = QCheckBox("Special Hand")
        self.special_hand_checkbox.setStyleSheet("font-size: 16px; text-align: center;")
        self.special_hand_checkbox.stateChanged.connect(self.toggle_special_hand_options)
        self.special_hand_checkbox.stateChanged.connect(lambda state: GLOBAL_STATE.update({"special_hand_enabled": state == Qt.CheckState.Checked.value}))

        self.special_hand_input = QLineEdit()
        self.special_hand_input.setPlaceholderText("Enter hand")
        self.special_hand_input.setMaxLength(2)
        self.special_hand_input.setStyleSheet("font-size: 16px; text-align: center;")
        self.special_hand_input.setVisible(False)
        self.special_hand_input.textChanged.connect(lambda text: GLOBAL_STATE.update({"special_hand_value": text}))

        self.suited_checkbox = QCheckBox("Suited-Only")
        self.suited_checkbox.setStyleSheet("font-size: 16px; text-align: center;")
        self.suited_checkbox.setVisible(False)
        self.suited_checkbox.stateChanged.connect(lambda state: GLOBAL_STATE.update({"suited_only": state == Qt.CheckState.Checked.value}))

        open_fold_layout.addWidget(self.special_hand_checkbox)
        open_fold_layout.addWidget(self.special_hand_input)
        open_fold_layout.addWidget(self.suited_checkbox)
        button_layout_left.addWidget(open_fold_container, 1)

        # CALCULATOR SECTION
        with open('./how_to_use/calculator.txt', 'r', encoding='utf-8') as f:
            calculator_text = f.read()
        calculator_container, calculator_layout = create_section("Calculator", calculator_text)

        # Input field
        self.calculator_input = QLineEdit()
        self.calculator_input.setPlaceholderText("Enter hand")
        self.calculator_input.setMaxLength(4)
        self.calculator_input.setStyleSheet("font-size: 16px; text-align: center;")

        def on_calculator_input_changed(text):
            GLOBAL_STATE["calculator_input"] = text
            if text.strip():
                self.top_top_checkbox.blockSignals(True)
                self.nuts_checkbox.blockSignals(True)
                self.top_top_checkbox.setChecked(False)
                self.nuts_checkbox.setChecked(False)
                self.top_top_checkbox.blockSignals(False)
                self.nuts_checkbox.blockSignals(False)
            self.on_calculator_change()  # ✅ Added

        self.calculator_input.textChanged.connect(on_calculator_input_changed)

        # Top-Top Checkbox
        self.top_top_checkbox = QCheckBox("Top-Top")
        self.top_top_checkbox.setStyleSheet("font-size: 16px; text-align: center;")

        def on_top_top_checked(state):
            is_checked = state == Qt.CheckState.Checked.value
            GLOBAL_STATE["top_top"] = is_checked
            if is_checked:
                self.nuts_checkbox.blockSignals(True)
                self.nuts_checkbox.setChecked(False)
                self.nuts_checkbox.blockSignals(False)
                self.calculator_input.blockSignals(True)
                self.calculator_input.setText("")
                self.calculator_input.blockSignals(False)
            self.on_calculator_change()  # ✅ Added

        self.top_top_checkbox.stateChanged.connect(on_top_top_checked)

        # Nuts Checkbox
        self.nuts_checkbox = QCheckBox("Nuts")
        self.nuts_checkbox.setStyleSheet("font-size: 16px; text-align: center;")

        def on_nuts_checked(state):
            is_checked = state == Qt.CheckState.Checked.value
            GLOBAL_STATE["nuts"] = is_checked
            if is_checked:
                self.top_top_checkbox.blockSignals(True)
                self.top_top_checkbox.setChecked(False)
                self.top_top_checkbox.blockSignals(False)
                self.calculator_input.blockSignals(True)
                self.calculator_input.setText("")
                self.calculator_input.blockSignals(False)
            self.on_calculator_change()

        self.nuts_checkbox.stateChanged.connect(on_nuts_checked)

        calculator_layout.addWidget(self.calculator_input)
        calculator_layout.addWidget(self.top_top_checkbox)
        calculator_layout.addWidget(self.nuts_checkbox)
        calculator_layout.addLayout(self.create_sizer_row("WIN %:", GLOBAL_STATE["win_percent"]))
        calculator_layout.addLayout(self.create_sizer_row("TIE %:", GLOBAL_STATE["tie_percent"]))
        open_fold_layout.addLayout(self.create_sizer_row("SUGGESTION:", GLOBAL_STATE["suggestion"]))
        button_layout_left.addWidget(calculator_container, 1)

        with open('./how_to_use/bet_sizer.txt', 'r', encoding='utf-8') as f:
            sizer_text = f.read()
        bet_sizer_container, bet_sizer_layout = create_section("Bet Sizer", sizer_text)
        bet_sizer_layout.addLayout(self.create_sizer_row("SPR:", GLOBAL_STATE["spr"]))
        bet_sizer_layout.addLayout(self.create_sizer_row("Bet Size:", GLOBAL_STATE["bet_size"]))
        button_layout_right.addWidget(bet_sizer_container, 1)

        with open('./how_to_use/tracker.txt', 'r', encoding='utf-8') as f:
            tracker_text = f.read()
        stat_tracker_container, stat_tracker_layout = create_section("Stat Tracker", tracker_text)
        stats_layout = QVBoxLayout()

        self.player_selector = QComboBox()
        self.player_selector.addItems([f"Player {i}" for i in range(1, 9)])
        self.player_selector.setStyleSheet("font-size: 18px; padding: 8px; background-color: white; border: 2px solid black;")
        self.player_selector.currentTextChanged.connect(lambda text: GLOBAL_STATE.update({"selected_player": text}))
        stats_layout.addWidget(self.player_selector)

        for stat in GLOBAL_STATE["stats"].keys():
            stats_layout.addLayout(self.create_sizer_row(f"{stat} %:", GLOBAL_STATE["stats"][stat]))

        stat_tracker_layout.addLayout(stats_layout)
        button_layout_right.addWidget(stat_tracker_container, 1)

        layout.addLayout(button_layout_left, 1)
        layout.addLayout(center_layout, 2)
        layout.addLayout(button_layout_right, 1)
        layout.setContentsMargins(5, 5, 5, 5)

        # Polling Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_game_state)
        self.timer.start(500)  # every .5 seconds

    def poll_game_state(self):
        js_code_hand = """
        (() => {
            const youPlayer = document.querySelector('.you-player');
            if (!youPlayer) return [];
            const cards = youPlayer.querySelectorAll('.card');
            const hand = [...cards].map(card => {
                const val = card.querySelector('.value')?.innerText.trim() || "";
                const suit = card.querySelector('.suit')?.innerText.trim() || "";
                return val + suit;
            });
            return hand.filter(x => x);
        })()
        """

        def handle_hand_result(hero_hand):
            self.browser.page().runJavaScript(self.get_players_js(),
                                              lambda players: self.display_hero_hand(hero_hand, players)
                                              )
            self.browser.page().runJavaScript(self.get_revealed_opponent_js(), self.display_opponent_hands)
            self.browser.page().runJavaScript(self.get_community_cards_js(), self.handle_community_cards)
            self.browser.page().runJavaScript(self.get_hero_stack_js(), self.handle_hero_stack)
            self.browser.page().runJavaScript(self.get_big_blind_js(), self.handle_big_blind_result)
            self.browser.page().runJavaScript(self.get_button_seat_js(), self.handle_button_seat)

        self.browser.page().runJavaScript(js_code_hand, handle_hand_result)
        self.check_game_type()
        self.update_bet_sizer()
        self.get_active_players_js()
        self.extract_pot_size()

    def handle_hero_stack(self, result):
        try:
            stack = float(result.replace(',', '')) if result else 0.0
            GLOBAL_STATE["hero_stack"] = stack
        except Exception as e:
            logging.error(f"Error parsing hero stack: {e}")

    def disable_modules(self):
        self.special_hand_checkbox.setEnabled(False)
        self.special_hand_input.setEnabled(False)
        self.suited_checkbox.setEnabled(False)
        self.calculator_input.setEnabled(False)
        self.top_top_checkbox.setEnabled(False)
        self.nuts_checkbox.setEnabled(False)
        self.player_selector.setEnabled(False)

    def enable_modules(self):
        self.special_hand_checkbox.setEnabled(True)
        self.special_hand_input.setEnabled(self.special_hand_checkbox.isChecked())
        self.suited_checkbox.setEnabled(self.special_hand_checkbox.isChecked())
        self.calculator_input.setEnabled(True)
        self.top_top_checkbox.setEnabled(True)
        self.nuts_checkbox.setEnabled(True)
        self.player_selector.setEnabled(True)

    def get_big_blind_js(self):
        return """
        (() => {
            const values = document.querySelectorAll('div span.normal-value');
            if (values.length >= 2) {
                return parseFloat(values[1].innerText.trim());
            }
            return null;
        })()
        """

    def get_button_seat_js(self):
        return """
        (() => {
            const btn = document.querySelector('.dealer-button-ctn');
            if (!btn) return null;
            const match = btn.className.match(/dealer-position-(\\d+)/);
            return match ? parseInt(match[1]) : null;
        })()
        """

    def get_active_players_js(self):
        js = """
        (() => {
            const results = [];
            const players = document.querySelectorAll('.table-player');
            players.forEach((playerDiv, idx) => {
                const classList = playerDiv.className;
                const folded = classList.includes('fold');
                if (folded) return;

                const isHero = classList.includes('you-player');
                const seatMatch = classList.match(/table-player-(\\d+)/);
                const seat = seatMatch ? parseInt(seatMatch[1]) : idx + 1;

                const nameTag = playerDiv.querySelector('.table-player-name a');
                const name = nameTag ? nameTag.innerText.trim() : `Seat ${seat}`;

                const stackTag = playerDiv.querySelector('.table-player-stack .normal-value');
                const stack = stackTag ? parseFloat(stackTag.innerText.trim()) : 0.0;

                const betTag = playerDiv.querySelector('.table-player-bet-value .normal-value');
                const lastBet = betTag ? parseFloat(betTag.innerText.trim()) : 0.0;

                results.push({
                    name,
                    seat,
                    stack,
                    last_bet: lastBet,
                    is_hero: isHero
                });
            });
            return results;
        })()
        """
        self.browser.page().runJavaScript(js, self.handle_active_players)

    def get_hero_stack_js(self):
        return """
        (() => {
            const stackEl = document.querySelector('.table-player.you-player .table-player-stack .normal-value');
            return stackEl ? stackEl.innerText.trim() : '';
        })()
        """

    def check_game_type(self):
        js = """
        (() => {
            const typeSpan = document.querySelector('.game-type-ctn .current-type');
            return typeSpan ? typeSpan.innerText.trim() : '';
        })()
        """

        def handle_game_type(result):
            if result and result != "NLH":
                self.warning_label.setText(f"❌ Wrong game type: {result}")
                self.disable_modules()
            elif result == "NLH":
                self.warning_label.setText("")
                self.enable_modules()
            # else: result is empty → no game loaded yet, do nothing

        self.browser.page().runJavaScript(js, handle_game_type)

    def handle_button_seat(self, seat_number):
        if seat_number is not None:
            GLOBAL_STATE["button_seat"] = seat_number
            #logging.info(f"Button is at seat {seat_number}")
        else:
            logging.warning("Could not determine button seat.")

    def handle_active_players(self, players):
        if isinstance(players, list):
            GLOBAL_STATE["active_players"] = players
            #logging.info("Updated active players:")
            #for p in players:
            #    logging.info(p)

    def extract_pot_size(self):
        js = """
        (() => {
            const el = document.querySelector('.table-pot-size .main-value .normal-value');
            return el ? el.innerText.trim() : null;
        })()
        """

        def handle_pot_size(value):
            try:
                if value is not None:
                    GLOBAL_STATE["pot_size"] = float(value)
                   # print(f"Pot Size: {GLOBAL_STATE['pot_size']}")
                else:
                    GLOBAL_STATE["pot_size"] = 0.0
                  #  print("Pot Size not found.")
            except Exception as e:
                logging.error(f"Error extracting pot size: {e}")
                GLOBAL_STATE["pot_size"] = 0.0

        self.browser.page().runJavaScript(js, handle_pot_size)

    def handle_big_blind_result(self, result):
        if result is not None:
            GLOBAL_STATE["big_blind"] = float(result)
           # print(f"Big Blind set to: {GLOBAL_STATE['big_blind']}")
        else:
            logging.warning("Big Blind value not found.")

    def update_bet_sizer(self):
        # --- Safe expand helper ---
        VALID_RANKS = {"2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"}
        VALID_SUITS = {"C", "D", "H", "S"}

        def expand(card_str):
            if len(card_str) == 3 and card_str.startswith("10"):
                rank = "10"
                suit = card_str[2]
            elif len(card_str) == 2:
                rank = '10' if card_str[0] == 'T' else card_str[0]
                suit = card_str[1]
            else:
                return None
            rank = rank.upper()
            suit = suit.upper()
            if rank not in VALID_RANKS or suit not in VALID_SUITS:
                return None
            return rank + suit

        # --- Parse board ---
        board_raw = GLOBAL_STATE.get("community_cards", "").upper()
        if len(board_raw) % 2 != 0:
            return

        board_strs = [expand(board_raw[i:i + 2]) for i in range(0, len(board_raw), 2)]
        if any(card is None for card in board_strs):
            return

        board = [Card(s) for s in board_strs]
        board_length = len(board)
        street = "preflop" if board_length == 0 else "postflop"

        hero_stack = GLOBAL_STATE.get('hero_stack', 0.0)
        active_players = GLOBAL_STATE.get("active_players", [])
        non_hero_players = [p for p in active_players if not p.get("is_hero")]
        villain_stack = min((p.get("stack", float("inf")) for p in non_hero_players), default=0)

        pot_size = GLOBAL_STATE.get("pot_size", 0)
        big_blind = GLOBAL_STATE["big_blind"]
        last_villain_bet = max((p.get("last_bet", 0) for p in non_hero_players), default=0)
        if last_villain_bet <= big_blind:
            last_villain_bet = 0

        multiway = len(active_players) > 2
        last_bet = max((p.get("last_bet", 0) for p in active_players), default=0)

        current_board_length = len(GLOBAL_STATE.get("community_cards", ""))
        current_button_seat = GLOBAL_STATE.get("button_seat", None)
        current_villain_bet = last_villain_bet

        if current_board_length != self.last_board_length or current_button_seat != self.last_button_seat:
            GLOBAL_STATE["raises"] = 0
        elif last_bet > getattr(self, "last_total_bet", 0):
            GLOBAL_STATE["raises"] += 1

        self.last_total_bet = last_bet
        self.last_villain_bet = current_villain_bet
        self.last_board_length = current_board_length
        self.last_button_seat = current_button_seat
        raises = GLOBAL_STATE["raises"]

        postflop_street = (
            "N/A" if board_length == 0
            else "flop" if board_length == 3
            else "turn" if board_length == 4
            else "river" if board_length >= 5
            else "unknown"
        )

        position_order = ["sb", "bb", "utg-1", "utg", "utg+1", "utg+2", "lj", "hj", "co", "btn"]
        hero_position_str = GLOBAL_STATE.get("hero_position", "").lower()
        hero_position = position_order.index(hero_position_str) + 1 if hero_position_str in position_order else 1

        hero_seat = next((p.get("seat") for p in active_players if p.get("is_hero")), None)
        villain = max(non_hero_players, key=lambda p: p.get("last_bet", 0), default=None)
        button_seat = GLOBAL_STATE.get("button_seat")

        if hero_seat and villain and button_seat:
            villain_seat = villain["seat"]
            seat_order = [(button_seat + i - 1) % 10 + 1 for i in range(1, 11)]
            hero_index = seat_order.index(hero_seat)
            villain_index = seat_order.index(villain_seat)
            GLOBAL_STATE["in_position"] = hero_index > villain_index
        else:
            GLOBAL_STATE["in_position"] = False

        args = (
            street, hero_stack, villain_stack, pot_size, raises, last_bet,
            big_blind, multiway, postflop_street, hero_position, GLOBAL_STATE["in_position"]
        )

        if getattr(self, "last_bet_sizer_args", None) != args:
            spr, bet_size = calculate_spr_and_bet(*args)
            GLOBAL_STATE["spr"] = f"{spr:.2f}"
            GLOBAL_STATE["bet_size"] = bet_size
            self.last_bet_sizer_args = args
            self.update_dynamic_labels()
            print(f'📏 Bet Sizer Updated: SPR={spr:.2f}, Bet Size={bet_size}')

    def on_calculator_change(self):
        try:
            # --- Safe expand helper ---
            VALID_RANKS = {"2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"}
            VALID_SUITS = {"C", "D", "H", "S"}

            def expand(card_str):
                if len(card_str) == 3 and card_str.startswith("10"):
                    rank = "10"
                    suit = card_str[2]
                elif len(card_str) == 2:
                    rank = '10' if card_str[0] == 'T' else card_str[0]
                    suit = card_str[1]
                else:
                    return None
                rank = rank.upper()
                suit = suit.upper()
                if rank not in VALID_RANKS or suit not in VALID_SUITS:
                    return None
                return rank + suit

            # --- Parse board ---
            board_raw = GLOBAL_STATE.get("community_cards", "").upper()
            if len(board_raw) % 2 != 0:
                logging.warning(f"Invalid community card string: '{board_raw}'")
                return

            board_strs = [expand(board_raw[i:i + 2]) for i in range(0, len(board_raw), 2)]

            if any(card is None for card in board_strs):
                logging.warning(f"Invalid board cards: {board_strs}")
                GLOBAL_STATE["win_percent"] = "0.00"
                GLOBAL_STATE["tie_percent"] = "0.00"
                self.update_dynamic_labels()
                return

            board = [Card(s) for s in board_strs]

            # --- Suit setup for override logic ---
            suits_on_board = [s[-1] for s in board_strs if s]
            all_suits = ["C", "D", "H", "S"]
            suit_counts = {s: suits_on_board.count(s) for s in all_suits}
            least_used_suits = sorted(suit_counts.items(), key=lambda x: x[1])
            min_count = least_used_suits[0][1]
            least_suits = [s for s, count in least_used_suits if count == min_count]

            def pick_least_used_suit(exclude=None):
                import random
                choices = [s for s in least_suits if s != exclude] if exclude else least_suits
                return random.choice(choices) if choices else random.choice(all_suits)

            villain_strs = None  # default

            # --- Nuts override ---
            if self.nuts_checkbox.isChecked():
                logging.info("Nuts mode enabled for villain")

                if board_strs:
                    try:
                        best_hole = best_possible_hole_cards(board_strs)
                        if best_hole:
                            villain_strs = [best_hole[0].__str__().upper(), best_hole[1].__str__().upper()]
                            logging.info(f"Best possible villain hole cards: {villain_strs}")
                        else:
                            raise ValueError("best_hole was None")
                    except Exception as e:
                        logging.warning(f"Nuts fallback due to error: {e}")
                        villain_strs = [
                            'A' + pick_least_used_suit(),
                            'A' + pick_least_used_suit()
                        ]
                else:
                    villain_strs = [
                        'A' + pick_least_used_suit(),
                        'A' + pick_least_used_suit()
                    ]
                logging.info(f"Overriding villain hand with NUTS: {villain_strs}")


            # --- Top-Top override ---
            elif self.top_top_checkbox.isChecked():
                logging.info("Top-Top mode enabled for villain")

                if board_strs:
                    rank_order = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
                    board_ranks = [card[:-1] for card in board_strs]

                    if "A" in board_ranks:
                        chosen_suit = pick_least_used_suit()
                        villain_strs = [
                            'A' + chosen_suit,
                            'K' + chosen_suit
                        ]
                        logging.info(f"Top-Top override with AK suited: {villain_strs}")
                    else:
                        top_rank = max(board_ranks, key=lambda r: rank_order.index(r))
                        villain_strs = [
                            'A' + pick_least_used_suit(),
                            top_rank + pick_least_used_suit(exclude='A')
                        ]
                        logging.info(f"Top-Top override with A + top board rank: {villain_strs}")
                else:
                    villain_strs = [
                        'A' + pick_least_used_suit(),
                        'A' + pick_least_used_suit()
                    ]
                    logging.info(f"Top-Top override default AA: {villain_strs}")

            # --- Manual calculator input fallback ---
            if villain_strs is None:
                raw = GLOBAL_STATE.get("calculator_input", "").upper()
                if len(raw) != 4:
                    logging.warning(f"Invalid calculator input length: '{raw}'")
                    return

                v1, v2 = raw[:2], raw[2:4]
                villain_strs = [expand(v1), expand(v2)]
                logging.info(f"Villain strings from input: {villain_strs}")

            # --- Final validation ---
            if None in villain_strs:
                logging.warning(f"Invalid villain card detected: {villain_strs}")
                GLOBAL_STATE["win_percent"] = "0.00"
                GLOBAL_STATE["tie_percent"] = "0.00"
                self.update_dynamic_labels()
                return

            villain = [Card(s) for s in villain_strs]

            # --- Hero parsing ---
            hero_cards = GLOBAL_STATE.get("hero_hand", [])
            if not isinstance(hero_cards, list) or len(hero_cards) != 2:
                logging.warning(f"Invalid hero_hand in GLOBAL_STATE: '{hero_cards}'")
                return

            hero_strs = [expand(hero_cards[0]), expand(hero_cards[1])]
            if None in hero_strs:
                logging.warning(f"Invalid hero cards: {hero_strs}")
                return

            hero = [Card(s) for s in hero_strs]

            # --- Evaluation ---
            win = get_hero_win_rate(hero, villain, board)
            tie = get_hero_tie_rate(hero, villain, board)

            GLOBAL_STATE["win_percent"] = f"{win * 100:.2f}"
            GLOBAL_STATE["tie_percent"] = f"{tie * 100:.2f}"

            self.update_dynamic_labels()
            print("calculator change")

        except Exception as e:
            logging.error(f"Error in on_calculator_change: {e}")

    def get_community_cards_js(self):
        return """
        (() => {
            const cards = document.querySelectorAll('.table-cards.run-1 .card');
            const result = [...cards].map(card => {
                const val = card.querySelector('.value')?.innerText.trim() || "";
                const suit = card.querySelector('.suit')?.innerText.trim() || "";
                return val + suit;
            });
            return result.filter(c => c);
        })()
        """

    def get_revealed_opponent_js(self):
        return """
        (() => {
            const players = document.querySelectorAll('.table-player');
            const revealedOpponents = [];

            players.forEach(player => {
                if (player.classList.contains('you-player')) return;

                const cards = player.querySelectorAll('.card-container.flipped .card');
                if (cards.length !== 2) return;

                const hand = [...cards].map(card => {
                    const val = card.querySelector('.value')?.innerText.trim() || "";
                    const suit = card.querySelector('.suit')?.innerText.trim() || "";
                    return val + suit;
                });

                const name = player.querySelector('.table-player-name a')?.innerText || "Unknown";
                revealedOpponents.push({ name, hand });
            });

            return revealedOpponents;
        })()
        """

    def get_players_js(self):
        return """
        (() => {
            try {
                const seats = [...document.querySelectorAll('.table-player')];
                const players = seats.map(seat => {
                    const classList = seat.className;
                    const seatMatch = classList.match(/table-player-(\\d+)/);
                    const seatIndex = seatMatch ? parseInt(seatMatch[1]) : -1;

                    const isHero = classList.includes("you-player");
                    const isWaiting = seat.querySelector('.waiting-next-hand') !== null;

                    const nameEl = seat.querySelector('.table-player-name a');
                    const name = nameEl ? nameEl.innerText.trim() : "";

                    const isDealer = document.querySelector(`.dealer-button-ctn.dealer-position-${seatIndex}`) !== null;

                    const cards = isHero
                        ? [...seat.querySelectorAll('.card')].map(card => {
                            const val = card.querySelector('.value')?.innerText.trim() || "";
                            const suit = card.querySelector('.suit')?.innerText.trim() || "";
                            return val + suit;
                        }).filter(c => c)
                        : [];

                    return {
                        seatIndex,
                        isHero,
                        isDealer,
                        isWaiting,
                        name,
                        cards
                    };
                });

                return players.filter(p => p.seatIndex !== -1 && !p.isWaiting);
            } catch (err) {
                return { error: err.toString() };
            }
        })()
        """

    def process_players(self, players):
        if isinstance(players, dict) and "error" in players:
            return "error"

        if not players:
            return "none"

        players.sort(key=lambda p: p.get("seatIndex", -1))

        hero = next((p for p in players if p.get("isHero")), None)
        dealer = next((p for p in players if p.get("isDealer")), None)

        if not hero or not dealer:
            return "none"

        dealer_idx = players.index(dealer)
        rotated_players = players[dealer_idx:] + players[:dealer_idx]
        total = len(rotated_players)

        if total == 2:
            positions = ["SB", "BB"]
            for i, player in enumerate(rotated_players):
                player["position"] = positions[i]
        else:
            for p in players:
                p["position"] = "Unknown"
            dealer["position"] = "BTN"

            non_dealers = [p for p in rotated_players if p != dealer]
            reversed_priority = ["UTG-1", "UTG", "UTG+1", "UTG+2", "LJ", "HJ", "CO"]
            needed_positions = ["SB", "BB"] + reversed_priority[-(len(non_dealers) - 2):]
            for i, p in enumerate(non_dealers):
                if i < len(needed_positions):
                    p["position"] = needed_positions[i]

        hero_position = next((p["position"] for p in players if p.get("isHero")), "Unknown")
        # ✅ Update GLOBAL_STATE
        GLOBAL_STATE["hero_position"] = hero_position.lower()

        return hero_position.lower()

    def display_opponent_hands(self, hands):
        if not hasattr(self, "last_revealed_hands"):
            self.last_revealed_hands = {}

        if not hands:
            return

        for player in hands:
            try:
                name = player.get("name", "Unknown")
                cards_list = player.get("hand", [])
                cards_str = " ".join(cards_list)

                # Only act if the hand is new or changed
                if self.last_revealed_hands.get(name) != cards_str:
                    logging.info(f"{name} revealed: {cards_str}")
                    self.last_revealed_hands[name] = cards_str

                    # ✅ Normalize to all caps and convert 10 to T
                    def normalize(card):
                        rank, suit = card[:-1], card[-1]
                        rank = 'T' if rank == '10' else rank.upper()
                        suit = suit.upper()
                        return rank + suit

                    normalized = [normalize(card) for card in cards_list]
                    condensed = "".join(normalized)  # e.g., AHTD
                    GLOBAL_STATE["calculator_input"] = condensed
                    self.calculator_input.setText(condensed)
                    self.on_calculator_change()

            except Exception as e:
                logging.error(f"Error processing opponent hand: {e}")

    def handle_community_cards(self, cards):
        try:
            def normalize(card):
                rank, suit = card[:-1], card[-1]
                rank = 'T' if rank == '10' else rank.upper()
                suit = suit.upper()
                return rank + suit

            normalized = [normalize(card) for card in cards]
            condensed = "".join(normalized)

            if GLOBAL_STATE.get("community_cards") != condensed:
                GLOBAL_STATE["community_cards"] = condensed
                self.on_calculator_change()  # ✅ Trigger update
        except Exception as e:
            logging.error(f"Error processing community cards: {e}")

    def display_hero_hand(self, hand, players):
        if not hand or len(hand) != 2:
            return

        card1, card2 = hand
        if len(card1) < 2 or len(card2) < 2:
            return

        hand_str = " ".join(hand)
        if hand_str != self.previous_hand:
            self.previous_hand = hand_str

        try:
            def normalize(card):
                rank, suit = card[:-1], card[-1]
                rank = 'T' if rank == '10' else rank.upper()
                return rank, suit

            rank1, suit1 = normalize(card1)
            rank2, suit2 = normalize(card2)

            valid_ranks = '23456789TJQKA'
            if rank1 not in valid_ranks or rank2 not in valid_ranks:
                raise ValueError(f"Invalid rank: {rank1} or {rank2}")

            def rank_value(r):
                return valid_ranks.index(r)

            # Normalize rank order
            if rank_value(rank1) < rank_value(rank2):
                rank1, rank2 = rank2, rank1
                suit1, suit2 = suit2, suit1

            suited = suit1 == suit2
            condensed_hand = f"{rank1}{rank2}{'s' if suited else 'o'}"

            special_on = GLOBAL_STATE["special_hand_enabled"]
            suited_only = GLOBAL_STATE["suited_only"]
            special_hand = GLOBAL_STATE["special_hand_value"].upper()
            pos = self.process_players(players)
            if pos == "utg-1":
                pos = "utg"

            # Prepare arguments
            args = (condensed_hand, pos, special_on, special_hand, suited_only)

            # Check if inputs changed
            if args != self.last_suggestion_args:
                result = should_play_hand(*args)
                suggestion = result.upper()
                GLOBAL_STATE["suggestion"] = suggestion
                GLOBAL_STATE["hero_hand"] = [card1.upper(), card2.upper()]
                self.on_calculator_change()
                self.update_dynamic_labels()
                print(f"{condensed_hand} in {pos.upper()} → {suggestion}")
                self.last_suggestion_args = args


        except Exception as e:
            print(f"Error processing hand: {e}")
            GLOBAL_STATE["suggestion"] = "ERROR"

    def update_dynamic_labels(self):
        key_mapping = {
            "win_%": "win_percent",
            "tie_%": "tie_percent"
        }

        for key, label in self.dynamic_labels.items():
            real_key = key_mapping.get(key, key)  # Remap if needed
            if real_key in GLOBAL_STATE:
                label.setText(str(GLOBAL_STATE[real_key]))
            elif real_key.upper() in GLOBAL_STATE.get("stats", {}):
                label.setText(str(GLOBAL_STATE["stats"][real_key.upper()]))

    def toggle_special_hand_options(self, state):
        checked = state == Qt.CheckState.Checked.value
        self.special_hand_input.setVisible(checked)
        self.suited_checkbox.setVisible(checked)

    def toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        self.theme_button.setText("Light Theme" if self.is_dark_theme else "Dark Theme")
        self.apply_theme()

    def apply_theme(self):
        self.setStyleSheet(self.dark_theme if self.is_dark_theme else self.light_theme)

    def load_url(self):
        url_text = self.url_input.text().strip()
        if url_text.startswith("https://www.pokernow.club"):
            self.warning_label.setText("")
            self.browser.setUrl(QUrl(url_text))
            self.browser.settings().setAttribute(
                QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True
            )
        else:
            self.warning_label.setText("❌ Invalid URL! Please enter a valid Poker Now link.")

    def create_sizer_row(self, label_text, value_text):
        layout = QHBoxLayout()
        label = QLabel(label_text)
        value = QLabel(value_text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 16px; font-weight: bold; text-align: center; padding: 5px;")
        value.setStyleSheet(
            "font-size: 16px; background-color: #f0f0f0; border: 1px solid gray; padding: 5px; text-align: center; color: black;")
        layout.addWidget(label)
        layout.addWidget(value)

        # Normalize the label_text into a key like "suggestion", "win_percent"
        key = label_text.strip().replace(":", "").replace(" ", "_").lower()
        self.dynamic_labels[key] = value

        return layout


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FoundryOverlay()
    window.show()
    sys.exit(app.exec())
