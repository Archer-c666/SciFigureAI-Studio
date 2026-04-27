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
  --icon "assets/app_icon.icns" \
  --add-data ".env.example:." \
  --hidden-import openpyxl \
  --hidden-import seaborn \
  --collect-all matplotlib \
  --collect-all PIL \
  main.py

echo "打包完成：dist/SciFigure AI Studio.app"
