@echo off
setlocal

cd /d "%~dp0"

echo.
echo ========================================
echo Building Ultimate Scraper pro
echo ========================================
echo.

python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [ERROR] PyInstaller not found. Installing...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller.
        pause
        exit /b 1
    )
)

python -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --name "Ultimate Scraper pro" ^
    --icon "app_icon.ico" ^
    --add-data "console_logos;console_logos" ^
    --add-data "Gamersicon.png;." ^
    --add-data "app_icon.ico;." ^
    "UltimateScraperProv2.0.py"

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo Done: "%~dp0dist\Ultimate Scraper pro.exe"
pause
