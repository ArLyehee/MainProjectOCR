import os
from pdf2image import convert_from_path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
POPPLER_PATH = os.path.join(ROOT_DIR, "poppler", "bin")

def pdf_to_images(pdf_path: str,
                  output_dir: str = None,
                  dpi: int = 300) -> list: # DPI가 높으면 정확도 증가
    if output_dir is None:
        output_dir = os.path.join(ROOT_DIR, "output", "images")
    os.makedirs(output_dir, exist_ok=True)

    images = convert_from_path(
        pdf_path,
        dpi=dpi,
        poppler_path=POPPLER_PATH
    )

    image_paths = []
    for i, img in enumerate(images):
        path = os.path.join(output_dir, f"page_{i+1}.png")
        img.save(path, "PNG")
        image_paths.append(path)

    return image_paths