# Imports

# > Standard Library
import os
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
from .config import SAMPLE_RATE, DEVICE, QWEN_MODEL_ID, REF_AUDIO_DIR

log = setup_logger(__name__)


def get_tts_backend():
    """
    Factory to return QwenBackend if GPU is available, otherwise KokoroBackend.
    """
    if torch.cuda.is_available():
        log.info("🚀 GPU Detected! Initializing Qwen3-TTS Backend...")
        try:
            return QwenBackend()
        except ImportError as e:
            log.error(f"❌ Qwen Import Error: {e}")
            log.warning("Falling back to Kokoro.")
            return KokoroBackend()
        except Exception as e:
            log.error(f"❌ Error loading Qwen: {e}. Falling back to Kokoro.")
            return KokoroBackend()
    else:
        log.info("🐢 No GPU detected. Using Kokoro Backend (CPU).")
        return KokoroBackend()


class QwenBackend:
    """
    TTS Engine wrapping Qwen3-TTS (0.6B) for Voice Cloning.
    Optimized for low-latency inference.
    """

    def __init__(self):
        from qwen_tts import Qwen3TTSModel

        log.info(f"Loading Qwen3-TTS Model [{QWEN_MODEL_ID}] on {DEVICE}...")

        self.model = Qwen3TTSModel.from_pretrained(
            QWEN_MODEL_ID,
            device_map=DEVICE,
            torch_dtype=torch.float32,
            attn_implementation="eager",
        )

        self.samplerate = 24000
        self.voice_library = self._load_voice_library()
        log.info(f"✅ Qwen Ready. Loaded {sum(len(v) for v in self.voice_library.values())} reference voices.")

        # Warmup to speed model up
        self._warmup()

    def _warmup(self):
        """
        Runs a silent, short generation to force PyTorch to compile the CUDA graphs.
        This prevents the first user click from lagging by 10+ seconds.
        """
        log.info("🔥 Warming up GPU (this takes ~5s)...")
        try:
            # Generate a very short, silent clip
            # We use a dummy voice or the first available one
            if "narrator" in self.voice_library:
                voice_id = "narrator|0"
            else:
                # Pick any key
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

                audio_files = sorted(
                    list(folder.glob("*.flac")),
                    key=lambda x: int(re.search(r"_(\d+)\.flac", x.name).group(1)) if re.search(r"_(\d+)\.flac",
                                                                                                x.name) else 0
                )

                for i, (text, audio_path) in enumerate(zip(clean_lines, audio_files)):
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

        # OPTIMIZATION  Dynamic Token Limit
        # 2048 is too high for short sentences.
        # Approx calculation: 1 sec audio ~= 50 tokens (varies wildly, but good heuristic)
        # We assume 1 character takes roughly 0.1s to speak.
        # Safe buffer: 256 tokens minimum, cap at 1024 for long texts.
        estimated_tokens = max(256, min(1024, int(len(text) * 3)))

        if not warmup:
            log.info(f"🎙️ Cloning [{category}]: {text[:30]}... (max_tokens={estimated_tokens})")

        try:
            wavs, sr = self.model.generate_voice_clone(
                text=text,
                language="Auto",
                ref_audio=ref_audio,
                ref_text=ref_text,
                max_new_tokens=estimated_tokens,  # Limit generation length
            )

            self.samplerate = sr
            if len(wavs) > 0:
                return wavs[0]

        except Exception as e:
            log.error(f"Generation failed: {e}")

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