"""供应商页：左侧档案列表 + 右侧表单（选中即编辑、自动保存）。"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from ..store import SupplierStore
from ..widgets import COMPANY_TYPES, SUPPLIER_FIELDS


class SuppliersPage(QWidget):
    def __init__(self, store: SupplierStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self._loading = False

        lay = QHBoxLayout(self)
        lay.setSpacing(12)

        # 左：档案列表 + 操作
        left = QVBoxLayout()
        left.addWidget(QLabel("供应商档案（✓ = 当前用于生成）"))
        self.listw = QListWidget()
        self.listw.currentItemChanged.connect(self._on_select)
        left.addWidget(self.listw, 1)
        btns = QHBoxLayout()
        for text, fn in [("新建", self.add), ("删除", self.delete_selected), ("设为当前", self.set_current)]:
            btn = QPushButton(text)
            btn.clicked.connect(fn)
            btns.addWidget(btn)
        left.addLayout(btns)
        lay.addLayout(left, 2)

        # 右：表单（选中即编辑、自动保存）
        right_box = QGroupBox("供应商信息（编辑即自动保存）")
        form = QFormLayout(right_box)
        self.fields: dict[str, QLineEdit] = {}
        for key, label in SUPPLIER_FIELDS:
            edit = QLineEdit()
            edit.textChanged.connect(self._save_current)
            self.fields[key] = edit
            form.addRow(label, edit)
        self.type_combo = QComboBox()
        self.type_combo.addItems(COMPANY_TYPES)
        self.type_combo.currentTextChanged.connect(self._save_current)
        form.addRow("供应商类型", self.type_combo)
        lay.addWidget(right_box, 3)

        self.refresh()

    # ------------------------------------------------------------------ #
    def refresh(self) -> None:
        current = self.store.current()
        self.listw.blockSignals(True)
        self.listw.clear()
        for name in self.store.list():
            item = QListWidgetItem(("✓ " if name == current else "   ") + name)
            item.setData(1, name)  # 纯名称存 role，避免 ✓ 前缀干扰
            if name == current:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.listw.addItem(item)
        self.listw.blockSignals(False)
        for i in range(self.listw.count()):
            if self.listw.item(i).data(1) == current:
                self.listw.setCurrentRow(i)
                break
        self._fill(current)

    def _fill(self, name: str) -> None:
        data = self.store.load(name)
        self._loading = True
        for key, edit in self.fields.items():
            edit.setText(str(data.get(key, "")))
        self.type_combo.setCurrentText(data.get("company_type", "企业"))
        self._loading = False

    def _on_select(self, current_item, _prev) -> None:
        if current_item is not None:
            self._fill(current_item.data(1))

    def _save_current(self) -> None:
        if self._loading:
            return
        item = self.listw.currentItem()
        if item is None:
            return
        name = item.data(1)
        data = {k: e.text().strip() for k, e in self.fields.items()}
        data["company_type"] = self.type_combo.currentText()
        self.store.save(name, {k: v for k, v in data.items() if v})

    def add(self) -> None:
        name, ok = QInputDialog.getText(self, "新建供应商", "供应商名称：")
        name = name.strip()
        if ok and name:
            self.store.save(name, {"company_name": name, "company_type": "企业"})
            self.refresh()
            for i in range(self.listw.count()):
                if self.listw.item(i).data(1) == name:
                    self.listw.setCurrentRow(i)
                    break

    def delete_selected(self) -> None:
        item = self.listw.currentItem()
        if item is None:
            return
        name = item.data(1)
        if QMessageBox.question(self, "删除", f"删除供应商「{name}」？") == QMessageBox.Yes:
            self.store.delete(name)
            self.refresh()

    def set_current(self) -> None:
        item = self.listw.currentItem()
        if item is not None:
            self.store.set_current(item.data(1))
            self.refresh()
