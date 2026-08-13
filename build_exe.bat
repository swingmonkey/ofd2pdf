@echo off
REM Build standalone OFD转PDF工具.exe (windowed GUI).
REM Requires 64-bit Python 3.9+ with easyofd, pymupdf and pyinstaller.
cd /d "%~dp0"

echo [1/3] Ensuring build dependencies (easyofd pymupdf pyinstaller)...
py -3.13 -m pip install easyofd pymupdf pyinstaller
if errorlevel 1 goto :fail

echo [2/3] Building with PyInstaller...
py -3.13 -m PyInstaller ofd2pdf.spec --noconfirm --clean
if errorlevel 1 goto :fail

echo [3/3] Done.
echo.
echo Output: dist\OFD转PDF工具.exe
pause
exit /b 0

:fail
echo.
echo Build FAILED. Check the messages above.
pause
exit /b 1
