# Imports

# > Standard Library
import os
import json
import logging
from pathlib import Path

# > Third-Party Libraries
import cv2
import numpy as np
from PIL import Image, ImageGrab

# > Local Dependencies
from .config import DATA_DIR, LOG_LEVEL

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)
COORDS_FILE = DATA_DIR / "coords.json"
MEMORY_FILE = DATA_DIR / "npc_memory.json"


def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    if not logger.handlers:
        ch = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger


log = setup_logger("UTILS")


# --- DATA MANAGEMENT ---

def load_coords():
    if COORDS_FILE.exists():
        try:
            with open(COORDS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def save_coords(coords):
    with open(COORDS_FILE, 'w') as f:
        json.dump(coords, f, indent=4)


def load_npc_memory():
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def save_npc_memory(memory):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f, indent=4)


# --- SCREEN CAPTURE UTILS ---

def get_crop_roi_interactive(img_np, prompt_title="SELECT AREA", full_screen=False):
    """
    Opens a window allowing the user to click-and-drag to select a region of interest.
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
        cv2.setWindowProperty(
            window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
        )
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

    # Allow the window to open and render
    cv2.imshow(window_name, img_np)
    cv2.waitKey(1)

    # Selection Loop
    r = cv2.selectROI(window_name, img_np, fromCenter=False, showCrosshair=True)
    cv2.destroyAllWindows()

    # r is (x, y, w, h). If w or h is 0, selection was cancelled or invalid.
    if r[2] == 0 or r[3] == 0:
        return None

    return int(r[0]), int(r[1]), int(r[2]), int(r[3])


def capture_screen_areas(mode_prefix="echoes"):
    """
    Captures the screen, checks for saved coordinates, and returns crops 
    for the Quest Text and NPC Name. 
    If coords are missing, triggers interactive setup.
    """
    # 1. Grab Full Screen
    try:
        screenshot = ImageGrab.grab()
    except OSError:
        log.error("Failed to grab screen. Ensure Game is visible.")
        return None, None

    screenshot_np = np.array(screenshot)
    # Convert RGB (PIL) to BGR (OpenCV)
    screenshot_np = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)

    all_coords = load_coords()
    q_key = f"{mode_prefix}_quest"
    n_key = f"{mode_prefix}_name"

    # 2. Check if setup is needed
    if (not isinstance(all_coords, dict) or
            q_key not in all_coords or
            n_key not in all_coords):

        log.info(f"⚠️ {mode_prefix.upper()} Coordinates missing. Initiating Setup...")

        # Setup Quest Area
        q_roi = get_crop_roi_interactive(
            screenshot_np,
            prompt_title="SELECT QUEST TEXT WINDOW",
            full_screen=True
        )
        if not q_roi:
            log.warning("Quest selection cancelled.")
            return None, None

        # Setup Name Area
        n_roi = get_crop_roi_interactive(
            screenshot_np,
            prompt_title="SELECT NPC NAME PLATE",
            full_screen=True
        )
        if not n_roi:
            log.warning("Name selection cancelled.")
            return None, None

        all_coords[q_key] = q_roi
        all_coords[n_key] = n_roi
        save_coords(all_coords)

    # 3. Extract Crops
    qx, qy, qw, qh = all_coords[q_key]
    nx, ny, nw, nh = all_coords[n_key]

    img_h, img_w, _ = screenshot_np.shape

    # Validate coords fit on current screen (in case resolution changed)
    if (qx + qw > img_w or qy + qh > img_h or
            nx + nw > img_w or ny + nh > img_h):
        log.warning("Saved coordinates are outside current screen. Resetting...")
        # Clear bad coords so next run triggers setup
        if q_key in all_coords: del all_coords[q_key]
        if n_key in all_coords: del all_coords[n_key]
        save_coords(all_coords)
        return None, None

    # Perform Crops
    quest_np = screenshot_np[qy: qy + qh, qx: qx + qw]
    name_np = screenshot_np[ny: ny + nh, nx: nx + nw]

    # Convert back to PIL for OCR engine
    quest_pil = Image.fromarray(cv2.cvtColor(quest_np, cv2.COLOR_BGR2RGB))
    name_pil = Image.fromarray(cv2.cvtColor(name_np, cv2.COLOR_BGR2RGB))

    return quest_pil, name_pil