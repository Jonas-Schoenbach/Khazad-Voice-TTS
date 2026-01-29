# Imports

# Standard library
import logging
import sys
import json
from pathlib import Path

# Local dependencies
from .config import DATA_DIR

def setup_logger(name: str) -> logging.Logger:
    """Configures a standard logger outputting to console."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

# --- COORDINATE PERSISTENCE ---

def load_coords(filename="coords.json"):
    """Loads crop coordinates dict from JSON."""
    path = DATA_DIR / filename
    if path.exists():
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load coords: {e}")
    return {}

def save_coords(coords: dict, filename="coords.json"):
    """Saves crop coordinates dict to JSON."""
    path = DATA_DIR / filename
    try:
        with open(path, "w") as f:
            json.dump(coords, f, indent=4)
        logging.info(f"Coordinates saved to {path}")
    except Exception as e:
        logging.error(f"Failed to save coords: {e}")

# --- NPC MEMORY PERSISTENCE ---

def load_npc_memory(filename="npc_memory.json"):
    """Loads the history of spoken NPCs and their assigned voices."""
    path = DATA_DIR / filename
    if path.exists():
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load NPC memory: {e}")
    return {}

def save_npc_memory(memory: dict, filename="npc_memory.json"):
    """Saves the NPC voice history."""
    path = DATA_DIR / filename
    try:
        with open(path, "w") as f:
            json.dump(memory, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to save NPC memory: {e}")