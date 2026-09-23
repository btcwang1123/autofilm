@echo off
rem autofilm: 把 MP4 拖到這個 .bat 上
rem     run.bat 網址1 網址2 ...   -> 直接轉多個
rem     run.bat urls.txt           -> 從清單檔批次轉(每行一個網址)
setlocal
cd /d "%~dp0"
if "%~1"=="" (
    echo 用法:
    echo   把 MP4 檔拖到本檔上
    echo   run.bat 網址1 網址2 ...
    echo   run.bat urls.txt
    echo.
    echo 例: run.bat "https://youtu.be/aaa" "https://youtu.be/bbb"
    echo      run.bat urls.txt
    pause
    exit /b 1
)
".venv\Scripts\python.exe" srt_gen.py %*
echo.
pause
