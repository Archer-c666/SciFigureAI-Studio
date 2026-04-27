#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r build_requirements.txt

rm -rf build dist
pyinstaller --noconfirm --clean --windowed --name "SciFigure AI Studio" \
  --add-data ".env.example:." \
  --hidden-import openpyxl \
  --hidden-import seaborn \
  --collect-all matplotlib \
  --collect-all PIL \
  main.py

echo "Linux 可执行文件已生成：dist/SciFigure AI Studio/SciFigure AI Studio"
echo "如需 AppImage，可再使用 appimagetool 或 linuxdeployqt 进行封装。"
