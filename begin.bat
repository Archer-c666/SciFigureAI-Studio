@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================
echo   SciFigure AI Studio - 开发版双击启动器
echo ============================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set PY_CMD=py -3
) else (
    set PY_CMD=python
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] 首次运行：正在创建 Python 虚拟环境 .venv ...
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo.
        echo 创建虚拟环境失败。请确认已安装 Python 3.9+，并勾选 Add Python to PATH。
        pause
        exit /b 1
    )

    call ".venv\Scripts\activate.bat"
    echo [2/3] 正在升级 pip ...
    python -m pip install --upgrade pip

    echo [3/3] 正在安装依赖，首次安装可能需要几分钟 ...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo 依赖安装失败。请检查网络，或尝试切换 pip 镜像。
        echo 示例：pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
        pause
        exit /b 1
    )
) else (
    call ".venv\Scripts\activate.bat"
)

echo.
echo 正在启动 SciFigure AI Studio ...
python main.py

if errorlevel 1 (
    echo.
    echo 程序异常退出，请查看上方报错信息。
    pause
)
endlocal
