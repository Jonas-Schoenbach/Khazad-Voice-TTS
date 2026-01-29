import cv2
import numpy as np
import pytesseract
import nltk
import re
from PIL import Image, ImageOps
from typing import List
from .config import TESSERACT_CMD

# Init dependencies
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
nltk.download("punkt", quiet=True)


def preprocess_image(img_pil: Image.Image) -> np.ndarray:
    """
    Standard preprocessing for Quest Text (Paragraphs).
    """
    img_np = np.array(img_pil.convert("L"))
    # 2x scaling helps Tesseract read small game fonts
    img_np = cv2.resize(img_np, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(img_np, 120, 255, cv2.THRESH_BINARY)
    return thresh


def preprocess_name_image(img_pil: Image.Image) -> np.ndarray:
    """
    Specialized preprocessing for NPC Names (Single Line).
    Strategy: Invert -> Upscale -> Padding -> Black text on White bg.
    """
    # 1. Convert to Grayscale
    gray = img_pil.convert("L")

    # 2. Invert: LOTRO has light text on dark bg.
    # Tesseract reads Black text on White bg much better.
    inverted = ImageOps.invert(gray)
    img_np = np.array(inverted)

    # 3. 3x Scaling: Helps distinguish similar letters (P vs T, E vs F)
    img_np = cv2.resize(img_np, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    # 4. Binary Threshold (Otsu helps find the best separation automatically)
    _, thresh = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    # 5. Add White Border (Padding)
    # PSM 7 fails if text touches the edge. We add 20px white padding.
    thresh = cv2.copyMakeBorder(thresh, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)

    return thresh


def clean_ocr_errors(sentences: List[str]) -> List[str]:
    """
    Corrects common OCR mistakes specific to LOTRO fonts.
    """
    cleaned = []
    for s in sentences:
        s = s.replace("|", "I").replace("‘", "'").replace("’", "'")
        s = re.sub(r"'lam\b", "I am", s, flags=re.IGNORECASE)
        s = re.sub(r"'l\b", "I", s)
        s = re.sub(r"\bgoad\b", "good", s)
        cleaned.append(s.strip())
    return cleaned


def run_ocr(img_pil: Image.Image) -> List[str]:
    """
    For QUEST TEXT (Multiple sentences).
    """
    thresh = preprocess_image(img_pil)
    raw = pytesseract.image_to_string(thresh, config="--psm 6")
    merged_block = re.sub(r"\s*\n\s*", " ", raw).strip()
    sentences = nltk.sent_tokenize(merged_block)
    return [line for line in clean_ocr_errors(sentences) if len(line) > 1]


def run_name_ocr(img_pil: Image.Image) -> str:
    """
    For NPC NAMES (Single Line).
    Uses PSM 7 (Single Line) and specialized preprocessing.
    """
    thresh = preprocess_name_image(img_pil)

    # PSM 7: Treat the image as a single text line.
    raw = pytesseract.image_to_string(thresh, config="--psm 7")

    # Basic cleanup: remove newlines and surrounding whitespace
    clean = raw.strip().replace("\n", " ")

    # Fix common Name OCR glitches
    # e.g. "PED" -> "TED" is hard to regex without context, but we can fix symbols
    clean = clean.replace("|", "I").replace("1", "I")

    return clean