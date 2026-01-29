# Imports

# > Standard Library
import random

# > Third-party imports
import numpy as np
from kokoro import KPipeline

# > Local dependencies
from .utils import setup_logger
from .config import SAMPLE_RATE, DEVICE

log = setup_logger(__name__)


class KokoroBackend:
    """
    TTS Engine wrapping Kokoro with LOTRO-specific voice logic.
    """

    VOICES = {
        "man male": [
            "am_echo",
            "am_eric",
            "am_fenrir",
            "am_liam",
            "am_onyx",
            "am_puck",
            "am_santa",
            "am_michael",
        ],
        "elf male": ["am_onyx", "am_puck"],
        "dwarf male": ["bm_daniel", "am_santa", "am_michael"],
        "hobbit male": ["bm_fable", "bm_george", "bm_lewis"],
        "man female": ["af_alloy", "af_aoede", "af_heart", "af_jessica"],
        "elf female": ["af_bella", "af_kore", "af_nova"],
        "dwarf female": ["af_river", "af_sarah"],
        "hobbit female": ["af_sky", "bf_alice", "bf_emma", "bf_isabella", "bf_lily"],
    }

    RACE_MAP = {
        "Men": "man",
        "Man": "man",
        "Human": "man",
        "Beorning": "man",
        "Elf": "elf",
        "High Elf": "elf",
        "Dwarf": "dwarf",
        "Stout-axe": "dwarf",
        "Hobbit": "hobbit",
        "River Hobbit": "hobbit",
    }

    def __init__(self):
        log.info(f"Loading AI Voice Model on [{DEVICE}]...")
        # 'a' = American English, but Kokoro handles 'b' (British) voices automatically
        self.pipeline = KPipeline(lang_code="a", device=DEVICE)
        self.samplerate = SAMPLE_RATE
        log.info("✅ Voice Model Ready.")

    def pick_voice(self, gender: str, race: str) -> tuple[str, str]:
        """
        Returns (voice_id, category_key) based on race/gender.
        """
        g_clean = (gender or "male").lower().strip()
        r_clean = (race or "man").strip()
        r_key = self.RACE_MAP.get(r_clean, "man")

        key = f"{r_key} {g_clean}"

        if key in self.VOICES:
            voice = random.choice(self.VOICES[key])
            return voice, key

        return "am_echo", "fallback"

    def generate(self, text: str, voice: str) -> np.ndarray:
        """
        Generates raw audio data.
        """
        # split_pattern handles newlines to keep flow natural
        generator = self.pipeline(text, voice=voice, speed=1.1, split_pattern=r"\n+")
        chunks = [audio for _, _, audio in generator if audio is not None]

        if chunks:
            return np.concatenate(chunks).astype(np.float32)
        return np.array([], dtype=np.float32)
