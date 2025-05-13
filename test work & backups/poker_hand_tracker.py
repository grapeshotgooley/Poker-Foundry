import sys
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

URL = "https://www.pokernow.club/start-game"

class PokerNowScraper(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PokerNow QWebEngineView Scraper")
        self.setGeometry(100, 100, 1200, 800)

        # Browser setup
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl(URL))
        self.browser.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True
        )

        # Status label
        self.status_label = QLabel("Loading...", self)
        self.status_label.setStyleSheet("font-size: 16px; padding: 10px;")

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.browser)
        layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Start polling
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_game_state)
        self.timer.start(3000)  # Poll every 3 seconds

    def poll_game_state(self):
        js_code = """
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
        self.browser.page().runJavaScript(js_code, self.display_hero_hand)

    def display_hero_hand(self, hand):
        if hand:
            hand_str = " ".join(hand)
            self.status_label.setText(f"Hero's Hand: {hand_str}")
            logging.info(f"Hero's Hand: {hand_str}")
        else:
            self.status_label.setText("No cards detected. Waiting for game to start.")
            logging.info("No cards detected. Waiting for game to start.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PokerNowScraper()
    window.show()
    sys.exit(app.exec())
