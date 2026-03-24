import cv2
import numpy as np

def preprocess_image(image_path: str, prep: str = "adaptive") -> np.ndarray:
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if prep == "adaptive":
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        result = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 10)
    else:
        _, result = cv2.threshold(gray, 0, 255,
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return result