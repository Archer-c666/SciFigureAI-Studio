@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0\.."

where py >nul 2>nul
if %errorlevel%==0 (set PY_CMD=py -3) else (set PY_CMD=python)

if not exist ".venv\Scripts\python.exe" %PY_CMD% -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r build_requirements.txt

rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

pyinstaller --noconfirm --clean --windowed --onefile ^
  --name "SciFigure AI Studio" ^
   --add-data ".env.example;." ^
  --hidden-import openpyxl ^
  --hidden-import seaborn ^
  --collect-all matplotlib ^
  --collect-all PIL ^
  main.py

if errorlevel 1 (
    echo 单文件版打包失败。
    pause
    exit /b 1
)

echo.
echo 单文件 EXE 已生成：dist\SciFigure AI Studio.exe
echo 注意：单文件版首次启动会较慢，推荐正式发布优先使用文件夹版。
pause
endlocal
