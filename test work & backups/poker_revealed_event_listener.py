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
        self.timer.start(3000)

    def poll_game_state(self):
        js_code = """
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
        self.browser.page().runJavaScript(js_code, self.display_opponent_hands)

    def display_opponent_hands(self, hands):
        if hands:
            for player in hands:
                name = player['name']
                cards = " ".join(player['hand'])
                logging.info(f"{name} revealed: {cards}")
                self.status_label.setText(f"{name} revealed: {cards}")
        else:
            self.status_label.setText("No opponent cards revealed.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PokerNowScraper()
    window.show()
    sys.exit(app.exec())
