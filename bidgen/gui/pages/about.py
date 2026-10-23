"""关于页：功能说明 + 版本 / 构建日期 + 版本更新检查 + 科创研发室提供支持。"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .. import updater
from ..version import BUILD_DATE, VERSION

_FEATURES = """将政府采购招标文件 PDF 自动转换为结构规范、内容预填的投标文件 Word 初稿：

• 招标文件 PDF 转 Word（乱码修复）
• 提取投标文件格式，重建 16 章骨架（自动编号、页眉页脚、目录域）
• 承诺函按通用规则填充采购人 / 代理机构 / 项目 / 编号 / 投标人
• 商务与技术表格按位置渲染，技术偏离表从招标文件模板提取
• 生成后清理文档机器码与用户信息
"""


class AboutPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        title = QLabel("投标文件生成助手")
        title.setStyleSheet("font-size:20px; font-weight:800;")
        lay.addWidget(title)
        lay.addWidget(QLabel(f"版本：{VERSION}（构建日期：{BUILD_DATE}）"))
        body = QLabel(_FEATURES)
        body.setWordWrap(True)
        lay.addWidget(body, 1)
        support = QLabel("科创研发室提供支持。")
        support.setStyleSheet("color:#4a5568; font-weight:600;")
        lay.addWidget(support)
        feedback = QLabel(
            '<a href="https://www.kdocs.cn/l/cj7LOlXOtrRH">问题反馈【金山文档 | WPS云文档】</a>'
        )
        feedback.setOpenExternalLinks(True)
        feedback.setStyleSheet("color:#4a7dff;")
        lay.addWidget(feedback)

        # 版本更新检查
        upd_row = QHBoxLayout()
        self.update_btn = QPushButton("检查更新")
        self.update_btn.clicked.connect(self.check_update)
        self.update_label = QLabel("")
        self.update_label.setOpenExternalLinks(True)
        self.update_label.setWordWrap(True)
        upd_row.addWidget(self.update_btn)
        upd_row.addWidget(self.update_label, 1)
        lay.addLayout(upd_row)
        self._update_thread: _UpdateCheckThread | None = None

    def check_update(self) -> None:
        self.update_btn.setEnabled(False)
        self.update_label.setText("正在检查更新…")
        self._update_thread = _UpdateCheckThread(updater.UPDATE_URL)
        self._update_thread.result.connect(self._on_update_result)
        self._update_thread.finished.connect(lambda: self.update_btn.setEnabled(True))
        self._update_thread.start()

    def _on_update_result(self, info: updater.UpdateInfo | None) -> None:
        if info is None:
            self.update_label.setText("检查失败（网络不可用或无法访问版本信息）")
        elif info.has_update:
            self.update_label.setText(
                f"发现新版本 v{info.latest}！<a href='{info.download_url}'>点击下载</a>"
            )
        else:
            self.update_label.setText(f"当前 v{info.current}，已是最新 ✓")


class _UpdateCheckThread(QThread):
    result = Signal(object)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self) -> None:
        self.result.emit(updater.check_update(self.url))
