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

echo "开始打包（配置唯一来源：BidgenGUI.spec，含 Info.plist 文档类型声明）..."
pyinstaller --clean --noconfirm BidgenGUI.spec

echo ""
echo "打包完成: dist/BidgenGUI.app（与 dist/BidgenGUI）"
