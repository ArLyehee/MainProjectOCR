import os
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

config_data = {
    "실험명":       ["KR_otsu", "KR_adaptive", "KR_sharpen", "KR_enlarge_ada"],
    "langs":       ["kor+eng"] * 4,
    "dpi":         [300, 300, 300, 300],
    "psm":         [6, 6, 6, 6],
    "prep":        ["otsu", "adaptive", "sharpen_otsu", "enlarge_adaptive"],
    "deskew":      ["no", "no", "no", "no"],
    "table_clean": ["no", "no", "no", "no"],
    "whitelist":   ["-", "-", "-", "-"],
    "RUN":         ["yes", "yes", "yes", "yes"],  # yes면 실행, no면 건너뜀
}

df = pd.DataFrame(config_data)
path = os.path.join(ROOT_DIR, "experiment_config.xlsx")
df.to_excel(path, index=False)
print(f"생성 완료: {path}")