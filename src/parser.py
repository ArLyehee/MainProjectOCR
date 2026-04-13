import re

def extract_header(lines):
    header = {
        "명세서번호": None, "발행일": None, "공급받는자": None, "공급자": None,
        "사업자번호": None, "연락처": None, "주소": None, "담당자": None,
        "공급가액": 0, "세액": 0, "합계금액": 0
    }
    all_amounts = []
    for line in lines:
        found = re.findall(r"([\d,]+)\s*원?", line)
        for f in found:
            clean_num = re.sub(r"[^\d]", "", f)
            if len(clean_num) >= 4:
                all_amounts.append(int(clean_num))

    for i, line in enumerate(lines):
        if m := re.search(r"명세서번호\s+([\w\-/_]+)", line): header["명세서번호"] = m.group(1)
        if m := re.search(r"발행일\s+(\d{4}-\d{2}-\d{2})", line): header["발행일"] = m.group(1)
        if m := re.search(r"사업자번호\s+(\d+)", line): header["사업자번호"] = m.group(1)
        if m := re.search(r"연락처\s+([\d-]+)", line): header["연락처"] = m.group(1)
        if m := re.search(r"주소\s+(.+?)\s+담당자\s+(.+)", line):
            header["주소"], header["담당자"] = m.group(1).strip(), m.group(2).strip()
        if "상호(법인명)" in line:
            names = re.findall(r"상호\(법인명\)\s+([^\s]+)", line)
            if len(names) >= 2:
                header["공급자"] = names[0].strip()
                header["공급받는자"] = names[1].strip()
            elif len(names) == 1:
                if line.find("공급자") < line.find("공급받는자") or "공급자" in line:
                    header["공급자"] = names[0].strip()
                else:
                    header["공급받는자"] = names[0].strip()

    for i in range(len(all_amounts)-1):
        v1, v2 = all_amounts[i], all_amounts[i+1]
        if 0.08 <= (v2 / v1) <= 0.12:
            header["공급가액"] = v1
            header["세액"] = v2
            if i+2 < len(all_amounts):
                v3_raw = str(all_amounts[i+2])
                if len(v3_raw) > len(str(v1 + v2)) + 1:
                    header["합계금액"] = int(v3_raw[:len(str(v1 + v2))])
                else:
                    header["합계금액"] = all_amounts[i+2]
            break
            
    return header

def extract_items(lines):
    items = []
    for line in lines:
        item_m = re.search(r"^(\d+)\s+(.+?)\s+(\d+)\s+([\d,]+)\s+([\d,]+)$", line)
        if item_m:
            try:
                items.append({
                    "item_name": item_m.group(2).strip(),
                    "quantity": int(item_m.group(3).replace(",", "")),
                    "unit_price": int(item_m.group(4).replace(",", "")),
                    "amount": int(item_m.group(5).replace(",", ""))
                })
            except: pass
    return items

def parse_receipt(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    result = extract_header(lines)
    result["items"] = extract_items(lines)
    return result