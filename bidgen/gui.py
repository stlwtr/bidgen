"""PySide6 图形界面：方便非技术人员使用 bidgen。

用法：`bidgen gui`（或 `python -m bidgen gui`）。选择招标文件 PDF、填写供应商
信息、点"生成"，即可在输出目录得到 投标文件.docx（可选同时生成 招标文件.docx）。
"""

from __future__ import annotations

import os
import sys
import tempfile

import yaml
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QTextEdit, QVBoxLayout, QWidget,
)

from . import cli

_SUPPLIER_FIELDS = [
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
    ("date", "日期（如 2026年08月25日，留空以占位显示）"),
]

_COMPANY_TYPES = ["企业", "事业单位", "社会团体", "非企业专业服务机构", "个体工商户", "自然人"]


class Worker(QThread):
    """后台生成线程，避免界面冻结。"""

    log = Signal(str)
    done = Signal(bool, str)

    def __init__(self, pdf: str, outdir: str, supplier_path: str, with_tender: bool):
        super().__init__()
        self.pdf = pdf
        self.outdir = outdir
        self.supplier_path = supplier_path
        self.with_tender = with_tender

    def run(self) -> None:
        try:
            if self.with_tender:
                self.log.emit("正在转换招标文件为 Word（约数分钟）…")
                tender = os.path.join(self.outdir, "招标文件.docx")
                cli._convert(self.pdf, tender, True)
                self.log.emit("已生成：" + tender)
            self.log.emit("正在生成投标文件…")
            bid = os.path.join(self.outdir, "投标文件.docx")
            cli._generate(self.pdf, bid, self.supplier_path, True)
            self.log.emit("已生成：" + bid)
            self.done.emit(True, self.outdir)
        except Exception as exc:  # noqa: BLE001 - surface a readable message in the GUI
            self.log.emit("错误：" + str(exc))
            self.done.emit(False, str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("投标文件生成助手")
        self.resize(660, 780)
        self._worker: Worker | None = None

        root = QWidget()
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)

        # 招标文件与输出
        file_box = QGroupBox("招标文件与输出")
        fl = QFormLayout(file_box)
        self.pdf_edit = QLineEdit()
        self.pdf_edit.setReadOnly(True)
        self.pdf_edit.setPlaceholderText("选择招标文件 PDF…")
        pdf_btn = QPushButton("浏览…")
        pdf_btn.clicked.connect(self.browse_pdf)
        row = QHBoxLayout()
        row.addWidget(self.pdf_edit)
        row.addWidget(pdf_btn)
        fl.addRow("招标文件 PDF", row)
        self.outdir_edit = QLineEdit(os.path.abspath("out"))
        out_btn = QPushButton("浏览…")
        out_btn.clicked.connect(self.browse_outdir)
        row2 = QHBoxLayout()
        row2.addWidget(self.outdir_edit)
        row2.addWidget(out_btn)
        fl.addRow("输出目录", row2)
        lay.addWidget(file_box)

        # 供应商信息
        sup_box = QGroupBox("供应商信息（未填写的字段在 Word 中以占位下划线显示）")
        form = QFormLayout(sup_box)
        self.fields: dict[str, QLineEdit] = {}
        for key, label in _SUPPLIER_FIELDS:
            edit = QLineEdit()
            self.fields[key] = edit
            form.addRow(label, edit)
        self.type_combo = QComboBox()
        self.type_combo.addItems(_COMPANY_TYPES)
        form.addRow("供应商类型", self.type_combo)
        load_btn = QPushButton("从 supplier.yaml 加载…")
        load_btn.clicked.connect(self.load_yaml)
        form.addRow(load_btn)
        lay.addWidget(sup_box)

        # 选项与生成
        self.tender_check = QCheckBox("同时生成招标文件 Word（较慢，约数分钟）")
        lay.addWidget(self.tender_check)
        self.gen_btn = QPushButton("生成投标文件")
        self.gen_btn.setStyleSheet("font-size:16px; padding:10px;")
        self.gen_btn.clicked.connect(self.generate)
        lay.addWidget(self.gen_btn)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        lay.addWidget(self.progress)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        lay.addWidget(self.log)

    def browse_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择招标文件 PDF", "", "PDF 文件 (*.pdf)")
        if path:
            self.pdf_edit.setText(path)

    def browse_outdir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", self.outdir_edit.text())
        if path:
            self.outdir_edit.setText(path)

    def load_yaml(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "加载供应商配置", "examples", "YAML 文件 (*.yaml *.yml)")
        if not path:
            return
        with open(path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        for key, edit in self.fields.items():
            value = data.get(key)
            if value not in (None, ""):
                edit.setText(str(value))
        if data.get("company_type") in _COMPANY_TYPES:
            self.type_combo.setCurrentText(data["company_type"])
        self.log.append("已加载配置：" + path)

    def _supplier_dict(self) -> dict:
        data = {k: e.text().strip() for k, e in self.fields.items()}
        data["company_type"] = self.type_combo.currentText()
        return {k: v for k, v in data.items() if v}

    def generate(self) -> None:
        pdf = self.pdf_edit.text().strip()
        outdir = self.outdir_edit.text().strip() or "out"
        if not pdf or not os.path.exists(pdf):
            QMessageBox.warning(self, "提示", "请先选择存在的招标文件 PDF。")
            return
        os.makedirs(outdir, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as handle:
            yaml.safe_dump(self._supplier_dict(), handle, allow_unicode=True)
            supplier_path = handle.name

        self.gen_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.log.append("开始生成…")
        self._worker = Worker(pdf, outdir, supplier_path, self.tender_check.isChecked())
        self._worker.log.connect(self.log.append)
        self._worker.done.connect(self.on_done)
        self._worker.start()

    def on_done(self, ok: bool, message: str) -> None:
        self.gen_btn.setEnabled(True)
        self.progress.setVisible(False)
        if ok:
            self.log.append("全部完成 ✓")
            QMessageBox.information(self, "完成", "生成完成，输出目录：" + message)
        else:
            self.log.append("生成失败 ✗")
            QMessageBox.critical(self, "失败", "生成失败：" + message)


def run_gui() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("投标文件生成助手")
    window = MainWindow()
    window.show()
    return app.exec()
