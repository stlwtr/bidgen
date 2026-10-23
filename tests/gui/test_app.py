"""主窗口冒烟测试：四页结构与导航切换。"""

from bidgen.gui import MainWindow


def test_mainwindow_pages_and_nav(qapp):
    win = MainWindow()
    win.show()
    assert win.nav.count() == 4
    assert win.pages.count() == 4
    assert [win.nav.item(i).text() for i in range(win.nav.count())] == ["生成", "供应商", "日志", "关于"]
    # 导航切换
    win.nav.setCurrentRow(1)
    assert win.pages.currentIndex() == 1
    win.nav.setCurrentRow(3)
    assert win.pages.currentIndex() == 3
    win.nav.setCurrentRow(0)
    assert win.pages.currentIndex() == 0


def test_generate_page_minimal_fields(qapp):
    win = MainWindow()
    win.show()  # 需 show 父窗口，子控件 isVisible() 才为 True
    page = win.generate_page
    # 最少字段：选 PDF + 生成按钮 + 高级选项默认折叠
    assert page.pdf_edit is not None
    assert page.gen_btn is not None
    assert page.advanced.content.isVisible() is False
    # 空状态引导：未选 PDF 时显示
    assert page.empty_label.isVisible()
    # 选了 PDF 后隐藏
    page.pdf_edit.setText("/tmp/x.pdf")
    assert not page.empty_label.isVisible()
    # 展开高级选项
    page.advanced.set_expanded(True)
    assert page.advanced.content.isVisible()
