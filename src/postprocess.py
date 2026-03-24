import re

def postprocess_text(text: str) -> str:
    lines = text.splitlines()
    filtered = []

    junk_patterns = [
        r"localhost:\d+",
        r"https?://\S+",
        r"서명\s*(또는|or)\s*날인",
        r"공급자\s*확인",
        r"수령\s*확인",
        r"^[>\s\-_=|/]+$",
        r"^\d{1,2}\s*/\s*\d{1,2}$",
    ]
    junk_re = re.compile("|".join(junk_patterns), re.IGNORECASE)

    datetime_pattern = r"\d{2,4}\.\s*\d{1,2}\.\s*\d{1,2}\.\s*(오전|오후)\s*\d{1,2}:\d{1,2}"

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        if junk_re.search(stripped):
            continue

        if re.search(datetime_pattern, stripped):
            continue

        cleaned = re.sub(r'\s*\|\s*', ' ', stripped)
        cleaned = re.sub(r'^[>『\s]+', '', cleaned)
        cleaned = re.sub(r'\s*[>『]\s*', ' ', cleaned)
        cleaned = re.sub(r'["\']', '', cleaned)
        cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()

        # 한글 글자 사이 공백 제거 (Tesseract OCR 특성: 각 글자를 분리 인식)
        # "상 호 ( 법 인 명 )" → "상호(법인명)"
        for _ in range(10):
            prev = cleaned
            cleaned = re.sub(r'([가-힣])\s+([가-힣])', r'\1\2', cleaned)
            cleaned = re.sub(r'([가-힣])\s+\(', r'\1(', cleaned)
            cleaned = re.sub(r'\(\s*([가-힣])', r'(\1', cleaned)
            cleaned = re.sub(r'([가-힣])\s*\)', r'\1)', cleaned)
            if cleaned == prev:
                break

        if len(cleaned) <= 1 and not cleaned.isdigit():
            continue

        filtered.append(cleaned)

    return "\n".join(filtered)