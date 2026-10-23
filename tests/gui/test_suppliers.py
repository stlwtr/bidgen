"""供应商档案 CRUD 与供应商页交互测试。"""

import pytest

from bidgen.gui.pages.suppliers import SuppliersPage
from bidgen.gui.store import SupplierStore


@pytest.fixture
def store(tmp_path):
    return SupplierStore(root=str(tmp_path / "suppliers"))


def test_store_crud(store):
    assert store.list() == ["默认供应商"]
    store.save("供应商A", {"company_name": "供应商A", "company_type": "企业"})
    assert "供应商A" in store.list()
    store.set_current("供应商A")
    assert store.current() == "供应商A"
    assert store.load("供应商A")["company_name"] == "供应商A"
    store.delete("供应商A")
    assert "供应商A" not in store.list()
    # 删除当前后回落到第一个
    assert store.current() == "默认供应商"


def test_suppliers_page_select_and_autosave(store, qapp):
    page = SuppliersPage(store)
    page.show()
    store.save("供应商B", {"company_name": "供应商B", "company_type": "企业"})
    page.refresh()
    for i in range(page.listw.count()):
        if page.listw.item(i).data(1) == "供应商B":
            page.listw.setCurrentRow(i)
            break
    # 编辑字段 → 自动保存
    page.fields["phone"].setText("13800000000")
    data = store.load("供应商B")
    assert data["phone"] == "13800000000"
    # 设为当前 → 列表 ✓ 标记
    page.set_current()
    assert store.current() == "供应商B"
    items = [page.listw.item(i).text() for i in range(page.listw.count())]
    assert any(t.startswith("✓ ") and "供应商B" in t for t in items)
