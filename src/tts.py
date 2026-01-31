# Imports

# > Standard Library
import os
import sys
import re
import random
import time
from pathlib import Path

# > Third-party imports
import numpy as np
import torch
from kokoro import KPipeline

# > Local dependencies
from .utils import setup_logger
from .config import SAMPLE_RATE, DEVICE, REF_AUDIO_DIR, TTS_SPEED, TTS_PADDING, TTS_WAVE_STEPS

log = setup_logger(__name__)


def get_tts_backend():
    """
    Factory to return LuxBackend if GPU is available, otherwise KokoroBackend.
    """
    if torch.cuda.is_available():
        log.info("🚀 GPU Detected! Initializing LuxTTS Backend...")
        try:
            return LuxBackend()
        except ImportError as e:
            log.error(f"❌ LuxTTS Import Error: {e}")
            log.warning("Falling back to Kokoro.")
            return KokoroBackend()
        except Exception as e:
            log.error(f"❌ Error loading LuxTTS: {e}. Falling back to Kokoro.")
            return KokoroBackend()
    else:
        log.info("🐢 No GPU detected. Using Kokoro Backend (CPU).")
        return KokoroBackend()


class LuxBackend:
    """
    TTS Engine wrapping LuxTTS for Voice Cloning.
    Optimized for high-quality, high-speed inference.
    """

    def __init__(self):
        log.info(f"Loading LuxTTS Model on {DEVICE}...")

        # --- Import Logic Fix ---
        # Add the local 'LuxTTS' folder to sys.path so Python can find 'zipvoice'
        lux_path = os.path.join(os.getcwd(), 'LuxTTS')
        if os.path.exists(lux_path) and lux_path not in sys.path:
            sys.path.append(lux_path)

        try:
            # Try importing directly (if LuxTTS folder is in sys.path)
            from zipvoice.luxvoice import LuxTTS
        except ImportError:
            try:
                # Fallback: Try importing as a package from root
                from LuxTTS.zipvoice.luxvoice import LuxTTS
            except ImportError as e:
                raise ImportError(f"Could not import LuxTTS. Checked '{lux_path}'. Error: {e}")

        # Initialize the model
        self.tts = LuxTTS('YatharthS/LuxTTS', device='cuda')

        self.samplerate = 48000
        self.voice_library = self._load_voice_library()
        log.info(f"✅ LuxTTS Ready. Loaded {sum(len(v) for v in self.voice_library.values())} reference voices.")

        # Warmup to speed model up
        self._warmup()

    def _warmup(self):
        """
        Runs a short generation to force PyTorch to compile and librosa to init.
        """
        log.info("🔥 Warming up LuxTTS (takes ~10s for first run)...")
        try:
            # Pick any key
            if "narrator" in self.voice_library:
                voice_id = "narrator|0"
            else:
                first_key = list(self.voice_library.keys())[0]
                voice_id = f"{first_key}|0"

            t0 = time.time()
            self.generate("Warmup.", voice_id, warmup=True)
            t1 = time.time()
            log.info(f"🔥 Warmup Complete in {t1 - t0:.2f}s.")
        except Exception as e:
            log.warning(f"⚠️ Warmup failed (non-critical): {e}")

    def _load_voice_library(self):
        library = {}
        if not REF_AUDIO_DIR.exists():
            log.warning(f"Reference Audio dir not found: {REF_AUDIO_DIR}")
            return library

        for folder in REF_AUDIO_DIR.iterdir():
            if not folder.is_dir():
                continue
            key = folder.name.lower()
            library[key] = []

            txt_files = list(folder.glob("*.txt"))
            if not txt_files:
                continue
            txt_path = txt_files[0]
            with open(txt_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            clean_lines = []
            for line in lines:
                text = re.sub(r"\"", "", line).strip()
                if text:
                    clean_lines.append(text)

            if not clean_lines:
                continue

            audio_files = sorted(
                list(folder.glob("*.flac")),
                key=lambda x: int(re.search(r"_(\d+)\.flac", x.name).group(1)) if re.search(r"_(\d+)\.flac",
                                                                                            x.name) else 0
            )

            # --- Handle 1 Text vs Many Audio Files ---
            for i, audio_path in enumerate(audio_files):
                # If we have the specific line for this index, use it (1-to-1 match)
                if i < len(clean_lines):
                    text = clean_lines[i]
                # Otherwise, reuse the first line (1-to-Many match, e.g., 1 transcript for 10 files)
                else:
                    text = clean_lines[0]

                library[key].append({
                    "id": i,
                    "text": text,
                    "audio": str(audio_path)
                })
        return library

    def pick_voice(self, gender: str, race: str) -> tuple[str, str]:
        g_clean = (gender or "").lower().strip()
        r_clean = (race or "").lower().strip()

        if "narrator" in r_clean or "narrator" in g_clean:
            key = "narrator"
        else:
            key = f"{r_clean}_{g_clean}"

        if key not in self.voice_library or not self.voice_library[key]:
            if "narrator" in self.voice_library and self.voice_library["narrator"]:
                key = "narrator"
            else:
                return "default", "fallback"

        sample = random.choice(self.voice_library[key])
        voice_id = f"{key}|{sample['id']}"
        return voice_id, key

    def generate(self, text: str, voice_id: str, warmup=False) -> np.ndarray:
        if "|" not in voice_id:
            return np.array([], dtype=np.float32)

        category, idx_str = voice_id.split("|")
        try:
            idx = int(idx_str)
            ref_data = self.voice_library[category][idx]
        except (ValueError, IndexError, KeyError):
            log.error(f"Invalid voice_id: {voice_id}")
            return np.array([], dtype=np.float32)

        ref_audio = ref_data["audio"]
        ref_text = ref_data["text"]

        if not warmup:
            log.info(f"🎙️ Cloning [{category}]: {text[:30]}...")

        try:
            # Encode prompt audio
            # We pass 'text=ref_text' so LuxTTS can skip Whisper transcription
            encoded_prompt = self.tts.encode_prompt(
                ref_audio, 
                text=ref_text, 
                rms=0.01, 
                duration=1000
            )

            # Use Configurable Padding
            padded_text = text.strip() + TTS_PADDING

            # Generate speech
            wav_tensor = self.tts.generate_speech(
                padded_text,
                encoded_prompt,
                num_steps=TTS_WAVE_STEPS,
                speed=TTS_SPEED
            )

            # Convert to numpy array (squeeze to remove batch/channel dims if any)
            # Ensure it is on CPU and detached
            if hasattr(wav_tensor, 'detach'):
                wav = wav_tensor.detach().cpu().numpy().squeeze()
            else:
                wav = wav_tensor.numpy().squeeze()

            return wav.astype(np.float32)

        except Exception as e:
            log.error(f"Generation failed: {e}")
            import traceback
            traceback.print_exc()

        return np.array([], dtype=np.float32)


class KokoroBackend:
    """
    Standard CPU Fallback
    """
    VOICES = {
        "man male": ["am_echo", "am_eric", "am_fenrir", "am_liam", "am_onyx", "am_puck", "am_santa", "am_michael"],
        "elf male": ["am_onyx", "am_puck"],
        "dwarf male": ["bm_daniel", "am_santa", "am_michael"],
        "hobbit male": ["bm_fable", "bm_george", "bm_lewis"],
        "man female": ["af_alloy", "af_aoede", "af_heart", "af_jessica"],
        "elf female": ["af_bella", "af_kore", "af_nova"],
        "dwarf female": ["af_river", "af_sarah"],
        "hobbit female": ["af_sky", "bf_alice", "bf_emma", "bf_isabella", "bf_lily"],
    }
    RACE_MAP = {
        "Men": "man", "Man": "man", "Human": "man", "Beorning": "man",
        "Elf": "elf", "High Elf": "elf",
        "Dwarf": "dwarf", "Stout-axe": "dwarf",
        "Hobbit": "hobbit", "River Hobbit": "hobbit",
    }

    def __init__(self):
        log.info(f"Loading Kokoro Voice Model on [{DEVICE}]...")
        self.pipeline = KPipeline(lang_code="a", device=DEVICE)
        self.samplerate = SAMPLE_RATE
        log.info("✅ Voice Model Ready.")

    def pick_voice(self, gender: str, race: str) -> tuple[str, str]:
        g_clean = (gender or "male").lower().strip()
        r_clean = (race or "man").strip()
        r_key = self.RACE_MAP.get(r_clean, "man")
        if "narrator" in r_clean.lower() or "narrator" in g_clean.lower():
            return "am_echo", "narrator"
        key = f"{r_key} {g_clean}"
        if key in self.VOICES:
            voice = random.choice(self.VOICES[key])
            return voice, key
        return "am_echo", "fallback"

    def generate(self, text: str, voice: str, warmup=False) -> np.ndarray:
        generator = self.pipeline(text, voice=voice, speed=1.1, split_pattern=r"\n+")
        chunks = [audio for _, _, audio in generator if audio is not None]
        if chunks:
            return np.concatenate(chunks).astype(np.float32)
        return np.array([], dtype=np.float32)