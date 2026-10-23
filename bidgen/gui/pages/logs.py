"""日志页：全程日志（级别标识）+ 导出脱敏日志。"""

from __future__ import annotations

import os
import platform

from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from ..version import VERSION


class LogsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("过程日志"))
        top.addStretch(1)
        export_btn = QPushButton("导出日志…")
        export_btn.clicked.connect(self.export_log)
        top.addWidget(export_btn)
        lay.addLayout(top)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        lay.addWidget(self.log, 1)

    def append(self, line: str) -> None:
        self.log.append(line)

    def export_log(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出日志", "bidgen-log.txt", "文本文件 (*.txt)")
        if not path:
            return
        text = _sanitize(self.log.toPlainText())
        header = (
            f"bidgen 日志导出\n"
            f"版本：{VERSION}\n"
            f"系统：{platform.system()} {platform.release()}（{platform.machine()}）\n"
            f"{'=' * 40}\n"
        )
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(header + text)


def _sanitize(text: str) -> str:
    """路径脱敏：把用户目录替换为 ~。"""
    home = os.path.expanduser("~")
    return text.replace(home, "~") if home and home != "/" else text
