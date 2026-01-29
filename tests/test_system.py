# Imports

# > Standard library
import sys
import os

# > Third party imports
import torch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.tts import KokoroBackend
from src.audio import play_audio
from src.config import DEVICE


def test():
    print(f"🚀 TEST MODE. Device: {DEVICE}")
    if torch.cuda.is_available():
        print(f"   GPU: {torch.cuda.get_device_name(0)}")

    try:
        tts = KokoroBackend()
        text = "This is a test of the automatic speech generation system."
        print(f"   Generating: '{text}'")

        voice = "af_heart"
        audio = tts.generate(text, voice)

        print("   Playing...")
        play_audio(audio, tts.samplerate)
        print("✅ Test Successful.")
    except Exception as e:
        print(f"❌ Test Failed: {e}")


if __name__ == "__main__":
    test()
