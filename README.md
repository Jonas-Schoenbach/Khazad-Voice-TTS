# LOTRO Narrator

An immersive AI-powered narrator for *The Lord of the Rings Online*. It reads quest text from your screen, identifies the NPC you are talking to, assigns them a persistent, lore-appropriate voice, and narrates the dialogue in real-time.

## Features

* **Kokoro TTS**: High-quality, offline text-to-speech.
* **NPC Memory**: Remembers the voice assigned to every NPC you meet. If you talk to "Ted Pickthorn" today, he will have the same voice next week.
* **Fuzzy Matching**: Matches OCR text to a database of ~3000 LOTRO NPCs to determine accurate Race and Gender for voice selection.
* **Live Streaming**: Audio plays sentence-by-sentence with minimal delay.
* **Dual-Window Capture**: Intelligently captures both the Quest Text and the NPC Nameplate simultaneously.

---

## 🛠️ Prerequisites (Install these first!)

1.  **Python 3.10+**: [Download Here](https://www.python.org/downloads/)
2.  **Tesseract OCR**:
    * [Download Windows Installer](https://github.com/UB-Mannheim/tesseract/wiki)
    * Install to default location: `C:\Program Files\Tesseract-OCR`
3.  **eSpeak-NG** (Required for the Voice AI):
    * [Download MSI Installer](https://github.com/espeak-ng/espeak-ng/releases)
    * Install to default location: `C:\Program Files\eSpeak NG`
4.  **Visual C++ Redistributable**:
    * [Download x64](https://aka.ms/vs/17/release/vc_redist.x64.exe) (Fixes "DLL Load Failed" errors)

---

## 🚀 Installation

1.  **Clone/Download** this folder to your PC.
2.  **Open in PyCharm** (Open "lotro-narrator" folder).
3.  **Create Virtual Environment**:
    * Open PyCharm Terminal.
    * Run: `python -m venv venv`
    * Activate: `.\venv\Scripts\activate`
4.  **Install Libraries (Base CPU)**:
    ```bash
    pip install -r requirements.txt
    ```

---

### ⚡ Optional: Enable GPU Support (NVIDIA Only)

By default, the requirements install the CPU version. To make the AI significantly faster, you must install the GPU version.

**1. First, uninstall the CPU version:**
```bash
pip uninstall torch torchvision torchaudio -y
```

**2. Choose your GPU Type:**

**Option A: Standard GPUs (RTX 40-Series, 30-Series, 20-Series, GTX 16xx/10xx)**
*Most users should use this.*

```bash
pip install torch torchvision torchaudio --index-url [https://download.pytorch.org/whl/cu121](https://download.pytorch.org/whl/cu121)
```

**Option B: New RTX 50-Series (RTX 5070, 5080, 5090)**
*These cards require the "Nightly" build to support the new Blackwell architecture.*

```bash
pip install --pre torch torchvision torchaudio --index-url [https://download.pytorch.org/whl/nightly/cu128](https://download.pytorch.org/whl/nightly/cu128)
```

**3. Verify Installation:**
Run this command in your terminal to confirm your GPU is detected:

```bash
python -c "import torch; dev = torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'; print(f'GPU: {dev}')"
```

*(If it prints your graphics card name, you are ready!)*

---

## 🎮 Modes

### 1. File Mode

Debug mode. Select an image file from the `data/samples` directory to test OCR and TTS generation without running the game.

### 2. Echoes of Angmar Mode (Live)

Designed for the *Echoes of Angmar* private server client (Shadows of Angmar era UI).

* **Trigger**: Middle Mouse Button.
* **Behavior**: Waits 1 second for the UI to settle, captures the text/name, and streams the audio.

### 3. Retail Mode (IN-PROGRESS)

Experimental support for the modern *LOTRO* Retail client.

* **Trigger**: Middle Mouse Button.
* **Separation**: Uses a separate set of saved screen coordinates so you can switch between Echoes and Retail without re-calibrating.

---

## 🏃 How to Run

1. **Start the Tool**:
```bash
python main.py
```


2. **Select Mode**:
Enter `2` for Echoes of Angmar or `3` for Retail.
3. **In-Game Setup (First Time Only)**:
* Make sure your game is in **Windowed Fullscreen** or **Windowed** mode.
* Open a quest dialogue in-game.
* **Click Middle Mouse Button**.
* The tool will wait 1 second, then overlay a frozen screenshot.
* **Draw Box 1**: Drag around the white **Quest Text**. Press `ENTER`.
* **Draw Box 2**: Drag around the **NPC's Name** (the plate above the text). Press `ENTER`.
* The tool will save these positions to `data/coords.json`.


4. **Routine Usage**:
* Just click the Middle Mouse button whenever you accept a quest or click "Continue".


5. **Resetting Coordinates**:
If you move your game window or change resolution, delete `data/coords.json` to trigger the setup again.