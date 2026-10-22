# 技术设计 (bid-doc-generator)

## 1. 架构与模块边界

单仓库、单一 Python 包 `bidgen/`（无 packages 配置）。模块按职责分层：

| 模块 | 职责 | 依赖 |
|------|------|------|
| `bidgen/cli.py` | 命令入口（argparse），编排流程 | 其余模块 |
| `bidgen/config.py` | 加载供应商配置（supplier.yaml/json），缺省字段兜底 | PyYAML |
| `bidgen/pdf_reader.py` | PyMuPDF 读取 PDF：逐页文本 + 行级 bbox、`find_tables()` 表格 | PyMuPDF |
| `bidgen/reflow.py` | 行→段落重建：去页眉页脚、编号起点识别、按列折行判定、跨页合并 | — |
| `bidgen/pdf_to_docx.py` | 调 `pdf2docx.Converter` 做整份 PDF→DOCX | pdf2docx |
| `bidgen/textfix.py` | 乱码修复：NFKC + CJK Radicals 映射 | 标准库 |
| `bidgen/punctuation.py` | 中英标点规范化（中文语境→全角，数字/英文/公式保留） | 标准库 |
| `bidgen/structure.py` | 定位章节、解析投标文件目录与格式一~十六 | pdf_reader, textfix |
| `bidgen/extract.py` | 采集字段（采购人/代理机构/项目名/编号）+ 资格项 / 评分项 | pdf_reader, textfix |
| `bidgen/docx_builder.py` | python-docx 构建投标文件：样式、页码、一级标题编号、页眉页脚、表格 | python-docx |
| `bidgen/fill.py` | 承诺函模板占位填充（采购人/代理机构/项目名称/项目编号/投标人名称，通用规则） | — |
| `bidgen/sanitize.py` | 清理 docx 机器码 / 用户信息（core/app 元数据、rsids、comments） | 标准库 |
| `tests/` | 乱码修复、标点、折行重建、结构/字段提取、填充、元数据清理的单测（docs 内 PDF 作 fixture） | pytest |

**边界原则**：`structure.py` / `extract.py` 只产出**纯数据（dataclass / dict）**，不接触 docx；`docx_builder.py` 只消费数据，不解析 PDF。二者通过明确的数据契约解耦，便于对未知招标文件做容错与测试。

## 2. CLI 接口

```bash
# 仅转招标文件
bidgen convert <招标文件.pdf> [-o 招标文件.docx]

# 生成投标文件初稿（招标转换 + 结构解析 + 填充）
bidgen generate <招标文件.pdf> --supplier <supplier.yaml> [-o 投标文件.docx]

# 一步到位：两个产物都出
bidgen all <招标文件.pdf> --supplier <supplier.yaml> --out-dir <dir>
```

- 退出码：0 成功；非 0 失败并打印可读错误。
- `generate` 时招标 `.docx` 默认输出到 `--out-dir`，可用 `--skip-tender-docx` 跳过中间产物。
- 通用选项：`--no-sanitize` 关闭元数据清理（默认开启，见 §4.10）；另可 `bidgen sanitize <file.docx>` 单独清理。

## 3. 数据流

```
招标PDF ──pdf2docx──▶ 招标文件.docx（交付产物①，经 textfix）
   │
   └─pdf_reader─▶ 页文本 + 行级 bbox + 表格
          │
          ├─reflow─────▶ 段落重建（剔页眉页脚/折行/跨页合并）
          │
          ├─structure─▶ {封面字段, 目录16项, 格式一..十六模板}
          └─extract──▶ {采购人, 代理机构, 项目名称, 项目编号,
                         资格审查项[], 符合性审查项[], 评分项[],
                         采购标的[], 技术要求[]}
          │
supplier.yaml ─config─▶ {公司名, 法人, 地址, 电话, 开户行, 账号, 代理人...}
          │
          ▼
     docx_builder ─▶ 投标文件.docx（交付产物②）
```

## 4. 关键实现要点

### 4.1 乱码修复（textfix）

