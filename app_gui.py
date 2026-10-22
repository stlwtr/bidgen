"""PyInstaller 打包入口：投标文件生成助手（GUI）。

各平台分别用 PyInstaller 打包生成原生可执行文件：
- Windows: 生成 `投标文件生成助手.exe`
- Linux:   生成 `投标文件生成助手`（可执行文件）
- macOS:   生成 `投标文件生成助手.app`

用法（在对应平台上，已装好 .venv 依赖）：
    .venv/bin/pyinstaller scripts/build_app.spec
或一键脚本：
    python3 scripts/build_app.py
"""

import sys

from bidgen.gui import run_gui

if __name__ == "__main__":
    sys.exit(run_gui())
