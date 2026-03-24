import re

def parse_receipt(text: str) -> dict:
    result = {
        "명세서번호": None, "발행일": None, "공급받는자": None, "공급자": None,
        "사업자번호": None, "연락처": None, "주소": None, "담당자": None,
        "공급가액": None, "세액": None, "합계금액": None, "비고": None, "품목": []
    }

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    for line in lines:
        if m := re.search(r"명세서번호\s+([\w\-]+)", line): result["명세서번호"] = m.group(1)
        if m := re.search(r"발행일\s+(\d{4}-\d{2}-\d{2})", line): result["발행일"] = m.group(1)
        if m := re.search(r"사업자번호\s+(\d+)", line): result["사업자번호"] = m.group(1)
        if m := re.search(r"연락처\s+(\d+)", line): result["연락처"] = m.group(1)

        if m := re.search(r"주소\s+(.+?)\s+담당자\s+(.+)", line):
            result["주소"], result["담당자"] = m.group(1).strip(), m.group(2).strip()

        if m := re.search(r"상호\(법인명\)\s+(\S+)\s+상호\(법인명\)\s+(.+)", line):
            result["공급받는자"], result["공급자"] = m.group(1).strip(), m.group(2).strip()

        amt_m = re.search(r"([\d,]+)원?\s+([\d,]+)원?\s+([\d,]+)원?", line)
        if amt_m:
            try:
                result["공급가액"] = int(amt_m.group(1).replace(",", ""))
                result["세액"] = int(amt_m.group(2).replace(",", ""))
                result["합계금액"] = int(amt_m.group(3).replace(",", ""))
            except (ValueError, IndexError): pass

        if note_m := re.search(r"비고\s*[:：]?\s*(.*)", line):
            result["비고"] = note_m.group(1).strip()

        item_m = re.match(r"^(\d+)\s+(.+?)\s+(\d+)\s+([\d,]+)\s+([\d,]+)$", line)
        if item_m and len(item_m.groups()) >= 5:
            try:
                result["품목"].append({
                    "No": int(item_m.group(1)),
                    "품목명": item_m.group(2).strip(),
                    "수량": int(item_m.group(3)),
                    "단가": int(item_m.group(4).replace(",", "")),
                    "금액": int(item_m.group(5).replace(",", ""))
                })
            except (ValueError, IndexError): pass

    return result