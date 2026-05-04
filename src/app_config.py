# Imports

# > Standard Library
import configparser
import os
import sys

class AppConfig:
    """
    App Config - INI file in the user's home directory

    The config file is automatically created with default values if it does not exist yet.
    Saving with save_config() writes the current state of the instance attributes to the configuration file.
    """
    def __init__(self):
        self._home_directory = os.path.expanduser("~")
        self._base_directory = os.path.join(self._home_directory, ".khazad-voice-tts")
        self._data_directory = os.path.join(self._base_directory, "data")
        self._config_file_path =os.path.join(self._base_directory, "config.ini")

        if not os.path.exists(self._config_file_path):
            self._write_default_config()

        self._cfg = configparser.ConfigParser()
        self._cfg.optionxform = str
        self._cfg.read(self._config_file_path)

        self._load_config()


    def save_config(self):
        """
        Writes the current state to the configuration file

        Returns
        -------
        None
        """
        self._cfg["PATHS"] = {
            "BASE_DIR": str(self.BASE_DIR),
            "DATA_DIR": str(self.DATA_DIR),
            "SAMPLES_DIR": str(self.SAMPLES_DIR),
            "REF_AUDIO_DIR": str(self.REF_AUDIO_DIR),
            "NPC_DATA_PATH": str(self.NPC_DATA_PATH),
            "TEMPLATES_DIR": str(self.TEMPLATES_DIR),
            "SCRIPT_LOG": str(self.SCRIPT_LOG),
        }

        self._cfg["WIKI"] = {
            "WIKI_BASE_URL": str(self.WIKI_BASE_URL),
            "MISSING_TEXT_INDICATOR": str(self.MISSING_TEXT_INDICATOR),
            "ENABLE_WIKI": "true" if self.ENABLE_WIKI else "false"
        }

        self._cfg["DETECTION"] = {
            "TEMPLATE_THRESHOLD": str(self.TEMPLATE_THRESHOLD),
            "STATIC_TEMPLATE_THRESHOLD": str(self.STATIC_TEMPLATE_THRESHOLD),
            "DEBUG_TEMPLATE_SCORES": str(self.DEBUG_TEMPLATE_SCORES),
            "CORNER_OFFSET_X": str(self.CORNER_OFFSET_X),
            "CORNER_OFFSET_Y": str(self.CORNER_OFFSET_Y),
            "PADDING_ICON_Y": str(self.PADDING_ICON_Y),
            "PADDING_INTERSECT_X": str(self.PADDING_INTERSECT_X),
            "MIN_BOX_DIM": str(self.MIN_BOX_DIM),
            "BASE_RESOLUTION": ",".join(str(number) for number in self.BASE_RESOLUTION),
        }

        self._cfg["DETECTION.DEFAULT_RETAIL_OFFSETS"] = {
            "CORNER_OFFSET_X": str(self.DEFAULT_RETAIL_OFFSETS["RETAIL_CORNER_OFFSET_X"]),
            "CORNER_OFFSET_Y": str(self.DEFAULT_RETAIL_OFFSETS["RETAIL_CORNER_OFFSET_Y"]),
            "PADDING_INTERSECT_X": str(self.DEFAULT_RETAIL_OFFSETS["RETAIL_PADDING_INTERSECT_X"]),
            "PADDING_ICON_Y": str(self.DEFAULT_RETAIL_OFFSETS["RETAIL_PADDING_ICON_Y"])
        }

        self._cfg["DETECTION.DEFAULT_ECHOES_OFFSETS"] = {
            "BODY_LEFT_MARGIN": str(self.DEFAULT_ECHOES_OFFSETS["ECHOES_BODY_LEFT_MARGIN"]),
            "BODY_TOP_MARGIN": str(self.DEFAULT_ECHOES_OFFSETS["ECHOES_BODY_TOP_MARGIN"]),
            "BODY_RIGHT_PADDING": str(self.DEFAULT_ECHOES_OFFSETS["ECHOES_BODY_RIGHT_PADDING"]),
            "BODY_BOTTOM_PADDING": str(self.DEFAULT_ECHOES_OFFSETS["ECHOES_BODY_BOTTOM_PADDING"])
        }

        self._cfg["AUDIO"] = {
            "SAMPLE_RATE": str(self.SAMPLE_RATE),
            "DEFAULT_VOLUME": str(self.DEFAULT_VOLUME),
            "LUX_VOLUME": str(self.LUX_VOLUME),
        }

        self._cfg["TTS"] = {
            "TTS_SPEED": str(self.TTS_SPEED),
            "TTS_WAVE_STEPS": str(self.TTS_WAVE_STEPS),
        }

        self._cfg["OCR"] = {
            "TESSERACT_CMD": str(self.TESSERACT_CMD),
            "POSSIBLE_PATHS": ";".join(self.POSSIBLE_PATHS),
        }

        self._cfg["LOGGING"] = {
            "LOG_LEVEL": str(self.LOG_LEVEL)
        }

        self._cfg["QUEST"] = {
            "QUEST_WINDOW_MODE": str(self.QUEST_WINDOW_MODE),
            "QUEST_WINDOW_BOX": ",".join(str(number) for number in self.QUEST_WINDOW_BOX),
            "QUEST_TRIGGER_MODE": str(self.QUEST_TRIGGER_MODE),
            "QUEST_TRIGGER_KEY": str(self.QUEST_TRIGGER_KEY),
            "NPC_NAME_MAX_AGE": str(self.NPC_NAME_MAX_AGE),
        }

        with open(self._config_file_path, "w") as config_file:
            self._cfg.write(config_file)


    def _load_config(self):
        """
        Loads the app configuration from the configuration file

        Returns
        -------
        None
        """
        # --- PATHS ---
        self.BASE_DIR = self._cfg.get("PATHS", "BASE_DIR")
        self.DATA_DIR = self._cfg.get("PATHS", "DATA_DIR")
        self.SAMPLES_DIR = self._cfg.get("PATHS", "SAMPLES_DIR")
        self.REF_AUDIO_DIR = self._cfg.get("PATHS", "REF_AUDIO_DIR")
        self.NPC_DATA_PATH = self._cfg.get("PATHS", "NPC_DATA_PATH")

        # Retail Mode Paths
        self.TEMPLATES_DIR = self._cfg.get("PATHS", "TEMPLATES_DIR")
        self.SCRIPT_LOG = self._cfg.get("PATHS", "SCRIPT_LOG")

        # --- WIKI SETTINGS ---
        # TODO: reconsider usefulness / accuracy of wiki lookups
        self.WIKI_BASE_URL = self._cfg.get("WIKI", "WIKI_BASE_URL")
        self.MISSING_TEXT_INDICATOR = self._cfg.get("WIKI", "MISSING_TEXT_INDICATOR")

        # Set to True to enable Wiki lookups, False for instant OCR
        self.ENABLE_WIKI = self._cfg.getboolean("WIKI", "ENABLE_WIKI")

        # --- DETECTION SETTINGS ---
        # Thresholds for template matching
        self.TEMPLATE_THRESHOLD = self._cfg.getfloat("DETECTION", "TEMPLATE_THRESHOLD")
        self.STATIC_TEMPLATE_THRESHOLD = self._cfg.getfloat("DETECTION", "STATIC_TEMPLATE_THRESHOLD")

        # Debug: log every template match score (name, value, threshold, pass/fail)
        # Set to True to see detailed matching info in the console output.
        self.DEBUG_TEMPLATE_SCORES = self._cfg.getboolean("DETECTION", "DEBUG_TEMPLATE_SCORES")

        # Offsets for text box extraction (Cascading Logic)
        self.CORNER_OFFSET_X = self._cfg.getint("DETECTION", "CORNER_OFFSET_X")
        self.CORNER_OFFSET_Y = self._cfg.getint("DETECTION", "CORNER_OFFSET_Y")
        self.PADDING_ICON_Y = self._cfg.getint("DETECTION", "PADDING_ICON_Y")
        self.PADDING_INTERSECT_X = self._cfg.getint("DETECTION", "PADDING_INTERSECT_X")
        self.MIN_BOX_DIM = self._cfg.getint("DETECTION", "MIN_BOX_DIM")

        # Base resolution for template scaling — all default templates were captured at 1440p
        self.BASE_RESOLUTION = [int(item.strip()) for item in self._cfg.get("DETECTION", "BASE_RESOLUTION").split(",")]

        # Default layout offsets for retail mode (calibrated at BASE_RESOLUTION)
        # Used as fallback when layout_retail.json is missing
        self.DEFAULT_RETAIL_OFFSETS = {
            "RETAIL_CORNER_OFFSET_X": self._cfg.getint("DETECTION.DEFAULT_RETAIL_OFFSETS", "CORNER_OFFSET_X"),
            "RETAIL_CORNER_OFFSET_Y": self._cfg.getint("DETECTION.DEFAULT_RETAIL_OFFSETS", "CORNER_OFFSET_Y"),
            "RETAIL_PADDING_INTERSECT_X": self._cfg.getint("DETECTION.DEFAULT_RETAIL_OFFSETS", "PADDING_INTERSECT_X"),
            "RETAIL_PADDING_ICON_Y": self._cfg.getint("DETECTION.DEFAULT_RETAIL_OFFSETS", "PADDING_ICON_Y")
        }

        # Default layout offsets for echoes mode (calibrated at BASE_RESOLUTION)
        # Used as fallback when layout_echoes.json is missing
        self.DEFAULT_ECHOES_OFFSETS = {
            "ECHOES_BODY_LEFT_MARGIN": self._cfg.getint("DETECTION.DEFAULT_ECHOES_OFFSETS", "BODY_LEFT_MARGIN"),
            "ECHOES_BODY_TOP_MARGIN": self._cfg.getint("DETECTION.DEFAULT_ECHOES_OFFSETS", "BODY_TOP_MARGIN"),
            "ECHOES_BODY_RIGHT_PADDING": self._cfg.getint("DETECTION.DEFAULT_ECHOES_OFFSETS", "BODY_RIGHT_PADDING"),
            "ECHOES_BODY_BOTTOM_PADDING": self._cfg.getint("DETECTION.DEFAULT_ECHOES_OFFSETS", "BODY_BOTTOM_PADDING")
        }

        # --- AUDIO SETTINGS ---
        self.SAMPLE_RATE = self._cfg.getint("AUDIO", "SAMPLE_RATE")
        self.DEFAULT_VOLUME = self._cfg.getfloat("AUDIO", "DEFAULT_VOLUME")
        self.LUX_VOLUME = self._cfg.getfloat("AUDIO", "LUX_VOLUME")

        # --- TTS SETTINGS ---
        self.TTS_SPEED = self._cfg.getfloat("TTS", "TTS_SPEED")
        self.TTS_WAVE_STEPS = self._cfg.getint("TTS", "TTS_WAVE_STEPS")

        # --- OCR SETTINGS ---
        # We check standard Windows paths to find Tesseract automatically
        self.TESSERACT_CMD = self._cfg.get("OCR", "TESSERACT_CMD")
        self.POSSIBLE_PATHS = [path.strip() for path in self._cfg.get("OCR", "POSSIBLE_PATHS").split(";")]

        if sys.platform == "linux": # On a linux system, the Tesseract binary is installed in a directory that is included in the $PATH variable
            self.TESSERACT_CMD = r"tesseract"

        for p in self.POSSIBLE_PATHS:
            if os.path.exists(p):
                self.TESSERACT_CMD = p
                break

        # --- LOGGING ---
        self.LOG_LEVEL = self._cfg.get("LOGGING", "LOG_LEVEL")

        # --- QUEST WINDOW DETECTION MODES ---
        # "auto"   = Template matching finds the quest window anywhere on screen.
        #            Trigger: automatic via Script.log NPC watcher (requires getNPCNames plugin).
        #            Run calibrate_retail.bat to capture templates.
        # "static" = Fixed bounding box (QUEST_WINDOW_BOX). Window must NOT move.
        #            Trigger: manual hotkey press (middle mouse button by default).
        #            Run calibrate_static.bat to set coordinates.
        self.QUEST_WINDOW_MODE = self._cfg.get("QUEST", "QUEST_WINDOW_MODE")

        # For static mode: [x, y, width, height] of quest window body area
        # Set these via calibrate_static.bat after drawing bounding box
        self.QUEST_WINDOW_BOX = [int(item.strip()) for item in self._cfg.get("QUEST", "QUEST_WINDOW_BOX").split(",")]

        # --- TRIGGER SETTINGS (legacy, kept for calibrate_static.py compat) ---
        # main.py now derives the trigger from QUEST_WINDOW_MODE:
        #   auto   -> log watcher triggers capture automatically
        #   static -> hotkey triggers capture manually
        # These values are only used by calibrate_static.py when writing config.
        self.QUEST_TRIGGER_MODE = self._cfg.get("QUEST", "QUEST_TRIGGER_MODE")

        # Hotkey for static mode
        # Supported: "middle_mouse", "left", "right", or keyboard key names like "f8", "t", "q"
        self.QUEST_TRIGGER_KEY = self._cfg.get("QUEST", "QUEST_TRIGGER_KEY")

        # Maximum age (in seconds) for NPC names from the log file in manual mode.
        # If the last NPC entry is older than this, the engine falls back to the
        # default narrator voice instead of using a potentially stale name.
        self.NPC_NAME_MAX_AGE = self._cfg.getint("QUEST", "NPC_NAME_MAX_AGE")

        # TODO: Discuss whether this needs to be part of the configuration file or not.
        self.DEVICE = None # Set on first access via __getattr__


    def _write_default_config(self):
        """
        Writes the default configuration file

        Returns
        -------
        None
        """
        templates_directory = os.path.join(self._base_directory, "templates")
        samples_directory = os.path.join(self._data_directory, "screenshots")
        ref_audio_directory = os.path.join(self._data_directory, "reference_audio")
        npc_data_file = os.path.join(self._data_directory, "npc_data.csv")
        script_log_file = os.path.join(self._home_directory, "Documents", "The Lord of the Rings Online", "Script.log")

        default_config = rf"""[PATHS]
BASE_DIR = {self._base_directory}
DATA_DIR = {self._data_directory}
SAMPLES_DIR = {samples_directory}
REF_AUDIO_DIR = {ref_audio_directory}
NPC_DATA_PATH = {npc_data_file}
TEMPLATES_DIR = {templates_directory}
SCRIPT_LOG = {script_log_file}

[WIKI]
WIKI_BASE_URL = https://lotro-wiki.com
MISSING_TEXT_INDICATOR = There is currently no text in this page
ENABLE_WIKI = false

[DETECTION]
TEMPLATE_THRESHOLD = 0.7
STATIC_TEMPLATE_THRESHOLD = 0.7
DEBUG_TEMPLATE_SCORES = false
CORNER_OFFSET_X = 5
CORNER_OFFSET_Y = 5
PADDING_ICON_Y = 5
PADDING_INTERSECT_X = 5
MIN_BOX_DIM = 50
BASE_RESOLUTION = 2560,1440

[DETECTION.DEFAULT_RETAIL_OFFSETS]
CORNER_OFFSET_X = 11
CORNER_OFFSET_Y = 10
PADDING_INTERSECT_X = -10
PADDING_ICON_Y = 17

[DETECTION.DEFAULT_ECHOES_OFFSETS]
BODY_LEFT_MARGIN = 11
BODY_TOP_MARGIN = 10
BODY_RIGHT_PADDING = 0
BODY_BOTTOM_PADDING = 0

[AUDIO]
SAMPLE_RATE = 24000
DEFAULT_VOLUME = 0.4
LUX_VOLUME = 0.5

[TTS]
TTS_SPEED = 1.1
TTS_WAVE_STEPS = 16

[OCR]
TESSERACT_CMD = C:\Program Files\Tesseract-OCR\tesseract.exe
POSSIBLE_PATHS = C:\Program Files\Tesseract-OCR\tesseract.exe;C:\Program Files (x86)\Tesseract-OCR\tesseract.exe;C:\Users\admin\AppData\Local\Programs\Tesseract-OCR\tesseract.exe

[LOGGING]
LOG_LEVEL = INFO

[QUEST]
QUEST_WINDOW_MODE = auto
QUEST_WINDOW_BOX = 555,380,425,539
QUEST_TRIGGER_MODE = manual
QUEST_TRIGGER_KEY = middle_mouse
NPC_NAME_MAX_AGE = 60
"""

        with open(self._config_file_path, "w", encoding="utf-8") as config_file:
            config_file.write(default_config)
