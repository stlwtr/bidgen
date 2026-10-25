"""外部打开 PDF 的接入：argv 解析 + macOS 拖放/打开方式（QFileOpenEvent）。

- Windows / Linux：拖文件到 exe 图标或命令行携带路径，经 argv 进入，pick_pdf 取首个合法 PDF。
- macOS：拖文件到 Dock / .app 图标或「打开方式」，系统投递 QFileOpenEvent，
  BidgenApplication 捕获后转发为 pdf_opened 信号（未运行时由系统先启动再投递，
  事件在事件循环内到达，run_gui 中先连接信号再 exec 即可覆盖）。
"""

from __future__ import annotations

import os
from typing import Iterable

from PySide6.QtCore import QEvent, Signal
from PySide6.QtWidgets import QApplication


def pick_pdf(paths: Iterable[str]) -> str | None:
    """从候选路径中取第一个真实存在的 .pdf（大小写不敏感）；无则返回 None。"""
    for path in paths:
        if path and path.lower().endswith(".pdf") and os.path.isfile(path):
            return path
    return None


def local_files(urls: Iterable) -> list[str]:
    """从 QMimeData.urls() 提取本地文件路径（忽略非本地 URL）。"""
    return [u.toLocalFile() for u in urls if u.isLocalFile()]


class BidgenApplication(QApplication):
    """捕获 macOS QFileOpenEvent（拖放到 Dock/图标、打开方式），转发为 pdf_opened 信号。"""

    pdf_opened = Signal(str)

    def event(self, event) -> bool:  # noqa: N802 - Qt 命名约定
        if event.type() == QEvent.Type.FileOpen:
            url = event.url()
            if url.isLocalFile():
                self.pdf_opened.emit(url.toLocalFile())
            return True
        return super().event(event)
