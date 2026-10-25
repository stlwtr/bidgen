#!/usr/bin/env bash
# 投标助手 - macOS 一键打包脚本
# 产出：dist/BidgenGUI.app（onedir，显示名「投标助手」）与 dist/投标助手-<version>.dmg（拖动到 Applications 安装）
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

APP="dist/投标助手.app"
VERSION=$(python -c "import json; print(json.load(open('version.json', encoding='utf-8'))['version'])")
DMG="dist/投标助手-${VERSION}.dmg"

echo "制作 DMG 安装镜像：${DMG} ..."
STAGING=$(mktemp -d)
trap 'rm -rf "$STAGING"' EXIT
cp -R "$APP" "$STAGING/"
ln -s /Applications "$STAGING/Applications"
cp "scripts/macos/安装说明.txt" "$STAGING/安装说明.txt"

hdiutil create -volname "投标助手" -srcfolder "$STAGING" -ov -format UDZO "$DMG"
codesign --force --sign - "$DMG"

echo ""
echo "打包完成:"
echo "  应用: $APP"
echo "  镜像: $DMG（拖动到 Applications 安装，上传云盘分发此文件）"
