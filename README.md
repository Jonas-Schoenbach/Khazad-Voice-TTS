# LOTRO Narrator

A smart, AI-powered narrator for *The Lord of the Rings Online*. This tool reads quest text from your screen and speaks it aloud using character-appropriate voices.

## Features
* **Two AI Engines:** * **CPU Mode (Kokoro):** Fast and lightweight. Works on almost any computer.
    * **GPU Mode (LuxTTS):** High-quality voice cloning. Requires an average NVIDIA GPU.
* **Two Game Modes:** Supports both Official Servers (Retail) and Private Servers (Echoes).

## Modes

### 1. Echoes of Angmar (Classic Mode)
**Best for:** Private servers or clean user interfaces.

* **Trigger:** Middle Mouse Button Click.
* **Mechanism:** OCR (Optical Character Recognition) scans the text and name on your screen.
    * **First Run:** You must manually select the **Quest Text** area and the **NPC Name** area by drawing a box on the screen.

### 2. Retail (Live Servers)
**Best for:** The official game servers (Live).

* **Trigger:** Automatic (triggered by game logs).
* **Mechanism:**
    * Watches `Script.log` for new NPC names.
    * When an NPC is detected, it scans the screen for the Quest Window icon.
    * If found, it reads the quest text automatically.

## Prerequisites (Important!)

Before installing, you need a few external tools to make the magic happen:

### 1. Tesseract OCR
This program is required to convert images of text into actual text.
* **Download:** [GitHub Wiki Link](https://github.com/UB-Mannheim/tesseract/wiki) (Download the Windows installer).
* **Guide:** [How to install Tesseract on Windows](https://linuxhint.com/install-tesseract-windows/)
* **Note:** The app expects Tesseract to be installed at the default location (`C:\Program Files\Tesseract-OCR\tesseract.exe`).

### 2. getNPCNames Plugin
This plugin is **VERY NECESSARY** for Retail Mode. It allows the AI to choose the correct voice model based on the NPC's gender and race.
* **Download:** [Dt192.zip (Direct Link)](https://github.com/ils94/LOTROToSpeech/raw/master/Helpful%20Stuffs/Plugins/Dt192.zip) *(Credit to dt192)*
* **Guide:** [How to install LOTRO Plugins](https://www.lotrointerface.com/wiki/Install_plugins)

## Installation & Setup

### Step 1: Install (Make sure you have at least 10GB of free space for the installation files such as packages and TTS models)
1.  Double-click **`install.bat`**.
2.  Follow the on-screen prompts:
    * It will check for **Python 3.12** and **Git**.
    * It will ask about your graphics card (to choose the right AI drivers).
    * It will download the voice models.

### Step 2: Templates (Retail Mode Only)
The project comes with default quest templates in the `templates/` folder.
* These are small images of the Quest Window icon (like the golden ring).
* **You usually do not need to do anything here.**
* *Optional:* If detection fails, you can take your own screenshot of the quest icon and save it as a `.png` in this folder.

### Step 3: Run the Narrator
Double-click **`start.bat`**.

Follow the on-screen prompts:
1.  **Select Audio Engine:** Choose CPU (Standard) or GPU (High Quality).
2.  **Select Game Mode:** Choose Echoes (Classic) or Retail (Live).

## Credits & Shoutouts
* **LOTROToSpeech by ils94**: A huge shoutout to [LOTROToSpeech](https://github.com/ils94/LOTROToSpeech) for the inspiration behind this project!
* **Kokoro**: For the incredible voice generation model. [Kokoro82M](https://huggingface.co/hexgrad/Kokoro-82M)
* **Yatharth Sharma**: For his amazing work on the LuxTTS model and backend. [LuxTTS](https://github.com/ysharma3501/LuxTTS)