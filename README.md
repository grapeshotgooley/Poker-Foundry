# 🃏 The Poker Foundry

**The Poker Foundry** is an advanced HUD (Heads-Up Display) and data analysis tool built for [PokerNow.com](https://www.pokernow.club/). It leverages real-time scraping and game state tracking to enhance decision-making for online poker games.
[![Watch the video](https://img.youtube.com/vi/TnOleSkJUdI/0.jpg)](https://www.youtube.com/watch?v=TnOleSkJUdI)
---

## ❌ Be Advised
While this tool is a fantastic mental, game theory, and coding exercise, the dynamic nature of its modules is not in alignment with the terms of use of PokerNow. That is to say use of this tool in a real setting is -currently- consider cheating, so don't do it. Instead use this tool with your friends for fun as a way to learn better poker without real money involvement and to better understand RTA tools you might have to face against.  

## ⚙️ Features

### 🧠 Foundry Engine
Extracts and tracks real-time hand and street data from Poker Now using Selenium. Compiles it into structured JSON for live tool updates and post-hand analysis.

### 💻 Foundry Overlay
A PySide-based UI that surrounds the Poker Now browser with dynamic stat windows and tool interfaces, powered by Selenium and ChromeDriver.

### 🎲 Open-Fold Suggester
Uses preflop strategy trees to recommend folds or opens. Includes a fun “special hand” toggle for custom strategies like the 7-2 game.

### 📏 Bet Sizer
Displays stack-to-pot ratio (SPR) and a suggested bet size using board texture, position, and randomization logic.

### 📊 Odds Calculator
Simulates win % between your hand and a selected opponent hand using multiprocessing, NumPy, and a custom hand-ranking library for fast calculations.

### 👁️ Villain Stat Tracker
Analyzes opponent behavior based on hand history. Provides real-time labels (e.g., Loose-Aggressive, Tilted) and auto-expands stats when heads-up.

---

## 📦 Installation

### 1. Clone and Install Dependencies

```bash
pip install git+https://github.com/glpcc/PokerPy
pip install PyQt6 PyQt6-WebEngine numpy
```

> **Note**: You must have `git` and `Microsoft Visual C++ 14.0 or greater` installed on your machine.

### 2. Install Microsoft C++ Build Tools

🔧 [Download Microsoft Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

Make sure to select the **C++ build tools** during installation.

### 3. Set Up ChromeDriver

Download the stable version of [Chrome for Testing](https://googlechromelabs.github.io/chrome-for-testing/):

- Select **Stable**
- Choose **ChromeDriver** for **Windows x64**

Ensure that `chromedriver.exe` is accessible from your system PATH or within the project directory.

---

## 🔍 Dependencies

- [PokerPy](https://github.com/glpcc/PokerPy)  
- [Selenium](https://www.selenium.dev/)  
- [PyQt6](https://pypi.org/project/PyQt6/)  
- [PyQt6-WebEngine](https://pypi.org/project/PyQt6-WebEngine/)

---

## 📄 License

**Reminder:** Apache 2 (look more into this)

---

## 🚧 Status

This project is currently under active development. Contributions and testing feedback are welcome!

---

## 📬 Contact

Questions? Ideas? Go to https://gooley.net to contact the developers.
