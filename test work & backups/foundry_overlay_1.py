import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QHBoxLayout, QLabel, QWidget, QVBoxLayout, QSizePolicy,
    QLineEdit, QCheckBox, QFrame, QPushButton, QComboBox
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView


class FoundryOverlay(QMainWindow):
    def __init__(self):
        super().__init__()

        # Get screen size
        screen = QApplication.primaryScreen().geometry()
        screen_width = screen.width()
        screen_height = screen.height()
        # Define light and dark theme styles
        self.light_theme = """
               QMainWindow {
                   background-color: white;
                   color: black;
               }
               QPushButton {
                   background-color: lightgray;
                   color: black;
               }
               QLineEdit, QComboBox {
                   background-color: white;
                   color: black;
               }
               QLabel {
                   color: black;
               }
               """

        self.dark_theme = """
               QMainWindow {
                   background-color: #2e2e2e;
                   color: white;
               }
               QPushButton {
                   background-color: #444444;
                   color: white;
               }
               QCheckBox{
                   color: white;
               }
               QLineEdit{
                   background-color: #555555;
                   color: white;
               }
               QComboBox {
                   background-color: #555555;
                   color: black;
               }
               QLabel {
                   background-color: #555555;
                   color: white;
               }
               """

        # Initialize theme state
        self.is_dark_theme = False

        # Set window size (80% of screen)
        self.setGeometry(
            screen_width // 10,
            screen_height // 10,
            int(screen_width * 0.8),
            int(screen_height * 0.8)
        )
        self.setWindowTitle("Foundry Overlay")

        # Main layout
        central_widget = QWidget()
        layout = QHBoxLayout()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Create layouts
        button_layout_left = QVBoxLayout()
        button_layout_right = QVBoxLayout()
        center_layout = QVBoxLayout()

        # URL Input with two side buttons
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
        self.url_input.returnPressed.connect(self.load_url)
        self.url_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.theme_button = QPushButton("Dark Theme")
        self.theme_button.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        self.theme_button.clicked.connect(self.toggle_theme)

        top_input_layout.addWidget(left_button)
        top_input_layout.addWidget(self.url_input)
        top_input_layout.addWidget(self.theme_button)

        # Warning label
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold; text-align: center;")
        self.warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Browser
        self.browser = QWebEngineView()
        self.browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        center_layout.addLayout(top_input_layout)
        center_layout.addWidget(self.warning_label)
        center_layout.addWidget(self.browser, 1)

        # Function to create sections
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

        # Open-Fold Section
        open_fold_container, open_fold_layout = create_section("Open-Fold", """How to Use
The Open-Fold Suggester analyzes your current hand and recommends whether to open or fold preflop when the pot is unopened. If you have a favorite hand or are playing a variant like 7-2, you can check Special Hand to always include it in your range. Use Suited Only to limit your opening range to suited versions of that hand.

How It’s Calculated
The suggester uses slightly adjusted preflop charts optimized for exploitation, then applies randomization to generate recommendations. If Special Hand is enabled, it shifts your range strategically to include that hand while maintaining a near-optimal balance and minimizing exploitability—particularly in 7-2 games. These charts are adapted for 100BB+ (deep stack) cash game NLH. For games with lower stack depth remember that tighter more aggressive strategies are better.""")

        self.special_hand_checkbox = QCheckBox("Special Hand")
        self.special_hand_checkbox.setStyleSheet("font-size: 16px; text-align: center;")
        self.special_hand_checkbox.stateChanged.connect(self.toggle_special_hand_options)

        self.special_hand_input = QLineEdit()
        self.special_hand_input.setPlaceholderText("Enter hand")
        self.special_hand_input.setMaxLength(2)
        self.special_hand_input.setStyleSheet("font-size: 16px; text-align: center;")
        self.special_hand_input.setVisible(False)

        self.suited_checkbox = QCheckBox("Suited-Only")
        self.suited_checkbox.setStyleSheet("font-size: 16px; text-align: center;")
        self.suited_checkbox.setVisible(False)

        #open_fold_layout.addWidget(open_fold_display)
        open_fold_layout.addWidget(self.special_hand_checkbox)
        open_fold_layout.addWidget(self.special_hand_input)
        open_fold_layout.addWidget(self.suited_checkbox)
        button_layout_left.addWidget(open_fold_container, 1)

        # Calculator Section (Fully Restored)
        calculator_container, calculator_layout = create_section("Calculator", """How to Use
This tool calculates poker odds, showing your Win % (chance of winning) and Tie % (chance of tying) against an inputted hand. You can quickly populate the opponent’s hand using the Top-Top or Nuts checkboxes, helping you evaluate matchups within their range. If your opponent’s hand is revealed, the input updates automatically.

How It's Calculated
This tool uses sampling-based approximation rather than full enumeration, introducing slight variance in probability estimates. Accuracy decreases when fewer community cards remain unknown, as the reduced number of possible outcomes makes random sampling less precise.""")
        calculator_input = QLineEdit()
        calculator_input.setPlaceholderText("Enter hand")
        calculator_input.setMaxLength(4)
        calculator_input.setStyleSheet("font-size: 16px; text-align: center;")

        bet_sizer_container, bet_sizer_layout = create_section("Bet Sizer", "Calculate optimal bet sizing.")

        self.top_top_checkbox = QCheckBox("Top-Top")
        self.top_top_checkbox.setStyleSheet("font-size: 16px; text-align: center;")

        self.nuts_checkbox = QCheckBox("Nuts")
        self.nuts_checkbox.setStyleSheet("font-size: 16px; text-align: center;")

        calculator_layout.addWidget(calculator_input)
        calculator_layout.addWidget(self.top_top_checkbox)
        calculator_layout.addWidget(self.nuts_checkbox)
        button_layout_left.addWidget(calculator_container, 1)

        calculator_layout.addLayout(self.create_sizer_row("WIN %:", ".645"))
        calculator_layout.addLayout(self.create_sizer_row("TIE %:", ".005"))

        open_fold_layout.addLayout(self.create_sizer_row("SUGGESTION:", "OPEN"))

        # Bet Sizer Section
        bet_sizer_container, bet_sizer_layout = create_section("Bet Sizer", """How to Use
The Bet Sizer suggests how much to bet in a given situation if you choose to bet, incorporating randomization and always rounding to a whole number. It does not indicate whether you should bet but provides sizing recommendations, including raises. The stack-to-pot ratio (SPR) is the primary factor influencing bet sizing, and it is displayed to help players evaluate both their own and their opponent’s bet sizes more effectively. This tool is less useful in microstakes due to its rounding adjustments. Keep in mind, this tool doesn't examine your hand or the board. In scenarios where the board is more dynamic or you would like to polarize your range more you should select your own bet size.

How It’s Calculated
Different betting scenarios—such as preflop, postflop, or low SPR spots—use distinct formulas to determine an exact bet size. Once the bet is calculated, a differential formula introduces slight randomization, making your bets less predictable and harder for opponents to exploit. The final suggested bet reflects this adjustment, ensuring a more balanced and deceptive betting strategy.""")
        bet_sizer_layout.addLayout(self.create_sizer_row("SPR:", "0.9"))
        bet_sizer_layout.addLayout(self.create_sizer_row("Bet Size:", "23"))
        button_layout_right.addWidget(bet_sizer_container, 1)

        # Stat Tracker Section (With Dropdown)
        stat_tracker_container, stat_tracker_layout = create_section("Stat Tracker", """How to Use
Select a player from the dropdown to view their stats, with your own stats displayed at the top. The tracker provides key preflop and postflop tendencies, including VPIP%, which measures how often a player voluntarily puts money into the pot, and PFR%, which shows how frequently they raise preflop. It also tracks 3B%, indicating how often they three-bet, and F3B%, which reflects how often they fold to a three-bet. Postflop stats include CBF%, measuring how often a player continuation bets after being the preflop aggressor, and WTSD%, showing how often they go to showdown after seeing the flop.

How It’s Calculated
At the end of each hand, all player actions are logged and used to update their stats in real time. The data is session-specific, meaning the stats reflect only the hands played during the current session. If a player swaps seats but keeps the same name, the tracker assumes they are the same player.""")

        stats_layout = QVBoxLayout()

        # **Player Dropdown**
        self.player_selector = QComboBox()
        self.player_selector.addItems([f"Player {i}" for i in range(1, 9)])
        self.player_selector.setStyleSheet("""
            font-size: 18px; 
            padding: 8px;
            background-color: white;
            border: 2px solid black;
            selection-background-color: lightgray;
        """)
        stats_layout.addWidget(self.player_selector)

        # **Player Stats**
        stats_labels = ["VPIP %:", "PFR %:", "3B %:", "F3B %:", "CBF %:", "WTSD %:"]
        for label_text in stats_labels:
            stats_layout.addLayout(self.create_sizer_row(label_text, "0.5"))

        stat_tracker_layout.addLayout(stats_layout)
        button_layout_right.addWidget(stat_tracker_container, 1)

        # Add layouts to main window
        layout.addLayout(button_layout_left, 1)
        layout.addLayout(center_layout, 2)
        layout.addLayout(button_layout_right, 1)
        layout.setContentsMargins(5, 5, 5, 5)

    def toggle_special_hand_options(self, state):
        """ Toggles visibility of input fields based on checkbox state """
        is_checked = state == Qt.CheckState.Checked.value
        self.special_hand_input.setVisible(is_checked)
        self.suited_checkbox.setVisible(is_checked)

    def toggle_theme(self):
        """ Toggle between dark and light themes """
        self.is_dark_theme = not self.is_dark_theme
        if self.is_dark_theme:
            self.theme_button.setText("Light Theme")
        else:
            self.theme_button.setText("Dark Theme")
        self.apply_theme()

    def apply_theme(self):
        """ Apply the current theme """
        if self.is_dark_theme:
            self.setStyleSheet(self.dark_theme)
        else:
            self.setStyleSheet(self.light_theme)

    def load_url(self):
        """ Loads the URL when the user enters a valid Poker Now link """
        url_text = self.url_input.text().strip()
        if url_text.startswith("https://www.pokernow.club"):
            self.warning_label.setText("")
            self.browser.setUrl(QUrl(url_text))
        else:
            self.warning_label.setText("❌ Invalid URL! Please enter a valid Poker Now link.")

    def create_sizer_row(self, label_text, value_text):
        """ Creates a row layout for displaying stats with labels """
        layout = QHBoxLayout()
        label = QLabel(label_text)
        value = QLabel(value_text)

        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label.setStyleSheet("font-size: 16px; font-weight: bold; text-align: center; padding: 5px;")

        value.setStyleSheet("""
            font-size: 16px;
            background-color: #f0f0f0;
            border: 1px solid gray;
            padding: 5px;
            text-align: center;
            color: black;  /* This makes sure the value text is black */
        """)
        value.setObjectName("value")  # Add this line to target it with the .value selector in dark_theme

        layout.addWidget(label)
        layout.addWidget(value)
        return layout


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FoundryOverlay()
    window.show()
    sys.exit(app.exec())
