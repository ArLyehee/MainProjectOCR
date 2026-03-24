import re
from datetime import datetime

# 거래명세서 ERP 자동등록 전용 파서
def parse_transaction_statement(text: str) -> dict:
    result = {
        "issue_date": None,
        "customer_name": None,
        "customer_biz_no": None,
        "customer_tel": None,
        "customer_addr": None,
        "manager_name": None,
        "notes": None,
        "items": [],
        "total_amount": None,
        "tax_amount": None,
        "grand_total": None
    }

    lines = text.strip().split("\n")

    # 금액 레이블과 값이 다른 줄에 있는 경우 한 줄로 합치기
    # "공급가액\n130,200 원" → "공급가액 130,200 원"
    merged = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if re.match(r"^(공급가액?|세액|합계금액|합계)$", line) and i + 1 < len(lines):
            next_l = lines[i + 1].strip()
            if re.match(r"^[\d,]+\s*(원|$)", next_l):
                merged.append(line + " " + next_l)
                i += 2
                continue
        merged.append(line)
        i += 1
    lines = merged

    for line in lines:
        # 발행일
        dm = re.search(r"발행일[^\d]*(\d{4})[-./년](\d{1,2})[-./월](\d{1,2})", line)
        if dm:
            result["issue_date"] = f"{dm.group(1)}-{dm.group(2).zfill(2)}-{dm.group(3).zfill(2)}"
        elif not result["issue_date"]:
            dm2 = re.search(r"(\d{4})[-./](\d{2})[-./](\d{2})", line)
            if dm2:
                result["issue_date"] = "-".join(dm2.groups())

        # 거래처명 (상호 행) - 공급자(납품처) 이름 추출
        # OCR은 좌측 컬럼(공급자)을 먼저, 우측 컬럼(공급받는자=우리회사)을 나중에 읽음
        # → 첫 번째로 나오는 상호 중 우리 회사가 아닌 것을 사용
        if "상호" in line and not result["customer_name"]:
            parts = re.split(r"상호[^\s]*\s*", line)
            for part in parts[1:]:
                name_part = part.strip()
                for kw in ["사업자", "연락처", "주소", "명세서", "발행일", "담당자"]:
                    idx = name_part.find(kw)
                    if idx > 0:
                        name_part = name_part[:idx].strip()
                        break
                name_part = name_part.strip()
                if not name_part:
                    continue
                # 우리 회사(공급받는자) 이름이 포함된 경우 건너뜀
                if re.search(r"개발환기|ERP", name_part):
                    continue
                # 유효 문자(한글/영문/숫자) 비율 30% 미만이면 OCR 쓰레기로 판단, 건너뜀
                valid = len(re.findall(r"[가-힣A-Za-z0-9]", name_part))
                total = len(name_part.replace(" ", ""))
                if total > 0 and valid / total < 0.3:
                    continue
                result["customer_name"] = name_part
                break

        # 사업자번호 - 두 컬럼 레이아웃에서 두 번째(공급자) 번호 추출
        biz_pattern = r"사업자[^\d]*(\d{3}[-]?\d{2}[-]?\d{5}|\d{9,10})"
        bm_all = list(re.finditer(biz_pattern, line))
        if bm_all:
            # 두 개 이상이면 두 번째(공급자), 하나뿐이면 그것 사용
            bm_target = bm_all[1] if len(bm_all) >= 2 else bm_all[0]
            if not result["customer_biz_no"]:
                result["customer_biz_no"] = bm_target.group(1)

        # 연락처
        tm = re.search(r"연락처[^\d]*(\d[\d\-]+)", line)
        if tm and not result["customer_tel"]:
            result["customer_tel"] = tm.group(1).strip()

        # 주소
        am = re.search(r"주소\s+(.+)", line)
        if am and not result["customer_addr"]:
            result["customer_addr"] = am.group(1).strip()

        # 담당자
        mm = re.search(r"담당자?\s+([가-힣]{2,5})", line)
        if mm and not result["manager_name"]:
            result["manager_name"] = mm.group(1).strip()

        # 공급가액
        sm = re.search(r"공급가[액]?\s*[：:]*\s*(\d[\d,]+)", line)
        if sm:
            result["total_amount"] = int(sm.group(1).replace(",", ""))

        # 세액
        taxm = re.search(r"세\s*액\s*[：:]*\s*(\d[\d,]+)", line)
        if taxm:
            result["tax_amount"] = int(taxm.group(1).replace(",", ""))

        # 합계
        totm = re.search(r"합\s*계\s*[：:]*\s*(\d[\d,]+)", line)
        if totm:
            result["grand_total"] = int(totm.group(1).replace(",", ""))

        # 품목 행: "번호 품목명 수량 단가 금액"
        im = re.match(r"^(\d+)\s+(.+?)\s+(\d[\d,]*)\s+(\d[\d,]+)\s+(\d[\d,]+)\s*$", line)
        if im:
            item_name = im.group(2).strip()
            # 유효 문자(한글/영문/숫자) 비율이 30% 미만이면 OCR 쓰레기 문자로 판단
            valid_chars = len(re.findall(r"[가-힣A-Za-z0-9]", item_name))
            total_chars = len(item_name.replace(" ", ""))
            readable = total_chars == 0 or (valid_chars / total_chars) >= 0.3
            if not readable:
                item_name = "(OCR 미인식 - 수정 필요)"
            if len(item_name) >= 1 and not re.match(r"^(No|번호|품목명|합계|소계)$", item_name, re.IGNORECASE):
                result["items"].append({
                    "item_name": item_name,
                    "quantity": int(im.group(3).replace(",", "")),
                    "unit_price": int(im.group(4).replace(",", "")),
                    "amount": int(im.group(5).replace(",", ""))
                })

    # 금액 미추출 시 보완
    if result["grand_total"] is None and result["total_amount"] is not None:
        tax = result["tax_amount"] if result["tax_amount"] is not None else int(result["total_amount"] * 0.1)
        result["grand_total"] = result["total_amount"] + tax
        if result["tax_amount"] is None:
            result["tax_amount"] = tax

    if result["total_amount"] is None and result["items"]:
        result["total_amount"] = sum(i["amount"] for i in result["items"])
        if result["tax_amount"] is None:
            result["tax_amount"] = int(result["total_amount"] * 0.1)
        if result["grand_total"] is None:
            result["grand_total"] = result["total_amount"] + result["tax_amount"]

    return result


# 기존 파서 (실험용)
def parse_receipt(text: str) -> dict:
    result = {
        "date": None,
        "supplier_name": None,
        "items": [],
        "total_amount": None
    }
    
    lines = text.strip().split("\n")
    
    for line in lines:
        date_match = re.search(r"(\d{4})[-./](\d{2})[-./](\d{2})", line)
        if date_match and not result["date"]:
            result["date"] = "-".join(date_match.groups())
        
        amount_match = re.search(r"합계[^\d]*(\d[\d,]+)", line)
        if amount_match:
            result["total_amount"] = int(amount_match.group(1).replace(",", ""))

        item_match = re.match(r"(.+?)\s+(\d[\d,]+)\s*원?$", line)
        if item_match:
            result["items"].append({
                "name": item_match.group(1).strip(),
                "amount": int(item_match.group(2).replace(",", ""))
            })
    
    return result