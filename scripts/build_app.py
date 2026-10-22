"""一键打包 GUI 为当前平台的原生可执行文件（Windows / Linux / macOS）。

PyInstaller 不能跨平台打包，请在目标平台上运行本脚本：
  - Windows:  python scripts/build_app.py   → dist/BidgenGUI.exe
  - Linux:    python3 scripts/build_app.py  → dist/BidgenGUI
  - macOS:    python3 scripts/build_app.py  → dist/BidgenGUI.app（与 dist/BidgenGUI）

前置：先 `pip install -r requirements.txt pyinstaller`（或项目 .venv 已含依赖）。
"""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_COLLECT = [
    "--collect-all", "fitz",        # PyMuPDF（PDF 读取，C 扩展）
    "--collect-all", "pdf2docx",    # PDF→DOCX 转换（含 opencv/numpy）
    "--collect-all", "cv2",         # opencv-python-headless（pdf2docx 依赖）
    "--collect-all", "docx",        # python-docx
    "--collect-all", "yaml",        # PyYAML（供应商配置）
    "--collect-all", "bidgen",      # 本项目包
    "--hidden-import", "PySide6",
]


def main() -> None:
    system = platform.system()
    args = [sys.executable, "-m", "PyInstaller", "--windowed", "--name", "BidgenGUI"]
    if system == "Darwin":
        # macOS：onedir（.app 包；onefile+windowed 在 macOS 已被弃用）
        args.append("--onedir")
    else:
        args.append("--onefile")
    args += _COLLECT + [str(ROOT / "app_gui.py")]

    print(f"平台：{system}")
    print("打包命令：" + " ".join(args))
    subprocess.run(args, cwd=ROOT, check=True)

    target = {
        "Windows": "dist/BidgenGUI.exe",
        "Darwin": "dist/BidgenGUI.app",
        "Linux": "dist/BidgenGUI",
    }.get(system, "dist/BidgenGUI")
    print(f"打包完成 → {target}")


if __name__ == "__main__":
    main()
