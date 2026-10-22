# bidgen 项目约定（Python CLI）

> 面向本仓库 `bidgen/` 的编码约定与踩坑记录。写代码前请先读本文件。

## 模块分层

`pdf_reader`（PyMuPDF 读取）→ `reflow`（行→段落）→ `structure` / `extract`（解析）→ `docx_builder`（生成）。
生成时对每个格式 body 先经 `fill` 用采集值填充空位，再经 `punctuation` 规范化。
**所有章节仅遵照招标文件模板原文输出**，不附加自造的采购人头部、签署块或"（本部分由供应商…）"提示段。
`fill` 用私有区哨兵（`U+E000`/`U+E001`）标记需下划线的值（项目名称 / 项目编号 / 投标人名称 / 日期），由 `docx_builder._add_runs` 拆成 `run.font.underline` 的 run；哨兵不写入 DOCX；**这些值的占位符统一为"不间断空格（U+00A0）+ 单下划线格式"**（`_ul` 把 `PLACEHOLDER` 换成不间断空格）。日期规则锚定行首以不误匹配"投标截止日期"。

## 常见坑

- **日期占位（右对齐签章行）下划线不显示**：普通行尾空格（U+0020）的下划线 Word 默认不显示（"尾随空格的下划线"选项默认关闭）。**解法**：占位符用**不间断空格（U+00A0）+ 单下划线格式**（`run.font.underline`），不间断空格的下划线始终显示，且不加粗。不要用"字面下划线字符 + underline 格式"（会叠加成双线）。
`structure` / `extract` 只产出纯数据（dataclass / dict），不触 Word；`docx_builder` 只消费数据，不解析 PDF。

## 文本处理管道（顺序不可乱）

1. `textfix.fix()`：`NFKC` + CJK Radicals 映射，用于 **PDF 提取文本**。
2. `reflow.rebuild()`：物理行 → 语义段落（去页眉页脚、按列满行判定（右界=该列 x1 的 80 分位，`_FULL_EPS=14`）、编号起点、跨页合并、**token 续接强制合并且仅字母边界补空格**）。
3. `punctuation.normalize()`：中文语境半角 `, . : ; ! ?` → 全角；数字 / 英文 / 单位 / 型号 / 公式语境保留；**数字后紧跟的 `.` 一律保留**（编号 `1.`、小数 `12.1`，不转 `。`）；折叠 CJK 之间的空格（`采 购`→`采购`、`的 项目`→`的项目`、`） 。`→`）。`）并保持**中英文连续**（`USB 接口`→`USB接口`、`500 万`→`500万`、`第 1 章`→`第1章`），但保留 `（项目编号： ）` 这类填写空位；纯 ASCII 之间的空格保留（`USB 2.0`）。

**禁忌**：不要对整份 DOCX 跑 `NFKC` —— 它会把正文里的全角标点（`（）` `。`）折成半角。
需要修已生成 DOCX 的字形时，用 `textfix.fix_docx()`（只替换 `U+2E80–U+2FDF` 与 `戶`）。

## 依赖与版本

- 锁定 `PyMuPDF==1.24.14`：`>=1.25` 移除 `Rect.get_area`，会让 `pdf2docx` 抛
  `AttributeError: 'Rect' object has no attribute 'get_area'`。
- 一律用 `.venv/bin/python` 运行；`.venv/` 已在 `.gitignore`。

## DOCX 生成要点（python-docx）

- 页面尺寸显式设 A4：`section.page_width = Cm(21)`、`section.page_height = Cm(29.7)`（`StyleSpec.page_width_cm / page_height_cm`）；页边距上/下 2.54cm、左/右 3.17cm。

