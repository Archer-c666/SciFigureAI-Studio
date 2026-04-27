@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================
echo   SciFigure AI Studio - Windows EXE 打包器
echo ============================================
echo.

echo 说明：
echo 1. 请在 Windows 电脑上运行本脚本。
echo 2. 打包完成后，可执行文件在 dist\SciFigure AI Studio\SciFigure AI Studio.exe
echo 3. 推荐先用“文件夹版”，稳定、启动更快；如需单文件版，看 build_tools\build_windows_onefile.bat
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set PY_CMD=py -3
) else (
    set PY_CMD=python
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] 创建虚拟环境 .venv ...
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo 创建虚拟环境失败。请安装 Python 3.9+。
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

echo [2/4] 安装/更新项目依赖 ...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r build_requirements.txt
if errorlevel 1 (
    echo 依赖安装失败，请检查网络或 pip 镜像。
    pause
    exit /b 1
)

echo [3/4] 清理旧打包文件 ...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

echo [4/4] 开始打包 EXE ...
pyinstaller --noconfirm --clean SciFigureAIStudio.spec
if errorlevel 1 (
    echo.
    echo 打包失败，请查看上方错误信息。
    pause
    exit /b 1
)

echo.
echo 打包完成！
echo EXE 位置：dist\SciFigure AI Studio\SciFigure AI Studio.exe
echo 可以把整个 dist\SciFigure AI Studio 文件夹压缩后发给别人。
echo.
pause
endlocal
