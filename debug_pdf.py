import fitz, sys

pdf_path = sys.argv[1] if len(sys.argv) > 1 else input("PDF 경로 입력: ")
doc = fitz.open(pdf_path)
for i, page in enumerate(doc):
    print(f"=== 페이지 {i+1} ===")
    print(repr(page.get_text()))
doc.close()
