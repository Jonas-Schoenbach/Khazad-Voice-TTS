# Imports

# > Standard library
import time
import sys
from threading import Event

# > Third party imports
from pynput import mouse

# > Local dependencies
from src.utils import setup_logger, load_coords, save_coords
from src.db import NPCDatabase
from src.tts import get_tts_backend
from src.engine import NarratorEngine
from src.utils import  capture_screen_areas

log = setup_logger("MAIN")
capture_trigger = Event()


def on_click(x, y, button, pressed):
    if pressed and button == mouse.Button.middle:
        capture_trigger.set()


def main():
    print(r"""
    ========================================
       LOTRO NARRATOR - AI VOICE OVER
    ========================================
    """)

    # 1. Initialize Components
    try:
        db = NPCDatabase()
        tts = get_tts_backend()
        engine = NarratorEngine(db, tts)
    except Exception as e:
        log.error(f"Initialization Failed: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

    # 2. Start Listener
    print("\n[INSTRUCTIONS]")
    print("1. Go to LOTRO.")
    print("2. Open a quest window.")
    print("3. CLICK MIDDLE MOUSE BUTTON to narrate.")
    print("   (First time run will ask you to draw boxes)\n")

    listener = mouse.Listener(on_click=on_click)
    listener.start()

    # 3. Main Loop
    try:
        while True:
            if capture_trigger.is_set():
                capture_trigger.clear()
                print("⏳ Capturing...")
                time.sleep(0.5)  # Wait for UI click ripple to fade
                q_img, n_img = capture_screen_areas()

                if q_img and n_img:
                    engine.process_capture(q_img, n_img)

                print("✅ Ready.")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Exiting...")
        listener.stop()


if __name__ == "__main__":
    main()