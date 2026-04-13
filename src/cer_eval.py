import os
import unicodedata
import sys
import pandas as pd
import importlib.util
from difflib import SequenceMatcher

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = " ".join(text.split())
    return text.strip()

def cer(ref: str, hyp: str) -> float:
    ref = normalize(ref)
    hyp = normalize(hyp)
    if len(ref) == 0:
        return 0.0
    r = list(ref)
    h = list(hyp)
    d = [[0] * (len(h) + 1) for _ in range(len(r) + 1)]
    for i in range(len(r) + 1):
        d[i][0] = i
    for j in range(len(h) + 1):
        d[0][j] = j
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            if r[i-1] == h[j-1]:
                d[i][j] = d[i-1][j-1]
            else:
                d[i][j] = 1 + min(d[i-1][j], d[i][j-1], d[i-1][j-1])
    return min(d[len(r)][len(h)] / len(r), 1.0)

def load_preprocess_module(root_dir: str):
    """preprocess.py를 한 번만 로드해서 재사용"""
    spec = importlib.util.spec_from_file_location(
        "preprocess",
        os.path.join(root_dir, "src", "preprocess.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def get_current_mode(root_dir: str) -> int:
    return load_preprocess_module(root_dir).MODE

def best_match_line(ref_line: str, hyp_lines: list) -> tuple:
    best_score = 0
    best_line = ""
    for hyp_line in hyp_lines:
        score = SequenceMatcher(None,
                                normalize(ref_line),
                                normalize(hyp_line)).ratio()
        if score > best_score:
            best_score = score
            best_line = hyp_line
    return best_line, best_score

def evaluate(ocr_text: str, ground_truth_path: str):
    with open(ground_truth_path, "r", encoding="utf-8") as f:
        ref_text = f.read()

    print("=" * 50)
    print("[ OCR 원본 텍스트 ]")
    print(ocr_text)
    print("=" * 50)
    print(f"OCR 글자수  : {len(normalize(ocr_text))}")
    print(f"정답 글자수 : {len(normalize(ref_text))}")
    print("=" * 50)

    total_cer = cer(normalize(ref_text), normalize(ocr_text))

    ref_lines = [l for l in ref_text.splitlines() if l.strip()]
    hyp_lines = [l for l in ocr_text.splitlines() if l.strip()]

    print("\nOCR 정확도 평가 결과")
    print("=" * 50)
    print(f"전체 CER   : {total_cer:.4f} ({total_cer*100:.2f}%)")
    print(f"전체 정확도: {(1 - total_cer)*100:.2f}%\n")
    print("[ 줄별 비교 — 유사도 기반 매칭 ]")

    line_cers = []
    for ref_line in ref_lines:
        best_hyp, _ = best_match_line(ref_line, hyp_lines)
        line_cer = cer(ref_line, best_hyp)
        line_cers.append(line_cer)
        status = "✓" if line_cer < 0.1 else "✗"
        print(f"  {status} [{line_cer*100:5.1f}%] 정답: {ref_line}")
        print(f"            OCR : {best_hyp}")

    avg_line_cer = sum(line_cers) / len(line_cers) if line_cers else 0.0
    best_line_cer  = min(line_cers) if line_cers else 0.0
    worst_line_cer = max(line_cers) if line_cers else 0.0

    print(f"\n줄별 평균 CER  : {avg_line_cer:.4f} ({avg_line_cer*100:.2f}%)")
    print(f"줄별 평균 정확도: {(1 - avg_line_cer)*100:.2f}%")
    print("=" * 50)

    return {
        "total_cer":     round(total_cer, 4),
        "accuracy":      round((1 - total_cer) * 100, 2),
        "avg_line_cer":  round(avg_line_cer, 4),
        "line_accuracy": round((1 - avg_line_cer) * 100, 2),
        "best_cer":      round(best_line_cer, 4),
        "worst_cer":     round(worst_line_cer, 4),
        "ocr_chars":     len(normalize(ocr_text)),
        "ref_chars":     len(normalize(ref_text))
    }


if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    from pdf_to_image import pdf_to_images
    from ocr_extractor import extract_text

    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_dir = os.path.join(ROOT_DIR, "input")
    pdf_files = [f for f in os.listdir(input_dir) if f.endswith(".pdf")]

    if not pdf_files:
        print("[오류] input 폴더에 PDF 없음")
        sys.exit(1)

    pdf_path = os.path.join(input_dir, pdf_files[0])
    print(f"[처리 중] {pdf_files[0]}\n")

    # OCR 실행
    image_paths = pdf_to_images(pdf_path)
    ocr_text = ""
    for image_path in image_paths:
        ocr_text += extract_text(image_path) + "\n"

    gt_path = os.path.join(ROOT_DIR, "src", "ground_truth.txt")
    result = evaluate(ocr_text, gt_path)

    # preprocess.py 한 번만 로드
    preprocess_mod = load_preprocess_module(ROOT_DIR)
    current_mode = preprocess_mod.MODE
    config = preprocess_mod.MODE_CONFIG.get(current_mode, {})

    # 누적 CSV 저장
    cer_dir = os.path.join(ROOT_DIR, "output", "cer_results")
    os.makedirs(cer_dir, exist_ok=True)
    summary_path = os.path.join(cer_dir, "tessaract_experiments.csv")

    row = {
        "실험명":       config.get("실험명", f"mode_{current_mode}"),
        "langs":       "kor+eng",
        "dpi":         300,
        "psm":         6,
        "prep":        config.get("prep", "-"),
        "deskew":      config.get("deskew", "no"),
        "table_clean": config.get("table_clean", "no"),
        "whitelist":   config.get("whitelist", "-"),
        "AVG CER":     result["avg_line_cer"],   # 줄별 평균
        "Best CER":    result["best_cer"],        # 가장 잘 맞은 줄
        "Worst CER":   result["worst_cer"],       # 가장 틀린 줄
        "accuracy":    result["accuracy"],
        "ocr_chars":   result["ocr_chars"],
        "ref_chars":   result["ref_chars"],
    }

    if os.path.exists(summary_path):
        existing_df = pd.read_csv(summary_path, encoding="utf-8-sig")
        existing_df = existing_df[existing_df["실험명"] != row["실험명"]]
        new_df = pd.concat([existing_df, pd.DataFrame([row])], ignore_index=True)
    else:
        new_df = pd.DataFrame([row])

    new_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
    print(f"\n실험 결과 누적 저장: {summary_path}")
    print(f"현재 실험 수: {len(new_df)}개")

    mode_dir = os.path.join(cer_dir, f"mode_{current_mode}")
    os.makedirs(mode_dir, exist_ok=True)

    txt_path = os.path.join(mode_dir, f"ocr_mode{current_mode}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"실험명: {row['실험명']}\n")
        f.write(f"MODE: {current_mode}\n")
        f.write(f"accuracy: {result['accuracy']}%\n")
        f.write("=" * 50 + "\n")
        f.write(ocr_text)
    print(f"OCR TXT 저장: {txt_path}")