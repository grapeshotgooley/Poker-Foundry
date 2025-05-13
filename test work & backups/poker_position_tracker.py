import sys
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QMessageBox
from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

URL = "https://www.pokernow.club/start-game"

class PokerNowScraper(QMainWindow):
    def __init__(self):
        super().__init__()
        try:
            self.setWindowTitle("PokerNow QWebEngineView Scraper")
            self.setGeometry(100, 100, 1200, 800)

            self.browser = QWebEngineView()
            self.browser.setUrl(QUrl(URL))
            self.browser.settings().setAttribute(
                QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True
            )

            self.status_label = QLabel("Loading...", self)
            self.status_label.setStyleSheet("font-size: 16px; padding: 10px;")

            layout = QVBoxLayout()
            layout.addWidget(self.browser)
            layout.addWidget(self.status_label)

            container = QWidget()
            container.setLayout(layout)
            self.setCentralWidget(container)

            self.timer = QTimer()
            self.timer.timeout.connect(self.poll_game_state)
            self.timer.start(500)
        except Exception as e:
            logging.error("Initialization error: %s", e)
            self.show_error("Initialization Error", str(e))

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

    def poll_game_state(self):
        try:
            js_code = """
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
            self.browser.page().runJavaScript(js_code, self.process_players)
        except Exception as e:
            logging.error("JavaScript execution error: %s", e)
            self.status_label.setText("Error polling game state.")

    def process_players(self, players):
        try:
            if isinstance(players, dict) and "error" in players:
                raise ValueError(f"JavaScript error: {players['error']}")

            if not players:
                self.status_label.setText("No active players found.")
                return

            players.sort(key=lambda p: p.get("seatIndex", -1))

            hero = next((p for p in players if p.get("isHero")), None)
            dealer = next((p for p in players if p.get("isDealer")), None)

            if not hero or not dealer:
                self.status_label.setText("Hero or Dealer not found.")
                return

            # Log dealer info
            logging.info(f"Dealer is at seat {dealer['seatIndex']} with name '{dealer.get('name', '(unknown)')}'")

            dealer_idx = players.index(dealer)
            rotated_players = players[dealer_idx:] + players[:dealer_idx]
            total = len(rotated_players)

            if total == 2:
                positions = ["SB", "BB"]
                for i, player in enumerate(rotated_players):
                    player["position"] = positions[i]
            else:
                # Assign "BTN" to dealer manually
                for p in players:
                    p["position"] = "Unknown"
                dealer["position"] = "BTN"

                # Assign other positions from dealer clockwise
                non_dealers = [p for p in rotated_players if p != dealer]
                reversed_priority = ["UTG-1", "UTG", "UTG+1", "UTG+2", "LJ", "HJ", "CO"]
                needed_positions = ["SB", "BB"] + reversed_priority[-(len(non_dealers) - 2):]
                for i, p in enumerate(non_dealers):
                    if i < len(needed_positions):
                        p["position"] = needed_positions[i]

            hero_position = next((p["position"] for p in players if p.get("isHero")), "Unknown")
            hand_str = " ".join(hero.get("cards", [])) if hero.get("cards") else "(no cards)"

            self.status_label.setText(f"Hero's Hand: {hand_str} | Position: {hero_position}")
            logging.info(f"Hero's Hand: {hand_str} | Position: {hero_position}")
        except Exception as e:
            logging.error("Processing error: %s", e)
            self.status_label.setText("Error processing player data.")


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = PokerNowScraper()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.critical("Fatal error on launch: %s", e)
