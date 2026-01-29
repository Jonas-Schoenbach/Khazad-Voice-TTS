# Imports

# > Standard library
import os
import time
import random
from threading import Event

# > Third party imports
import cv2
import numpy as np
from PIL import Image, ImageGrab
from pynput import mouse

# > Local dependencies
from src.config import SAMPLES_DIR, DEFAULT_VOLUME
from src.db import NPCDatabase
from src.tts import KokoroBackend
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
    """
    pynput Callback: specific check for Middle Mouse Button press.
    """
    if pressed and button == mouse.Button.middle:
        capture_trigger.set()


def get_crop_roi(img_np, prompt_title="SELECT AREA", full_screen=False):
    """
    Opens an OpenCV window for cropping.
    """
    if img_np is None:
        return None

    print(f"\n--- {prompt_title} ---")
    print("1. Click/Drag to box the area.")
    print("2. Press SPACE/ENTER to confirm.")
    print("3. Press 'c' to cancel.")

    window_name = prompt_title
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    if full_screen:
        # Overlay on top of everything for the initial setup
        cv2.setWindowProperty(
            window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
        )
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

    r = cv2.selectROI(window_name, img_np, fromCenter=False, showCrosshair=True)
    cv2.destroyAllWindows()

    # ROI format: (x, y, w, h)
    if r[2] == 0 or r[3] == 0:
        return None
    return int(r[0]), int(r[1]), int(r[2]), int(r[3])


def capture_dual_areas(mode_prefix="echoes"):
    """
    Captures screen and returns (quest_img_pil, npc_name_img_pil).
    Handles saving/loading coordinates for BOTH regions.
    Args:
        mode_prefix: String to distinguish coords between modes (e.g. 'echoes' vs 'retail')
    """
    print("📸 Capturing screen...")
    screenshot = ImageGrab.grab()  # Captures primary monitor
    screenshot_np = np.array(screenshot)

    # Convert RGB (PIL) to BGR (OpenCV)
    screenshot_np = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)

    # Load existing coordinates
    all_coords = load_coords()

    # Ensure we look for the specific mode's coords
    # Structure: { "echoes_quest": [...], "echoes_name": [...], "retail_quest": ... }
    q_key = f"{mode_prefix}_quest"
    n_key = f"{mode_prefix}_name"

    # Check if we have both required regions
    if (
        not isinstance(all_coords, dict)
        or q_key not in all_coords
        or n_key not in all_coords
    ):
        print(f"⚠️ {mode_prefix.upper()} Coordinates missing. Initiating Setup...")

        # 1. Select Quest Text
        q_roi = get_crop_roi(
            screenshot_np, prompt_title="SELECT QUEST TEXT WINDOW", full_screen=True
        )
        if not q_roi:
            return None, None

        # 2. Select NPC Name
        n_roi = get_crop_roi(
            screenshot_np, prompt_title="SELECT NPC NAME PLATE", full_screen=True
        )
        if not n_roi:
            return None, None

        all_coords[q_key] = q_roi
        all_coords[n_key] = n_roi
        save_coords(all_coords)

    # --- Crop Quest Region ---
    qx, qy, qw, qh = all_coords[q_key]
    img_h, img_w, _ = screenshot_np.shape

    if qx + qw > img_w or qy + qh > img_h:
        log.warning(f"Saved {q_key} coordinates are outside current screen. Resetting.")
        # Clear specific keys
        del all_coords[q_key]
        del all_coords[n_key]
        save_coords(all_coords)
        return None, None

    quest_np = screenshot_np[qy : qy + qh, qx : qx + qw]

    # --- Crop Name Region ---
    nx, ny, nw, nh = all_coords[n_key]
    if nx + nw > img_w or ny + nh > img_h:
        log.warning(f"Saved {n_key} coordinates are outside current screen. Resetting.")
        del all_coords[q_key]
        del all_coords[n_key]
        save_coords(all_coords)
        return None, None

    name_np = screenshot_np[ny : ny + nh, nx : nx + nw]

    # Convert both back to PIL for OCR
    quest_pil = Image.fromarray(cv2.cvtColor(quest_np, cv2.COLOR_BGR2RGB))
    name_pil = Image.fromarray(cv2.cvtColor(name_np, cv2.COLOR_BGR2RGB))

    return quest_pil, name_pil


