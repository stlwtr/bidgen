"""GUI 测试公共夹具：offscreen 平台（向导不再自动弹出，无需再跳过）。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from bidgen.gui.opener import BidgenApplication


@pytest.fixture(scope="session")
def qapp():
    # 用应用真实的 QApplication 子类，覆盖 QFileOpenEvent（拖放打开）分发逻辑
    app = QApplication.instance() or BidgenApplication([])
    yield app
