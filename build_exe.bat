@echo off
setlocal
cd /d "%~dp0"
py -3.12 build_release.py
if errorlevel 1 exit /b 1
echo Built release\Ultimate-Scraper-Pro-Studio.exe
