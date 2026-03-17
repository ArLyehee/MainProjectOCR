import pytesseract
import cv2
from preprocess import preprocess_image

pytesseract.pytesseract.tesseract_cmd = \
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text(image_path: str,
                 prep: str = "otsu",
                 langs: str = "kor+eng",
                 psm: int = 6) -> str:
    processed = preprocess_image(image_path, prep=prep)
    text = pytesseract.image_to_string(
        processed,
        lang=langs,
        config=f"--psm {psm}"
    )
    return text