# Imports

# > Standard Library
import os
import json
import time
import logging
from pathlib import Path
from typing import List, Union, Tuple, Optional, Any

# > Third-Party Libraries
import cv2
import numpy as np
from PIL import Image, ImageGrab

# > Local Dependencies
from .config import DATA_DIR, LOG_LEVEL, TEMPLATES_DIR

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger(name: str) -> logging.Logger:
    """Configures a standard logger outputting to console."""
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    if not logger.handlers:
        ch = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - [%(name)s] - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger


log = setup_logger("UTILS")


# --- DATA MANAGEMENT ---

def get_file_paths(mode: str) -> Tuple[Path, Path]:
    """
    Returns file paths for coordinates and memory based on mode.

    Parameters
    ----------
    mode : str
        'echoes' or 'retail'.

    Returns
    -------
    Tuple[Path, Path]
        (coords_path, memory_path)
    """
    safe_mode = mode.lower().strip()
    return (
        DATA_DIR / f"coords_{safe_mode}.json",
        DATA_DIR / f"npc_memory_{safe_mode}.json",
    )


def load_coords(mode: str) -> dict:
    """Loads crop coordinates dict from JSON."""
    coords_file, _ = get_file_paths(mode)
    if coords_file.exists():
        try:
            with open(coords_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def save_coords(coords: dict, mode: str):
    """Saves crop coordinates dict to JSON."""
    coords_file, _ = get_file_paths(mode)
    with open(coords_file, "w") as f:
        json.dump(coords, f, indent=4)


def load_npc_memory(mode: str) -> dict:
    """Loads the history of spoken NPCs and their assigned voices."""
    _, memory_file = get_file_paths(mode)
    if memory_file.exists():
        try:
            with open(memory_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def save_npc_memory(memory: dict, mode: str):
    """Saves the NPC voice history."""
    _, memory_file = get_file_paths(mode)
    with open(memory_file, "w") as f:
        json.dump(memory, f, indent=4)


# --- RETAIL: QUEST WINDOW DETECTION ---

_TEMPLATES: List[cv2.Mat] = []


def _load_templates() -> List[np.ndarray]:
    """Lazy-loads PNG templates from the templates directory."""
    global _TEMPLATES
    if _TEMPLATES:
        return _TEMPLATES

    if not TEMPLATES_DIR.exists():
        pass

    for fn in TEMPLATES_DIR.glob("*.png"):
        tmpl = cv2.imread(str(fn), cv2.IMREAD_GRAYSCALE)
        if tmpl is not None:
            _TEMPLATES.append(tmpl)

    if not _TEMPLATES:
        log.warning(f"No quest templates found in {TEMPLATES_DIR}")
    else:
        log.info(f"Loaded {len(_TEMPLATES)} detection templates.")

    return _TEMPLATES


def detect_quest_window(
        image_source: Union[str, np.ndarray], threshold: float = 0.8
) -> bool:
    """
    Checks if any quest icon template is present in the image.

    Parameters
    ----------
    image_source : Union[str, np.ndarray]
        File path or numpy array of the screenshot.
    threshold : float
        Correlation threshold (0.0 to 1.0) for template matching.

    Returns
    -------
    bool
        True if a quest window icon is detected.
    """
    if isinstance(image_source, str):
        img = cv2.imread(image_source, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"Could not read screenshot {image_source}")
    else:
        if len(image_source.shape) == 3:
            img = cv2.cvtColor(image_source, cv2.COLOR_BGR2GRAY)
        else:
            img = image_source

    templates = _load_templates()
    if not templates:
        return True  # Fail-safe

    for tmpl in templates:
        res = cv2.matchTemplate(img, tmpl, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        if loc[0].size > 0:
            return True

    return False


# --- RETAIL: LOG WATCHER ---

def watch_npc_file(callback, log_path: str, ready_event=None):
    """
    Tails the LOTRO script.log. When a new line appears, triggers callback.

    Parameters
    ----------
    callback : function
        Function to call with (npc_name) when a line is read.
    log_path : str
        Path to Script.log.
    ready_event : threading.Event, optional
        Set when the watcher is ready.
    """
    watcher_log = setup_logger("WATCHER")

    while not os.path.exists(log_path):
        watcher_log.warning(f"Log file {log_path} not found - waiting...")
        time.sleep(2)

    last_size = os.path.getsize(log_path)

    if ready_event is not None:
        ready_event.set()

    watcher_log.info(f"Watching: {log_path}")

    while True:
        try:
            if not os.path.exists(log_path):
                time.sleep(1)
                continue

            size = os.path.getsize(log_path)
            if size > last_size:
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(last_size)
                    new_lines = f.readlines()
                last_size = size

                for line in new_lines:
                    name = line.strip()
                    if name:
                        watcher_log.info(f"New NPC detected: {name}")
                        callback(name)

        except Exception as exc:
            watcher_log.exception(f"Watcher error: {exc}")

        time.sleep(0.5)


# --- SCREEN CAPTURE UTILS ---

def get_crop_roi_interactive(
        img_np: np.ndarray, prompt_title: str = "SELECT AREA", full_screen: bool = False
) -> Optional[Tuple[int, int, int, int]]:
    """
    Opens an OpenCV window for the user to select a region of interest.

    Returns
    -------
    Tuple[int, int, int, int] or None
        (x, y, w, h) of the selected area.
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

    cv2.imshow(window_name, img_np)
    cv2.waitKey(1)

    r = cv2.selectROI(window_name, img_np, fromCenter=False, showCrosshair=True)
    cv2.destroyAllWindows()

    if r[2] == 0 or r[3] == 0:
        return None

    return int(r[0]), int(r[1]), int(r[2]), int(r[3])


def capture_screen_areas(mode_prefix: str = "echoes") -> Tuple[Any, Any]:
    """
    Captures screen and crops based on mode settings.
    Handles interactive setup if coordinates are missing.

    Parameters
    ----------
    mode_prefix : str
        'echoes' or 'retail'.

    Returns
    -------
    Tuple[Any, Any]
        If mode='echoes': Returns (quest_pil, name_pil).
        If mode='retail': Returns (quest_pil, screenshot_np).
        Returns (None, None) on failure.
    """
    try:
        screenshot = ImageGrab.grab()
    except OSError:
        log.error("Failed to grab screen.")
        return None, None

    screenshot_np = np.array(screenshot)
    screenshot_np = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)

    # LOAD COORDS for specific mode
    all_coords = load_coords(mode_prefix)

    q_key = f"{mode_prefix}_quest"
    n_key = f"{mode_prefix}_name"

    # --- Setup Checks ---
    missing_quest = q_key not in all_coords
    missing_name = mode_prefix == "echoes" and n_key not in all_coords

    if missing_quest or missing_name:
        log.info(f"⚠️ {mode_prefix.upper()} Coordinates missing. Initiating Setup...")

        if missing_quest:
            q_roi = get_crop_roi_interactive(
                screenshot_np,
                prompt_title=f"SELECT QUEST TEXT ({mode_prefix})",
                full_screen=True,
            )
            if not q_roi:
                return None, None
            all_coords[q_key] = q_roi

        if missing_name:
            n_roi = get_crop_roi_interactive(
                screenshot_np, prompt_title="SELECT NPC NAME PLATE", full_screen=True
            )
            if not n_roi:
                return None, None
            all_coords[n_key] = n_roi

        # SAVE COORDS for specific mode
        save_coords(all_coords, mode_prefix)

    # --- Extraction ---
    h, w, _ = screenshot_np.shape

    qx, qy, qw, qh = all_coords[q_key]
    # Sanity check bounds
    if qx + qw > w or qy + qh > h:
        log.warning("Quest coordinates off-screen. Resetting.")
        del all_coords[q_key]
        save_coords(all_coords, mode_prefix)
        return None, None

    quest_np = screenshot_np[qy: qy + qh, qx: qx + qw]
    quest_pil = Image.fromarray(cv2.cvtColor(quest_np, cv2.COLOR_BGR2RGB))

    if mode_prefix == "echoes":
        nx, ny, nw, nh = all_coords[n_key]
        if nx + nw > w or ny + nh > h:
            log.warning("Name coordinates off-screen. Resetting.")
            del all_coords[n_key]
            save_coords(all_coords, mode_prefix)
            return None, None

        name_np = screenshot_np[ny: ny + nh, nx: nx + nw]
        name_pil = Image.fromarray(cv2.cvtColor(name_np, cv2.COLOR_BGR2RGB))
        return quest_pil, name_pil

    # Retail: Return (Quest, FullScreen for Detection)
    return quest_pil, screenshot_np