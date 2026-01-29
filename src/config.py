# Imports

# > Standard Library
import os
from pathlib import Path

# > Third-party imports
import torch

# Path Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
NPC_DATA_PATH = DATA_DIR / "npc_data.csv"
SAMPLES_DIR = DATA_DIR / "screenshots"
REF_AUDIO_DIR = DATA_DIR / "reference_audio"

# External Tool Paths (Adjust if installed elsewhere)
# Tesseract OCR
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if not os.path.exists(TESSERACT_CMD):
    # Fallback to local app data if Program Files fails
    TESSERACT_CMD = r"C:\Users\admin\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# eSpeak-NG (Critical for Kokoro)
ESPEAK_PATH = r"C:\Program Files\eSpeak NG\espeak-ng.exe"
if os.path.exists(ESPEAK_PATH):
    os.environ["PHONEMIZER_ESPEAK_PATH"] = ESPEAK_PATH

# Hardware Settings
# Automatically select CUDA (GPU) if available, otherwise CPU
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
SAMPLE_RATE = 24000
DEFAULT_VOLUME = 0.1

# Qwen Settings
QWEN_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"