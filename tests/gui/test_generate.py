"""生成流程交互测试（mock 生成，避免真实耗时）。"""

import os
import time

import pytest

from bidgen.gui.pages.generate import GeneratePage
from bidgen.gui.store import SupplierStore


@pytest.fixture
def store(tmp_path):
    return SupplierStore(root=str(tmp_path / "suppliers"))


def test_generate_requires_pdf(store, qapp, monkeypatch):
    page = GeneratePage(store)
    called = []
    monkeypatch.setattr(
        "bidgen.gui.pages.generate.QMessageBox.warning",
        lambda *a, **k: called.append(True),
    )
    page.generate()
    assert called, "未选 PDF 时应弹警告"
    assert page._worker is None


def test_generate_success_flow(store, qapp, tmp_path, monkeypatch):
    pdf = os.path.abspath("docs/招标文件1.pdf")
    if not os.path.exists(pdf):
        pytest.skip("tender PDF not present under docs/")
    page = GeneratePage(store)
    page.show()  # 需 show 父窗口，success_banner isVisible() 才为 True
    page.pdf_edit.setText(pdf)
    page.outdir_edit.setText(str(tmp_path / "out"))
    page.tender_check.setChecked(False)

    created = {}

    def fake_generate(pdf_path, out, supplier, do_sanitize):
        created["out"] = out
        with open(out, "w", encoding="utf-8") as handle:
            handle.write("docx")
        return out

    monkeypatch.setattr("bidgen.cli._generate", fake_generate)

    page.generate()
    if page._worker is not None:
        page._worker.wait(10000)  # 阻塞等后台线程结束
    # worker 的 done 是 queued 到主线程，需 processEvents 才触发 on_done
    for _ in range(50):
        page.poll_worker()
        qapp.processEvents()
        time.sleep(0.02)

    assert "out" in created, "generate 应调用 cli._generate 产出文件"
    assert os.path.exists(created["out"])
    # 成功条显示
    assert page.success_banner.isVisible()
