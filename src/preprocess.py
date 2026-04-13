import cv2
import numpy as np

# 전처리
def preprocess_image(image_path: str, prep: str = "adaptive") -> np.ndarray:
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    if prep == "adaptive":
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)
        
        result = cv2.adaptiveThreshold(
            filtered, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 15)

        kernel = np.ones((1, 1), np.uint8)
        result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kernel)
        
    else:
        _, result = cv2.threshold(gray, 0, 255,
                                  cv2.ADAPTIVE_THRESH_BINARY + cv2.THRESH_OTSU)
                                  
    return result