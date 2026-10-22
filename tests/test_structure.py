import glob

import pytest

from bidgen import pdf_reader, reflow, structure

_DOCS = sorted(glob.glob("docs/*.pdf"))


def test_cn_to_int():
    assert structure.cn_to_int("一") == 1
    assert structure.cn_to_int("九") == 9
    assert structure.cn_to_int("十") == 10
    assert structure.cn_to_int("十六") == 16
    assert structure.cn_to_int("二十") == 20


@pytest.mark.skipif(not _DOCS, reason="tender PDF not present under docs/")
def test_real_pdf_template():
    paras = reflow.rebuild_paras(pdf_reader.read_lines(_DOCS[0]))
    template = structure.build_template(paras)

    assert template.chapter_index is not None
    assert len(template.toc_items) == 16
    assert template.toc_items[0].startswith("一、")
    assert template.toc_items[-1].startswith("十六、")

    numbers = {f.number for f in template.formats}
    assert 1 in numbers and 16 in numbers
    assert template.format_for(1) is not None


@pytest.mark.skipif(not _DOCS, reason="tender PDF not present under docs/")
def test_real_pdf_format_tables_attached():
    from bidgen import pdf_reader

    tables = pdf_reader.read_tables(_DOCS[0])
    paras = reflow.rebuild_paras(pdf_reader.read_lines(_DOCS[0], tables))

    # Table-cell text must not leak into the flowing body.
    assert not any("品目号" in p.text for p in paras)

    # A line wrapping right after "（请" must be merged back (production path:
    # lines are read together with the table regions).
    assert any("自然人(请" in p.text and "勾选一项" in p.text for p in paras)

    template = structure.build_template(paras, tables)

    def header_text(rows):
        return " ".join("".join(cell or "" for cell in row) for row in rows[:1])

    fmt4 = template.format_for(4)  # 分项报价明细表
    assert fmt4 is not None and any("品目号" in header_text(tb) for tb in fmt4.tables)

    fmt8 = template.format_for(8)  # 优先采购节能和环境标志产品明细表
    assert fmt8 is not None and any("认证证书编号" in header_text(tb) for tb in fmt8.tables)


@pytest.mark.skipif(not _DOCS, reason="tender PDF not present under docs/")
def test_real_pdf_bold_lines_detected():
    from bidgen import pdf_reader

    tables = pdf_reader.read_tables(_DOCS[0])
    paras = reflow.rebuild_paras(pdf_reader.read_lines(_DOCS[0], tables))

    # note: textfix (NFKC) has already folded "（二）" to "(二)" at this stage
    bold = next((p for p in paras if p.text.strip().startswith("(二)分包意向协议")), None)
    assert bold is not None and bold.bold

    # plain body text must remain non-bold
    assert any(not p.bold for p in paras if len(p.text) > 20)


@pytest.mark.skipif(not _DOCS, reason="tender PDF not present under docs/")
def test_real_pdf_fields_and_tables():
    from bidgen import extract

    lines = pdf_reader.read_lines(_DOCS[0])
    fields = extract.extract_fields(lines)
    assert fields["project_code"] == "[230524]YRZB[GK]20260001"
    assert fields["project_name"] and "饶河县" in fields["project_name"]
    assert fields["purchaser"] == "饶河县教育和体育局"
    assert fields["agency"] == "黑龙江省毅润项目管理有限公司"

    tables = pdf_reader.read_tables(_DOCS[0])
    assert not extract.extract_qualification(tables).is_empty()
    assert not extract.extract_compliance(tables).is_empty()
    assert not extract.extract_scoring(tables).is_empty()
    assert not extract.extract_purchase_items(tables).is_empty()
