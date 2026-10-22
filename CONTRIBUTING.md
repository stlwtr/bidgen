# 贡献指南

## 提交信息规范（Conventional Commits · 中文版）

本项目采用 [Conventional Commits](https://www.conventionalcommits.org/) 的约定，
描述使用中文，代码 / 路径 / 标识符等保持原文。

### 格式

```
<type>(<scope>): <描述>

<body>

<footer>
```

- **type**（必填）：变更类型，见下表。
- **scope**（可选）：受影响模块，如 `fill`、`docx_builder`、`punctuation`、`reflow`、`cli`。
- **描述**（必填）：中文，动宾结构，一句话说清"做了什么"；≤ 50 字，结尾不加句号。
- **body**（可选）：空行后写"为什么 / 怎么做"，可多行。
- **footer**（可选）：空行后写破坏性变更或关联 issue，如 `BREAKING CHANGE: ...`、`Refs #12`。

### type 取值

| type | 含义 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复缺陷 |
| `docs` | 仅文档变更 |
| `refactor` | 重构（不改变外部行为） |
| `test` | 新增 / 修改测试 |
| `chore` | 构建、工具、依赖、杂项 |
| `perf` | 性能优化 |
| `style` | 格式调整（不影响逻辑） |

### 规则

- 一次提交只做一件事；不要把不相关的改动混在一个提交里。
- 描述用中文祈使语气（"修复…""新增…"），不用"修复了…"。
- 描述结尾不加句号；不用 emoji（除非团队另行约定）。
- 破坏性变更必须在 footer 用 `BREAKING CHANGE:` 说明。
- 提交前确保 `.venv/bin/python -m pytest -q` 与 `.venv/bin/ruff check --select F,E9 bidgen tests` 通过。

### 示例

```
feat(fill): 承诺函模板按通用规则填充采购人、项目名称与投标人

fix(punctuation): 数字后的半角点不再被误转为中文句号

fix(reflow): 列右界改用 80 分位，避免满行被误判而断行

docs: 补充 README 的安装与运行示例

chore: 忽略 .venv 与生成的 Word 产物
```

带 body 与 footer：

```
feat(docx_builder): 一级标题改为左对齐并在标题前分页

每个一级标题另起一页，便于装订与阅读。

Refs #7
```

## 提交模板

仓库根目录提供 `.gitmessage` 模板。启用方式（本地一次性配置）：

```bash
git config commit.template .gitmessage
```

启用后 `git commit` 会带出模板注释（以 `#` 开头的行不会被写入提交信息）。
