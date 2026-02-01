# Imports

# > Standard Library
import re
from typing import List

# > Third-party Libraries
import cv2
import numpy as np
import pytesseract
import nltk
from PIL import Image, ImageOps

# > Local Dependencies
from .config import TESSERACT_CMD

# Init dependencies
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
nltk.download("punkt", quiet=True)


def preprocess_image(img_pil: Image.Image) -> np.ndarray:
    """
    Standard preprocessing for Quest Text (Paragraphs).

    Parameters
    ----------
    img_pil : PIL.Image.Image
        The input image containing the quest text.

    Returns
    -------
    np.ndarray
        The preprocessed binary image ready for OCR.
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

    Parameters
    ----------
    img_pil : PIL.Image.Image
        The input image containing the NPC nameplate.

    Returns
    -------
    np.ndarray
        The preprocessed image optimized for single-line OCR.
    """
    # 1. Convert to Grayscale
    gray = img_pil.convert("L")

    # 2. Invert: LOTRO has light text on dark bg.
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

    Parameters
    ----------
    sentences : List[str]
        A list of raw strings detected by Tesseract.

    Returns
    -------
    List[str]
        The cleaned list of strings.
    """
    # Map of direct string replacements
    replacements = {
        "|": "I",
        "‘": "'",
        "’": "'",
        "'T": "'I",
        "1": "I",
        "'Ihe": "The",
        "REWARDS": "",
        "'l": "I",  # Fix 'l -> I
    }

    cleaned = []
    for s in sentences:
        # Apply direct replacements
        for old, new in replacements.items():
            s = s.replace(old, new)

        # Regex fixes for context-dependent errors
        s = re.sub(r"'lam\b", "I am", s, flags=re.IGNORECASE)
        s = re.sub(r"\bgoad\b", "good", s, flags=re.IGNORECASE)

        s = s.strip()
        if s:
            cleaned.append(s)

    return cleaned


def run_ocr(img_pil: Image.Image) -> List[str]:
    """
    Executes OCR on an image containing quest text (multiple sentences).

    Parameters
    ----------
    img_pil : PIL.Image.Image
        The source image.

    Returns
    -------
    List[str]
        A list of cleaned sentences extracted from the image.
    """
    thresh = preprocess_image(img_pil)
    raw = pytesseract.image_to_string(thresh, config="--psm 6")

    # Merge newlines to handle paragraph wrapping, then re-tokenize
    merged_block = re.sub(r"\s*\n\s*", " ", raw).strip()
    sentences = nltk.sent_tokenize(merged_block)

    return [line for line in clean_ocr_errors(sentences) if len(line) > 1]


def run_name_ocr(img_pil: Image.Image) -> str:
    """
    Executes OCR on an image containing a single NPC name.

    Parameters
    ----------
    img_pil : PIL.Image.Image
        The source image.

    Returns
    -------
    str
        The detected NPC name.
    """
    thresh = preprocess_name_image(img_pil)

    # PSM 7: Treat the image as a single text line.
    raw = pytesseract.image_to_string(thresh, config="--psm 7")

    # Basic cleanup: remove newlines and surrounding whitespace
    clean = raw.strip().replace("\n", " ")

    # Fix symbols common in name plates
    clean = clean.replace("|", "I").replace("1", "I")

    return clean