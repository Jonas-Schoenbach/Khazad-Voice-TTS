# Imports

# > Standard library
import os

# > Third party imports
import cv2
from PIL import Image

# > Local dependencies
from src.config import SAMPLES_DIR, DEFAULT_VOLUME
from src.db import NPCDatabase
from src.tts import KokoroBackend
from src.ocr import run_ocr
from src.audio import play_audio
from src.utils import setup_logger

log = setup_logger("MAIN")


def get_crop_roi(image_path):
    """
    Opens an OpenCV window for cropping.
    """
    img = cv2.imread(str(image_path))
    if img is None:
        return None

    print("\n--- INSTRUCTIONS ---")
    print("1. Click/Drag to box the text.")
    print("2. Press SPACE/ENTER to confirm.")
    print("3. Press 'c' to cancel.")

    cv2.namedWindow("CROP", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("CROP", cv2.WND_PROP_TOPMOST, 1)
    r = cv2.selectROI("CROP", img, fromCenter=False, showCrosshair=True)
    cv2.destroyAllWindows()

    if r[2] == 0 or r[3] == 0:
        return None
    return int(r[0]), int(r[1]), int(r[2]), int(r[3])


def select_npc_from_random(db: NPCDatabase):
    """
    Shows random NPCs to allow the user to pick a Race/Gender profile.
    """
    print("\n⚠️ NPC not detected automatically.")
    print("   Please select a similar NPC from the list below to match Race/Gender.")
    print("   (The specific name doesn't matter, only the Race and Gender)")

    while True:
        # 1. Get 10 random NPCs
        candidates = db.get_random_npcs(10)

        print("\n--- VOICE PALETTE (Random Selection) ---")
        for i, row in enumerate(candidates):
            # Print format: [0] Bingo Boffin (Hobbit Male)
            print(f"[{i}] {row['Name'][:25]:<25} \t({row['Race']} {row['Gender']})")

        print("[r] Reroll (Get 10 new randoms)")
        print("[m] Manual Entry (Type Race/Gender yourself)")

        choice = input("\nSelect Option: ").strip().lower()

        if choice == "m":
            return None, None, None
        elif choice == "r":
            continue  # Loop again to get new randoms

        try:
            idx = int(choice)
            if 0 <= idx < len(candidates):
                selected = candidates[idx]
                return selected["Name"], selected["Gender"], selected["Race"]
            else:
                print("❌ Invalid number.")
        except ValueError:
            print("❌ Invalid input.")


def main():
    print("========================================")
    print("       LOTRO NARRATOR - CLI             ")
    print("========================================")

    # 1. Init
    db = NPCDatabase()
    tts = KokoroBackend()

    # 2. Select Image
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
    except:
        return

    # 3. Crop & OCR
    roi = get_crop_roi(img_path)
    if not roi:
        return

    full_img = Image.open(img_path)
    cropped_img = full_img.crop((roi[0], roi[1], roi[0] + roi[2], roi[1] + roi[3]))

    print("\nReading text...")
    sentences = run_ocr(cropped_img)
    if not sentences:
        log.warning("No text found.")
        return

    # 4. NPC Detection
    ocr_guess = sentences[0] if sentences else ""
    print(f"\n📝 OCR Read Name: '{ocr_guess}'")

    # Try automatic lookup first
    gender, race = db.lookup(ocr_guess)

    final_name = ocr_guess

    if gender and race:
        print(f"✅ Auto-Matched in DB: {final_name} ({race} {gender})")
    else:
        # If not found, trigger the Random Selection Palette
        sel_name, sel_gender, sel_race = select_npc_from_random(db)

        if sel_name:
            # We use the Race/Gender from the selected random NPC
            # But we keep the name from the OCR (or just generic)
            gender = sel_gender
            race = sel_race
            print(f"✅ Applied Config from {sel_name}: {race} {gender}")
        else:
            # Manual Fallback
            gender = input("Enter Gender (Male, Female): ").strip()
            race = input("Enter Race (Men, Elf, Dwarf, Hobbit): ").strip()

    # 5. Playback
    voice_id, category = tts.pick_voice(gender, race)
    print(f"\n🎙️ Selected Voice: {voice_id} ({category})")

    print("\n--- PLAYBACK ---")
    for i, line in enumerate(sentences):
        print(f"\nLine {i + 1}: {line}")
        action = input("Press ENTER to play, 's' to skip, 'q' to quit: ").lower()
        if action == "q":
            break
        if action == "s":
            continue

        play_audio(tts.generate(line, voice_id), tts.samplerate, volume=DEFAULT_VOLUME)


if __name__ == "__main__":
    main()
