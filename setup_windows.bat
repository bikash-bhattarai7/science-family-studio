@echo off
REM One-click setup for Windows. Needs Python 3.10+ (python.org, tick "Add to PATH").
cd /d "%~dp0"
where ffmpeg >nul 2>nul || (echo Installing ffmpeg... & winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements)
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
echo.
echo Setup done. Rendering a test video (about 3 minutes)...
python run.py demo
echo.
echo Your test video is in episodes\demo-why-is-the-sky-blue\output
echo If ffmpeg was just installed and the test failed, close this window and run setup again.
pause
