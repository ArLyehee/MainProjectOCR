import os
import shutil
import platform
import pytesseract
import cv2
from preprocess import preprocess_image

def _find_tesseract() -> str:
    # PATH에서 먼저 탐색
    path = shutil.which("tesseract")
    if path:
        return path
    # Windows 일반 설치 경로
    if platform.system() == "Windows":
        for p in [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]:
            if os.path.exists(p):
                return p
    return "tesseract"

pytesseract.pytesseract.tesseract_cmd = _find_tesseract()

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