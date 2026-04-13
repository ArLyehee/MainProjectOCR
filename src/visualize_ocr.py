import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
import pytesseract
from pdf_to_image import pdf_to_images
from preprocess import preprocess_image
from postprocess import postprocess_text

pytesseract.pytesseract.tesseract_cmd = \
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def visualize_pipeline(pdf_path: str,
                       prep: str = "adaptive",
                       save_dir: str = None):

    vis_dir = save_dir if save_dir else os.path.join(ROOT_DIR, "output", "visualization")
    os.makedirs(vis_dir, exist_ok=True)
    print(f"  저장 경로: {vis_dir}")

    image_paths = pdf_to_images(pdf_path, dpi=300)
    if not image_paths:
        print("  [오류] 이미지 변환 실패")
        return None
    image_path = image_paths[0]
    print(f"  이미지 변환 완료: {image_path}")

    original = cv2.imread(image_path)
    if original is None:
        print(f"  [오류] 이미지 읽기 실패: {image_path}")
        return None
    print(f"  원본 이미지 크기: {original.shape}")

    processed = preprocess_image(image_path, prep=prep)
    print(f"  전처리 완료: {processed.shape}")

    raw_text = pytesseract.image_to_string(
        processed, lang="kor+eng", config="--psm 6"
    )
    clean_text = postprocess_text(raw_text)

    ocr_vis = original.copy()
    orig_h, orig_w = original.shape[:2]
    proc_h, proc_w = processed.shape[:2]

    scale_x = orig_w / proc_w
    scale_y = orig_h / proc_h

    data = pytesseract.image_to_data(
        processed, lang="kor+eng",
        config="--psm 6",
        output_type=pytesseract.Output.DICT
    )
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        conf = int(data['conf'][i])
        if text and conf > 30:
            x = int(data['left'][i]   * scale_x)
            y = int(data['top'][i]    * scale_y)
            w = int(data['width'][i]  * scale_x)
            h = int(data['height'][i] * scale_y)
            if conf > 70:
                color = (0, 200, 0)
            elif conf > 50:
                color = (0, 165, 255)
            else:
                color = (0, 0, 255)
            cv2.rectangle(ocr_vis, (x, y), (x+w, y+h), color, 2)

    processed_resized = cv2.resize(processed, (orig_w, orig_h))
    processed_color = cv2.cvtColor(processed_resized, cv2.COLOR_GRAY2BGR)

    def add_label(img, label):
        result = img.copy()
        cv2.rectangle(result, (0, 0), (img.shape[1], 40), (50, 50, 50), -1)
        cv2.putText(result, label, (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        return result

    orig_labeled = add_label(original,        "1. Original")
    proc_labeled = add_label(processed_color, f"2. Preprocessed ({prep})")
    ocr_labeled  = add_label(ocr_vis,         "3. OCR Boxes")

    scale = 0.3  # 30%로 축소
    orig_labeled  = cv2.resize(orig_labeled,  None, fx=scale, fy=scale)
    proc_labeled  = cv2.resize(proc_labeled,  None, fx=scale, fy=scale)
    ocr_labeled   = cv2.resize(ocr_labeled,   None, fx=scale, fy=scale)

    combined = np.hstack([orig_labeled, proc_labeled, ocr_labeled])

    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    save_path = os.path.join(vis_dir, f"{pdf_name}_{prep}_visual.png")
    result = cv2.imencode('.png', combined)[1]

    with open(save_path, 'wb') as f:
        f.write(result.tobytes())
    print(f"  시각화 저장: {save_path}")


    txt_path = os.path.join(vis_dir, f"{pdf_name}_{prep}_text.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"prep: {prep}\n")
        f.write("=" * 50 + "\n")
        f.write("=== 후처리 전 ===\n")
        f.write(raw_text)
        f.write("\n\n=== 후처리 후 ===\n")
        f.write(clean_text)
    print(f"  텍스트 저장: {txt_path}")

    return save_path


if __name__ == "__main__":
    input_dir = os.path.join(ROOT_DIR, "input")
    pdf_files = [f for f in os.listdir(input_dir) if f.endswith(".pdf")]

    if not pdf_files:
        print("[오류] input 폴더에 PDF 없음")
    else:
        pdf_path = os.path.join(input_dir, pdf_files[0])
        print(f"[처리 중] {pdf_files[0]}\n")

        for prep in ["otsu", "adaptive", "sharpen_otsu", "enlarge_adaptive"]:
            print(f"--- {prep} ---")
            result = visualize_pipeline(pdf_path, prep=prep)
            if result:
                print(f"  완료: {result}\n")
            else:
                print(f"  실패\n")

        print("전체 완료!")