```python
import unicodedata
RADICAL_FIX = {"⻰": "龙", "⻚": "页", "⼾": "户", ...}  # 覆盖 U+2E80–U+2EFF 中简体差异项
def fix(text: str) -> str:
    return unicodedata.normalize("NFKC", text).translate(str.maketrans(RADICAL_FIX))
```
- 先 NFKC（修康熙部首），再叠加映射（修 CJK Radicals Supplement）。
- 对**所有**进入解析或写出的文本强制调用 `fix()`（含从 PDF 直接取的文本，因为 pdf2docx 输出不含修复）。

### 4.2 章节定位（structure）

- 优先 `doc.get_toc()` 命中标题含"投标文件格式"；无目录时按页文本正则：
  `第[一二三四五六七八九十]+章[\s]*投标[\s]*文件(的)?格式`。
- 格式分段：正则 `格式[一二三四五六七八九十]+[：:]`，切出每段标题+正文。
- 目录 16 项：从"投标文件目录"到第一个"格式一"之间，按 `[一二三四五六七八九十]+、` 切行。
- 章节名不同（如"格式要求"）时降级为关键词匹配并告警。

### 4.3 一级标题自动编号（docx_builder）

- 目标：Word 原生自动编号，非硬编码序号。
- 做法：向 `document.part.numbering_part` 注入 `abstractNum`（多级十进制）+ `num`，并把 `numPr` 绑定到 `Heading 1` 样式；正文标题用 `style='Heading 1'`。
- 目录本身用带项列表（`一、二、`）→ 保留为普通段落，不参与自动编号。

### 4.4 页眉页脚

- `section.header` / `section.footer` 写入文本（如"投标文件"）+ 页码域：
  `fldSimple w:instr="PAGE"`；首页不同时设 `different_first_page_header_footer`。

### 4.5 表格

- 采购标的一览表、评分表等用 `page.find_tables()` 提取 → `docx_builder` 重建为 Word 表格。
- 合并单元格 / 跨页表格按行结构近似重建，不做版式还原。

### 4.6 字段提取容错

- 正则优先；匹配不到返回 `None`，`docx_builder` 渲染为 `______` 占位。
- 供应商配置缺失字段同样占位，不抛异常（保证 AC6/AC9）。

### 4.7 行→段落重建（reflow）

**问题**：PDF 的物理行 ≠ 自然段，直接写 Word 会把一段拆成多行（如 12.1、14.1 条款、书名号跨行、跨页折行）。证据见 `research/tech-feasibility.md` §6。

**接口**：`reflow.rebuild(lines) -> list[str]`，入参每行含 `x0, x1, text, page`（由 `pdf_reader` 提供行级 bbox）。

1. **剔除页眉页脚**：正则 `^-\s*第\s*\d+\s*[页⻚]\s*-?$`，及重复出现的页眉文本。
2. **文本列聚类**：按 `x0` 聚类得到若干列（正文列 x0≈53、缩进/表格列 x0≈144/161…）；每列**右界 = 该列行 `x1` 的高分位值**（不用全局绝对右边界，实测仅 10% 行达绝对边界）。
3. **段落起点判定**，下一行满足任一即为**新段**：
   - 以条款/列举编号开头：`^\d+(\.\d+)*[\.、\s]`、`^[（(]\d+[）)]`、`^[一二三四五六七八九十]+[、.]`、`^第[一二三四五六七八九十]+[章节条]`、`^[★☆]`
   - 上一行以结束标点结尾（`。；！？`）
   - `x0` 跳到另一列
4. **折行合并**：上一行**未满行**（`x1 < 本列右界 − ε`，右界取该列 `x1` 的 80 分位、`ε = _FULL_EPS = 14`）且下一行同列、不以编号开头 → 合并。
   - 中文合并**不加空格**；拼接处两侧均为 ASCII 字母/数字时才补一个空格。
   - **跨页合并**：上页末行未满行、下页首行同列非编号 → 合并（如 14.2 跨第 8–9 页）。
5. 输出 `list[段落字符串]`，供 `structure` / `extract` / `docx_builder` 使用。
6. **token 续接**：上一行以 ASCII 字母/数字结尾、下一行以 ASCII 字母/数字开头 → 判定为同一 token（如文号 `141`）被换行拆开，**强制合并**（优先于列跳变与"未满行"判定）；合并时只有**字母-字母**边界才补一个空格，数字边界绝不加空格（`〔2017〕1` + `41 号）` → `〔2017〕141 号）`）。

