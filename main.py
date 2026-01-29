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
    save_npc_memory
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
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

    r = cv2.selectROI(window_name, img_np, fromCenter=False, showCrosshair=True)
    cv2.destroyAllWindows()

    # ROI format: (x, y, w, h)
    if r[2] == 0 or r[3] == 0:
        return None
    return int(r[0]), int(r[1]), int(r[2]), int(r[3])


def capture_dual_areas():
    """
    Captures screen and returns (quest_img_pil, npc_name_img_pil).
    Handles saving/loading coordinates for BOTH regions.
    """
    print("📸 Capturing screen...")
    screenshot = ImageGrab.grab()  # Captures primary monitor
    screenshot_np = np.array(screenshot)

    # Convert RGB (PIL) to BGR (OpenCV)
    screenshot_np = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)

    # Load existing coordinates
    coords = load_coords()

    # Check if we have both required regions
    if not isinstance(coords, dict) or "quest" not in coords or "name" not in coords:
        print("⚠️ Coordinates missing or invalid. Initiating Setup...")

        # 1. Select Quest Text
        q_roi = get_crop_roi(screenshot_np, prompt_title="SELECT QUEST TEXT WINDOW", full_screen=True)
        if not q_roi:
            return None, None

        # 2. Select NPC Name
        # We pass full_screen=True again to ensure overlay is correct
        n_roi = get_crop_roi(screenshot_np, prompt_title="SELECT NPC NAME PLATE", full_screen=True)
        if not n_roi:
            return None, None

        coords = {"quest": q_roi, "name": n_roi}
        save_coords(coords)

    # --- Crop Quest Region ---
    qx, qy, qw, qh = coords["quest"]
    # Boundary check
    img_h, img_w, _ = screenshot_np.shape
    if qx + qw > img_w or qy + qh > img_h:
        log.warning("Saved 'quest' coordinates are outside current screen. Resetting.")
        save_coords({})  # clear corrupt coords
        return None, None

    quest_np = screenshot_np[qy: qy + qh, qx: qx + qw]

    # --- Crop Name Region ---
    nx, ny, nw, nh = coords["name"]
    # Boundary check
    if nx + nw > img_w or ny + nh > img_h:
        log.warning("Saved 'name' coordinates are outside current screen. Resetting.")
        save_coords({})
        return None, None

    name_np = screenshot_np[ny: ny + nh, nx: nx + nw]

    # Convert both back to PIL for OCR
    quest_pil = Image.fromarray(cv2.cvtColor(quest_np, cv2.COLOR_BGR2RGB))
    name_pil = Image.fromarray(cv2.cvtColor(name_np, cv2.COLOR_BGR2RGB))

    return quest_pil, name_pil


