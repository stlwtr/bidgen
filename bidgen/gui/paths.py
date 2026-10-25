"""应用数据目录解析：打包分发时落到用户级数据目录，不依赖启动时的工作目录。

PyInstaller 打包的 GUI app 双击启动时 cwd 为 /（macOS 只读根目录），
相对路径「suppliers」会抛 OSError: Read-only file system，进程在窗口显示前退出。
"""

from __future__ import annotations

import os
import sys


def _user_data_dir() -> str:
    """跨平台用户级数据目录（Win / macOS / Linux）。"""
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/BidgenGUI")
    if os.name == "nt":
        return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "BidgenGUI")
    return os.path.join(
        os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")), "BidgenGUI"
    )


def resource_path(rel: str) -> str:
    """只读资源路径（assets 等）：打包（frozen）时在 sys._MEIPASS 下，开发时保持相对路径。"""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, rel)  # type: ignore[attr-defined]
    return rel


def suppliers_dir() -> str:
    """供应商档案目录：打包（frozen）时用用户数据目录，开发时沿用项目下 suppliers/。

    注意：开发模式返回相对路径，需从项目根目录启动（python -m bidgen gui），
    否则档案会落到启动时的 cwd。分发形态为 PyInstaller 打包，frozen 分支不受此限。
    """
    if getattr(sys, "frozen", False):
        return os.path.join(_user_data_dir(), "suppliers")
    return "suppliers"
