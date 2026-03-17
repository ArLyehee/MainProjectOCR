@echo off
chcp 65001 > nul
echo =============================================
echo    OCR 환경 자동 세팅 시작
echo =============================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [오류] 관리자 권한으로 실행해주세요.
    echo setup.bat 우클릭 후 "관리자 권한으로 실행" 선택
    pause
    exit /b
)

:: Python 설치 확인
echo [1/4] Python 설치 확인 중...
python --version > nul 2>&1
if %errorLevel% neq 0 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo https://www.python.org 에서 설치 후 다시 실행해주세요.
    pause
    exit /b
)
echo Python 확인 완료

:: pip 패키지 설치
echo.
echo [2/4] pip 패키지 설치 중...
pip install -r requirements.txt
if %errorLevel% neq 0 (
    echo [오류] pip 설치 실패. 인터넷 연결을 확인해주세요.
    pause
    exit /b
)
echo pip 패키지 설치 완료

:: Tesseract 설치 (winget 사용)
echo.
echo [3/4] Tesseract OCR 설치 중...
winget install --id UB-Mannheim.TesseractOCR -e --silent
if %errorLevel% neq 0 (
    echo [경고] winget 설치 실패. 수동 설치가 필요합니다.
    echo 브라우저에서 아래 주소로 이동해 설치해주세요:
    echo https://github.com/UB-Mannheim/tesseract/wiki
    pause
)
echo Tesseract 설치 완료

:: poppler PATH 안내 (폴더에 포함되어 있음)
echo.
echo [4/4] poppler 경로 확인 중...
if exist "poppler\bin\pdftoppm.exe" (
    echo poppler 확인 완료 - 프로젝트 폴더에서 정상 감지됨
) else (
    echo [경고] poppler\bin\pdftoppm.exe 파일이 없습니다.
    echo STEP 2 안내에 따라 poppler 파일을 넣어주세요.
)

echo.
echo =============================================
echo    설치 완료! verify_setup.py 실행으로 확인
echo =============================================
pause