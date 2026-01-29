# Imports

# > Standard library
import os
import time
import random
import queue
import threading
from threading import Event

# > Third party imports
import cv2
import numpy as np
from PIL import Image, ImageGrab
from pynput import mouse

# > Local dependencies
from src.config import SAMPLES_DIR, DEFAULT_VOLUME
from src.db import NPCDatabase
from src.tts import get_tts_backend
from src.ocr import run_ocr, run_name_ocr
from src.audio import play_audio
from src.utils import (
    setup_logger,
    load_coords,
    save_coords,
    load_npc_memory,
    save_npc_memory,
)

log = setup_logger("MAIN")

# Event flag to trigger processing from the mouse thread
capture_trigger = Event()


def on_click(x, y, button, pressed):
    if pressed and button == mouse.Button.middle:
        capture_trigger.set()


def get_crop_roi(img_np, prompt_title="SELECT AREA", full_screen=False):
    if img_np is None:
        return None

    print(f"\n--- {prompt_title} ---")
    print("1. Click/Drag to box the area.")
    print("2. Press SPACE/ENTER to confirm.")
    print("3. Press 'c' to cancel.")

    window_name = prompt_title
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    if full_screen:
        cv2.setWindowProperty(
            window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
        )
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

    r = cv2.selectROI(window_name, img_np, fromCenter=False, showCrosshair=True)
    cv2.destroyAllWindows()

    if r[2] == 0 or r[3] == 0:
        return None
    return int(r[0]), int(r[1]), int(r[2]), int(r[3])


def capture_dual_areas(mode_prefix="echoes"):
    print("📸 Capturing screen...")
    screenshot = ImageGrab.grab()
    screenshot_np = np.array(screenshot)
    screenshot_np = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)

    all_coords = load_coords()
    q_key = f"{mode_prefix}_quest"
    n_key = f"{mode_prefix}_name"

    if (
            not isinstance(all_coords, dict)
            or q_key not in all_coords
            or n_key not in all_coords
    ):
        print(f"⚠️ {mode_prefix.upper()} Coordinates missing. Initiating Setup...")
        q_roi = get_crop_roi(
            screenshot_np, prompt_title="SELECT QUEST TEXT WINDOW", full_screen=True
        )
        if not q_roi:
            return None, None

        n_roi = get_crop_roi(
            screenshot_np, prompt_title="SELECT NPC NAME PLATE", full_screen=True
        )
        if not n_roi:
            return None, None

        all_coords[q_key] = q_roi
        all_coords[n_key] = n_roi
        save_coords(all_coords)

    qx, qy, qw, qh = all_coords[q_key]
    img_h, img_w, _ = screenshot_np.shape

    if qx + qw > img_w or qy + qh > img_h:
        log.warning(f"Saved {q_key} coordinates are outside current screen. Resetting.")
        del all_coords[q_key]
        del all_coords[n_key]
        save_coords(all_coords)
        return None, None

    quest_np = screenshot_np[qy: qy + qh, qx: qx + qw]

    nx, ny, nw, nh = all_coords[n_key]
    if nx + nw > img_w or ny + nh > img_h:
        log.warning(f"Saved {n_key} coordinates are outside current screen. Resetting.")
        del all_coords[q_key]
        del all_coords[n_key]
        save_coords(all_coords)
        return None, None

    name_np = screenshot_np[ny: ny + nh, nx: nx + nw]
    quest_pil = Image.fromarray(cv2.cvtColor(quest_np, cv2.COLOR_BGR2RGB))
    name_pil = Image.fromarray(cv2.cvtColor(name_np, cv2.COLOR_BGR2RGB))

    return quest_pil, name_pil


def play_streaming(sentences, tts, voice_id):
    """
    Producer-Consumer Pipeline:
    - Thread 1 (Producer): Generates audio on GPU and pushes to Queue.
    - Thread 2 (Main): Pulls from Queue and plays audio immediately.
    """
    audio_queue = queue.Queue()

    # --- Producer Thread ---
    def generator_worker():
        for line in sentences:
            if not line.strip():
                continue

            # Generate Audio (This blocks the worker thread, but not playback)
            audio = tts.generate(line, voice_id)

            # Grab the samplerate used for this specific clip
            sr = tts.samplerate

            # Push result to queue
            audio_queue.put((line, audio, sr))

        # Signal End of Queue
        audio_queue.put(None)

    # Start the generation in background
    gen_thread = threading.Thread(target=generator_worker, daemon=True)
    gen_thread.start()

    # --- Consumer (Main Thread) ---
    print("\n--- STREAMING PLAYBACK ---")

    while True:
        # Get next audio chunk (blocks if generator is slower than playback)
        item = audio_queue.get()

        # Check for sentinel (End of Stream)
        if item is None:
            break

        text, audio, sr = item
        print(f"▶️ Playing: {text}")

        if len(audio) > 0:
            play_audio(audio, sr, volume=DEFAULT_VOLUME)
            # Small natural pause between sentences
            time.sleep(0.15)