- 中文字体必须同时设 `rPr.rFonts` 的 `w:eastAsia`；只设 `font.name` 对中文无效。
- 首行缩进 2 字符用 `w:ind w:firstLineChars="200"`。
- 一级标题自动编号：`numbering.xml` 注入 `abstractNum`（`numFmt="chineseCounting"`，`lvlText="%1、"`，**`suff="nothing"`**——顿号紧贴标题，其后无空格/制表位，呈现为 `一、投标承诺书`）+ `num`，绑定 `Heading 1`；失败时降级为硬编码 `一、`。一级标题文本去掉编号前缀与"（如涉及）"字样（`_AS_INVOLVED_RE`）。
- 目录用普通段落（非 Heading），否则会被自动编号并污染 TOC。
- 一级标题**左对齐**，且每个一级标题前设 `page_break_before`（`w:pageBreakBefore`）。
- 正文段落**两端对齐**（`WD_ALIGN_PARAGRAPH.JUSTIFY`）；标题、封面、格式副标题等显式覆盖为居中/左对齐。
- 每个格式在一级标题下输出居中题名（黑体四号），题名上下各留一个空行。
- 模板 body 行对齐按其 PDF 水平位置识别（`structure._classify`）：靠右→右对齐、居中→居中，其余两端对齐；签署块"投标人名称 / 日期"行右对齐。
- 模板 body 行加粗按 PDF 字体识别（`font` 含 `Bold` 或 `flags & 16`，占比 ≥ 0.6）→ `Line.bold` → `Paragraph.bold` → `BodyLine.bold` → run 加粗。
- 招标文件中"独占一页"的小块（整页只有该内容、无跨页段落、字数 < 700）在投标文件中保持独立页（`reflow.independent_pages` → `BodyLine.own_page` → `page_break_before`）。
- 附件标题行（`_ATTACHMENT_TITLE_RE` = `^附件\s*[一二三四五六七八九十\d]*\s*[：:]?\s*$`，如 `附件：`、`附件 1:`）强制另起一页（`page_break_before`）；正文中的"附件：xxx"不受影响。
- 封面按招标文件封面模板（`template.cover_lines`）的字段顺序生成（`_cover_field_order`）；字段标签必须带冒号（`项目名称：`、`项目编号：`、`投标人：`），避免误匹配说明文字；`【第_包】` 用模板原文（`_cover_package_text`）。
- 表格：`read_lines(path, tables)` 用 `read_tables()` 的 bbox 标记 `Line.in_table`，`reflow` 剔除之；`structure._assign_tables` 按页归属到 `Format.tables`（并记 `table_spans=(page, top)`）；`docx_builder` 在 body 内**按 `(page, top)` 顺序插入表格**；**格式六（技术偏离表）从招标文件提供的模板提取**（渲染模板表格原样骨架，按 `(page, top)` 插入，位于居中题名与"说明"之间）；表头行水平居中 + 垂直居中（`WD_CELL_VERTICAL_ALIGNMENT.CENTER`）。
- **格式十六（各类证明材料）为定制输出**：`（一）招标文件要求提供的其他资料`（**二级标题**）下按类别附表——`1.资格审查`（资格审查表）、`2.符合性审查`（符合性审查表）、`3.技术评审`（综合评分表·技术部分）、`4.商务评审`（综合评分表·商务/价格部分，`extract.split_scoring` 按标记行拆分），随后 `（二）投标人认为需提供的其他资料`（**二级标题**）；资格承诺函不再插入这些表格（`_business_tables` 已移除）。
- 表格续页合并：`_is_continuation` 允许"商务评审"等**标签数据行**续页（非数字、非空、非表头词），保证跨页表格（如综合评分表）完整。
- 封面独立分节，且首节不含 `headerReference` / `footerReference`，页眉页脚只加在正文节。
- 表格单元格内换行需在写入前替换掉（`"\n" → ""`）。

## 输出卫生

`sanitize.sanitize_docx()`：清空 core / app 元数据、删除 `<w:rsids>` 与 `w:rsid*` 属性、
移除 `custom.xml` / `people.xml` / `comments*.xml` 并同步 `[Content_Types].xml` 与 rels。
