# 🧙‍♂️ LOTRO AI Narrator

**Immersive AI Voice-Over for Lord of the Rings Online**

This tool reads Quest Text and NPC Names from your screen and generates high-quality, race-specific AI voices (Dwarves, Elves, Hobbits, Men) in real-time.

## ✨ Features
* **Automatic Voice Selection:** Detects NPC gender and race to pick the correct voice actor.
* **High Quality AI:** Uses `LuxTTS` (GPU) or `Kokoro` (CPU) for realistic speech.
* **Memory:** Remembers voices for specific NPCs so they always sound the same.
* **One-Click:** Just press your Middle Mouse Button.

---

## 🚀 Installation (Windows)

### 1. Prerequisites
You must have **Python 3.12** installed.
* [Download Python 3.12 Here](https://www.python.org/downloads/release/python-31210/)
* **IMPORTANT:** During installation, check the box **"Add Python to PATH"**.

### 2. Setup
1.  Download this folder.
2.  Double-click `install.bat` (Make sure you have at least 10GB of free space for packages + TTS Models).
3.  **Select your GPU Version** when asked:
    * Choose **[1] CUDA 12.1** for most NVIDIA cards (RTX 4070, 3060, 2060, etc.).
    * Choose **[2] CUDA 12.8** if you have a new RTX 50-Series card.
    * Choose **[3] CPU Only** if you don't have an NVIDIA GPU (Note: LuxTTS will be disabled).
4.  Wait for the installation to finish.

---

## 🎮 How to Use

1.  **Start the Tool:** Double-click `start.bat`. Wait for the message "Ready for capture".

2.  **In Game (First Time Only):**
    * Find a Quest Giver and open the quest dialog.
    * Click your **Middle Mouse Button**.
    * The tool will ask you to draw a box around the **Quest Text**.
    * Then, it will ask you to draw a box around the **NPC Name**.
    * *These locations are saved automatically in `data/coords.json`.*

3.  **Playing:**
    * Whenever you see quest text, click **Middle Mouse Button**.
    * Listen to the narration!

---

## 🛠️ Configuration
You can tweak settings in `src/config.py` using any text editor (Notepad):
* `TTS_SPEED`: Change how fast they speak (0.8 is default).
* `TTS_PADDING`: Fixes issues where the voice cuts off too early.
* `DEFAULT_VOLUME`: Process volume.

## ❓ Troubleshooting
* **"Unknown compiler" / Scipy Error:** You are likely using Python 3.13. Please install Python 3.12 and try again.
* **It cuts off the end of sentences:** Open `src/config.py` and ensure `TTS_PADDING` is set to `" ..."`.
* **The boxes are in the wrong place:** Delete the file `data/coords.json` to reset the screen positions.