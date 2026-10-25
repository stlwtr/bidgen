"""QApplication 工厂与主窗口装配（侧边导航四页 + 菜单（帮助→使用向导） + run_gui）。"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QStackedWidget, QStyle, QVBoxLayout, QWidget,
)

from . import styles
from .pages.about import AboutPage
from .pages.generate import GeneratePage
from .pages.logs import LogsPage
from .opener import BidgenApplication, local_files, pick_pdf
from .pages.suppliers import SuppliersPage
from .paths import resource_path
from .store import SupplierStore
from .version import BUILD_DATE, VERSION
from .widgets import DropOverlay, GuideDialog

_NAV = [
    ("生成", QStyle.SP_FileDialogNewFolder),
    ("供应商", QStyle.SP_DirHomeIcon),
    ("日志", QStyle.SP_FileDialogContentsView),
    ("关于", QStyle.SP_MessageBoxInformation),
]


class MainWindow(QMainWindow):
    def __init__(self, initial_pdf: str | None = None) -> None:
        super().__init__()
        self.setWindowTitle("投标助手")
        self.resize(960, 760)
        self.store = SupplierStore()

        root = QWidget()
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)

        self.setWindowIcon(QIcon(resource_path("assets/logo.png")))

        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        logo_label = QLabel()
        logo_label.setPixmap(
            QPixmap(resource_path("assets/logo.png")).scaled(
                44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )
        logo_label.setFixedSize(48, 48)
        title_row.addWidget(logo_label)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("投标助手")
        title.setObjectName("title")
        subtitle = QLabel(f"招标文件 PDF → 投标文件 Word　|　版本 {VERSION}（{BUILD_DATE}）")
        subtitle.setObjectName("subtitle")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        title_row.addLayout(title_col, 1)
        lay.addLayout(title_row)

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

        # 主窗口接受拖放：PDF 拖到窗口任意位置均可打开（行为同拖到图标）
        self.setAcceptDrops(True)
        self._drop_overlay = DropOverlay(self.centralWidget())

        if initial_pdf:
            self.open_pdf(initial_pdf)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt 命名约定
        super().resizeEvent(event)
        self._drop_overlay.setGeometry(self.centralWidget().rect())

    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt 命名约定
        paths = local_files(event.mimeData().urls())
        if not paths:
            event.ignore()
            return
        # 含本地文件即接受（无 PDF 时 drop 阶段给 Banner 反馈）；含 PDF 才显示遮罩预告可打开
        event.acceptProposedAction()
        if pick_pdf(paths) is not None:
            self._drop_overlay.setVisible(True)
            self._drop_overlay.raise_()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802 - Qt 命名约定
        self._drop_overlay.setVisible(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt 命名约定
        self._drop_overlay.setVisible(False)
        paths = local_files(event.mimeData().urls())
        if not paths:
            event.ignore()
            return
        event.acceptProposedAction()
        self.open_pdf(pick_pdf(paths) or paths[0])

    def _on_nav(self, row: int) -> None:
        self.pages.setCurrentIndex(row)

    def open_pdf(self, path: str) -> None:
        """外部打开招标文件（拖到图标 / argv 携带）：合法 PDF 预填并切到生成页，否则 Banner 提示。"""
        if path.lower().endswith(".pdf"):
            self.generate_page.error_banner.hide_banner()
            self.generate_page.pdf_edit.setText(path)
        else:
            self.generate_page.error_banner.show_error(
                "仅支持 PDF 招标文件", f"无法打开：{path}", []
            )
        self.nav.setCurrentRow(0)

    def _build_menus(self) -> None:
        view_menu = self.menuBar().addMenu("视图")
        view_menu.addAction("放大字号", lambda: self._scale_font(0.1))
        view_menu.addAction("缩小字号", lambda: self._scale_font(-0.1))
        help_menu = self.menuBar().addMenu("帮助")
        help_menu.addAction("使用向导…", self.show_guide)
        help_menu.addAction("关于 投标助手…", self.show_about)

    def _scale_font(self, delta: float) -> None:
        styles.set_font_scale(styles._FONT_SCALE + delta)  # noqa: SLF001
        self.setStyleSheet(styles.qss())

    def show_guide(self) -> None:
        """使用向导：仅从「帮助」菜单手动打开，启动时不再自动弹出。"""
        GuideDialog(self).exec()

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "关于 投标助手",
            f"<h3>投标助手</h3>"
            f"<p>版本：{VERSION}（构建日期：{BUILD_DATE}）</p>"
            f"<p>将政府采购招标文件 PDF 自动转换为结构规范、内容预填的投标文件 Word 初稿。</p>"
            f"<p>科创研发室提供支持。</p>",
        )


def run_gui(initial_pdf: str | None = None) -> int:
    # Windows 任务栏按 AppUserModelID 归类按钮与图标，须在创建 QApplication 前显式设置，
    # 否则打包后的 exe 运行时任务栏不显示应用图标
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BidgenGUI")
    app = BidgenApplication(sys.argv)
    app.setApplicationName("投标助手")
    # 应用级图标：Windows 任务栏 / Alt-Tab 与 Linux 窗口（.ico 多尺寸）
    app.setWindowIcon(QIcon(resource_path("assets/logo.ico")))
    app.setStyleSheet(styles.qss())
    window = MainWindow(initial_pdf)
    # macOS 拖放到 Dock/图标（QFileOpenEvent）在事件循环内到达，先接信号再 exec
    app.pdf_opened.connect(window.open_pdf)
    window.show()
    return app.exec()
