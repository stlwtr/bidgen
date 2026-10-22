# 投标文件生成助手 (bidgen)

将政府采购**招标文件 PDF** 自动转换为结构规范、内容预填的**投标文件 Word 初稿**，并额外产出招标文件 Word。

## 功能

- 招标文件 PDF → Word（自动修复 PDF 文本层的异体字形乱码）
- 从「投标文件格式与要求」章提取封面、目录与格式一~格式十六模板，重建投标文件骨架
- 采集 **采购人 / 采购代理机构 / 项目名称 / 项目编号**，自动填入各承诺函
- 编入第四章**资格审查项**、第五章**符合性审查项 / 评分项**（商务部分）
- 生成**技术偏离表**骨架（按第三章采购标的），并附第三章技术要求供参考
- 一级标题 Word 原生自动编号、页眉页脚页码、目录域（TOC）
- 生成后清理文档**机器码 / 用户信息**（`rsids`、`python-docx` 等痕迹）

## 环境

Python 3.9+。依赖见 `requirements.txt`（已锁定 `PyMuPDF==1.24.14`，兼容 pdf2docx）。

## 安装

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 使用

```bash
# 图形界面（非技术人员推荐）：选择招标 PDF、填供应商信息、点生成
.venv/bin/python -m bidgen gui
```

## 打包可执行文件（Win / Linux / macOS，供非技术人员双击运行）

界面基于 PySide6，代码天然跨平台。要生成各平台**原生可执行文件**（无需装 Python），用 PyInstaller 在**对应平台**上分别打包（PyInstaller 不能跨平台打包）：

```bash
pip install -r requirements.txt pyinstaller

# Windows：python scripts/build_app.py   → dist/BidgenGUI.exe
# Linux：  python3 scripts/build_app.py  → dist/BidgenGUI
# macOS：  python3 scripts/build_app.py  → dist/BidgenGUI.app
```

```bash
# 1) 仅把招标文件 PDF 转为 Word
.venv/bin/python -m bidgen convert "docs/招标文件.pdf" -o 招标文件.docx

# 2) 生成投标文件初稿
.venv/bin/python -m bidgen generate "docs/招标文件.pdf" --supplier examples/supplier.yaml -o 投标文件.docx

# 3) 一次产出两个文件
.venv/bin/python -m bidgen all "docs/招标文件.pdf" --supplier examples/supplier.yaml --out-dir out

# 4) 清理已有 Word 的机器码 / 用户信息
.venv/bin/python -m bidgen sanitize 投标文件.docx
```

通用选项：`--no-sanitize` 关闭元数据清理（默认开启）。

## 供应商配置

复制 `examples/supplier.yaml` 并按实际填写。未填写的字段在 Word 中以 `______` 占位，不会报错。

| 字段 | 说明 |
|------|------|
| `company_name` | 投标人（公司全称） |
| `company_type` | 企业 / 事业单位 / 社会团体 / … |
| `legal_representative` | 法定代表人（单位负责人） |
| `address` / `postal_code` / `phone` / `email` | 联系方式 |
| `bank_name` / `bank_account` | 开户银行 / 账号 |
| `authorized_representative`(_id) | 委托代理人（及身份证号） |
| `date` | 日期，留空以 `______` 占位 |

## 产物说明

- **招标文件.docx**：pdf2docx 转换 + 乱码修复。
- **投标文件.docx**：封面（独立分节，无页眉页脚）+ 目录（TOC 域）+ 16 个格式章节（一级标题自动编号）+ 商务 / 技术内容。

> 打开 `投标文件.docx` 后，请在目录处按 **F9**（或右键「更新域」）生成目录页码。

## 已知限制

- PDF→Word **不保留图片**；125 页全量转换约 7 分钟。
- 技术偏离表的「招标技术要求」列由供应商参照文末「第三章 技术要求」填写。
- 需供应商提供的章节（项目实施方案、各类证明材料等）留占位提示。

## 开发

```bash
.venv/bin/python -m pytest -q
```
