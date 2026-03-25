import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pdf_to_image import pdf_to_images
from ocr_extractor import extract_text
from parser import parse_receipt, parse_transaction_statement
from cer_eval import evaluate, normalize
import pandas as pd
from datetime import datetime
from postprocess import postprocess_text


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_config() -> pd.DataFrame:
    """experiment_config.xlsx에서 RUN=yes인 실험만 로드"""
    config_path = os.path.join(ROOT_DIR, "experiment_config.xlsx")
    if not os.path.exists(config_path):
        print("[오류] experiment_config.xlsx 없음 → create_config.py 먼저 실행")
        sys.exit(1)
    df = pd.read_excel(config_path)
    run_df = df[df["RUN"].str.lower() == "yes"].reset_index(drop=True)
    print(f"실행할 실험: {len(run_df)}개 / 전체: {len(df)}개\n")
    return run_df

def process_receipt(pdf_path: str,
                    exp_name: str,
                    prep: str,
                    langs: str,
                    psm: int,
                    dpi: int,
                    folder_name: str) -> dict:
    """단일 실험 실행 — OCR + 파싱 + CER 평가"""

    print(f"  ▶ [{exp_name}] prep={prep}, dpi={dpi}, psm={psm}")

    image_paths = pdf_to_images(pdf_path, dpi=dpi)

    ocr_text = ""
    all_parsed = []
    for image_path in image_paths:
        raw_text = extract_text(image_path, prep=prep, langs=langs, psm=psm)
    
        clean_text = postprocess_text(raw_text)
        ocr_text += clean_text + "\n"
        
        parsed = parse_receipt(clean_text)
        all_parsed.append(parsed)

    exp_dir = os.path.join(ROOT_DIR, "output", folder_name)
    os.makedirs(exp_dir, exist_ok=True)

    parsed_csv = os.path.join(exp_dir, f"{exp_name}_parsed.csv")
    pd.DataFrame(all_parsed).to_csv(parsed_csv, index=False, encoding="utf-8-sig")

    gt_path = os.path.join(ROOT_DIR, "src", "ground_truth.txt")
    result = {}
    if os.path.exists(gt_path):
        result = evaluate(ocr_text, gt_path)
    else:
        print("ground_truth.txt 없음 → CER 건너뜀")

    txt_path = os.path.join(exp_dir, f"{exp_name}_ocr.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"실험명: {exp_name}\n")
        f.write(f"prep={prep} | dpi={dpi} | psm={psm}\n")
        f.write(f"accuracy: {result.get('accuracy', 'N/A')}%\n")
        f.write("=" * 50 + "\n")
        f.write(ocr_text)

    print(f"  → accuracy: {result.get('accuracy', 'N/A')}% "
          f"| AVG CER: {result.get('avg_line_cer', 'N/A')}")
    print(f"  → 저장: output/{folder_name}/{exp_name}_ocr.txt\n")

    return {
        "실험명":       exp_name,
        "langs":       langs,
        "dpi":         dpi,
        "psm":         psm,
        "prep":        prep,
        "AVG CER":     result.get("avg_line_cer", "-"),
        "Best CER":    result.get("best_cer", "-"),
        "Worst CER":   result.get("worst_cer", "-"),
        "accuracy":    result.get("accuracy", "-"),
        "ocr_chars":   result.get("ocr_chars", "-"),
        "ref_chars":   result.get("ref_chars", "-")
    }


def extract_text_from_pdf(pdf_path: str):
    """pdfplumber로 PDF 텍스트와 테이블 직접 추출 (이미지 변환 없이)"""
    import pdfplumber
    text = ""
    all_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
            tables = page.extract_tables()
            if tables:
                all_tables.extend(tables)
    return text.strip(), all_tables


def run_erp_mode(pdf_path: str):
    """ERP 자동등록 모드 - JSON을 stdout으로 출력"""
    try:
        # 1차: pdfplumber로 텍스트 직접 추출 (컴퓨터 생성 PDF에 최적)
        raw_text, tables = extract_text_from_pdf(pdf_path)
        method = "pdfplumber"

        # 텍스트가 너무 짧으면 스캔 PDF로 판단 → OCR로 폴백
        image_paths = []
        if len(raw_text.strip()) < 20:
            image_paths = pdf_to_images(pdf_path, dpi=300)
            raw_text = ""
            tables = []
            for image_path in image_paths:
                t = extract_text(image_path, prep="otsu", langs="kor+eng", psm=4)
                raw_text += postprocess_text(t) + "\n"
            method = "ocr"

        sys.stderr.buffer.write((f"[{method.upper()} TEXT]\n" + raw_text).encode("utf-8", errors="replace"))
        debug_tables = f"\n[TABLES FOUND: {len(tables)}]\n"
        for ti, t in enumerate(tables):
            debug_tables += f"  table[{ti}]: {len(t)} rows\n"
            for ri, row in enumerate(t[:5]):
                debug_tables += f"    row[{ri}]: {row}\n"
        sys.stderr.buffer.write(debug_tables.encode("utf-8", errors="replace"))

        # Groq → Gemini → 정규식 순서로 시도
        parsed = None
        if os.environ.get("GROQ_API_KEY"):
            try:
                from parser import parse_with_groq
                parsed = parse_with_groq(raw_text)
                sys.stderr.buffer.write(b"[PARSER: Groq]\n")
            except Exception as e:
                sys.stderr.buffer.write(f"[GROQ FAILED: {e}]\n".encode("utf-8", errors="replace"))
        if parsed is None and os.environ.get("GEMINI_API_KEY"):
            try:
                from parser import parse_with_gemini
                parsed = parse_with_gemini(raw_text)
                sys.stderr.buffer.write(b"[PARSER: Gemini]\n")
            except Exception as e:
                sys.stderr.buffer.write(f"[GEMINI FAILED: {e}]\n".encode("utf-8", errors="replace"))
        if parsed is None:
            parsed = parse_transaction_statement(raw_text, tables)
            sys.stderr.buffer.write(b"[PARSER: regex fallback]\n")

        # 결과가 부실하고 이미지가 있으면 Vision으로 재시도
        def _is_poor(p):
            return p.get("customer_name") is None and p.get("total_amount") is None and not p.get("items")
        if _is_poor(parsed) and image_paths and os.environ.get("GROQ_API_KEY"):
            try:
                from parser import parse_with_groq_vision
                parsed = parse_with_groq_vision(image_paths)
                sys.stderr.buffer.write(b"[PARSER: Groq Vision fallback]\n")
            except Exception as e:
                sys.stderr.buffer.write(f"[GROQ VISION FAILED: {e}]\n".encode("utf-8", errors="replace"))

        # manager_name은 Java 폼에서 입력받음 — OCR 추출값 사용 안 함
        parsed["manager_name"] = None

        sys.stderr.buffer.write(f"\n[PARSED ITEMS: {len(parsed.get('items', []))}]\n{parsed.get('items')}\n".encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(json.dumps({"success": True, "data": parsed}, ensure_ascii=False).encode("utf-8") + b"\n")
    except Exception as e:
        sys.stdout.buffer.write(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False).encode("utf-8") + b"\n")


if __name__ == "__main__":
    # ERP 모드: python src/main.py --erp-mode <pdf_path>
    if "--erp-mode" in sys.argv:
        idx = sys.argv.index("--erp-mode")
        if idx + 1 >= len(sys.argv):
            print(json.dumps({"success": False, "error": "파일 경로 인자 없음"}, ensure_ascii=False))
            sys.exit(1)
        run_erp_mode(sys.argv[idx + 1])
        sys.exit(0)

    input_dir = os.path.join(ROOT_DIR, "input")
    pdf_files = [f for f in os.listdir(input_dir) if f.endswith(".pdf")]
    if not pdf_files:
        print("input 폴더에 PDF 없음")
        sys.exit(1)

    pdf_path = os.path.join(input_dir, pdf_files[0])

    pdf_name    = os.path.splitext(pdf_files[0])[0]
    date_str    = datetime.now().strftime("%y%m%d")
    folder_name = f"{pdf_name}_{date_str}"

    print(f"[PDF] {pdf_files[0]}")
    print(f"[저장 폴더] output/{folder_name}\n")

    config_df = load_config()

    all_rows = []
    for _, row in config_df.iterrows():
        result_row = process_receipt(
            pdf_path    = pdf_path,
            exp_name    = row["실험명"],
            prep        = row["prep"],
            langs       = row["langs"],
            psm         = int(row["psm"]),
            dpi         = int(row["dpi"]),
            folder_name = folder_name
        )
        all_rows.append(result_row)

    exp_dir = os.path.join(ROOT_DIR, "output", folder_name)
    cer_csv = os.path.join(exp_dir, "cer_results.csv")
    pd.DataFrame(all_rows).to_csv(cer_csv, index=False, encoding="utf-8-sig")

    summary_path = os.path.join(ROOT_DIR, "output", "tessaract_experiments.csv")
    new_df = pd.DataFrame(all_rows)
    if os.path.exists(summary_path):
        existing_df = pd.read_csv(summary_path, encoding="utf-8-sig")
        for r in all_rows:
            existing_df = existing_df[existing_df["실험명"] != r["실험명"]]
        new_df = pd.concat([existing_df, new_df], ignore_index=True)
    new_df.to_csv(summary_path, index=False, encoding="utf-8-sig")

    print("=" * 50)
    print(f"전체 완료 → output/{folder_name}/")
    print(f"  cer_results.csv — 이번 실험 결과")
    print(f"  tessaract_experiments.csv — 전체 누적")
    print()
    print(new_df[["실험명", "prep", "AVG CER", "accuracy"]].to_string(index=False))