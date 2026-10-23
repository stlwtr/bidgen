# 产品级 GUI 重构 (product-gui)

## Goal

把 bidgen 的 PySide6 界面（`bidgen/gui.py`，现状为浅色卡片风 + QTabWidget「生成/设置」两页 + 单文件）重构为**产品级桌面应用**：面向非技术投标专员，开箱即用、少出错；以易用与可靠为核心，视觉服务于易用性；PySide6 + PyInstaller 原生包在 Win / Linux / macOS 内部共享分发。

## Background（已确认现状）

- GUI：PySide6 6.12；浅色卡片风 QSS；`bidgen gui` 子命令；QTabWidget「生成/设置」；多供应商档案（`suppliers/` + SupplierStore）；关于菜单（科创研发室）；fd 级捕获真实进度（pdf2docx 页进度 + `[bidgen] n/5` 阶段进度）；PyInstaller 三平台一键打包脚本（`scripts/build_{windows,linux,macos}.{bat,sh}`），macOS 已验证打包可启动；单文件 `bidgen/gui.py`（~600 行）。
- 决策（四轮 24 项，均已确认）见 Decisions。

## Requirements

- **R1 信息架构**：左侧竖向导航四页（生成 / 供应商 / 日志 / 关于，Qt 内置图标 + 中文标签）；首次启动一次性引导页（可勾选「不再显示」）；菜单栏仅「帮助 → 关于」。
- **R2 生成页**：最少字段（选招标 PDF + 大生成按钮）；「高级选项」折叠区（输出目录、同时生成招标文件 Word）；顶部全局进度条 + 阶段文本（转换 `n/125 页`、生成 `n/5 阶段`）；内联成功条（绿，含「打开输出目录」「打开投标文件」按钮）/ 内联失败条（红，含「重试」「导出日志」「展开详情」）；内嵌简要过程日志。
- **R3 供应商页**：左侧档案列表（当前 ✓ 标记，「新建 / 删除 / 设为当前」）；右侧表单（11 字段 + 类型），选中即编辑、自动保存。
- **R4 日志页**：全程日志（级别标识）+「导出日志」按钮（脱敏路径）。
- **R5 关于页**：功能说明 + 语义化版本（1.0.0 起）+ 构建日期 + 科创研发室提供支持。
- **R6 视觉规范**：浅色卡片风增强；主色 `#4a7dff`；状态色（绿成功 / 红失败 / 橙警告）；Qt 内置标准图标；基础字号 14-15px + 「设置」可调大；高对比文字；键盘可达（Tab 顺序 / 快捷键）；仅简体中文。
- **R7 交互流程**：首次引导页（三步图文 + 界面示意 + 「不再显示」存配置）→ 主界面空状态引导（未选 PDF 时引导文案）；生成 → 顶部进度条 → 成功条或失败条；出错 → 内联错误条（标题 + 展开详情）+ 一键重试 + 一键导出日志（版本号 / OS / 输入文件 / 供应商名 / 当前阶段 / 堆栈，路径脱敏）。
- **R8 技术实现**：`gui/` 包拆分（pages / widgets / store / workers / styles）；保留 fd 进度捕获与 SupplierStore 多档案；语义化版本 1.0.0 起 + 构建日期写入关于页。
- **R9 测试与分发**：offscreen 冒烟 + pytest-qt 关键交互测试（选文件 / 生成流程 mock / 供应商 CRUD）；保留三平台打包脚本 + 新增 GitHub Actions 自动三平台打包（push 上传 artifact / release）。
- **R10 版本更新检查（COS 迁移）**：关于页「检查更新」从远程 version.json 拉取最新版本号并语义化对比；version.json 托管于腾讯云 COS 公开读对象，应用匿名拉取（不携带任何密钥）。
- **R11 表单布局统一（标题左对齐 + 字段可伸缩）**：三处 QFormLayout（suppliers.py:51 供应商页表单、generate.py:47 文件选择行、generate.py:62 高级选项）显式设置 `setLabelAlignment(AlignLeft|AlignVCenter)` 与 `setFieldGrowthPolicy(AllNonFixedFieldsGrow)`，覆盖 macOS Aqua 默认（标签右对齐 + FieldsStayAtSizeHint 不拉伸），使标签左对齐、字段填充可用宽度并随窗口伸缩。

## Acceptance Criteria