### 4.8 字体与段落样式规范

招标文件未规定投标文件版式（`research` 已核实），故按中文投标文件通用惯例设定；参数集中在 `bidgen/style.py` 的 `StyleSpec`，可整体覆盖。

**页面**
- 纸张 A4（21×29.7cm）。
- 页边距：上/下 2.54cm，左/右 3.17cm；装订线可另加左侧 0.5cm。
- 页眉距边 1.5cm，页脚距边 1.75cm。

**样式表**

| 元素 | 中文字体 | 西文/数字 | 字号 | 加粗 | 对齐 | 缩进 | 行距 | 段前/段后 |
|------|---------|-----------|------|:---:|------|------|------|-----------|
| 封面主标题 | 黑体 | Times New Roman | 小初 36pt | 是 | 居中 | 0 | 单倍 | — |
| 封面信息行 | 宋体 | Times New Roman | 三号 16pt | 否 | 居中 | 0 | 1.5 | — |
| 一级标题（章） | 黑体 | Times New Roman | 三号 16pt | 是 | 左 | 0 | 单倍 | 12/6 |
| 二级标题 | 黑体 | Times New Roman | 四号 14pt | 是 | 左 | 0 | 1.5 | 6/6 |
| 三级标题 | 黑体 | Times New Roman | 小四 12pt | 是 | 左 | 0 | 1.5 | 6/3 |
| 正文 | 宋体 | Times New Roman | 小四 12pt | 否 | 两端对齐 | 首行 2 字符 | 1.5 | 0/0 |
| 表格标题 | 黑体 | Times New Roman | 五号 10.5pt | 是 | 居中 | 0 | 单倍 | 6/3 |
| 表格正文 | 宋体 | Times New Roman | 五号 10.5pt | 否 | 左/居中 | 0 | 单倍 | 0/0 |
| 页眉 | 宋体 | Times New Roman | 五号 10.5pt | 否 | 居中 | 0 | 单倍 | — |
| 页脚页码 | 宋体 | Times New Roman | 五号 10.5pt | 否 | 居中 | 0 | 单倍 | — |

**分页与对齐**
- 每个一级标题前插入分页（`w:pageBreakBefore`）；一级标题左对齐。
- 每个格式在一级标题下输出**居中的格式题名**（黑体四号），题名上下各留一个空行（与招标文件模板一致）。
- 模板 body 行的对齐**按其在 PDF 中的水平位置识别**（`structure._classify`：`x1` 贴近右边距且左移→右对齐；左右留白近似相等→居中），识别不出的一律两端对齐；生成签署块中的"投标人名称 / 日期"行固定右对齐。
- 模板 body 行的**加粗**按 PDF 字体识别（span `font` 含 `Bold` 或 `flags & 16`，加粗字符占比 ≥ 0.6），贯通 `Line.bold` → `Paragraph.bold`（取段落首行）→ `BodyLine.bold` → run 加粗。
- 招标文件中**独占一页**的小块（整页只有该内容、无段落跨页、正文字数 < `_OWN_PAGE_MAX_CHARS=700`）在投标文件中保持独立页：块首、块后各分页一次（`reflow.independent_pages` → `structure.BodyLine.own_page` → `docx_builder` 的 `page_break_before`）。
- **附件标题行**（`_ATTACHMENT_TITLE_RE` = `^附件\s*[一二三四五六七八九十\d]*\s*[：:]?\s*$`，如 `附件：`、`附件 1:`、`附件一：`）强制另起一页（`page_break_before`），与招标文件"附件另起一页"的排版惯例一致；正文中的"附件：xxx"（如 `附件：具体标的…`）不受影响。

**编号**
- 一级标题走 Word 多级列表自动编号，`numFmt="chineseCounting"`，`lvlText="%1、"`、`suff="nothing"` → 呈现为 `一、投标承诺书`、`二、资格承诺函`…（**顿号后无空格/制表位**），绑定 `Heading 1` 样式（非硬编码序号）。
- 二级标题可选 `（一）`（`numFmt="chineseCounting"` 加括号）或 `1.`。