def process_narrator(quest_img, name_img, db, tts):
    # 1. Quest Text
    print("\nReading Quest Text...")
    sentences = run_ocr(quest_img)
    if not sentences:
        log.warning("No quest text found.")
        return

    # 2. NPC Name
    print("Reading NPC Name...")
    ocr_name_clean = run_name_ocr(name_img)
    if not ocr_name_clean:
        ocr_name_clean = "Unknown"

    print(f"📝 OCR Name: '{ocr_name_clean}'")

    # 3. Voice Resolution
    memory = load_npc_memory()
    mem_key = ocr_name_clean.lower()

    if mem_key in memory:
        data = memory[mem_key]
        voice_id = data["voice_id"]
        print(f"🧠 Memory Recall: '{data['name']}' -> Voice: {voice_id}")
    else:
        print("🔍 Resolving new NPC...")
        gender, race, matched_name = db.lookup(ocr_name_clean)

        if gender and race:
            print(f"✅ DB Match: {matched_name} ({race} {gender})")
        else:
            print("⚠️ No DB match. Using Default Narrator.")
            matched_name = "Narrator"
            race = "Narrator"
            gender = "Narrator"

        voice_id, category = tts.pick_voice(gender, race)

        memory[mem_key] = {
            "name": matched_name,
            "race": race,
            "gender": gender,
            "voice_id": voice_id,
        }
        save_npc_memory(memory)
        print(f"💾 Saved to memory: {matched_name} -> {voice_id} ({category})")

    # 4. Streamed Playback
    play_streaming(sentences, tts, voice_id)


def main():
    print("========================================")
    print("       LOTRO NARRATOR - CLI             ")
    print("========================================")
    print("[1] File Mode (Process Saved Images)")
    print("[2] Echoes of Angmar Mode (Live Capture)")
    print("[3] Retail Mode (IN-PROGRESS)")

    mode_choice = input("\nSelect Mode: ").strip()

    # Init Core Systems
    db = NPCDatabase()
    tts = get_tts_backend()

    if mode_choice == "1":
        files = [
            f for f in os.listdir(SAMPLES_DIR) if f.lower().endswith((".png", ".jpg"))
        ]
        if not files:
            log.error(f"No images in {SAMPLES_DIR}")
            return

        print("\nAvailable Images:")
        for i, f in enumerate(files):
            print(f"[{i}] {f}")

        try:
            idx = int(input("\nSelect Image ID: "))
            img_path = SAMPLES_DIR / files[idx]
            img_np = cv2.imread(str(img_path))
            roi = get_crop_roi(img_np, prompt_title="CROP TEXT")
            if not roi:
                return

            full_img = Image.open(img_path)
            cropped_img = full_img.crop(
                (roi[0], roi[1], roi[0] + roi[2], roi[1] + roi[3])
            )

            print("\nReading text...")
            sentences = run_ocr(cropped_img)
            if not sentences:
                log.warning("No text found.")
                return

            voice_id, _ = tts.pick_voice("Male", "Men")

            # Use the new streaming function here too
            play_streaming(sentences, tts, voice_id)

        except Exception as e:
            log.error(f"Error in File Mode: {e}")
            return

    elif mode_choice in ["2", "3"]:
        is_retail = mode_choice == "3"
        mode_name = "RETAIL (WIP)" if is_retail else "ECHOES OF ANGMAR"
        mode_prefix = "retail" if is_retail else "echoes"

        print(f"\n--- {mode_name} MODE ACTIVE ---")
        if is_retail:
            print("⚠️ NOTE: This mode is experimental for the modern Retail client.")

        print("Go to your game window.")
        print("CLICK MIDDLE MOUSE BUTTON to capture.")
        print("Press Ctrl+C in this terminal to quit.")

        listener = mouse.Listener(on_click=on_click)
        listener.start()

        try:
            while True:
                if capture_trigger.is_set():
                    capture_trigger.clear()
                    print("⏳ Delaying capture by 1s (waiting for UI)...")
                    time.sleep(1.0)

                    q_img, n_img = capture_dual_areas(mode_prefix=mode_prefix)
                    if q_img and n_img:
                        process_narrator(q_img, n_img, db, tts)
                    print("\nReady for next capture...")
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nStopping listener...")
            listener.stop()

    else:
        print("Invalid selection.")
        return


if __name__ == "__main__":
    main()