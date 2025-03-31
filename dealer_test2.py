from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import re

# Setup
service = Service(".\\chromedriver-win64\\chromedriver.exe")
options = Options()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=service, options=options)

driver.get("https://www.pokernow.club/start-game")
time.sleep(5)

def detect_dealer():
    try:
        dealer_els = driver.find_elements(By.CSS_SELECTOR, ".dealer-button-ctn")
        if not dealer_els:
            print("❌ No dealer button found.")
            return None, None

        for el in dealer_els:
            class_attr = el.get_attribute("class")

            match = re.search(r"dealer-position-(\d+)", class_attr)  # ✅ FIXED: use raw string with single backslash
            if not match:
                print("❌ Couldn't extract seat number from class.")
                continue

            seat_index = int(match.group(1))

            # Now find the table-player div for that seat
            player_els = driver.find_elements(By.CSS_SELECTOR, ".table-player")
            for player in player_els:
                player_class = player.get_attribute("class")
                if f"table-player-{seat_index}" in player_class:
                    try:
                        name_el = player.find_element(By.CSS_SELECTOR, ".table-player-name")
                        name = name_el.text.strip()
                        if not name:
                            try:
                                name = name_el.find_element(By.CSS_SELECTOR, "a").text.strip()
                            except:
                                name = "(no name)"
                        return seat_index, name
                    except:
                        print("⚠️ Could not extract name from dealer.")
                        return seat_index, "(no name)"
        return None, None

    except Exception as e:
        print(f"[!] Dealer detection error: {e}")
        return None, None

# Main loop
print("🔄 Polling dealer every second (Ctrl+C to stop)")
try:
    while True:
        seat, name = detect_dealer()
        print(f"🪑 Dealer seat: {seat}, name: {name}")
        time.sleep(1)
except KeyboardInterrupt:
    print("🛑 Stopped by user.")
    driver.quit()


