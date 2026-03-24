import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pdf_to_image import pdf_to_images
from ocr_extractor import extract_text
from parser import parse_receipt
from cer_eval import evaluate, normalize
import pandas as pd
from datetime import datetime
from postprocess import postprocess_text
from visualize_ocr import visualize_pipeline
from sqlalchemy import create_engine

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_url = "mysql+pymysql://root:9927@192.168.0.224:3306/gaebalfan_erp?charset=utf8mb4"
engine = create_engine(db_url)

def load_config() -> pd.DataFrame:
    config_path = os.path.join(ROOT_DIR, "experiment_config.xlsx")
    if not os.path.exists(config_path):
        print("[오류] experiment_config.xlsx 없음")
        sys.exit(1)
    df = pd.read_excel(config_path)
    run_df = df[df["RUN"].str.lower() == "yes"].reset_index(drop=True)

    print(f"실행할 실험: {len(run_df)}개 / 전체: {len(df)}개\n")
    return run_df

def save_to_db(all_parsed_data):
    if not all_parsed_data:
        return
        
    df = pd.DataFrame(all_parsed_data)

    column_mapping = {
        '명세서번호': 'statement_no',
        '발행일': 'issue_date',
        '공급받는자': 'customer_name',
        '주소': 'customer_addr',
        '연락처': 'customer_tel',
        '사업자번호': 'customer_biz_no',
        '공급가액': 'total_amount',
        '세액': 'tax_amount',
        '합계금액': 'grand_total',
        '담당자': 'manager_name',
        '공급자': 'supply_name',
        '비고': 'notes'
        }

    df = df.rename(columns=column_mapping)

    db_columns = [
        'statement_no', 'issue_date', 'customer_name', 'customer_addr', 
        'customer_tel', 'customer_biz_no', 'total_amount', 'tax_amount', 
        'grand_total', 'manager_name', 'supply_name', 'notes'
    ]

    num_cols = ['total_amount', 'tax_amount', 'grand_total']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    df = df[db_columns]

    try:
        df.to_sql(name='transaction_statements', con=engine, if_exists='append', index=False)
        print(f"[DB 저장 성공] {len(df)}건의 데이터가 영문 컬럼에 맞춰 저장되었습니다.")
    except Exception as e:
        print(f"[DB 저장 실패] 오류 발생: {e}")

def process_receipt(pdf_path: str,
                    exp_name: str,
                    prep: str,
                    langs: str,
                    psm: int,
                    dpi: int,
                    folder_name: str) -> dict:

    print(f"  ▶ [{exp_name}] prep={prep}, dpi={dpi}, psm={psm}")

    image_paths = pdf_to_images(pdf_path, dpi=dpi)

    exp_dir = os.path.join(ROOT_DIR, "output", folder_name)
    os.makedirs(exp_dir, exist_ok=True)

    ocr_text   = ""
    all_parsed = []
    all_items  = []

    for image_path in image_paths:
        raw_text   = extract_text(image_path, prep=prep, langs=langs, psm=psm)
        clean_text = postprocess_text(raw_text)
        ocr_text  += clean_text + "\n"

        parsed = parse_receipt(clean_text)

        items = parsed.pop("품목", [])
        all_parsed.append(parsed)

        for item in items:
            item["명세서번호"] = parsed.get("명세서번호")
            all_items.append(item)

    header_csv = os.path.join(exp_dir, f"{exp_name}_header.csv")
    pd.DataFrame(all_parsed).to_csv(header_csv, index=False, encoding="utf-8-sig")
    print(f"  → 헤더 저장: {exp_name}_header.csv")

    items_csv = os.path.join(exp_dir, f"{exp_name}_items.csv")
    pd.DataFrame(all_items).to_csv(items_csv, index=False, encoding="utf-8-sig")
    print(f"  → 품목 저장: {exp_name}_items.csv")

    gt_path = os.path.join(ROOT_DIR, "src", "ground_truth.txt")
    result = {}
    if os.path.exists(gt_path):
        result = evaluate(ocr_text, gt_path)
    else:
        print("ground_truth.txt 없음 → CER 건너뜀")

    vis_dir = os.path.join(ROOT_DIR, "output", folder_name, "visualization", exp_name)
    os.makedirs(vis_dir, exist_ok=True)

    visualize_pipeline(pdf_path, prep=prep, save_dir=vis_dir)
    print(f"  → 시각화 저장: output/{folder_name}/visualization/{exp_name}/")

    txt_path = os.path.join(exp_dir, f"{exp_name}_ocr.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"실험명: {exp_name}\n")
        f.write(f"prep={prep} | dpi={dpi} | psm={psm}\n")
        f.write(f"accuracy: {result.get('accuracy', 'N/A')}%\n")
        f.write("=" * 50 + "\n")
        f.write(ocr_text)

    print(f"  → accuracy: {result.get('accuracy', 'N/A')}% "
          f"| AVG CER: {result.get('avg_line_cer', 'N/A')}\n")
    result_data = {
        "실험명": exp_name,
        "langs":    langs,
        "dpi":      dpi,
        "psm":      psm,
        "prep":     prep,
        "AVG CER":  result.get("avg_line_cer", "-"),
        "Best CER": result.get("best_cer", "-"),
        "Worst CER":result.get("worst_cer", "-"),
        "accuracy": result.get("accuracy", "-"),
        "ocr_chars":result.get("ocr_chars", "-"),
        "ref_chars":result.get("ref_chars", "-")
    }
    result_data["parsed_data"] = all_parsed
    return result_data

if __name__ == "__main__":
    input_dir = os.path.join(ROOT_DIR, "input")
    pdf_files = [f for f in os.listdir(input_dir) if f.endswith(".pdf")]
    if not pdf_files:
        print("input 폴더에 PDF 없음")
        sys.exit(1)

    pdf_path = os.path.join(input_dir, pdf_files[0])
    pdf_name = os.path.splitext(pdf_files[0])[0]
    date_str = datetime.now().strftime("%y%m%d")
    folder_name = f"{pdf_name}_{date_str}"

    print(f"[PDF] {pdf_files[0]}")
    print(f"[저장 폴더] output/{folder_name}\n")

    config_df = load_config()
    all_rows = []

    for _, row in config_df.iterrows():
        result_row = process_receipt(
            pdf_path = pdf_path,
            exp_name = row["실험명"],
            prep = row["prep"],
            langs = row["langs"],
            psm = int(row["psm"]),
            dpi = int(row["dpi"]),
            folder_name = folder_name
        )

        if "parsed_data" in result_row:
            save_to_db(result_row["parsed_data"])
            
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