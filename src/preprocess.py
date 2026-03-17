import cv2
import numpy as np

def preprocess_image(image_path: str, prep: str = "otsu") -> np.ndarray:
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if prep == "otsu":
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        _, result = cv2.threshold(denoised, 0, 255,
                                    cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif prep == "adaptive":
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        result = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 10)
    elif prep == "sharpen_otsu":
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        sharpened = cv2.filter2D(gray, -1, kernel)
        _, result = cv2.threshold(sharpened, 0, 255,
                                    cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif prep == "enlarge_adaptive":
        enlarged = cv2.resize(gray, None, fx=1.5, fy=1.5,
                                interpolation=cv2.INTER_CUBIC)
        blurred = cv2.GaussianBlur(enlarged, (5, 5), 0)
        result = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 10)
    else:
        _, result = cv2.threshold(gray, 0, 255,
                                    cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return result