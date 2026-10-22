# 实施计划 (bid-doc-generator)

> 平台为 inline 模式（湛卢/Kilo），Phase 2 通过 `trellis-before-dev` 加载上下文，无需 JSONL 清单。

## 有序实现清单

1. **脚手架**
   - [ ] 项目内 `.venv` 虚拟环境（已创建）：`.venv/bin/pip install -r requirements.txt`
   - [ ] `requirements.txt`（`PyMuPDF==1.24.14`、`pdf2docx==0.5.8`、`python-docx`、`PyYAML`、`pytest`）
   - [ ] `.gitignore` 忽略 `.venv/`
   - [ ] 建 `bidgen/__init__.py`
   - [ ] `examples/supplier.yaml` 示例配置（字段全注释）
   - [ ] `README.md`（安装 + 三条例行命令）
2. **文本清洗（textfix + punctuation）**（无外部依赖，先做）
   - [ ] `textfix.fix()`：NFKC + `RADICAL_FIX` 映射表（U+2E80–U+2EFF）
   - [ ] `punctuation.normalize()`：中文语境半角→全角，数字/英文/公式语境保留（design §4.9）
   - [ ] 单测：`⼈→人`、`⻰→龙`；`金额3,649,020.00元,共100台.`→`金额3,649,020.00元，共100台。`；`16:10`/`8dB(A)`/`(Cr)≤20`/英文句子不变
3. **pdf_reader**
   - [ ] `read_pages(path) -> list[str]`（逐页文本，出口统一 `textfix.fix`）
   - [ ] `read_tables(path) -> list[list[list[str]]]`（`page.find_tables()`）
   - [ ] `read_lines(path) -> list[{x0,x1,text,page}]`（行级 bbox，供 reflow）
   - [ ] **reflow `rebuild(lines)`（关键）**：剔页眉页脚 → 按 x0 列聚类 → 编号/满行/跨页判定 → 折行合并
   - [ ] reflow 单测：`12.1`/`14.1` 恢复整段；页脚 `-第N页-` 剔除；书名号跨行正确拼接
4. **pdf_to_docx**
   - [ ] `convert(pdf, docx_path)` 封装 pdf2docx
5. **structure**
   - [ ] `find_format_chapter(doc)`：TOC 优先，正则兜底
   - [ ] `parse_formats(texts) -> dict[编号 → {title, body}]`
   - [ ] `parse_toc(texts) -> list[str]`（16 项）
   - [ ] 单测：用 docs PDF 断言命中 16 项与格式一~九标题
6. **extract**
   - [ ] `extract_fields()`：采购人 / 代理机构 / 项目名称 / 项目编号
   - [ ] `extract_qualification()`：第四章资格审查项
   - [ ] `extract_scoring()`：第五章符合性审查表 + 综合评分表
   - [ ] `extract_purchase_items()`：第三章采购标的 + 技术要求
   - [ ] 单测：字段断言（含代理机构名、项目编号）
7. **config**
   - [ ] `load_supplier(path)`，缺字段返回 `None` 占位
8. **docx_builder**
   - [ ] `style.py` 定义 `StyleSpec`（字体/字号/行距/缩进/页边距，默认见 design §4.8）
   - [ ] 页面与样式基座（中文字体 `w:eastAsia`、首行缩进 2 字符、行距 1.5）
   - [ ] 一级标题自动编号（numbering.xml 注入 + Heading 1 绑定，失败降级）
   - [ ] 页眉 / 页脚 + 页码域
   - [ ] 封面、目录、章节骨架
   - [ ] 表格渲染（采购标的一览表、评分表、偏离表）
   - [ ] 承诺函填充（格式一/二/五…）
   - [ ] 商务部分（资格申请 / 符合审查 / 评分项）
   - [ ] 技术部分（偏离表骨架 + 实施方案占位）
9. **sanitize**
   - [ ] `sanitize_docx(path)`：清 core/app 元数据、删 `w:rsids` 与 `w:rsid*` 属性、去 custom/people/comments（design §4.10）
   - [ ] 单测：清理后无 `python-docx` / `Microsoft` / `rsid` 残留，且文档可被 python-docx 打开
10. **cli**
   - [ ] `convert` / `generate` / `all` 三子命令编排，退出码与错误可读
11. **端到端验证**
    - [ ] 跑 `all`，人工核对 AC1–AC14

## 验证命令

```bash
# 依赖
.venv/bin/pip install -r requirements.txt

# 单元测试
.venv/bin/python -m pytest -q

# 仅转换招标文件
.venv/bin/python -m bidgen convert "docs/2026年饶河县中考考点基本办学条件改善项目招标文件（[230524]YRZB[GK]2026000120260730001）.pdf" -o /tmp/tender.docx

# 端到端
.venv/bin/python -m bidgen all "docs/2026年饶河县中考考点基本办学条件改善项目招标文件（[230524]YRZB[GK]2026000120260730001）.pdf" --supplier examples/supplier.yaml --out-dir /tmp/out
```

## 风险文件 / 回滚点

- `bidgen/docx_builder.py` —— 最复杂：编号 XML、页眉页脚域、表格。若编号注入不稳，走硬编码降级路径。
- `bidgen/structure.py` —— 章节定位对模板差异最敏感，需以 docs PDF 为回归 fixture。
- 依赖版本锁定在 `requirements.txt`，勿随意升级 PyMuPDF。
- 新项目无既有代码：回滚 = 删除 `bidgen/` + `tests/` + `requirements.txt`（`.venv/` 为本地环境，可保留）。

## 提交前检查

- [ ] `.venv/bin/python -m pytest -q` 全绿
- [ ] 对 docs PDF 端到端产出两个 docx，AC1–AC14 逐条核对
- [ ] README 命令可直接复制运行
