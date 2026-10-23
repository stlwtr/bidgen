"""关于页：功能说明 + 版本 / 构建日期 + 科创研发室提供支持。"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

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
