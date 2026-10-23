"""供应商页：左侧档案列表 + 右侧表单（选中即编辑、自动保存）。"""

from __future__ import annotations

import re

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QFormLayout, QGroupBox, QHBoxLayout, QInputDialog,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from ..store import SupplierStore
from ..widgets import COMPANY_TYPES, SUPPLIER_FIELDS

_DATE_PLACEHOLDER = QDate(1900, 1, 1)  # 表示"留空（以占位显示）"的最小日期


def _parse_cn_date(text: str) -> QDate | None:
    """解析 '2026年8月25日' / '2026年08月25日' 为 QDate；失败返回 None。"""
    m = re.match(r"^\s*(\d{4})年(\d{1,2})月(\d{1,2})日\s*$", text or "")
    if m:
        return QDate(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


class SuppliersPage(QWidget):
    def __init__(self, store: SupplierStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self._loading = False

        lay = QHBoxLayout(self)
        lay.setSpacing(12)

        # 左：档案列表 + 操作（QGroupBox，与右侧"供应商信息"上边缘对齐）
        left_box = QGroupBox("供应商档案（✓ = 当前用于生成）")
        left_lay = QVBoxLayout(left_box)
        self.listw = QListWidget()
        self.listw.currentItemChanged.connect(self._on_select)
        left_lay.addWidget(self.listw, 1)
        btns = QHBoxLayout()
        for text, fn in [("新建", self.add), ("删除", self.delete_selected), ("设为当前", self.set_current)]:
            btn = QPushButton(text)
            btn.clicked.connect(fn)
            btns.addWidget(btn)
        left_lay.addLayout(btns)
        lay.addWidget(left_box, 2)

        # 右：表单（选中即编辑、自动保存）
        right_box = QGroupBox("供应商信息（编辑即自动保存）")
        form = QFormLayout(right_box)
        self.fields: dict[str, QLineEdit | QDateEdit] = {}
        for key, label in SUPPLIER_FIELDS:
            if key == "date":
                edit = QDateEdit()
                edit.setDisplayFormat("yyyy年MM月dd日")
                edit.setCalendarPopup(True)
                edit.setMinimumDate(_DATE_PLACEHOLDER)
                edit.setSpecialValueText("留空（以占位显示）")
                edit.setDate(_DATE_PLACEHOLDER)
                edit.dateChanged.connect(self._save_current)
            else:
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
            if key == "date":
                parsed = _parse_cn_date(str(data.get(key, "")))
                edit.setDate(parsed if parsed is not None else _DATE_PLACEHOLDER)
            else:
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
        data: dict[str, str] = {}
        for key, edit in self.fields.items():
            if key == "date":
                d = edit.date()
                data[key] = "" if d == edit.minimumDate() else d.toString("yyyy年MM月dd日")
            else:
                data[key] = edit.text().strip()
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
