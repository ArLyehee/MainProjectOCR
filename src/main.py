import sys
import os
import pandas as pd
import glob
from datetime import datetime
from sqlalchemy import create_engine, text
from pdf_to_image import pdf_to_images
from ocr_extractor import extract_text
from parser import parse_receipt
from cer_eval import evaluate
from postprocess import postprocess_text
from visualize_ocr import visualize_pipeline

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

db_url = "mysql+pymysql://root:9927@192.168.0.224:3306/gaebalfan_erp?charset=utf8mb4"
engine = create_engine(db_url)

OCR_CONFIG = {
    "prep":  "adaptive",
    "langs": "kor+eng",
    "psm":   6,
    "dpi":   300,
}

def save_to_db(all_parsed_data):
    if not all_parsed_data:
        return

    header_mapping = {
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
        '공급자': 'supply_name'
    }

    item_mapping = {
        'No': 'item_no',
        '품목명': 'item_name',
        '수량': 'quantity',
        '단가': 'unit_price',
        '금액': 'amount'
    }

    for parsed in all_parsed_data:
        header_row = {header_mapping[k]: v for k, v in parsed.items() if k in header_mapping}
        
        for col in ['total_amount', 'tax_amount', 'grand_total']:
            if col in header_row and header_row[col] is not None:
                header_row[col] = float(str(header_row[col]).replace(',', ''))
            else:
                header_row[col] = 0

        try:
            with engine.begin() as conn:
                header_df = pd.DataFrame([header_row])
                header_df.to_sql(name='transaction_statements', con=conn, if_exists='append', index=False)
                
                res = conn.execute(text("SELECT LAST_INSERT_ID()"))
                new_statement_id = res.fetchone()[0]

                if "items" in parsed and parsed["items"]:
                    items_df = pd.DataFrame(parsed["items"])
                    items_df = items_df.rename(columns=item_mapping)
                    items_df['statement_id'] = new_statement_id
                    
                    for col in ['quantity', 'unit_price', 'amount']:
                        if col in items_df.columns:
                            items_df[col] = pd.to_numeric(items_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                    
                    items_df.to_sql(name='transaction_statement_items', con=conn, if_exists='append', index=False)
                    print(f"[DB 저장 성공] Statement ID: {new_statement_id} (품목 {len(items_df)}건)")

        except Exception as e:
            print(f"[DB 저장 실패] {e}")

def process_receipt(pdf_path: str):
    file_name   = os.path.splitext(os.path.basename(pdf_path))[0]
    folder_name = f"{file_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    exp_dir     = os.path.join(ROOT_DIR, "output", folder_name)
    os.makedirs(exp_dir, exist_ok=True)

    print(f"prep={OCR_CONFIG['prep']} | dpi={OCR_CONFIG['dpi']} | psm={OCR_CONFIG['psm']}")

    image_paths = pdf_to_images(pdf_path, dpi=OCR_CONFIG["dpi"])

    ocr_text   = ""
    all_parsed = []

    for image_path in image_paths:
        raw_text   = extract_text(image_path,
                                  prep=OCR_CONFIG["prep"],
                                  langs=OCR_CONFIG["langs"],
                                  psm=OCR_CONFIG["psm"])
        clean_text = postprocess_text(raw_text)
        ocr_text  += clean_text + "\n"

        parsed = parse_receipt(clean_text)
        all_parsed.append(parsed)

    save_to_db(all_parsed)

    pd.DataFrame(all_parsed).to_csv(
        os.path.join(exp_dir, "header.csv"), index=False, encoding="utf-8-sig")

    vis_dir = os.path.join(exp_dir, "visualization")
    visualize_pipeline(pdf_path, prep=OCR_CONFIG["prep"], save_dir=vis_dir)

    with open(os.path.join(exp_dir, "ocr_result.txt"), "w", encoding="utf-8") as f:
        f.write(ocr_text)

    print(f"저장 완료: output/{folder_name}/")


if __name__ == "__main__":
    input_folder = os.path.join(ROOT_DIR, "input")
    pdf_files = glob.glob(os.path.join(input_folder, "*.pdf"))

    if not pdf_files:
        print("[알림] input 폴더에 PDF 파일이 없습니다.")
        sys.exit()

    print(f"[실행] 총 {len(pdf_files)}개 파일 처리 시작\n")

    for pdf_path in pdf_files:
        print(f"--- {os.path.basename(pdf_path)} ---")
        process_receipt(pdf_path)

    print("\n전체 완료!")