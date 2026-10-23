# 技术设计 (product-gui)

## 1. 架构（`gui/` 包拆分）

| 文件 | 职责 |
|------|------|
| `bidgen/gui/__init__.py` | 导出 `run_gui` |
| `bidgen/gui/app.py` | QApplication 工厂 + MainWindow 装配（侧边导航 + 四页 + 首次引导） |
| `bidgen/gui/styles.py` | QSS 常量：浅色卡片风、主色 `#4a7dff`、状态色、字号（14-15px + 可调） |
| `bidgen/gui/store.py` | SupplierStore 多供应商档案（`suppliers/` + `.current`），自单文件 gui.py 迁入 |
| `bidgen/gui/workers.py` | Worker QThread + fd 进度捕获 + `_QueueWriter`，自 gui.py 迁入 |
| `bidgen/gui/version.py` | `VERSION = "1.0.0"`、`BUILD_DATE` |
| `bidgen/gui/widgets.py` | 共享控件：内联成败 / 错误条、折叠「高级选项」、空状态、引导页 |
| `bidgen/gui/pages/__init__.py` | 页面包 |
| `bidgen/gui/pages/generate.py` | 生成页（最少字段 + 高级折叠 + 顶部进度条 + 内联成败条） |
| `bidgen/gui/pages/suppliers.py` | 供应商页（左列表右表单） |
| `bidgen/gui/pages/logs.py` | 日志页（级别 + 导出脱敏日志） |
| `bidgen/gui/pages/about.py` | 关于页（功能说明 + 版本 / 构建日期 + 科创研发室） |

**边界**：pages 只管布局与交互；`store` 管供应商档案数据；`workers` 管后台生成与进度；`styles` 管样式。`gui` 调 `cli._convert` / `_generate`，核心逻辑（bidgen 各模块）不依赖 `gui`。

## 2. 页面与控件明细

**生成页（pages/generate.py）**
- 招标 PDF 选择行（只读 QLineEdit + 「浏览…」）
- 「高级选项 ▸」折叠区（QToolButton checkable）：输出目录行、「同时生成招标文件 Word」复选框
- 大生成按钮（`#primary`）
- 顶部全局进度条（`QProgressBar` 0-100）+ 阶段文本 QLabel
- 内联成功条 `SuccessBanner`（绿底 #2f9e44 浅底，含「打开输出目录」「打开投标文件」按钮）
- 内联失败条 `ErrorBanner`（红底浅底，标题 + 「重试」「导出日志」「展开详情 ▸」）
- 内嵌简要过程日志（QTextEdit 只读）

**供应商页（pages/suppliers.py）**
- 左：`QListWidget` 档案列表（当前 ✓ 加粗标记）+「新建 / 删除 / 设为当前」按钮列
- 右：表单（`_SUPPLIER_FIELDS` 11 字段 + 类型 QComboBox），选中档案即填充、编辑自动保存（`textChanged` → store.save）

**日志页（pages/logs.py）**：`QTextEdit` 全程日志（带级别前缀）+「导出日志…」（QFileDialog 保存，内容脱敏路径）。

**关于页（pages/about.py）**：功能说明 + `VERSION` / `BUILD_DATE` + 「科创研发室提供支持」。

## 3. 数据流

- 生成：PDF → `cli._build_context`（`[bidgen] n/5` 阶段 print）→ `docx_builder` → docx；`cli._convert`（pdf2docx）页进度 `(n/125) Page`；两者经 fd 重定向（`os.pipe` + `dup2`）→ `workers.Worker.q` → 主线程 `QTimer.poll` → 顶部进度条 + 阶段文本。
- 供应商：`SupplierStore`（`suppliers/<名称>.yaml` + `.current`）→ 表单自动保存 → 生成时 `store.load(store.current())` 写临时 yaml 供 `cli._generate`。
- 错误：异常 → `ErrorBanner`；「导出日志」收集版本号 / OS / 输入文件 / 当前供应商 / 当前阶段 / 堆栈，路径脱敏（`~` 替换用户目录）。

## 4. 视觉规范

- 主色 `#4a7dff`；状态色：成功 `#2f9e44`、失败 `#e03131`、警告 `#f08c00`。
- 浅色卡片风增强（白底圆角卡片、统一留白与层级）；基础字号 14-15px，`styles.set_font_scale(scale)` 可调大；高对比文字；键盘可达（`setTabOrder` / 快捷键）；Qt 内置标准图标（`QStyle.StandardPixmap`）；仅简体中文。

## 5. 兼容与迁移

- 从单文件 `bidgen/gui.py` 拆分为 `bidgen/gui/` 包，保持 `bidgen gui` 入口（`run_gui`）与功能等价：生成、真实进度、多供应商、打包脚本均不回归。
- `cli.py` 的 `[bidgen] n/5` 阶段 print 保留（CLI 与 GUI 共用进度源）。
- `app_gui.py`（PyInstaller 入口）改为 `from bidgen.gui import run_gui`。

## 6. 风险与回滚

- **重构回归**：offscreen 冒烟 + pytest-qt 关键交互测试兜底；回滚点 = 单文件 `bidgen/gui.py`（git 历史）。
- **哨兵泄漏**：`_add_runs` 入口统一 `underscore_to_ul` + `split_markup`（已修复，保持）；`document.xml` 哨兵数 = 0 为验收。
- **fd 重定向**：Worker 结束 `finally` 恢复 fd，避免影响进程。
- **CI 打包大依赖**（PySide6 / fitz / cv2）：`--collect-all` + 三平台 runner；本地 `scripts/` 兜底。

## 7. 分发

- 保留 `scripts/build_{windows,linux,macos}.{bat,sh}` 本地一键打包。
- 新增 `.github/workflows/build-gui.yml`：push 自动在 windows / ubuntu / macos runner 上 `pip install -r requirements.txt pyinstaller` + 对应打包命令，上传 artifact；tag 时产 release。
