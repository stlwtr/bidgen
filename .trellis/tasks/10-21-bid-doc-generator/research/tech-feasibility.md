# 技术可行性验证（research）

## 1. PDF → DOCX 转换

- 候选：`pdf2docx`（纯 Python，基于 PyMuPDF + python-docx）、LibreOffice headless、pandoc。
- pandoc/poppler/mutool 均未安装；LibreOffice 已安装（`/Applications/LibreOffice.app`）。
- **结论**：采用 `pdf2docx`。
  - 依赖 `python-docx`、`PyMuPDF`、`opencv-python-headless` 等，可 `pip install`。
  - **版本陷阱**：`pdf2docx 0.5.8` 与 `PyMuPDF >= 1.25`（实测 1.26.5）不兼容，报
    `AttributeError: 'Rect' object has no attribute 'get_area'`（`pdf2docx/shape/Path.py:258`）。
  - **锁定 `PyMuPDF==1.24.14` 后转换成功**：前 4 页耗时 5.6s，输出 40 段落 + 2 表格，结构基本正确。

## 2. 乱码 / 异体字形修复

PDF 文本层含 CJK 康熙部首与 CJK Radicals Supplement 字形（非标准常用字），导致 Word 显示乱码。

- `unicodedata.normalize('NFKC', s)` 可修复大部分康熙部首类：
  - `⼈`(U+2F08)→`人`、`⽂`(U+2F42)→`文`、`⽬`(U+2F6C)→`目`、`⼀`(U+2F00)→`一`、`⽅`(U+2F45)→`方`、`⽹`(U+2F79)→`网`、`⼯`(U+2F2F)→`工业`字。
- NFKC **无法**修复的少数（CJK Radicals Supplement，简体差异），需自定义映射表：
  - `⻰`(U+2EF0)→`龙`、`⻚`(U+2EDA)→`页`、`⼾`(U+2F3E)→`户`（NFKC 给出繁体 `戶`）。
- **结论**：两级修复 —— 先 `NFKC`，再叠加自定义映射表（覆盖 U+2E80–U+2EFF 全部部首）。

## 3. Word 生成

- `python-docx` 可安装可用，支持段落、表格、样式、页眉页脚、编号（`numbering` 需手工构造 XML）。
- 从零构建投标文件（不继承转换出的招标 Word 的脏排版）。

## 4. 环境

- Python 3.9.6（macOS，`/Applications/Xcode.app/.../python3`）。
- 已装：`PyMuPDF 1.24.14`、`pdf2docx 0.5.8`、`python-docx`。
- LibreOffice 已装：`/Applications/LibreOffice.app/Contents/MacOS/soffice`（不在 PATH）。

## 5. PDF→DOCX 方案对比（补充验证，125 页全量）

对同一份招标 PDF 做了完整对比：

| 维度 | pdf2docx 0.5.8 + PyMuPDF 1.24.14 | LibreOffice `writer_pdf_import` |
|------|----------------------------------|--------------------------------|
| 耗时（125 页） | 409s（6m49s） | 415s（6m55s） |
| 段落 | 1285 | 125 |
| 表格 | **174** | **0** |
| 正文文本 | 51961 字符 | 1532 run / 3756 非空格字符（**丢失约 95%，中文几乎全丢**） |
| 结构 | 正常段落流 | 27764 个 `w:txbxContent` 文本框 + 13882 个 `w:drawing` |
| 图片 | 未保留（media=0） | 未保留（media=0） |
| 输出大小 | 0.28MB | 1.08MB |

**结论：LibreOffice 明显更差**，`writer_pdf_import` 把 PDF 按矢量图形重建，导出 docx 时内容散成数万文本框、文本严重丢失、表格全无。**维持 pdf2docx 方案**。

**共性限制**：两种方案都不保留图片；全量转换都需 ~7 分钟（注意：前几页 5.6s 是乐观值，表格/图片密集页显著变慢）。

**后续可选优化**（不改变 MVP 行为）：投标文件生成走 PyMuPDF 直读文本+`find_tables()`，无需依赖转换出的 docx；招标 Word 全量转换耗时可通过"按需只转关键页"缓解。

## 6. 行尾换行 ≠ 语义段落（文本重建，关键陷阱）

**PDF 的物理行不是自然段**，直接按 `\n` 写入 Word 会把一个段落拆成多行。实证：

- 第 6 页：`12.1…不得将一个采购包中的内容拆分` / `投标，否则其对该采购包的投标将被认定为投标无效。` 属**同一自然段**，PDF 折成 2 行。
- 书名号跨行：`…按照《黑龙江省政府采购供应商信用评价管理暂行办法` / `》，在确定的收取额度的基础上…`——合并时必须正确拼接（中文不加空格）。
- 跨页折行：`14.2…由于投标保`(第8页末) / `证金到账需要一定时间…`(第9页首) 同属一段。

**全文档统计（5746 行）**：
- 每页 1 个页脚行（`-第N页-`），共 **125** 个 → 必须先剔除。
- **27%（1581 行）以条款/编号开头**（`\d+(\.\d+)*`、`（1）`、`一、`、`第X章/节`、`★`）→ 强段落起点信号。
- 仅 **10% 行到达绝对右边界(≥554)**；`x0` 分布多峰（53=正文左边距，144/161=表格或缩进列）→ "满行"判定不能用全局绝对阈值，需**按列**计算右界。
- PyMuPDF `get_text('dict')` 中 `block` 与 `line` 常 **1:1**（一个视觉行 = 一个 block）→ **block 不能充当段落**。

**结论**：无论 pdf2docx 还是 PyMuPDF 直读，输出都按物理行给 `\n`；两种路径都必须做"行→段落"重建后再写 Word。
