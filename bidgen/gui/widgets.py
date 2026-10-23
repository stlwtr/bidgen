"""共享界面控件与常量。"""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QLabel,
    QPushButton, QToolButton, QVBoxLayout, QWidget,
)

SUPPLIER_FIELDS = [
    ("company_name", "投标人名称"),
    ("legal_representative", "法定代表人（单位负责人）"),
    ("address", "详细地址"),
    ("postal_code", "邮政编码"),
    ("phone", "电话"),
    ("email", "电子函件（邮箱）"),
    ("bank_name", "投标人开户银行"),
    ("bank_account", "账号 / 行号"),
    ("authorized_representative", "委托代理人姓名"),
    ("authorized_representative_id", "委托代理人身份证号"),
    ("date", "日期"),
]

COMPANY_TYPES = ["企业", "事业单位", "社会团体", "非企业专业服务机构", "个体工商户", "自然人"]


def open_path(path: str) -> None:
    """跨平台打开文件或目录（不存在则忽略）。"""
    if not path or not os.path.exists(path):
        return
    if sys.platform == "darwin":
        os.system(f'open "{path}"')
    elif os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        os.system(f'xdg-open "{path}"')


def default_downloads_dir() -> str:
    """系统下载目录（Win/Linux/macOS 通用默认：~/Downloads）。"""
    return os.path.join(os.path.expanduser("~"), "Downloads")


class CollapsibleSection(QWidget):
    """「高级选项 ▸」可折叠区。"""

    def __init__(self, title: str = "高级选项", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._toggle = QToolButton(self)
        self._toggle.setText(f"{title} ▸")
        self._toggle.setCheckable(True)
        self._toggle.setStyleSheet("border:none; font-weight:600; color:#4a5568; padding:0;")
        self._toggle.toggled.connect(self._on_toggled)

        self.content = QWidget()
        self.content.setVisible(False)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(self._toggle)
        lay.addWidget(self.content)

    def set_expanded(self, expanded: bool) -> None:
        self._toggle.setChecked(expanded)
        self._on_toggled(expanded)

    def _on_toggled(self, checked: bool) -> None:
        self.content.setVisible(checked)
        self._toggle.setText(f"{self._title} {'▾' if checked else '▸'}")


class Banner(QFrame):
    """内联成败/错误条（成功绿 / 失败红，可带按钮与可展开详情）。"""

    def __init__(self, ok: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("banner")
        self.setProperty("ok", ok)
        self.setProperty("err", not ok)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(6)
        self._title = QLabel()
        self._title.setStyleSheet("font-weight:700;")
        self._title.setWordWrap(True)
        lay.addWidget(self._title)
        self._detail = QLabel()
        self._detail.setWordWrap(True)
        self._detail.setVisible(False)
        lay.addWidget(self._detail)
        self._btn_row = QHBoxLayout()
        self._btn_row.setSpacing(8)
        lay.addLayout(self._btn_row)
        self.setVisible(False)

    def _set(self, title: str, detail: str, buttons: list) -> None:
        self._title.setText(title)
        self._detail.setText(detail)
        self._detail.setVisible(bool(detail))
        while self._btn_row.count():
            item = self._btn_row.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        for text, fn in buttons:
            btn = QPushButton(text)
            btn.clicked.connect(fn)
            self._btn_row.addWidget(btn)
        self._btn_row.addStretch(1)
        self.setVisible(True)

    def show_success(self, title: str, buttons: list | None = None) -> None:
        self._set(title, "", buttons or [])

    def show_error(self, title: str, detail: str = "", buttons: list | None = None) -> None:
        self._set(title, detail, buttons or [])

    def hide_banner(self) -> None:
        self.setVisible(False)


class GuideDialog(QDialog):
    """首次启动引导页（三步图文 + 「不再显示」）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("欢迎使用 投标文件生成助手")
        self.setModal(True)
        self.resize(560, 430)

        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        title = QLabel("三步生成投标文件")
        title.setStyleSheet("font-size:18px; font-weight:800;")
        lay.addWidget(title)

        steps = QLabel(
            "<b>① 选择招标文件 PDF</b><br>在「生成」页点「浏览…」选择招标文件。<br><br>"
            "<b>② 检查 / 选择供应商</b><br>左侧导航「供应商」维护多个供应商档案，设为当前。<br><br>"
            "<b>③ 点击「生成投标文件」</b><br>等待顶部进度条完成，成功后可「打开输出目录」或「打开投标文件」。"
        )
        steps.setWordWrap(True)
        lay.addWidget(steps, 1)

        self.dont_show = QCheckBox("不再显示")
        lay.addWidget(self.dont_show)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        lay.addWidget(buttons)