**页眉页脚**
- 页眉**默认为空**（`header_text=""`）；非空时居中文字、宋体五号、带下边框线。
- 页脚：`第 X 页 共 Y 页`（`PAGE` / `NUMPAGES` 域），居中，宋体五号。
- 封面独立分节、`different_first_page`，不显示页眉页脚与页码。

**目录**
- 用 Word TOC 域 `TOC \o "1-3" \h \z \u`，并在交付说明中提示"打开后按 F9 更新域"；解析兜底时退化为静态文本目录。

**python-docx 实现要点**
1. 中文字体必须显式设 `rPr.rFonts.set(qn('w:eastAsia'), '宋体')`；只设 `font.name` 对中文无效。优先在 `styles.xml`（Normal / 各级标题样式）统一设置，减少逐 run 开销。
2. 首行缩进 2 字符用 `w:ind w:firstLineChars="200"`（字符单位，随字号自适应）；退化方案 `first_line_indent=Pt(2×字号)`。
3. 行距：倍数用 `line_spacing=1.5`；固定值用 `line_spacing_rule=EXACTLY` + `line_spacing=Pt(22)`。
4. 页码域用 `fldSimple w:instr=" PAGE "`；页边距/页眉页脚距用 `section.*_margin` / `header_distance` / `footer_distance`。
5. 一级编号：向 `numbering_part` 注入 `abstractNum`(multilevel) + `num`，绑定 `Heading 1`；失败则降级为硬编码 `一、二、`。
6. 不内嵌字体：字体名仅写入文档，由打开端解析（服务器无字体不影响生成）。

### 4.9 中英标点规范化（punctuation）

**目标**：把中文语境里的半角标点改为全角，但**不动**数字 / 英文 / 单位 / 型号 / 公式语境。

**模块**：`bidgen/punctuation.py`，`normalize(text) -> str`；在 `reflow` 之后、写 docx 之前统一调用（正文与表格文本都过一遍）。

**转换集（默认）**：`,`→`，`、`.`→`。`、`:`→`：`、`;`→`；`、`!`→`！`、`?`→`？`。
**成对符号**：`(...)` 内容含 CJK 时 → `（...）`；`"..."` 中文语境 → `“...”`（可用开关关闭）。

**判定规则**（对每个候选 ASCII 标点，取左邻 `L`、右邻 `R`）：
- 仅当 **`L` 是 CJK** 且 **`R` 不是 ASCII 字母/数字**（且 `R` 不是 ASCII 标点，避免打断英文串）→ 转换。
- **数字守则**（任一命中则不转）：`,` `.` `:` 的 `L` 或 `R` 为数字 → 保留。覆盖金额 `3,649,020.00`、比例/时间 `16:10`、条款编号 `12.1`。
- **英文/公式守则**：`L` 或 `R` 为 ASCII 字母 → 保留。覆盖 `8dB(A)`、`(Cr)≤20`、`(1m,1w)`、纯英文句子。
- **括号规则**：`(...)` 仅当括号内出现 CJK 才转全角（`(如涉及)`→`（如涉及）`），否则保留（`(Cr)`、`(A)`）。
- 数字后紧跟的 `.` 一律保留（编号 `1.`、小数 `12.1`），不转 `。`。
- 折叠 CJK 字符 / 标点之间的 ASCII / 全角空格（`采 购`→`采购`、`的 项目`→`的项目`、`） 。`→`）。`）；并保持**中英文连续**（`USB 接口`→`USB接口`、`500 万`→`500万`、`第 1 章`→`第1章`）；纯 ASCII 之间的空格保留（`USB 2.0`）；纯标点之间的空位（如 `（项目编号： ）`）保留为填写空位。
- 省略号 `...`、版本号、日期时间等不处理；已是全角的标点不动。

**不做**：不改动数字 / 字母 / 单位 / 公式内部的标点；不删字符；不做中英互译。

**验证样例（写入单测）**