def process_echoes_mode(quest_img, name_img, db, tts):
    """
    1. OCR Quest Text
    2. OCR NPC Name
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
        # --- HIT: Use stored voice ---
        data = memory[mem_key]
        voice_id = data["voice_id"]
        print(f"🧠 Memory Recall: '{data['name']}' -> Voice: {voice_id}")
    else:
        # --- MISS: Resolve new ---
        print("🔍 Resolving new NPC...")

        # db.lookup now returns (Gender, Race, RealName)
        gender, race, matched_name = db.lookup(ocr_name_clean)

        if gender and race:
            print(f"✅ DB Match: {matched_name} ({race} {gender})")
        else:
            print("⚠️ No DB match. Assigning Random Profile.")
            # Random fallback
            races = ["Men", "Elf", "Dwarf", "Hobbit"]
            genders = ["Male", "Female"]
            race = random.choice(races)
            gender = random.choice(genders)
            matched_name = ocr_name_clean  # Use the raw OCR name if no match found

        # Pick Voice
        voice_id, category = tts.pick_voice(gender, race)

        # Save to Memory
        memory[mem_key] = {
            "name": matched_name,
            "race": race,
            "gender": gender,
            "voice_id": voice_id
        }
        save_npc_memory(memory)
        print(f"💾 Saved to memory: {matched_name} -> {voice_id} ({category})")

    # 4. Playback
    print("\n--- PLAYBACK (Streaming) ---")
    for i, line in enumerate(sentences):
        print(f"Line {i + 1}: {line}")

        # Generate audio (compute)
        audio = tts.generate(line, voice_id)

        # Play audio (this blocks until the sentence finishes)
        play_audio(audio, tts.samplerate, volume=DEFAULT_VOLUME)

        # Small pause for natural flow
        time.sleep(0.2)


def main():
    print("========================================")
    print("       LOTRO NARRATOR - CLI             ")
    print("========================================")
    print("[1] Process Saved Image (File Mode)")
    print("[2] Echoes of Angmar Mode (Middle Mouse)")

    mode_choice = input("\nSelect Mode: ").strip()

    # Init Core Systems
    db = NPCDatabase()
    tts = KokoroBackend()

    if mode_choice == "1":
        # --- ORIGINAL FILE MODE ---
        files = [f for f in os.listdir(SAMPLES_DIR) if f.lower().endswith((".png", ".jpg"))]
        if not files:
            log.error(f"No images in {SAMPLES_DIR}")
            return

        print("\nAvailable Images:")
        for i, f in enumerate(files):
            print(f"[{i}] {f}")

        try:
            idx = int(input("\nSelect Image ID: "))
            img_path = SAMPLES_DIR / files[idx]

            # Use OpenCV to read file for cropping
            img_np = cv2.imread(str(img_path))
            roi = get_crop_roi(img_np, prompt_title="CROP TEXT")
            if not roi:
                return

            full_img = Image.open(img_path)
            cropped_img = full_img.crop((roi[0], roi[1], roi[0] + roi[2], roi[1] + roi[3]))

            # Process file mode (using a simplified standalone logic here to avoid complex dual-capture requirement)
            print("\nReading text...")
            sentences = run_ocr(cropped_img)
            if not sentences:
                log.warning("No text found.")
                return

            ocr_guess = sentences[0] if sentences else ""
            print(f"\n📝 OCR Read Name: '{ocr_guess}'")
            gender, race, _ = db.lookup(ocr_guess)  # Updated lookup returns 3 values now

            if not (gender and race):
                # Simple fallback for file mode
                gender, race = "Male", "Men"

            voice_id, _ = tts.pick_voice(gender, race)
            print(f"🎙️ Voice: {voice_id}")

            for line in sentences:
                print(f"Playing: {line}")
                play_audio(tts.generate(line, voice_id), tts.samplerate, volume=DEFAULT_VOLUME)

        except Exception as e:
            log.error(f"Error in File Mode: {e}")
            return

    elif mode_choice == "2":
        # --- ECHOES OF ANGMAR MODE ---
        print("\n--- ECHOES OF ANGMAR MODE ACTIVE ---")
        print("Go to your game window.")
        print("CLICK MIDDLE MOUSE BUTTON to capture.")
        print("  - First run: Select Quest Text area -> Then NPC Name area.")
        print("  - Subsequent runs: Uses saved coordinates.")
        print("Press Ctrl+C in this terminal to quit.")

        # Start the listener in a non-blocking way
        listener = mouse.Listener(on_click=on_click)
        listener.start()

        try:
            while True:
                # Wait for the event flag
                if capture_trigger.is_set():
                    capture_trigger.clear()

                    # Delay because middle-mouse button hides NPC name window
                    time.sleep(1.0)

                    # Capture & Process
                    q_img, n_img = capture_dual_areas()
                    if q_img and n_img:
                        process_echoes_mode(q_img, n_img, db, tts)

                    print("\nReady for next capture...")

                time.sleep(0.1)  # Reduce CPU usage
        except KeyboardInterrupt:
            print("\nStopping listener...")
            listener.stop()

    else:
        print("Invalid selection.")
        return


if __name__ == "__main__":
    main()