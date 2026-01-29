# LOTRO Narrator

An AI-powered narrator for Lord of the Rings Online. It reads quest text from screenshots, detects the NPC, and speaks the text using an appropriate voice.

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
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**Option B: New RTX 50-Series (RTX 5070, 5080, 5090)**
*These cards require the "Nightly" build to support the new Blackwell architecture.*

```bash
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
```

**3. Verify Installation:**
Run this command in your terminal to confirm your GPU is detected:

```bash
python -c "import torch; dev = torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'; print(f'GPU: {dev}')"
```

*(If it prints your graphics card name, you are ready!)*
## 🎮 How to Run

1.  Place your screenshots in `data/samples/`.
2.  Run the main app:
    ```bash
    python main.py
    ```
3.  Follow the on-screen prompts to select an image, crop the text, and confirm the NPC.