- [ ] AC1 侧边导航四页可切换（生成 / 供应商 / 日志 / 关于），各页职责清晰。
- [ ] AC2 生成页默认仅「选 PDF + 生成按钮」；输出目录 / 同时生成招标文件在「高级选项」折叠区，可展开。
- [ ] AC3 转换招标文件时进度条显示真实页进度（n/125）；生成投标文件时显示阶段进度（n/5）；均为百分比。
- [ ] AC4 成功后显示内联成功条（绿）且含「打开输出目录」「打开投标文件」按钮；失败显示内联失败条（红）且含「重试」「导出日志」「展开详情」。
- [ ] AC5 供应商页左列表右表单；选中档案即编辑、修改自动保存；「设为当前」在列表上打 ✓；生成使用当前档案。
- [ ] AC6 日志页可查看全程日志并可「导出日志」；导出内容含版本号 / OS / 输入文件 / 供应商名 / 当前阶段 / 堆栈且路径脱敏。
- [ ] AC7 首次启动显示引导页（三步），可勾选「不再显示」且重启后不再显示；未选 PDF 时生成页显示空状态引导文案。
- [ ] AC8 关于页显示功能说明、语义化版本号（1.0.0 起）、构建日期、科创研发室提供支持。
- [ ] AC9 主色 `#4a7dff` 与状态色（绿 / 红 / 橙）应用一致；基础字号 14-15px 且可在设置调大；界面仅简体中文；导航 / 按钮含 Qt 内置图标；主要操作可键盘到达。
- [ ] AC10 `gui/` 拆分为包（pages / widgets / store / workers / styles），原有功能（生成、进度、多供应商、打包脚本）不回归。
- [ ] AC11 offscreen 冒烟通过；pytest-qt 关键交互测试通过（选文件 / 生成流程 mock / 供应商 CRUD）。
- [ ] AC12 GitHub Actions 工作流存在：push 自动在 Win / Linux / macOS 打包并上传 artifact。
- [ ] AC13 更新检查改为从 COS 公开 URL `https://bidgen-1251440031.cos.ap-guangzhou.myqcloud.com/version.json` 匿名拉取；应用内不含任何 COS 密钥；网络 / 解析失败仍按「无更新 / 检查失败」处理，不崩溃。
- [ ] AC14 三处表单（suppliers.py:51 / generate.py:47 / generate.py:62）标签文字左对齐（不再右对齐贴近字段）；字段（含日期选择器、供应商类型下拉、文件路径、输出目录等）水平填充表单可用宽度，窗口拉宽时字段同步变长；pytest tests/gui 通过且 ruff 无错。

## Out of Scope

- 自动更新（手动重下）。
- 代码签名 / 公证（notarize）。
- 深色模式 / 主题切换。
- 国际化（i18n）/ 英文界面。
- Web 界面 / Electron / Tauri。
- COS 私有读 / 签名请求 / STS 临时密钥（version.json 公开读，应用匿名访问）。

## Decisions

- D1 目标：非技术人员开箱即用、少出错（易用 + 可靠优先）。
- D2 用户 / 分发：企业内部投标专员，内部共享 exe，手动重下，语义化版本号。
- D3 技术栈：PySide6 + PyInstaller。
- D4 信息架构：左侧竖向导航四页；首次引导页；菜单仅帮助 → 关于。
- D5 视觉：浅色卡片风增强；主色 `#4a7dff`；状态色；Qt 内置图标；14-15px 可调字号；高对比；键盘可达；仅中文。
- D6 生成页：最少字段 + 高级选项折叠；顶部进度条 + 内联成败条（含打开目录 / 文件 / 重试 / 导出日志 / 展开详情）。
- D7 供应商页：左列表右表单同页，自动保存，设为当前标记。
- D8 进度 / 错误：顶部全局进度条 + 内联成败 / 错误条；错误条含重试 + 导出日志（脱敏）。
- D9 引导：首次引导页 + 空状态引导。
- D10 测试：offscreen 冒烟 + pytest-qt 关键交互测试。
- D11 分发：保留三平台打包脚本 + GitHub Actions 自动三平台打包。
- D12 代码：`gui/` 包拆分（pages / widgets / store / workers / styles）。
- D13 更新检查源：version.json 托管于腾讯云 COS 公开读对象（`bidgen-1251440031` / `ap-guangzhou` / `version.json`），应用匿名拉取，不引入 qcloud_cos SDK、不携带密钥（方案 A，用户已确认）。
- D14 表单布局：显式设置 label 左对齐 + 字段拉伸（不依赖平台 style hint），同时统一三平台表现；实现仅需每处两行 setter，风险极低。
- D15 R11 范围：三处 QFormLayout 统一修改（供应商页 + 生成页两处），用户已确认（避免跨页面表单行为不一致与后续返工）。

## Technical Notes

- 现状 `bidgen/gui/updater.py`：`UPDATE_URL = "https://bidgen-1251440031.cos.ap-guangzhou.myqcloud.com/version.json"`（腾讯云 COS 公开读对象），`urllib.request` 匿名拉取 + `_version_tuple` 语义化对比；`about.py` 后台线程调用。
- 迁移自 Gitee raw URL（`raw.giteeusercontent.com/yanglishuan/bidgen/raw/dev/version.json`）；COS 公开读即普通 HTTPS GET，`urllib.request` 逻辑原样复用，无需新增依赖。
- version.json 不参与 PyInstaller 打包（仅 logo.png 被 `--add-data`），运行时远程拉取，迁移不影响打包脚本。
- COS URL 已实测可达（HTTP 200，内容与仓库 version.json 一致）。

- R11 根因：macOS（cocoa/QMacStyle）下 QFormLayout 默认为标签右对齐（SH_FormLayoutLabelAlignment=AlignRight）且 FieldsStayAtSizeHint（字段不拉伸、form 水平居中），即用户所见「标题右对齐、内容短、不可伸缩」；显式 setter 后跨平台一致。offscreen 平台默认不同（AlignLeft + AllNonFixedFieldsGrow），故截图验证需在 cocoa 下或信显式设置。
