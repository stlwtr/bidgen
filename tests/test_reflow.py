import glob

import pytest

from bidgen import pdf_reader, reflow
from bidgen.pdf_reader import Line

_DOCS = sorted(glob.glob("docs/*.pdf"))


def _L(page, x0, x1, text):
    return Line(page, x0, x1, 0.0, 0.0, text)


def _fillers(n=20):
    # Full-width filler paragraphs (each ends a sentence) give the column right
    # bound a stable value without merging into the lines under test.
    return [_L(1, 50, 550, "填充行内容。") for _ in range(n)]


def test_wrapped_line_is_merged():
    lines = [
        _L(1, 50, 550, "第一部分内容被折行了"),
        _L(1, 50, 260, "接上一行的续写。"),
    ] + _fillers()
    paras = reflow.rebuild(lines)
    assert "第一部分内容被折行了接上一行的续写。" in paras


def test_short_previous_line_starts_new_paragraph():
    lines = [
        _L(1, 50, 200, "一个短行。"),
        _L(1, 50, 550, "另一个段落开始。"),
    ] + _fillers()
    paras = reflow.rebuild(lines)
    assert "一个短行。" in paras
    assert "另一个段落开始。" in paras


def test_clause_marker_starts_new_paragraph():
    lines = [
        _L(1, 50, 550, "上一段结束于句号。"),
        _L(1, 50, 550, "12.1这是一条新条款"),
    ] + _fillers()
    paras = reflow.rebuild(lines)
    assert any(p.startswith("12.1") for p in paras)
    assert "上一段结束于句号。" in paras


def test_footer_is_dropped():
    lines = [
        _L(1, 50, 550, "正文第一行。"),
        _L(1, 40, 120, "-第1页-"),
        _L(2, 50, 550, "正文第二行。"),
    ] + _fillers()
    paras = reflow.rebuild(lines)
    assert all("第1页" not in p for p in paras)


def test_ascii_words_joined_with_space():
    lines = [
        _L(1, 50, 550, "Specification Detail"),
        _L(1, 50, 300, "Sheet。"),
    ] + _fillers()
    paras = reflow.rebuild(lines)
    assert any(p.startswith("Specification Detail Sheet") for p in paras)


def test_split_token_is_merged_without_space():
    # A numeric token ("141") split across lines — and even across columns —
    # must be rejoined without inserting a space.
    lines = [
        _L(1, 460, 530, "（财库〔2017〕1"),
        _L(1, 33, 546, "41 号）的规定"),
    ] + _fillers()
    paras = reflow.rebuild(lines)
    assert any(p.startswith("（财库〔2017〕141 号）的规定") for p in paras)


@pytest.mark.skipif(not _DOCS, reason="tender PDF not present under docs/")
def test_real_pdf_reflow_merges_wrapped_clauses():
    paras = reflow.rebuild(pdf_reader.read_lines(_DOCS[0]))

    p121 = next((p for p in paras if p.startswith("12.1")), None)
    assert p121 is not None and "拆分投标" in p121 and "投标无效。" in p121

    p141 = next((p for p in paras if p.startswith("14.1")), None)
    assert p141 is not None and "暂行办法" in p141  # merged across pages

    # A line wrapping right after "（请" must be merged back.
    ptype = next((p for p in paras if "类型为" in p), None)
    assert ptype is not None and "据实在所属类型前" in ptype

    # A document number split across lines must be rejoined ("〔2017〕141 号").
    assert not any(p.rstrip().endswith("〕1") for p in paras)
    assert any("财库〔2017〕141" in p for p in paras)
