# docs/

把招标文件 PDF 放到本目录（例如 `招标文件1.pdf`、`招标文件2.pdf`）。

**本目录下的 PDF 已被 `.gitignore` 忽略，不会提交到代码库**（招标文件可能含敏感/非公开信息或受版权限制，请勿提交入库）。

- CLI 与 GUI 的「选择招标文件」指向本目录下的 PDF。
- 单元测试（`tests/test_reflow.py`、`tests/test_structure.py`）以本目录 PDF 为 fixture；PDF 不存在时相关测试自动跳过（`skipif`）。
