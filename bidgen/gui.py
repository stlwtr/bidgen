"""PySide6 图形界面：方便非技术人员使用 bidgen。

用法：`bidgen gui`（或 `python -m bidgen gui`）。
- 「生成」页：选择招标文件 PDF 与输出目录，点"生成投标文件"，转换过程有真实进度条。
- 「设置」菜单 →「供应商设置」：管理多个供应商配置（新建 / 编辑 / 删除 / 设为当前）。
- 「帮助」菜单 →「关于」：功能说明，科创研发室提供支持。

界面现代化（浅色卡片风）；后台线程生成，fd 级捕获 pdf2docx 页进度与 [bidgen] 阶段进度。
"""

from __future__ import annotations

import os
import queue
import re
import sys
import tempfile
import threading

import yaml
from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
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

_QSS = """
QMainWindow, QWidget {
    background: #f4f6fb;
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13.5px; color: #1f2733;
}
QLabel#title { font-size: 22px; font-weight: 800; color: #17202b; }
QLabel#subtitle { color: #6b7a90; margin-bottom: 4px; }
QGroupBox {
    background: #ffffff; border: 1px solid #e4e8f0; border-radius: 10px;
    margin-top: 14px; padding: 14px 12px 10px; font-weight: 600;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; top: 0px; color: #4a5568; }
QLineEdit, QComboBox {
    background: #f8fafc; border: 1px solid #d7dee9; border-radius: 6px; padding: 7px 9px;
    selection-background-color: #4a7dff;
}
QLineEdit:focus, QComboBox:focus { border: 1px solid #4a7dff; background: #ffffff; }
QPushButton {
    background: #eef1f7; border: 1px solid #d7dee9; border-radius: 6px;
    padding: 7px 14px; color: #2d3748;
}
QPushButton:hover { background: #e2e8f5; }
QPushButton#primary {
    background: #4a7dff; color: #ffffff; border: none;
    font-size: 15px; font-weight: 700; padding: 11px; border-radius: 8px;
}
QPushButton#primary:hover { background: #3b6fe0; }
QPushButton#primary:disabled { background: #a9bcd8; }
QProgressBar {
    border: 1px solid #d7dee9; border-radius: 6px; background: #eef1f7;
    height: 16px; text-align: center; color: #2d3748;
}
QProgressBar::chunk { background: #4a7dff; border-radius: 5px; }
QTextEdit, QListWidget { background: #ffffff; border: 1px solid #e4e8f0; border-radius: 8px; padding: 6px; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: transparent; padding: 8px 20px; border-radius: 6px; color: #4a5568; }
QTabBar::tab:selected { background: #4a7dff; color: #ffffff; }
QCheckBox { color: #2d3748; }
QMenuBar { background: #ffffff; border-bottom: 1px solid #e4e8f0; }
QMenu { background: #ffffff; border: 1px solid #e4e8f0; }
QMenu::item:selected { background: #4a7dff; color: #ffffff; }
"""


# --------------------------------------------------------------------------- #
# 供应商配置存储（多档案，可选中当前使用的）
# --------------------------------------------------------------------------- #
class SupplierStore:
    """把多个供应商配置存为 suppliers/<名称>.yaml，并记录当前使用的档案。"""

    _CURRENT_FILE = ".current"

    def __init__(self, root: str = "suppliers") -> None:
        self.root = root
        os.makedirs(self.root, exist_ok=True)
        if not self.list():
            self.save("默认供应商", {"company_type": "企业"})

    def _path(self, name: str) -> str:
        return os.path.join(self.root, name + ".yaml")

    def list(self) -> list[str]:
        names = [os.path.splitext(f)[0] for f in os.listdir(self.root) if f.endswith(".yaml")]
        return sorted(names)

    def load(self, name: str) -> dict:
        try:
            with open(self._path(name), encoding="utf-8") as handle:
                return yaml.safe_load(handle) or {}
        except FileNotFoundError:
            return {}

    def save(self, name: str, data: dict) -> None:
        with open(self._path(name), "w", encoding="utf-8") as handle:
            yaml.safe_dump(data, handle, allow_unicode=True)

    def delete(self, name: str) -> None:
        try:
            os.remove(self._path(name))
        except FileNotFoundError:
            pass

    def current(self) -> str:
        try:
            with open(os.path.join(self.root, self._CURRENT_FILE), encoding="utf-8") as handle:
                name = handle.read().strip()
                if name and os.path.exists(self._path(name)):
                    return name
        except FileNotFoundError:
            pass
        names = self.list()
        return names[0] if names else "默认供应商"

    def set_current(self, name: str) -> None:
        with open(os.path.join(self.root, self._CURRENT_FILE), "w", encoding="utf-8") as handle:
            handle.write(name)


