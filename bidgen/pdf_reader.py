"""Read text, line boxes and tables from a tender PDF using PyMuPDF.

All text passes through :func:`bidgen.textfix.fix` on the way out so that glyph
artifacts (Kangxi radicals / CJK radical supplements) are already repaired.
Lines that fall inside a detected table region are flagged with ``in_table`` so
callers can keep table text out of the flowing body.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import fitz  # PyMuPDF

from . import textfix

BBox = Tuple[float, float, float, float]


@dataclass
class Line:
    """A single visual text line with its bounding box."""

    page: int  # 1-based page number
    x0: float
    x1: float
    y0: float
    y1: float
    text: str
    in_table: bool = False
    bold: bool = False


@dataclass
class Table:
    """An extracted table (list of rows, each a list of cell strings)."""

    page: int
    rows: List[List[str]]
    bbox: Optional[BBox] = None


def _span_is_bold(span) -> bool:
    if "bold" in (span.get("font") or "").lower():
        return True
    return bool(span.get("flags", 0) & 16)  # bit 4 = bold


def _spans_are_bold(spans) -> bool:
    """A line counts as bold when most of its characters are bold."""
    total = sum(len(s.get("text", "")) for s in spans)
    if not total:
        return False
    bold = sum(len(s.get("text", "")) for s in spans if _span_is_bold(s))
    return bold / total >= 0.6


def _line_in_boxes(bbox: BBox, boxes: Sequence[BBox]) -> bool:
    if not boxes:
        return False
    x0, y0, x1, y1 = bbox
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    return any(b[0] <= cx <= b[2] and b[1] <= cy <= b[3] for b in boxes)


def read_lines(path: str, tables: Optional[List[Table]] = None) -> List[Line]:
    """Return every non-empty visual line, in reading order.

    When *tables* (from :func:`read_tables`) is supplied, lines that fall inside
    a table region are flagged ``in_table=True``; otherwise no table scanning is
    performed.
    """
    boxes_by_page: Dict[int, List[BBox]] = {}
    if tables:
        for table in tables:
            if table.bbox:
                boxes_by_page.setdefault(table.page, []).append(table.bbox)

    doc = fitz.open(path)
    try:
        lines: List[Line] = []
        for pno in range(doc.page_count):
            page = doc[pno]
            boxes = boxes_by_page.get(pno + 1, [])
            data = page.get_text("dict")
            for block in data.get("blocks", []):
                if block.get("type") != 0:  # 0 == text block
                    continue
                for ln in block.get("lines", []):
                    spans = ln.get("spans", [])
                    text = "".join(span.get("text", "") for span in spans)
                    text = textfix.fix(text)
                    if not text.strip():
                        continue
                    x0, y0, x1, y1 = ln["bbox"]
                    lines.append(Line(pno + 1, x0, x1, y0, y1, text,
                                      _line_in_boxes((x0, y0, x1, y1), boxes),
                                      _spans_are_bold(spans)))
        return lines
    finally:
        doc.close()


def read_pages(path: str) -> List[str]:
    """Return the raw (glyph-fixed) text of every page."""
    doc = fitz.open(path)
    try:
        return [textfix.fix(doc[pno].get_text()) for pno in range(doc.page_count)]
    finally:
        doc.close()


def read_tables(path: str) -> List[Table]:
    """Return every table detected by PyMuPDF across the document."""
    doc = fitz.open(path)
    try:
        tables: List[Table] = []
        for pno in range(doc.page_count):
            try:
                found = doc[pno].find_tables()
            except Exception:
                # Table detection is best-effort; never abort the whole run.
                continue
            for tbl in found.tables:
                try:
                    raw = tbl.extract()
                    bbox = tuple(tbl.bbox)
                except Exception:
                    continue
                rows = [[textfix.fix(cell or "") for cell in row] for row in raw]
                tables.append(Table(pno + 1, rows, bbox))
        return tables
    finally:
        doc.close()
