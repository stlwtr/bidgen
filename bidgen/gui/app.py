"""QApplication 工厂与主窗口装配（侧边导航四页 + 首次引导 + 菜单 + run_gui）。"""

from __future__ import annotations

import json
import os
import sys

from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QStackedWidget, QStyle, QVBoxLayout, QWidget,
)

from . import styles
from .pages.about import AboutPage
from .pages.generate import GeneratePage
from .pages.logs import LogsPage
from .pages.suppliers import SuppliersPage
from .store import SupplierStore
from .version import BUILD_DATE, VERSION
from .widgets import GuideDialog

_NAV = [
    ("生成", QStyle.SP_FileDialogNewFolder),
    ("供应商", QStyle.SP_DirHomeIcon),
    ("日志", QStyle.SP_FileDialogContentsView),
    ("关于", QStyle.SP_MessageBoxInformation),
]

_UI_STATE_FILE = os.path.join("suppliers", ".ui.json")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("投标文件生成助手")
        self.resize(860, 760)
        self.store = SupplierStore()

        root = QWidget()
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)

        title = QLabel("投标文件生成助手")
        title.setObjectName("title")
        subtitle = QLabel(f"招标文件 PDF → 投标文件 Word　|　版本 {VERSION}（{BUILD_DATE}）")
        subtitle.setObjectName("subtitle")
        lay.addWidget(title)
        lay.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(12)
        lay.addLayout(body, 1)

        # 左侧竖向导航
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFixedWidth(150)
        style = self.style()
        for text, icon in _NAV:
            self.nav.addItem(QListWidgetItem(style.standardIcon(icon), text))
        self.nav.currentRowChanged.connect(self._on_nav)
        body.addWidget(self.nav)

        # 右侧四页
        self.pages = QStackedWidget()
        self.generate_page = GeneratePage(self.store)
        self.suppliers_page = SuppliersPage(self.store)
        self.logs_page = LogsPage()
        self.about_page = AboutPage()
        for page in (self.generate_page, self.suppliers_page, self.logs_page, self.about_page):
            self.pages.addWidget(page)
        body.addWidget(self.pages, 1)

        # 生成页日志同步到日志页
        self.generate_page.log_line.connect(self.logs_page.append)

        self.nav.setCurrentRow(0)
        self.setStyleSheet(styles.qss())

        self._build_menus()
        self._maybe_show_guide()

    def _on_nav(self, row: int) -> None:
        self.pages.setCurrentIndex(row)

    def _build_menus(self) -> None:
        view_menu = self.menuBar().addMenu("视图")
        view_menu.addAction("放大字号", lambda: self._scale_font(0.1))
        view_menu.addAction("缩小字号", lambda: self._scale_font(-0.1))
        help_menu = self.menuBar().addMenu("帮助")
        help_menu.addAction("关于 投标文件生成助手…", self.show_about)

    def _scale_font(self, delta: float) -> None:
        styles.set_font_scale(styles._FONT_SCALE + delta)  # noqa: SLF001
        self.setStyleSheet(styles.qss())

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "关于 投标文件生成助手",
            f"<h3>投标文件生成助手</h3>"
            f"<p>版本：{VERSION}（构建日期：{BUILD_DATE}）</p>"
            f"<p>将政府采购招标文件 PDF 自动转换为结构规范、内容预填的投标文件 Word 初稿。</p>"
            f"<p>科创研发室提供支持。</p>",
        )

    def _maybe_show_guide(self) -> None:
        # 测试 / CI 可用 BIDGEN_NO_GUIDE=1 跳过模态引导页
        if os.environ.get("BIDGEN_NO_GUIDE"):
            return
        if self._ui_state().get("dont_show_guide"):
            return
        dlg = GuideDialog(self)
        if dlg.exec() and dlg.dont_show.isChecked():
            self._save_ui_state({"dont_show_guide": True})

    def _ui_state(self) -> dict:
        try:
            with open(_UI_STATE_FILE, encoding="utf-8") as handle:
                return json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_ui_state(self, data: dict) -> None:
        state = self._ui_state()
        state.update(data)
        os.makedirs(os.path.dirname(_UI_STATE_FILE), exist_ok=True)
        with open(_UI_STATE_FILE, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False)


def run_gui() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("投标文件生成助手")
    app.setStyleSheet(styles.qss())
    window = MainWindow()
    window.show()
    return app.exec()
