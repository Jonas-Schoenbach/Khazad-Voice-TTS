# Imports

# > Third party imports
import sounddevice as sd
import numpy as np

# > Local dependencies
from .config import DEFAULT_VOLUME


def play_audio(data: np.ndarray, rate: int, volume: float = DEFAULT_VOLUME):
    """
    Plays audio via system speakers.
    """
    if len(data) > 0:
        sd.play(data * volume, rate)
        sd.wait()
