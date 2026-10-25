"""PyInstaller 打包入口：投标助手（GUI）。

各平台分别用 PyInstaller 打包生成原生可执行文件（产物名为 BidgenGUI，
macOS 经 Info.plist 的 CFBundleDisplayName 显示为「投标助手」）：
- Windows: 生成 `BidgenGUI.exe`
- Linux:   生成 `BidgenGUI`（可执行文件）
- macOS:   生成 `BidgenGUI.app`

用法（macOS）：
    bash scripts/build_macos.sh   # 一键打包并产出 DMG 安装镜像
"""

import os
import sys
import traceback


def _crash_log_path() -> str:
    """崩溃日志路径（跨平台用户级目录）；windowed 打包后 stderr 不可见，异常落盘以便排障。"""
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Logs/BidgenGUI.log")
    if os.name == "nt":
        return os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "BidgenGUI", "crash.log"
        )
    return os.path.join(
        os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state")),
        "BidgenGUI",
        "crash.log",
    )


_CRASH_LOG = _crash_log_path()


def _excepthook(exc_type, exc, tb):
    try:
        os.makedirs(os.path.dirname(_CRASH_LOG), exist_ok=True)
        with open(_CRASH_LOG, "a", encoding="utf-8") as f:
            f.write("".join(traceback.format_exception(exc_type, exc, tb)))
    except OSError:
        pass
    sys.__excepthook__(exc_type, exc, tb)


sys.excepthook = _excepthook

from bidgen.gui import run_gui
from bidgen.gui.opener import pick_pdf

if __name__ == "__main__":
    # Windows / Linux：拖到 exe 图标时文件路径经 argv 进入；macOS 走 QFileOpenEvent（见 opener）
    sys.exit(run_gui(pick_pdf(sys.argv[1:])))
