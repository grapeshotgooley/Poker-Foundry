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
    "calculator_input": "",
    "top_top": False,
    "nuts": False,
    "selected_player": "",
    "stats": {
        "VPIP": "0.0",
        "PFR": "0.0",
        "3B": "0.0",
        "F3B": "0.0",
        "CBF": "0.0",
        "WTSD": "0.0"
    },
    "win_percent": ".000",
    "tie_percent": ".000",
    "suggestion": "FOLD",
    "spr": "0.0",
    "bet_size": "0"
}

class FoundryOverlay(QMainWindow):
    def __init__(self):
        super().__init__()
        self.last_suggestion_args = None
        self.last_revealed_hands = {}

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
        self.timer.start(300)  # every .3 seconds

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

        def handle_hand_result(hand):
            self.browser.page().runJavaScript(self.get_players_js(),
                                              lambda players: self.display_hero_hand(hand, players))
            self.browser.page().runJavaScript(self.get_revealed_opponent_js(), self.display_opponent_hands)

        self.browser.page().runJavaScript(js_code_hand, handle_hand_result)

    def on_calculator_change(self):
        # Generate random float percentages (0.000 to 1.000)
        win = round(random.uniform(0, 1), 3)
        tie = round(random.uniform(0, 1), 3)

        # Format as string with 3 decimal places
        GLOBAL_STATE["win_percent"] = f"{win:.3f}"
        GLOBAL_STATE["tie_percent"] = f"{tie:.3f}"

        self.update_dynamic_labels()
        print("calculator change")

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
