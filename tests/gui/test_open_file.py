"""外部打开 PDF：QFileOpenEvent 预填并切页、非 PDF Banner 提示、argv 解析。"""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QFileOpenEvent

from bidgen.gui.app import MainWindow
from bidgen.gui.opener import pick_pdf
from bidgen.gui.store import SupplierStore


def _window(tmp_path, monkeypatch) -> MainWindow:
    """构造 MainWindow，供应商档案隔离到 tmp_path（不读写项目根 suppliers/）。"""
    monkeypatch.setattr(
        "bidgen.gui.app.SupplierStore",
        lambda: SupplierStore(root=str(tmp_path / "suppliers")),
    )
    win = MainWindow()
    win.show()  # offscreen 下建立可见性链，Banner 的 isVisible 才能反映显隐
    return win


def test_pick_pdf_returns_first_existing_pdf(tmp_path):
    real = tmp_path / "招标文件.pdf"
    real.write_bytes(b"%PDF-1.4")
    assert pick_pdf(["/no/such.txt", str(real), str(tmp_path / "other.pdf")]) == str(real)


def test_pick_pdf_ignores_missing_and_non_pdf(tmp_path):
    docx = tmp_path / "a.docx"
    docx.write_text("x", encoding="utf-8")
    assert pick_pdf([str(docx), str(tmp_path / "missing.pdf")]) is None


def test_open_pdf_prefills_and_switches(qapp, tmp_path, monkeypatch):
    pdf = tmp_path / "招标文件.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    win = _window(tmp_path, monkeypatch)
    win.nav.setCurrentRow(1)  # 先离开生成页
    win.open_pdf(str(pdf))
    assert win.generate_page.pdf_edit.text() == str(pdf)
    assert win.pages.currentIndex() == 0
    assert not win.generate_page.error_banner.isVisible()


def test_open_pdf_non_pdf_shows_banner(qapp, tmp_path, monkeypatch):
    win = _window(tmp_path, monkeypatch)
    win.open_pdf("/tmp/说明.docx")
    assert win.generate_page.error_banner.isVisible()
    assert win.generate_page.pdf_edit.text() == ""


def test_file_open_event_dispatches_to_window(qapp, tmp_path, monkeypatch):
    """macOS 拖放到 Dock/图标：QFileOpenEvent 经 BidgenApplication 转发为 pdf_opened。"""
    pdf = tmp_path / "招标文件.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    win = _window(tmp_path, monkeypatch)
    qapp.pdf_opened.connect(win.open_pdf)
    qapp.sendEvent(qapp, QFileOpenEvent(QUrl.fromLocalFile(str(pdf))))
    assert win.generate_page.pdf_edit.text() == str(pdf)
    assert win.pages.currentIndex() == 0


# --------------------------------------------------------------------- #
# 主窗口拖放（PDF 拖到窗口任意位置打开）
# --------------------------------------------------------------------- #
from PySide6.QtCore import QMimeData, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent  # noqa: E402


def _mime(*paths) -> QMimeData:
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    return mime


def _drag_enter(win, mime) -> QDragEnterEvent:
    evt = QDragEnterEvent(QPointF(10, 10), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    win.dragEnterEvent(evt)
    return evt


def _drop(win, mime) -> None:
    win.dropEvent(QDropEvent(QPointF(10, 10), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier))


def test_drag_enter_with_pdf_shows_overlay(qapp, tmp_path, monkeypatch):
    pdf = tmp_path / "招标文件.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    win = _window(tmp_path, monkeypatch)
    evt = _drag_enter(win, _mime(pdf))
    assert evt.isAccepted()
    assert win._drop_overlay.isVisible()


def test_drag_enter_non_pdf_accepted_but_no_overlay(qapp, tmp_path, monkeypatch):
    docx = tmp_path / "说明.docx"
    docx.write_text("x", encoding="utf-8")
    win = _window(tmp_path, monkeypatch)
    evt = _drag_enter(win, _mime(docx))
    assert evt.isAccepted()  # 接受以便 drop 阶段给出 Banner 反馈
    assert not win._drop_overlay.isVisible()  # 但无遮罩预告


def test_drag_leave_hides_overlay(qapp, tmp_path, monkeypatch):
    pdf = tmp_path / "招标文件.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    win = _window(tmp_path, monkeypatch)
    _drag_enter(win, _mime(pdf))
    win.dragLeaveEvent(QDragLeaveEvent())
    assert not win._drop_overlay.isVisible()


def test_drop_pdf_prefills_switches_and_hides_overlay(qapp, tmp_path, monkeypatch):
    pdf = tmp_path / "招标文件.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    win = _window(tmp_path, monkeypatch)
    win.nav.setCurrentRow(2)  # 离开生成页
    _drag_enter(win, _mime(pdf))
    _drop(win, _mime(pdf))
    assert win.generate_page.pdf_edit.text() == str(pdf)
    assert win.pages.currentIndex() == 0
    assert not win._drop_overlay.isVisible()
    assert not win.generate_page.error_banner.isVisible()


def test_drop_multi_files_takes_first_pdf(qapp, tmp_path, monkeypatch):
    docx = tmp_path / "说明.docx"
    docx.write_text("x", encoding="utf-8")
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    win = _window(tmp_path, monkeypatch)
    _drop(win, _mime(docx, pdf))
    assert win.generate_page.pdf_edit.text() == str(pdf)


def test_drop_non_pdf_shows_banner_and_keeps_state(qapp, tmp_path, monkeypatch):
    docx = tmp_path / "说明.docx"
    docx.write_text("x", encoding="utf-8")
    win = _window(tmp_path, monkeypatch)
    win.generate_page.pdf_edit.setText("/既有/老文件.pdf")
    _drop(win, _mime(docx))
    assert win.generate_page.error_banner.isVisible()
    assert win.generate_page.pdf_edit.text() == "/既有/老文件.pdf"  # 已选文件不受影响
