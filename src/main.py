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
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

load_dotenv(os.path.join(ROOT_DIR, ".env"))

db_user = os.getenv('DB_USER')
db_pw   = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_name = os.getenv('DB_NAME')


db_url = (
    f"mysql+pymysql://{db_user}:{db_pw}"
    f"@{db_host}:{db_port}"
    f"/{db_name}?charset=utf8mb4"
)

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


def erp_mode(pdf_path: str):
    """ERP 연동 모드: Tesseract OCR → 공백 보정 파서 → JSON 출력"""
    import json, re
    try:
        image_paths = pdf_to_images(pdf_path, dpi=OCR_CONFIG["dpi"])
        all_text = ""
        for image_path in image_paths:
            raw = extract_text(image_path, prep=OCR_CONFIG["prep"],
                               langs=OCR_CONFIG["langs"], psm=OCR_CONFIG["psm"])
            all_text += postprocess_text(raw) + "\n"

        def clean_kr(s):
            if not s: return s
            prev = ""
            while prev != s:
                prev = s
                s = re.sub(r'([가-힣\?\!]) ([가-힣\?\!])', r'\1\2', s)
            return s.strip()

        def to_num(s):
            if not s: return 0
            return int(re.sub(r'[^\d]', '', str(s)) or '0')

        m = re.search(r'발\s*행\s*일\s+(\d{4}-\d{2}-\d{2})', all_text)
        issue_date = m.group(1) if m else None

        m = re.search(r'사\s*업\s*자\s*번\s*호\s+([\d]+)', all_text)
        biz_no = m.group(1) if m else None

        m = re.search(r'연\s*락\s*처\s+([\d\-]+)', all_text)
        tel = m.group(1) if m else None

        m = re.search(r'상\s*호\s*\(\s*법\s*인\s*명\s*\)\s+(.+?)\s+상\s*호\s*\(\s*법\s*인\s*명\s*\)', all_text)
        supplier = clean_kr(m.group(1)) if m else None

        m = re.search(r'주\s*소\s+(.+?)\s+담\s*당\s*자', all_text)
        addr = clean_kr(m.group(1)) if m else None

        m = re.search(r'담\s*당\s*자\s+(.+?)(?:\s{2,}|\n|$)', all_text)
        manager = clean_kr(m.group(1)) if m else None

        total_amount = tax_amount = grand_total = 0
        lines = all_text.splitlines()
        for i, line in enumerate(lines):
            if re.search(r'공\s*급\s*가\s*액', line):
                nums = re.findall(r'[\d,]{3,}', line)
                if len(nums) >= 3:
                    total_amount = to_num(nums[0])
                    tax_amount   = to_num(nums[1])
                    grand_total  = to_num(nums[2])
                else:
                    for j in range(i + 1, min(i + 4, len(lines))):
                        nums = re.findall(r'[\d,]{3,}', lines[j])
                        if len(nums) >= 2:
                            total_amount = to_num(nums[0])
                            tax_amount   = to_num(nums[1]) if len(nums) > 1 else 0
                            grand_total  = to_num(nums[2]) if len(nums) > 2 else 0
                            break
                break

        items = []
        for m in re.finditer(r'^(\d+)\s+(.+?)\s+(\d+)\s+([\d,]+)\s+([\d,]+)\s*$', all_text, re.MULTILINE):
            no, name, qty, price, amt = m.groups()
            if int(no) >= 1:
                items.append({"item_name": name.strip(), "quantity": int(qty),
                              "unit_price": to_num(price), "amount": to_num(amt)})

        data = {
            "issue_date": issue_date, "customer_name": supplier,
            "customer_biz_no": biz_no, "customer_tel": tel,
            "customer_addr": addr, "manager_name": manager,
            "total_amount": total_amount, "tax_amount": tax_amount,
            "grand_total": grand_total, "items": items,
        }

        # 시각화 저장
        try:
            pdf_name  = os.path.splitext(os.path.basename(pdf_path))[0]
            vis_dir   = os.path.join(ROOT_DIR, "output", "erp_results",
                                     f"{pdf_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            os.makedirs(vis_dir, exist_ok=True)
            visualize_pipeline(pdf_path, prep=OCR_CONFIG["prep"], save_dir=vis_dir)
            with open(os.path.join(vis_dir, "ocr_data.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        sys.stdout.buffer.write(
            json.dumps({"success": True, "data": data}, ensure_ascii=True).encode("utf-8") + b"\n"
        )
    except Exception as e:
        import json as _json
        sys.stdout.buffer.write(
            _json.dumps({"success": False, "error": str(e)}, ensure_ascii=True).encode("utf-8") + b"\n"
        )


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--erp-mode":
        erp_mode(sys.argv[2])
        sys.exit()

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