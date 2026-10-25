"""paths.suppliers_dir：打包后必须落用户目录（双击启动 cwd 为只读根目录的回归）。"""

from __future__ import annotations

import sys

from bidgen.gui import paths


def test_dev_mode_uses_project_relative_suppliers(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert paths.suppliers_dir() == "suppliers"


def test_frozen_mode_uses_user_data_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths, "_user_data_dir", lambda: str(tmp_path))
    root = paths.suppliers_dir()
    assert root.startswith(str(tmp_path))
    assert root.endswith("suppliers")