| 输入 | 输出 |
|------|------|
| `金额3,649,020.00元,共100台.` | `金额3,649,020.00元，共100台。` |
| `屏幕比例16:10,分辨率高.` | `屏幕比例16:10，分辨率高。` |
| `规格8dB(A),符合(Cr)≤20` | `规格8dB(A)，符合(Cr)≤20` |
| `型号(1m,1w),如下:` | `型号(1m,1w)，如下：` |
| `本章(如涉及)内容` | `本章（如涉及）内容` |
| `This is a test, do not change.` | `This is a test, do not change.` |

### 4.10 元数据清理（sanitize，可选）

**目标**：移除 Word 产物中的机器码与用户信息（隐私 / 去指纹），对两个产物都生效。

**实测现状**（pdf2docx 产物）：
- `docProps/core.xml`：`dc:creator=python-docx`、`dc:description=generated by python-docx`、`dcterms:created/modified=2013-12-23`
- `docProps/app.xml`：`<Application>Microsoft Macintosh Word</Application>`、`<Template>Normal.dotm</Template>`、`<Manager/>`、`<Company/>`
- `word/settings.xml`：`<w:rsids>` 含 9 个 rsid
- `word/document.xml`：3 个 `w:rsid*` 属性

**模块**：`bidgen/sanitize.py`，`sanitize_docx(path)`（zip 级后处理，适用于任意 docx，含 pdf2docx 产物）。

**清理项**
1. `core.xml`：清空 `creator` / `lastModifiedBy` / `title` / `subject` / `keywords` / `description` / `category`；`revision=1`；`created` / `modified` 置固定时间。
2. `app.xml`：清空 `Application` / `Template` / `Manager` / `Company` / `TotalTime`。
3. `settings.xml`：删除 `<w:rsids>` 块。
4. `document.xml` 及 `header*.xml` / `footer*.xml`：删除所有 `w:rsidR*` / `w:rsidP` / `w:rsidTr` 属性。
5. 删除 `docProps/custom.xml` 与 `word/people.xml`、`word/comments*.xml`（若存在），并同步 `[Content_Types].xml` 与 `_rels/.rels`。

**接线**：默认开启；CLI `--no-sanitize` 关闭；亦可 `bidgen sanitize <file.docx>` 独立清理。

**风险**：zip 重建须保持 parts、`[Content_Types].xml`、`_rels/.rels` 一致；单测断言清理后无 `python-docx` / `Microsoft` / `rsid` 残留，且文档能被 python-docx 正常打开。

### 4.11 承诺函占位填充（fill）

**目标**：把承诺函模板正文中的空位用采集值填充；做法通用，不针对单一招标文件。

**模块**：`bidgen/fill.py`，`fill_line(text, values) -> str`；对**每个格式 body 逐行**应用，未匹配的行原样保留。

**规则**（正则 → 替换；`采购人`/`代理机构`/`项目名称`/`项目编号` 取自 `extract`，`投标人名称` 取自 `supplier.yaml`，缺失→`______`）：

| 模式 | 替换为 |
|------|--------|
| `^采购人[、,]?采购代理机构名称\s*[：:].*$` | `采购人、采购代理机构名称：{采购人}、{代理机构}` |
| `[（(]\s*项目编号\s*[：:]?\s*[）)]` | `（项目编号：{项目编号}）` |
| `[（(]\s*投标人名称\s*[：:]?\s*[）)]` | `（投标人名称：{投标人名称}）` |
| `[（(]\s*项目名称\s*[：:]?\s*[）)]` | `（{项目名称}）` |
| `[（(]\s*单位名称\s*[：:]?\s*[）)]` | `（{采购人}）` |
| `已收到的\s*项目` | `已收到的{项目名称}项目` |

填充在 `punctuation` 规范化之前执行（模板为半角形态，填充后再统一转全角）。**项目名称 / 项目编号 / 投标人名称** 三个值用私有区哨兵（`U+E000`/`U+E001`）包裹，由 `docx_builder._add_runs` 拆分为带下划线（`run.font.underline`）的 run；采购人 / 代理机构不加下划线；哨兵不写入 DOCX。