def process_narrator(quest_img, name_img, db, tts):
    """
    Common logic for both Echoes and Retail:
    1. OCR Quest Text
    2. OCR NPC Name (Optimized)
    3. Check Memory (Persisted Voice)
    4. If new, Fuzzy Match DB -> Pick Voice -> Save Memory
    5. Stream Audio
    """
    # 1. Quest Text
    print("\nReading Quest Text...")
    sentences = run_ocr(quest_img)
    if not sentences:
        log.warning("No quest text found.")
        return

    # 2. NPC Name (Optimized)
    print("Reading NPC Name...")
    ocr_name_clean = run_name_ocr(name_img)
    if not ocr_name_clean:
        ocr_name_clean = "Unknown"

    print(f"📝 OCR Name: '{ocr_name_clean}'")

    # 3. Voice Resolution
    memory = load_npc_memory()
    mem_key = ocr_name_clean.lower()

    if mem_key in memory:
        # HIT: Use stored voice
        data = memory[mem_key]
        voice_id = data["voice_id"]
        print(f"🧠 Memory Recall: '{data['name']}' -> Voice: {voice_id}")
    else:
        # MISS: Resolve new
        print("🔍 Resolving new NPC...")
        gender, race, matched_name = db.lookup(ocr_name_clean)

        if gender and race:
            print(f"✅ DB Match: {matched_name} ({race} {gender})")
        else:
            print("⚠️ No DB match. Assigning Random Profile.")
            races = ["Men", "Elf", "Dwarf", "Hobbit"]
            genders = ["Male", "Female"]
            race = random.choice(races)
            gender = random.choice(genders)
            matched_name = ocr_name_clean

        voice_id, category = tts.pick_voice(gender, race)

        # Save to Memory
        memory[mem_key] = {
            "name": matched_name,
            "race": race,
            "gender": gender,
            "voice_id": voice_id,
        }
        save_npc_memory(memory)
        print(f"💾 Saved to memory: {matched_name} -> {voice_id} ({category})")

    # 4. Playback
    print("\n--- PLAYBACK (Streaming) ---")
    for i, line in enumerate(sentences):
        print(f"Line {i + 1}: {line}")
        audio = tts.generate(line, voice_id)
        play_audio(audio, tts.samplerate, volume=DEFAULT_VOLUME)
        time.sleep(0.2)


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
    tts = KokoroBackend()

    if mode_choice == "1":
        # --- ORIGINAL FILE MODE ---
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

            # Simple fallback for file mode
            voice_id, _ = tts.pick_voice("Male", "Men")
            for line in sentences:
                print(f"Playing: {line}")
                play_audio(
                    tts.generate(line, voice_id), tts.samplerate, volume=DEFAULT_VOLUME
                )

        except Exception as e:
            log.error(f"Error in File Mode: {e}")
            return

    elif mode_choice in ["2", "3"]:
        # --- LIVE CAPTURE MODES ---
        is_retail = mode_choice == "3"
        mode_name = "RETAIL (WIP)" if is_retail else "ECHOES OF ANGMAR"
        mode_prefix = "retail" if is_retail else "echoes"

        print(f"\n--- {mode_name} MODE ACTIVE ---")
        if is_retail:
            print("⚠️ NOTE: This mode is experimental for the modern Retail client.")

        print("Go to your game window.")
        print("CLICK MIDDLE MOUSE BUTTON to capture.")
        print("  - First run: Select Quest Text area -> Then NPC Name area.")
        print("  - Subsequent runs: Uses saved coordinates.")
        print("Press Ctrl+C in this terminal to quit.")

        listener = mouse.Listener(on_click=on_click)
        listener.start()

        try:
            while True:
                if capture_trigger.is_set():
                    capture_trigger.clear()

                    print("⏳ Delaying capture by 1s (waiting for UI)...")
                    time.sleep(1.0)

                    # Capture & Process
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
