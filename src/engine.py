# Imports

# > Standard Library
import time
import queue
import threading

# > Third-party Libraries
import cv2

# > Local Dependencies
from .utils import setup_logger, save_npc_memory, load_npc_memory, detect_quest_window
from .ocr import run_ocr, run_name_ocr
from .audio import play_audio
from .config import DEFAULT_VOLUME

log = setup_logger("ENGINE")


class NarratorEngine:
    """
    Orchestrates the pipeline: Capture -> OCR -> Data Lookup -> TTS -> Audio Playback.

    Parameters
    ----------
    db : NPCDatabase
        Instance of the NPC database.
    tts_backend : object
        Instance of the active TTS backend (LuxBackend or KokoroBackend).
    mode : str
        The current operation mode ('echoes' or 'retail').
    """

    def __init__(self, db, tts_backend, mode="echoes"):
        self.db = db
        self.tts = tts_backend
        self.mode = mode

        # Load memory specific to the mode (e.g., npc_memory_retail.json)
        self.memory = load_npc_memory(self.mode)
        log.info(f"🧠 Loaded Memory for mode: {self.mode}")

        self.audio_queue = queue.Queue()
        self.is_playing = False

    def process_capture(self, quest_img_pil, name_img_pil):
        """
        Processing pipeline for Echoes mode (manual trigger).

        Parameters
        ----------
        quest_img_pil : PIL.Image.Image
            Screenshot crop of the quest text.
        name_img_pil : PIL.Image.Image
            Screenshot crop of the NPC name.
        """
        # 1. Quest Text OCR
        log.info("Reading Quest Text...")
        sentences = run_ocr(quest_img_pil)
        if not sentences:
            log.warning("No quest text found.")
            return

        # 2. Name Tag OCR
        log.info("Reading NPC Name...")
        npc_name = run_name_ocr(name_img_pil) or "Unknown"
        log.info(f"📝 NPC Name: '{npc_name}'")

        # 3. Resolve Voice
        voice_id = self._resolve_voice(npc_name)

        # 4. Generate & Stream Audio
        self._start_streaming(sentences, voice_id)

    def process_retail(self, quest_img_pil, full_screen_np, npc_name):
        """
        Processing pipeline for Retail mode (log-file triggered).

        Parameters
        ----------
        quest_img_pil : PIL.Image.Image
            Screenshot crop of the quest text.
        full_screen_np : np.ndarray
            Full screenshot for UI element validation (template matching).
        npc_name : str
            Name extracted directly from the game logs.
        """
        # 1. Verify Window Existence (Template Matching)
        if not detect_quest_window(full_screen_np):
            log.info("🙈 NPC in log, but no Quest Window detected. Ignoring.")
            return

        # 2. Quest Text OCR (We already know the name!)
        log.info(f"Reading Quest Text for: {npc_name}...")
        sentences = run_ocr(quest_img_pil)
        if not sentences:
            log.warning("No quest text found (OCR failed or empty).")
            return

        # 3. Resolve Voice
        voice_id = self._resolve_voice(npc_name)

        # 4. Generate & Stream
        self._start_streaming(sentences, voice_id)

    def _resolve_voice(self, npc_name: str) -> str:
        """
        Determines the correct voice ID based on memory or database lookup.

        Parameters
        ----------
        npc_name : str
            The name of the NPC.

        Returns
        -------
        str
            The resolved voice ID to be used by the TTS backend.
        """
        key = npc_name.lower()

        # Check Memory first
        if key in self.memory:
            data = self.memory[key]
            log.info(f"🧠 Memory Recall: '{data['name']}' -> {data['voice_id']}")
            return data["voice_id"]

        # Check Database
        log.info("🔍 Resolving new NPC...")
        gender, race, matched_name = self.db.lookup(npc_name)

        # Fallback
        if not gender or not race:
            log.info("⚠️ No DB match. Using Default Narrator.")
            matched_name = "Narrator"
            race, gender = "Narrator", "Narrator"

        # Pick Voice via Backend
        voice_id, category = self.tts.pick_voice(gender, race)

        # Save to Memory (Specific to current mode)
        self.memory[key] = {
            "name": matched_name,
            "race": race,
            "gender": gender,
            "voice_id": voice_id,
        }
        save_npc_memory(self.memory, self.mode)
        log.info(f"💾 Saved: {matched_name} -> {voice_id} ({category})")
        return voice_id

    def _start_streaming(self, sentences: list[str], voice_id: str):
        """
        Starts a producer thread for TTS generation and plays audio in the main loop.

        Parameters
        ----------
        sentences : list[str]
            List of text segments to speak.
        voice_id : str
            The specific voice ID string for the backend.
        """

        def producer():
            """Generates audio chunks and puts them in the queue."""
            clean_lines = [s.strip() for s in sentences if s.strip()]

            # LuxTTS optimization: Batch generation often sounds better/faster
            if type(self.tts).__name__ == "LuxBackend":
                # Chunk into batches of 4 sentences to keep generation smooth
                chunk_size = 4
                for i in range(0, len(clean_lines), chunk_size):
                    batch = clean_lines[i : i + chunk_size]
                    full_text = " ".join(batch)
                    if full_text:
                        audio = self.tts.generate(full_text, voice_id)
                        self.audio_queue.put((full_text, audio, self.tts.samplerate))
            else:
                # Kokoro: Line-by-line generation
                for line in clean_lines:
                    audio = self.tts.generate(line, voice_id)
                    self.audio_queue.put((line, audio, self.tts.samplerate))

            self.audio_queue.put(None)  # End signal

        threading.Thread(target=producer, daemon=True).start()

        # Playback Loop (Blocking)
        print("\n--- 🟢 PLAYBACK STARTED ---")
        while True:
            item = self.audio_queue.get()
            if item is None:
                break

            text, audio, sr = item
            display_text = (text[:60] + "...") if len(text) > 60 else text
            print(f"▶️ Speaking: {display_text}")

            if len(audio) > 0:
                play_audio(audio, sr, volume=DEFAULT_VOLUME)
                time.sleep(0.1)
        print("--- 🔴 PLAYBACK ENDED ---\n")