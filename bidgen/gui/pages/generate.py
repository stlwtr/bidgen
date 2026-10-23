"""生成页：选招标 PDF → 生成 → 顶部进度条 → 内联成败条。"""

from __future__ import annotations

import os
import tempfile

import yaml
from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QProgressBar, QPushButton, QTextEdit,
    QVBoxLayout, QWidget,
)

from ..store import SupplierStore
from ..widgets import Banner, CollapsibleSection, default_downloads_dir, open_path
from ..workers import Worker


class GeneratePage(QWidget):
    log_line = Signal(str)

    def __init__(self, store: SupplierStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self._worker: Worker | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.poll_worker)

        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        # 空状态引导（未选 PDF 时显示）
        self.empty_label = QLabel(
            "① 点「浏览…」选择招标文件 PDF\n"
            "② 「高级选项」可调整输出目录与是否同时生成招标文件 Word\n"
            "③ 点「生成投标文件」"
        )
        self.empty_label.setStyleSheet(
            "color:#6b7a90; padding:8px; border:1px dashed #d7dee9; border-radius:8px;"
        )
        lay.addWidget(self.empty_label)

        # 招标 PDF（最少字段）
        file_box = QGroupBox("招标文件")
        fl = QFormLayout(file_box)
        self.pdf_edit = QLineEdit()
        self.pdf_edit.setReadOnly(True)
        self.pdf_edit.setPlaceholderText("选择招标文件 PDF…")
        self.pdf_edit.textChanged.connect(self._on_pdf_changed)
        pdf_btn = QPushButton("浏览…")
        pdf_btn.clicked.connect(self.browse_pdf)
        row = QHBoxLayout()
        row.addWidget(self.pdf_edit)
        row.addWidget(pdf_btn)
        fl.addRow(row)
        lay.addWidget(file_box)

        # 高级选项（折叠）
        self.advanced = CollapsibleSection("高级选项")
        adv_form = QFormLayout(self.advanced.content)
        self.outdir_edit = QLineEdit(default_downloads_dir())
        out_btn = QPushButton("浏览…")
        out_btn.clicked.connect(self.browse_outdir)
        row2 = QHBoxLayout()
        row2.addWidget(self.outdir_edit)
        row2.addWidget(out_btn)
        adv_form.addRow("输出目录", row2)
        self.tender_check = QCheckBox("同时生成招标文件 Word（较慢，约数分钟）")
        adv_form.addRow(self.tender_check)
        lay.addWidget(self.advanced)

        # 大生成按钮
        self.gen_btn = QPushButton("生成投标文件")
        self.gen_btn.setObjectName("primary")
        self.gen_btn.clicked.connect(self.generate)
        lay.addWidget(self.gen_btn)

        # 顶部全局进度条 + 阶段文本
        self.stage_label = QLabel("就绪")
        self.stage_label.setStyleSheet("color:#4a5568;")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        lay.addWidget(self.stage_label)
        lay.addWidget(self.progress)

        # 内联成败条
        self.success_banner = Banner(ok=True)
        lay.addWidget(self.success_banner)
        self.error_banner = Banner(ok=False)
        lay.addWidget(self.error_banner)

        # 内嵌简要过程日志
        lay.addWidget(QLabel("过程日志"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        lay.addWidget(self.log, 1)

    # ------------------------------------------------------------------ #
    def _on_pdf_changed(self, text: str) -> None:
        self.empty_label.setVisible(not text.strip())

    def browse_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择招标文件 PDF", "", "PDF 文件 (*.pdf)")
        if path:
            self.pdf_edit.setText(path)

    def browse_outdir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", self.outdir_edit.text())
        if path:
            self.outdir_edit.setText(path)

    def generate(self) -> None:
        pdf = self.pdf_edit.text().strip()
        outdir = self.outdir_edit.text().strip() or default_downloads_dir()
        if not pdf or not os.path.exists(pdf):
            QMessageBox.warning(self, "提示", "请先选择存在的招标文件 PDF。")
            return
        os.makedirs(outdir, exist_ok=True)
        supplier_data = self.store.load(self.store.current())
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as handle:
            yaml.safe_dump(supplier_data, handle, allow_unicode=True)
            supplier_path = handle.name

        self.gen_btn.setEnabled(False)
        self.success_banner.hide_banner()
        self.error_banner.hide_banner()
        self.progress.setValue(0)
        self.stage_label.setText("开始生成…")
        self._emit_log(f"开始生成（供应商：{self.store.current()}）…")

        self._worker = Worker(pdf, outdir, supplier_path, self.tender_check.isChecked())
        self._worker.log.connect(self._emit_log)
        self._worker.progress.connect(self.on_progress)
        self._worker.done.connect(lambda ok, msg: self.on_done(ok, msg, outdir))
        self._worker.start()
        self._timer.start(50)

    def _emit_log(self, line: str) -> None:
        self.log.append(line)
        self.log_line.emit(line)

    def poll_worker(self) -> None:
        if self._worker is not None:
            self._worker.poll()
            if not self._worker.isRunning():
                self._timer.stop()

    def on_progress(self, value: int, maximum: int, label: str) -> None:
        self.progress.setMaximum(maximum)
        self.progress.setValue(value)
        self.stage_label.setText(label)

    def on_done(self, ok: bool, message: str, outdir: str) -> None:
        self._timer.stop()
        if self._worker is not None:
            self._worker.poll()
        self.gen_btn.setEnabled(True)
        if ok:
            self.stage_label.setText("完成 ✓")
            self.progress.setValue(self.progress.maximum())
            self._emit_log("全部完成 ✓")
            bid = message  # worker.emit 的是投标文件完整路径（含项目名）
            self.success_banner.show_success(
                "生成完成 ✓",
                [
                    ("打开输出目录", lambda: open_path(outdir)),
                    ("打开投标文件", lambda: open_path(bid)),
                ],
            )
        else:
            self.stage_label.setText("失败 ✗")
            self._emit_log("生成失败 ✗")
            self.error_banner.show_error(
                "生成失败",
                message,
                [
                    ("重试", self.generate),
                    ("导出日志", self.export_log),
                ],
            )

    def export_log(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出日志", "bidgen-log.txt", "文本文件 (*.txt)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.log.toPlainText())
