import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from pdf_to_image import pdf_to_images
from ocr_extractor import extract_text
from postprocess import postprocess_text

pdf_path = sys.argv[1] if len(sys.argv) > 1 else input("PDF 경로: ")
images = pdf_to_images(pdf_path, dpi=300)
for img in images:
    raw = extract_text(img, prep="adaptive", langs="kor+eng", psm=6)
    clean = postprocess_text(raw)
    print("=== OCR 결과 ===")
    print(clean)
