@echo off
rem autofilm - MP4 / YouTube URL to SRT subtitle generator.
rem Usage: double-click, drag & drop an MP4 onto this file, or run:
rem     run.bat <file.mp4 | url | urls.txt> [url2 ...]
rem First run auto-creates .venv and installs dependencies.
setlocal
cd /d "%~dp0"

rem ---- Auto-create venv if missing ----
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create .venv. Make sure Python 3.10+ is installed and on PATH.
        pause
        exit /b 1
    )
    echo [2/3] Installing dependencies from requirements.txt...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies. Check your network connection.
        pause
        exit /b 1
    )
)
set PYTHONIOENCODING=utf-8

rem ---- Check ffmpeg ----
".venv\Scripts\python.exe" -c "import shutil,sys; sys.exit(0 if shutil.which('ffmpeg') else 1)" >nul 2>&1
if errorlevel 1 echo [WARN] ffmpeg not found. Install it first: winget install Gyan.FFmpeg

rem ---- Run ----
if "%~1"=="" (
    echo.
    echo   autofilm - MP4 / YouTube URL to SRT subtitles
    echo   ----------------------------------------------
    echo   Usage:
    echo     Drag an MP4 file onto this .bat window
    echo     run.bat url1 url2 ...
    echo     run.bat urls.txt
    echo   Example: run.bat "https://youtu.be/aaa" "https://youtu.be/bbb"
    echo   ----------------------------------------------
    echo   Output: one .srt per input in the current folder.
    echo.
    pause
    exit /b 0
)

echo [3/3] Processing...
".venv\Scripts\python.exe" srt_gen.py %*
echo.
pause
