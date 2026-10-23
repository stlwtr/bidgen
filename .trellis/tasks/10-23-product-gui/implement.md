# 实施计划 (product-gui)

> 平台为 inline 模式（湛卢/Kilo），Phase 2 通过 `trellis-before-dev` 加载上下文，无需 JSONL 清单。

## 有序实现清单（里程碑）

1. **`gui/` 包拆分重构（功能等价）+ 四页骨架（侧边导航）**
   - [ ] 建 `bidgen/gui/`（app / styles / store / workers / version / widgets / pages）
   - [ ] 迁入 SupplierStore、Worker、QSS；`run_gui` 改为从包导出
   - [ ] `app_gui.py`（PyInstaller 入口）改为 `from bidgen.gui import run_gui`
   - [ ] 四页骨架：侧边导航（QListWidget 作导航）+ QStackedWidget
2. **生成页最少字段 + 高级折叠 + 顶部进度条 + 内联成败条**
   - [ ] 选 PDF + 大生成按钮；「高级选项 ▸」折叠（输出目录、同时生成招标文件）
   - [ ] 顶部进度条 + 阶段文本（接 workers 进度信号）
   - [ ] `SuccessBanner`（绿 + 打开输出目录 / 打开投标文件）/ `ErrorBanner`（红 + 重试 / 导出日志 / 展开详情）
3. **供应商页（左列表右表单）+ 日志页 + 关于页**
   - [ ] 左列表（当前 ✓，新建 / 删除 / 设为当前）+ 右表单（自动保存）
   - [ ] 日志页：全程日志 + 级别 + 导出脱敏日志
   - [ ] 关于页：功能说明 + `VERSION` / `BUILD_DATE` + 科创研发室
4. **首次引导页 + 空状态引导 + 错误条**
   - [ ] 引导页（三步图文 + 示意 + 「不再显示」存 `suppliers/.ui.json` 或配置）
   - [ ] 空状态引导文案（未选 PDF 时）
   - [ ] 错误条：标题 + 展开详情 + 重试 + 导出日志（版本 / OS / 输入 / 供应商 / 阶段 / 堆栈，脱敏路径）
5. **视觉打磨**
   - [ ] 主色 / 状态色统一；Qt 内置图标；14-15px 基础字号 + 设置可调大
   - [ ] 高对比文字；键盘可达（Tab 顺序 / 快捷键）
6. **pytest-qt 交互测试 + GitHub Actions 三平台打包**
   - [ ] offscreen 冒烟 + pytest-qt（选文件 / 生成流程 mock / 供应商 CRUD）
   - [ ] `.github/workflows/build-gui.yml`（windows / ubuntu / macos runner，push 打包上传 artifact，tag 产 release）

## 验证命令

```bash
# offscreen 冒烟（窗口与各页创建）
QT_QPA_PLATFORM=offscreen .venv/bin/python -c "from PySide6.QtWidgets import QApplication; from bidgen.gui.app import MainWindow; app=QApplication([]); w=MainWindow(); w.show(); print('ok')"

# 单测
.venv/bin/python -m pytest -q

# pytest-qt 界面交互
.venv/bin/python -m pytest -q tests/gui

# macOS 打包验证
bash scripts/build_macos.sh
```

## 风险文件 / 回滚点

- `bidgen/gui.py`（现状单文件，拆分包前的回滚点）。
- `bidgen/cli.py`（`[bidgen]` 阶段 print 保留，勿删）。
- 回滚 = 恢复单文件 `bidgen/gui.py` 并删除 `bidgen/gui/` 包。

## 提交前检查

- [ ] offscreen 冒烟通过
- [ ] `pytest` + `pytest-qt` 全绿
- [ ] AC1-AC12 逐条核对
- [ ] `document.xml` 哨兵数 = 0（哨兵不泄漏）
