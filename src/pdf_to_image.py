import os
import fitz

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

def pdf_to_images(pdf_path: str,
                  output_dir: str = None,
                  dpi: int = 300) -> list:
    if output_dir is None:
        output_dir = os.path.join(ROOT_DIR, "output", "images")
    os.makedirs(output_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    image_paths = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat)
        path = os.path.join(output_dir, f"page_{i+1}.png")
        pix.save(path)
        image_paths.append(path)

    doc.close()
    return image_paths
