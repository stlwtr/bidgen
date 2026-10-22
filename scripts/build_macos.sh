#!/usr/bin/env bash
# 投标文件生成助手 - macOS 一键打包脚本（生成 dist/BidgenGUI.app）
set -e
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
    echo "创建虚拟环境 .venv ..."
    python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "安装依赖..."
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller

echo "开始打包..."
pyinstaller --onedir --windowed --name BidgenGUI \
  --collect-all fitz --collect-all pdf2docx --collect-all cv2 \
  --collect-all docx --collect-all yaml --collect-all bidgen \
  --hidden-import PySide6 app_gui.py

echo ""
echo "打包完成: dist/BidgenGUI.app（与 dist/BidgenGUI）"
