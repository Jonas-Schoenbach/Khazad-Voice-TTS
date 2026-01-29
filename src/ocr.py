import cv2
import numpy as np
import pytesseract
import nltk
import re
from PIL import Image
from typing import List
from .config import TESSERACT_CMD

# Init dependencies
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
nltk.download("punkt", quiet=True)


def preprocess_image(img_pil: Image.Image) -> np.ndarray:
    """
    Converts PIL image to Grayscale -> Resize 2x -> Binary Threshold.
    """
    img_np = np.array(img_pil.convert("L"))
    # 2x scaling helps Tesseract read small game fonts
    img_np = cv2.resize(img_np, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(img_np, 120, 255, cv2.THRESH_BINARY)
    return thresh


def clean_ocr_errors(sentences: List[str]) -> List[str]:
    """
    Corrects common OCR mistakes specific to LOTRO fonts.
    """
    cleaned = []
    for s in sentences:
        s = s.replace("|", "I").replace("‘", "'").replace("’", "'")
        # Fix: "'lam" -> "I am"
        s = re.sub(r"'lam\b", "I am", s, flags=re.IGNORECASE)
        s = re.sub(r"'l\b", "I", s)
        # Fix: "goad" -> "good"
        s = re.sub(r"\bgoad\b", "good", s)
        cleaned.append(s.strip())
    return cleaned


def run_ocr(img_pil: Image.Image) -> List[str]:
    """
    Main pipeline: Image -> Text Block -> Sentences -> Cleaned List.
    """
    thresh = preprocess_image(img_pil)

    # PSM 6: Assume a single uniform block of text
    raw = pytesseract.image_to_string(thresh, config="--psm 6")

    # Merge broken lines into a single paragraph
    merged_block = re.sub(r"\s*\n\s*", " ", raw).strip()

    # Split by grammar (sentences)
    sentences = nltk.sent_tokenize(merged_block)

    return [line for line in clean_ocr_errors(sentences) if len(line) > 1]
