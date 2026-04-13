# MainProject OCR

거래명세서 / 영수증 PDF를 OCR로 텍스트 추출 후
데이터를 정제하여 ERP DB에 자동 입력하는 파이프라인 구성예정

## 프로젝트 개요
- 개발 기간 : 2026.03.16 ~ 진행중
- 사용 기술 : Python, TesseractOCR, OpenCV, pdf2image
- 목적 : 거래명세서 PDF -> OCR -> 데이터 정제 -> ERP DB에 자동 입력

## 라이브러리
- pytesseract==0.3.13
- pdf2image==1.17.0
- opencv-python==4.13.0.92
- Pillow
- pandas==3.0.1
- PyMySQL==1.1.2
- openpyxl==3.1.5
- PyMuPDF==1.27.2
- python-dotenv

## 주요 기능
- PDF → 이미지 변환 후 Tesseract OCR 텍스트 추출
- 전처리 4종 (otsu / adaptive / sharpen / enlarge) 실험 자동화
- 후처리로 노이즈 줄 제거 (URL, 날짜헤더, 확인란 등)
- CER(Character Error Rate) 기반 정확도 측정 및 실험 결과 누적 저장
- experiment_config.xlsx에서 실험 설정 관리 (RUN=yes/no)
- 결과 저장: output/PDF이름_yymmdd/ 폴더 자동 분류

## 환경 세팅

### 1. poppler 설치
https://github.com/oschwartz10612/poppler-windows/releases
- 다운로드 후 압축 해제 → `poppler/bin/` 폴더에 배치


### 2. 자동 설치 (setup.bat)
Tesseract 및 pip 패키지를 자동으로 설치합니다.
setup.bat 우클릭 → 관리자 권한으로 실행

> Python이 먼저 설치되어 있어야 합니다.  
> poppler는 자동 설치되지 않으므로 1번 단계를 먼저 완료해주세요.

### 3. 수동 패키지 설치
```bash
pip install -r requirements.txt
```

### 4. .env로 DB연결
DB_HOST=
DB_PORT=
DB_NAME=
DB_USER=
DB_PASSWORD=

### 5. 환경 점검
설치가 완료되면 아래 명령어로 환경을 점검합니다.
```bash
python verify_setup.py
```
모든 항목이 `[OK]`로 표시되면 실행 가능한 상태입니다.

## 가상환경 설정 (권장)

패키지 버전 충돌 방지를 위해 가상환경에서 실행했습니다.

```bash
# 1. 프로젝트 루트에서 가상환경 생성
python -m venv venv

# 2. 가상환경 활성화 (Windows PowerShell)
.\venv\Scripts\activate

# 3. 가상환경 활성화 (Windows CMD)
venv\Scripts\activate.bat

# 4. 패키지 설치
pip install -r requirements.txt

# 5. 환경 점검
python verify_setup.py

# 6. 가상환경 비활성화
deactivate
```

> VSCode 사용 시 `Ctrl+Shift+P` → `Python: Select Interpreter` → `./venv/Scripts/python.exe` 선택

## 실행 방법

1. `input/` 폴더에 PDF 파일 넣기
2. 실행
```bash
cd src
python main.py
```

3. 결과 확인: `output/PDF이름_yymmdd/` 폴더

## 개발 환경

- Python 3.14
- Windows 10/11
- Tesseract OCR 5.x
- VSCode