# MainProject OCR

거래명세서 / 영수증 PDF를 OCR로 텍스트 추출 후
데이터를 정제하여 ERP DB에 자동 입력하는 파이프라인 구성예정

## 프로젝트 개요

개발 기간 : 2026.03.16 ~ 진행중
사용 기술 : Python, TesseractOCR, OpenCV, pdf2image
목적 : 거래명세서 PDF -> OCR -> 데이터 정제 -> ERP DB에 자동 입력

## 라이브러리
- pytesseract==0.3.13
- pdf2image==1.17.0
- opencv-python==4.13.0.92
- Pillow
- pandas==3.0.1
- PyMySQL==1.1.2
- openpyxl==3.1.5
- PyMuPDF==1.27.2

## 주요 기능
- PDF → 이미지 변환 후 Tesseract OCR 텍스트 추출
- 전처리 4종 (otsu / adaptive / sharpen / enlarge) 실험 자동화
- 후처리로 노이즈 줄 제거 (URL, 날짜헤더, 확인란 등)
- CER(Character Error Rate) 기반 정확도 측정 및 실험 결과 누적 저장
- experiment_config.xlsx에서 실험 설정 관리 (RUN=yes/no)
- 결과 저장: output/PDF이름_yymmdd/ 폴더 자동 분류

## 환경 세팅

### 1. Tesseract 설치
https://github.com/UB-Mannheim/tesseract/wiki
- 설치 시 Korean 언어팩 체크 필수

### 2. poppler 설치
https://github.com/oschwartz10612/poppler-windows/releases
- 다운로드 후 압축 해제 → `poppler/bin/` 폴더에 배치

### 3. 패키지 설치
```bash
pip install -r requirements.txt
```

### 4. 환경 점검
```bash
python verify_setup.py
```

## 실행 방법

1. `input/` 폴더에 PDF 파일 넣기
2. `experiment_config.xlsx`에서 실행할 실험 RUN=yes 설정
3. 실행
```bash
cd src
python main.py
```

4. 결과 확인: `output/PDF이름_yymmdd/` 폴더

## 개발 환경

- Python 3.14
- Windows 10/11
- Tesseract OCR 5.x
- VSCode