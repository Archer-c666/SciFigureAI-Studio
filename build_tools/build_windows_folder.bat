@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
call 打包成EXE.bat