### 4.12 表格识别与渲染

- `pdf_reader.read_lines(path, tables)`：传入 `read_tables()` 结果时，落在表格 `bbox` 内的行标记 `Line.in_table=True`（不重复扫描表格）。
- `reflow` 剔除 `in_table` 行，**表格文本不进入正文段落流**（避免"品目号/标的名称…"被当成段落）。
- `structure` 按页把表格归属到"其上最近的格式标题"：`Format.start_page` + `_assign_tables()` → `Format.tables`。
- `docx_builder` 在格式 body 之内**按 `(page, top)` 位置**插入模板表格（`Table Grid`，单元格去换行），保证与招标文件中的行/表顺序一致（如格式七：题名 → `包号：` → 表格 → `说明：…`）；**格式六（技术偏离表）从招标文件提供的模板提取**（渲染模板表格原样骨架：7 列，含 `1/★/1.1`、`1.2`、`……` 等结构行，位于居中题名与"说明"之间）。

### 4.13 各类证明材料（格式十六）输出定制

- 格式十六为定制输出：`（一）招标文件要求提供的其他资料`（**二级标题**）下按类别附表——`1.资格审查`（资格审查表，第四章）、`2.符合性审查`（符合性审查表，第五章）、`3.技术评审`（综合评分表·技术部分）、`4.商务评审`（综合评分表·商务/价格部分），随后 `（二）投标人认为需提供的其他资料`（**二级标题**）。`extract.split_scoring` 按"商务评审"/"价格评审"标记行把综合评分表拆为技术/商务两部分。
- **资格承诺函不再插入**这些表格；`_business_tables` 已移除。
- 综合评分表跨页（技术 68 分 → 商务 2 分 → 价格 30 分）：`_is_continuation` 放宽，允许"商务评审"等**标签数据行**续页（非数字、非空、且非表头词），保证评分表完整。

### 4.14 封面（按招标文件封面模板自适应）

- 封面字段顺序**从招标文件封面模板（`template.cover_lines`）提取**：`_cover_field_order` 按字段标签（`第_包` / `项目名称：` / `项目编号：` / `投标人：` / `年 月 日`）在封面模板中出现的顺序排列；字段标签必须带冒号，避免误匹配说明文字（如"投标人提供投标文件…"）。
- 标题"投标文件"大字居中；各字段行居中；`【第_包】` 用模板原文（如 `【第_包】（如不分包，请删去本行）`，`_cover_package_text`）；名称/编号/投标人填采集值；日期填 `supplier.date`（模板无日期标签时在末尾补）。

## 5. 兼容性与权衡

- **锁 PyMuPDF==1.24.14**：新版 `Rect.get_area` 移除导致 pdf2docx 崩溃（见 research）。写入 `requirements.txt`。
- **PDF→DOCX 双路径**：招标 Word 产物走 pdf2docx（保排版）；投标文件生成走 PyMuPDF 直读文本+表格（更可控、更快）。避免把 pdf2docx 的脏样式带进投标文件。
- **排除 LibreOffice**：实测 `writer_pdf_import` 导出 docx 会把内容散成数万文本框、丢失约 95% 文本、0 表格，质量远差于 pdf2docx，不采用（详见 `research/tech-feasibility.md`）。
- **不接入 LLM**：承诺函正文用招标文件原文模板，字段规则填充。
- **虚拟环境**：统一使用项目内 `.venv`（`python3 -m venv .venv`），依赖装在其内；`.venv/` 写入 `.gitignore`；一律以 `.venv/bin/python` 运行，不污染系统环境。

## 6. 风险与回滚

| 风险 | 缓解 |
|------|------|
| 不同招标文件章节命名不一致 | 关键词降级匹配 + 告警；AC9 覆盖 |
| 表格跨页/合并单元格解析错位 | 近似重建 + 单元测试；不阻塞主流程 |
| PyMuPDF/pdf2docx 版本漂移 | requirements.txt 精确锁版本 |
| python-docx 编号 XML 注入失败 | 提供降级：退化为硬编码"一、二、"编号并告警 |

无既有代码，无迁移成本；回滚 = 删除 `bidgen/` 目录。
