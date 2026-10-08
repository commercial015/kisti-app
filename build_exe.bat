@echo off
setlocal
cd /d "%~dp0"
python -m pip install --upgrade pip
python -m pip install pyinstaller
python -m PyInstaller --clean --onefile --windowed --name KistiHisabProfessional main.py
echo.
echo =========================================
echo EXE তৈরি হয়েছে:
echo dist\KistiHisabProfessional.exe
echo =========================================
pause
