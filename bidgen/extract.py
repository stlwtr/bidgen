"""Extract key fields and business / technical tables from the tender document."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .pdf_reader import Line, Table

_PROJECT_NAME_RE = re.compile(r"项目名称\s*[：:]\s*(\S.*)")
_PROJECT_CODE_RE = re.compile(r"项目编号\s*[：:]\s*(\S.*)")
_PURCHASER_RE = re.compile(r"采\s*购\s*人\s*[：:]\s*(\S.*)")
_AGENCY_RE = re.compile(r"采购代理机构\s*[：:]\s*(\S.*)")
_NAME_RE = re.compile(r"名\s*称\s*[：:]\s*(\S.*)")


@dataclass
class Section:
    """A group of matching tables lifted from the tender (one entry per table)."""

    title: str
    tables: List[List[List[str]]] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.tables


def extract_fields(lines: List[Line]) -> Dict[str, Optional[str]]:
    """Best-effort extraction of purchaser / agency / project name / code."""
    fields: Dict[str, Optional[str]] = {
        "project_name": None,
        "project_code": None,
        "purchaser": None,
        "agency": None,
    }
    text_lines = [ln.text.strip() for ln in lines]

    for i, text in enumerate(text_lines):
        if fields["project_name"] is None:
            m = _PROJECT_NAME_RE.search(text)
            if m:
                fields["project_name"] = m.group(1).strip()
        if fields["project_code"] is None:
            m = _PROJECT_CODE_RE.search(text)
            if m:
                fields["project_code"] = m.group(1).strip()
        if fields["purchaser"] is None:
            m = _PURCHASER_RE.search(text)
            if m and "信息" not in text[:6]:
                fields["purchaser"] = m.group(1).strip()
        if fields["agency"] is None:
            m = _AGENCY_RE.search(text)
            if m and "信息" not in text[:8]:
                fields["agency"] = m.group(1).strip()

        if fields["purchaser"] is None and "采购人信息" in text:
            found = _next_name(text_lines, i)
            if found:
                fields["purchaser"] = found
        if fields["agency"] is None and "采购代理机构信息" in text:
            found = _next_name(text_lines, i)
            if found:
                fields["agency"] = found

    return fields


def _next_name(lines: List[str], start: int, window: int = 6) -> Optional[str]:
    for text in lines[start + 1:start + 1 + window]:
        m = _NAME_RE.search(text)
        if m:
            return m.group(1).strip()
    return None


def _header_key(table: Table) -> tuple:
    return tuple((c or "").replace("\n", "").strip() for c in (table.rows[0] if table.rows else []))


def _header(table: Table) -> str:
    return " ".join(_header_key(table))


_HEADER_TOKENS = ("序号", "名称", "概况", "类型", "参数", "评审点", "评审内容",
                  "要求概况", "标的", "品目")


def _is_continuation(table: Table, group: dict) -> bool:
    """A page that continues a table whose header only appears on the first page."""
    if not table.rows:
        return False
    if len(table.rows[0]) != group["cols"]:
        return False
    if table.page not in (group["page"], group["page"] + 1):
        return False
    first = (table.rows[0][0] or "").strip()
    if first.isdigit():
        return True
    row0 = [(c or "").strip() for c in table.rows[0]]
    if sum(1 for c in row0 if c) < 2:
        return False
    # A continuation row may start with a label (e.g. "商务评审") instead of a
    # digit or a blank; treat anything that is not a known header as data.
    return not any(token in row0[0] for token in _HEADER_TOKENS)


def _collect(tables: List[Table], predicate) -> List[List[List[str]]]:
    """Group matching tables, merging header-less continuation pages."""
    groups: List[dict] = []
    for table in tables:
        if not table.rows:
            continue
        key = _header_key(table)
        if predicate(" ".join(key)):
            if (
                groups
                and groups[-1]["key"] == key
                and table.page in (groups[-1]["page"], groups[-1]["page"] + 1)
            ):
                groups[-1]["rows"].extend(table.rows[1:])
                groups[-1]["page"] = table.page
            else:
                groups.append({"key": key, "cols": len(key), "page": table.page, "rows": list(table.rows)})
        elif groups and _is_continuation(table, groups[-1]):
            groups[-1]["rows"].extend(table.rows)
            groups[-1]["page"] = table.page
    return [g["rows"] for g in groups]


def extract_qualification(tables: List[Table]) -> Section:
    return Section("资格审查", _collect(tables, lambda h: "资格审查要求概况" in h))


def extract_compliance(tables: List[Table]) -> Section:
    return Section("符合性审查", _collect(tables, lambda h: "符合审查要求概况" in h))


def extract_scoring(tables: List[Table]) -> Section:
    return Section("综合评分", _collect(tables, lambda h: "评审内容" in h and "评审标准" in h))


def split_scoring(section: Section) -> Tuple["Section", "Section"]:
    """Split 综合评分表 into 技术评审 (top) and 商务/价格评审 (bottom marker rows)."""
    tech_tables: List[List[List[str]]] = []
    biz_tables: List[List[List[str]]] = []
    for rows in section.tables:
        if not rows:
            continue
        split = None
        for i, row in enumerate(rows):
            if row and (row[0] or "").strip() in ("商务评审", "价格评审"):
                split = i
                break
        if split is None:
            tech_tables.append(rows)
        else:
            tech_tables.append(rows[:split])
            biz_tables.append([rows[0]] + rows[split:])
    return Section("技术评审", tech_tables), Section("商务评审", biz_tables)


def extract_purchase_items(tables: List[Table]) -> Section:
    return Section("采购标的", _collect(tables, lambda h: "标的名称" in h and "品目名称" in h))


def extract_tech_requirements(tables: List[Table]) -> Section:
    return Section("技术要求", _collect(tables, lambda h: "参数性质" in h or "具体技术" in h))