# --------------------------------------------------------------------------- #
# 后台生成线程（fd 级捕获进度）
# --------------------------------------------------------------------------- #
class _QueueWriter:
    def __init__(self, q: "queue.Queue[str]") -> None:
        self.q = q
        self._buf = ""

    def write(self, data: str) -> int:
        self._buf += data
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line.strip():
                self.q.put(line)
        return len(data)

    def flush(self) -> None:
        pass


class Worker(QThread):
    log = Signal(str)
    progress = Signal(int, int, str)
    done = Signal(bool, str)

    def __init__(self, pdf: str, outdir: str, supplier_path: str, with_tender: bool):
        super().__init__()
        self.pdf = pdf
        self.outdir = outdir
        self.supplier_path = supplier_path
        self.with_tender = with_tender
        self.q: "queue.Queue[str]" = queue.Queue()

    def run(self) -> None:
        read_fd, write_fd = os.pipe()
        old_out, old_err = os.dup(1), os.dup(2)
        os.dup2(write_fd, 1)
        os.dup2(write_fd, 2)
        pump = threading.Thread(target=self._pump, args=(read_fd,), daemon=True)
        pump.start()
        try:
            if self.with_tender:
                self.log.emit("【1/2】转换招标文件为 Word…")
                tender = os.path.join(self.outdir, "招标文件.docx")
                cli._convert(self.pdf, tender, True)
                self.log.emit("已生成：" + tender)
            self.log.emit("【2/2】生成投标文件…")
            bid = os.path.join(self.outdir, "投标文件.docx")
            cli._generate(self.pdf, bid, self.supplier_path, True)
            self.log.emit("已生成：" + bid)
            self.done.emit(True, self.outdir)
        except Exception as exc:  # noqa: BLE001 - surface a readable message in the GUI
            self.q.put("错误：" + str(exc))
            self.done.emit(False, str(exc))
        finally:
            os.dup2(old_out, 1)
            os.dup2(old_err, 2)
            os.close(old_out)
            os.close(old_err)
            os.close(write_fd)

    def _pump(self, read_fd: int) -> None:
        with os.fdopen(read_fd, "r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                line = raw.rstrip()
                if line:
                    self.q.put(line)

    def poll(self) -> None:
        try:
            while True:
                self._handle(self.q.get_nowait())
        except queue.Empty:
            pass

    _STAGE_RE = re.compile(r"\[bidgen\]\s*(\d+)/(\d+)\s*(.*)")
    _PAGE_RE = re.compile(r"\((\d+)/(\d+)\)\s*Page\s*(\d+)")

    def _handle(self, line: str) -> None:
        m = self._STAGE_RE.search(line)
        if m:
            n, total, stage = int(m.group(1)), int(m.group(2)), m.group(3).strip()
            self.progress.emit(n, total, f"生成投标文件：{stage}（{n}/{total}）")
            return
        m = self._PAGE_RE.search(line)
        if m:
            n, total = int(m.group(1)), int(m.group(2))
            self.progress.emit(n, total, f"转换招标文件：{n}/{total} 页")
            return
        self.log.emit(line)


# --------------------------------------------------------------------------- #
# 供应商设置对话框（多档案管理）
# --------------------------------------------------------------------------- #
class SupplierEditDialog(QDialog):
    """编辑单个供应商档案。"""

    def __init__(self, store: SupplierStore, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑供应商：" + name)
        self._fields: dict[str, QLineEdit] = {}
        lay = QVBoxLayout(self)
        form = QFormLayout()
        data = store.load(name)
        for key, label in _SUPPLIER_FIELDS:
            edit = QLineEdit(str(data.get(key, "")))
            self._fields[key] = edit
            form.addRow(label, edit)
        self.type_combo = QComboBox()
        self.type_combo.addItems(_COMPANY_TYPES)
        self.type_combo.setCurrentText(data.get("company_type", "企业"))
        form.addRow("供应商类型", self.type_combo)
        lay.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def data(self) -> dict:
        data = {k: e.text().strip() for k, e in self._fields.items()}
        data["company_type"] = self.type_combo.currentText()
        return {k: v for k, v in data.items() if v}


class SupplierManagerDialog(QDialog):
    """供应商设置：管理多个供应商配置（新建 / 编辑 / 删除 / 设为当前）。"""

    def __init__(self, store: SupplierStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("供应商设置")
        self.resize(460, 500)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("供应商配置（双击编辑；「设为当前」用于生成投标文件）"))
        self.listw = QListWidget()
        self.listw.itemDoubleClicked.connect(self.edit_item)
        lay.addWidget(self.listw, 1)

        btns = QHBoxLayout()
        for text, fn in [
            ("新建", self.add),
            ("编辑", self.edit_selected),
            ("删除", self.delete_selected),
            ("设为当前", self.set_current),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(fn)
            btns.addWidget(btn)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)
        lay.addLayout(btns)

        self.refresh()

    def refresh(self) -> None:
        current = self.store.current()
        self.listw.clear()
        for name in self.store.list():
            item = QListWidgetItem(("✓ " if name == current else "   ") + name)
            if name == current:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.listw.addItem(item)

    def _selected_name(self) -> str | None:
        item = self.listw.currentItem()
        return item.text().lstrip("✓ ").strip() if item else None

    def add(self) -> None:
        name, ok = QInputDialog.getText(self, "新建供应商", "供应商名称：")
        name = name.strip()
        if ok and name:
            self.store.save(name, {"company_name": name, "company_type": "企业"})
            self.refresh()
            self._edit(name)

    def edit_selected(self) -> None:
        name = self._selected_name()
        if name:
            self._edit(name)

    def edit_item(self, item: QListWidgetItem) -> None:
        self._edit(item.text().lstrip("✓ ").strip())

    def _edit(self, name: str) -> None:
        dlg = SupplierEditDialog(self.store, name, self)
        if dlg.exec():
            self.store.save(name, dlg.data())
            self.refresh()

    def delete_selected(self) -> None:
        name = self._selected_name()
        if name and QMessageBox.question(self, "删除", f"删除供应商「{name}」？") == QMessageBox.Yes:
            self.store.delete(name)
            self.refresh()

    def set_current(self) -> None:
        name = self._selected_name()
        if name:
            self.store.set_current(name)
            self.refresh()


# --------------------------------------------------------------------------- #
# 主窗口
# --------------------------------------------------------------------------- #
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("投标文件生成助手")
        self.resize(680, 800)
        self.setStyleSheet(_QSS)
        self._worker: Worker | None = None
        self.store = SupplierStore()
        self._loading_supplier = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.poll_worker)

        self._build_menus()

        root = QWidget()
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(8)

        title = QLabel("投标文件生成助手")
        title.setObjectName("title")
        subtitle = QLabel("招标文件 PDF → 投标文件 Word，一键生成")
        subtitle.setObjectName("subtitle")
        lay.addWidget(title)
        lay.addWidget(subtitle)

        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)
        self.tabs.addTab(self._build_generate_tab(), "生成")
        self.tabs.addTab(self._build_settings_tab(), "设置")

        self._reload_current_supplier()

    # ------------------------------------------------------------------ #
    # 菜单
    # ------------------------------------------------------------------ #
    def _build_menus(self) -> None:
        settings_menu = self.menuBar().addMenu("设置")
        settings_menu.addAction("供应商设置…", self.open_supplier_manager)
        help_menu = self.menuBar().addMenu("帮助")
        help_menu.addAction("关于 投标文件生成助手…", self.show_about)

    def open_supplier_manager(self) -> None:
        dlg = SupplierManagerDialog(self.store, self)
        dlg.exec()
        self._reload_current_supplier()

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "关于 投标文件生成助手",
            "<h3>投标文件生成助手</h3>"
            "<p>将政府采购招标文件 PDF 自动转换为结构规范、内容预填的投标文件 Word 初稿：</p>"
            "<ul>"
            "<li>招标文件 PDF 转 Word（乱码修复）</li>"
            "<li>提取投标文件格式，重建 16 章骨架（自动编号、页眉页脚、目录域）</li>"
            "<li>承诺函按通用规则填充采购人 / 代理机构 / 项目 / 编号 / 投标人</li>"
            "<li>商务与技术表格按位置渲染，技术偏离表从招标文件模板提取</li>"
            "<li>生成后清理文档机器码与用户信息</li>"
            "</ul>"
            "<p>科创研发室提供支持。</p>",
        )

    # ------------------------------------------------------------------ #
    # 「生成」页
    # ------------------------------------------------------------------ #
    def _build_generate_tab(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(10)

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

        self.tender_check = QCheckBox("同时生成招标文件 Word（较慢，约数分钟）")
        fl.addRow(self.tender_check)
        lay.addWidget(file_box)

        self.gen_btn = QPushButton("生成投标文件")
        self.gen_btn.setObjectName("primary")
        self.gen_btn.clicked.connect(self.generate)
        lay.addWidget(self.gen_btn)

        self.stage_label = QLabel("就绪")
        self.stage_label.setStyleSheet("color:#4a5568;")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        lay.addWidget(self.stage_label)
        lay.addWidget(self.progress)

        lay.addWidget(QLabel("过程日志"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        lay.addWidget(self.log, 1)
        return page

    # ------------------------------------------------------------------ #
    # 「设置」页（当前供应商表单，自动保存到当前档案）
    # ------------------------------------------------------------------ #
    def _build_settings_tab(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)

        top_row = QHBoxLayout()
        self.supplier_label = QLabel()
        manage_btn = QPushButton("管理供应商…")
        manage_btn.clicked.connect(self.open_supplier_manager)
        top_row.addWidget(self.supplier_label)
        top_row.addStretch(1)
        top_row.addWidget(manage_btn)
        lay.addLayout(top_row)

        self.sup_box = QGroupBox("供应商信息（未填写的字段在 Word 中以占位下划线显示；编辑即自动保存）")
        form = QFormLayout(self.sup_box)
        self.fields: dict[str, QLineEdit] = {}
        for key, label in _SUPPLIER_FIELDS:
            edit = QLineEdit()
            edit.textChanged.connect(self._save_current_supplier)
            self.fields[key] = edit
            form.addRow(label, edit)
        self.type_combo = QComboBox()
        self.type_combo.addItems(_COMPANY_TYPES)
        self.type_combo.currentTextChanged.connect(self._save_current_supplier)
        form.addRow("供应商类型", self.type_combo)
        lay.addWidget(self.sup_box)
        lay.addStretch(1)
        return page

    def _reload_current_supplier(self) -> None:
        current = self.store.current()
        data = self.store.load(current)
        self.supplier_label.setText(f"当前供应商：<b>{current}</b>")
        self._loading_supplier = True
        for key, edit in self.fields.items():
            edit.setText(str(data.get(key, "")))
        self.type_combo.setCurrentText(data.get("company_type", "企业"))
        self._loading_supplier = False

    def _save_current_supplier(self) -> None:
        if self._loading_supplier:
            return
        data = {k: e.text().strip() for k, e in self.fields.items()}
        data["company_type"] = self.type_combo.currentText()
        self.store.save(self.store.current(), {k: v for k, v in data.items() if v})

    # ------------------------------------------------------------------ #
    # 交互
    # ------------------------------------------------------------------ #
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
        outdir = self.outdir_edit.text().strip() or "out"
        if not pdf or not os.path.exists(pdf):
            QMessageBox.warning(self, "提示", "请先选择存在的招标文件 PDF。")
            return
        os.makedirs(outdir, exist_ok=True)
        supplier_data = self.store.load(self.store.current())
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as handle:
            yaml.safe_dump(supplier_data, handle, allow_unicode=True)
            supplier_path = handle.name

        self.gen_btn.setEnabled(False)
        self.progress.setValue(0)
        self.stage_label.setText("开始生成…")
        self.log.append(f"开始生成（供应商：{self.store.current()}）…")

        self._worker = Worker(pdf, outdir, supplier_path, self.tender_check.isChecked())
        self._worker.log.connect(self.log.append)
        self._worker.progress.connect(self.on_progress)
        self._worker.done.connect(self.on_done)
        self._worker.start()
        self._timer.start(50)

    def poll_worker(self) -> None:
        if self._worker is not None:
            self._worker.poll()
            if not self._worker.isRunning():
                self._timer.stop()

    def on_progress(self, value: int, maximum: int, label: str) -> None:
        self.progress.setMaximum(maximum)
        self.progress.setValue(value)
        self.stage_label.setText(label)

    def on_done(self, ok: bool, message: str) -> None:
        self._timer.stop()
        if self._worker is not None:
            self._worker.poll()
        self.gen_btn.setEnabled(True)
        if ok:
            self.stage_label.setText("完成 ✓")
            self.progress.setValue(self.progress.maximum())
            self.log.append("全部完成 ✓")
            QMessageBox.information(self, "完成", "生成完成，输出目录：" + message)
        else:
            self.stage_label.setText("失败 ✗")
            self.log.append("生成失败 ✗")
            QMessageBox.critical(self, "失败", "生成失败：" + message)


def run_gui() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("投标文件生成助手")
    window = MainWindow()
    window.show()
    return app.exec()
