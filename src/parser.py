import re
from datetime import datetime

# 데이터 파싱
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