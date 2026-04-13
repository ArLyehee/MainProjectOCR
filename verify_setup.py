import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

print(f"프로젝트 루트: {ROOT_DIR}")

def check(name, fn):
    try:
        fn()
        print(f"  [OK] {name}")
    except Exception as e:
        print(f"  [FAIL] {name} → {e}")

print("=== OCR 환경 점검 ===\n")

check("pytesseract import", lambda: __import__("pytesseract"))
check("pdf2image import",   lambda: __import__("pdf2image"))
check("opencv import",      lambda: __import__("cv2"))
check("Pillow import",      lambda: __import__("PIL"))
check("pandas import",      lambda: __import__("pandas"))
check("openpyxl import",    lambda: __import__("openpyxl"))
check("PyMySQL import",     lambda: __import__("pymysql"))

def check_tesseract():
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = \
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    ver = pytesseract.get_tesseract_version()
    print(f"  [OK] Tesseract 버전: {ver}")

check("Tesseract 실행파일", check_tesseract)

def check_poppler():
    path = os.path.join(ROOT_DIR, "poppler", "bin", "pdftoppm.exe")
    assert os.path.exists(path), f"pdftoppm.exe 없음: {path}"

check("poppler 바이너리", check_poppler)

def check_kor():
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = \
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    langs = pytesseract.get_languages()
    assert "kor" in langs, f"kor 없음. 현재: {langs}"

check("한국어 언어팩(kor)", check_kor)

print("\n모든 항목 OK면 main.py 실행 가능합니다.")