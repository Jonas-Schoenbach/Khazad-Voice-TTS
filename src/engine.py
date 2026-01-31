# Imports

# > Standard Library
import time
import queue
import threading

# > Third-party Libraries
import cv2

# > Local Dependencies
from .utils import setup_logger, save_npc_memory, load_npc_memory
from .ocr import run_ocr, run_name_ocr
from .audio import play_audio
from .config import DEFAULT_VOLUME

log = setup_logger("ENGINE")


class NarratorEngine:
    def __init__(self, db, tts_backend):
        self.db = db
        self.tts = tts_backend
        self.memory = load_npc_memory()
        self.audio_queue = queue.Queue()
        self.is_playing = False

    def process_capture(self, quest_img_pil, name_img_pil):
        """
        Orchestrates the pipeline: OCR -> Lookup -> TTS Generation -> Playback
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

        # 3. Resolve Voice (Memory -> DB -> Random)
        voice_id = self._resolve_voice(npc_name)

        # 4. Generate & Stream Audio
        self._start_streaming(sentences, voice_id)

    def _resolve_voice(self, npc_name):
        key = npc_name.lower()

        # Check Memory
        if key in self.memory:
            data = self.memory[key]
            log.info(f"🧠 Memory Recall: '{data['name']}' -> {data['voice_id']}")
            return data['voice_id']

        # Check Database
        log.info("🔍 Resolving new NPC...")
        gender, race, matched_name = self.db.lookup(npc_name)

        # Fallback
        if not gender or not race:
            log.info("⚠️ No DB match. Using Default Narrator.")
            matched_name = "Narrator"
            race, gender = "Narrator", "Narrator"

        # Pick Voice
        voice_id, category = self.tts.pick_voice(gender, race)

        # Save to Memory
        self.memory[key] = {
            "name": matched_name,
            "race": race,
            "gender": gender,
            "voice_id": voice_id
        }
        save_npc_memory(self.memory)
        log.info(f"💾 Saved: {matched_name} -> {voice_id} ({category})")
        return voice_id

    def _start_streaming(self, sentences, voice_id):
        """Background thread generator, Main thread player"""

        # Generator Thread
        def producer():
            clean_lines = [s.strip() for s in sentences if s.strip()]

            # LuxTTS optimization: Process huge blocks
            if type(self.tts).__name__ == "LuxBackend":
                full_text = " ".join(clean_lines)
                if full_text:
                    audio = self.tts.generate(full_text, voice_id)
                    self.audio_queue.put((full_text, audio, self.tts.samplerate))
            else:
                # Kokoro: Sentence by sentence
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
            display_text = (text[:60] + '...') if len(text) > 60 else text
            print(f"▶️ Speaking: {display_text}")

            if len(audio) > 0:
                play_audio(audio, sr, volume=DEFAULT_VOLUME)
                time.sleep(0.1)  # Breath pause
        print("--- 🔴 PLAYBACK ENDED ---\n")