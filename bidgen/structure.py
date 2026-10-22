"""Locate the '投标文件格式与要求' chapter and parse its TOC and format templates."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from .pdf_reader import Table
from .reflow import Paragraph, independent_pages

_CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十]+章\s*投标文件(的)?格式")
_TOC_RE = re.compile(r"^[一二三四五六七八九十]+[、.]\s*\S")
_FORMAT_RE = re.compile(r"^格式([一二三四五六七八九十]+)\s*[：:]")

_CN_DIGITS = "零一二三四五六七八九"

# Horizontal-alignment detection tolerances (PDF points).
_RIGHT_TOL = 12.0
_CENTER_TOL = 15.0
_INDENT_TOL = 40.0


def cn_to_int(text: str) -> int:
    """Convert a short Chinese numeral (一..二十, 十六, ...) to an int."""
    if not text:
        return 0
    if text == "十":
        return 10
    if text.startswith("十"):
        return 10 + _CN_DIGITS.index(text[1])
    if "十" in text:
        left, right = text.split("十", 1)
        return _CN_DIGITS.index(left) * 10 + (_CN_DIGITS.index(right) if right else 0)
    return _CN_DIGITS.index(text)


@dataclass
class BodyLine:
    """A template body line with its detected alignment and source position."""

    text: str
    align: str = "left"  # left | center | right
    own_page: bool = False  # belongs to a page that holds only this small block
    page: int = 0
    bold: bool = False
    top: float = 0.0  # y of the line's first row, for placing tables in order


@dataclass
class Format:
    """A single '格式X' template inside the format chapter."""

    number: int
    label: str
    title: str
    body: List[BodyLine] = field(default_factory=list)
    start_page: int = 0
    tables: List[List[List[str]]] = field(default_factory=list)
    table_spans: List[Tuple[int, float]] = field(default_factory=list)


@dataclass
class BidTemplate:
    chapter_index: Optional[int]
    cover_lines: List[str]
    toc_items: List[str]
    formats: List[Format]

    def format_for(self, position: int) -> Optional[Format]:
        """Return the format template for the 1-based TOC position."""
        return next((f for f in self.formats if f.number == position), None)


def find_format_chapter(paras: List[Paragraph]) -> Optional[int]:
    """Index of the format chapter in *paras* (last match, i.e. body not TOC)."""
    hits = [i for i, p in enumerate(paras) if _CHAPTER_RE.match(p.text.strip())]
    if not hits:
        hits = [i for i, p in enumerate(paras) if "投标文件格式" in p.text]
    return hits[-1] if hits else None


def _classify(paragraph: Paragraph, left: float, right: float) -> str:
    """Infer a paragraph's alignment from its horizontal extent in the PDF."""
    x0, x1 = paragraph.x0, paragraph.x1
    if x1 >= right - _RIGHT_TOL and x0 > left + _INDENT_TOL:
        return "right"
    if x0 > left + _INDENT_TOL and abs((x0 - left) - (right - x1)) <= _CENTER_TOL:
        return "center"
    return "left"


def _parse_formats(paras: List[Paragraph], left: float, right: float, own_pages: set) -> List[Format]:
    formats: List[Format] = []
    cur: Optional[Format] = None
    for paragraph in paras:
        text = paragraph.text.strip()
        match = _FORMAT_RE.match(text)
        if match:
            if cur is not None:
                formats.append(cur)
            cur = Format(number=cn_to_int(match.group(1)), label=match.group(1), title="",
                         start_page=paragraph.page_start)
            continue
        if cur is None:
            continue
        if not cur.title and text:
            cur.title = text
        else:
            own_page = (
                paragraph.page_start == paragraph.page_end
                and paragraph.page_start in own_pages
            )
            cur.body.append(BodyLine(text, _classify(paragraph, left, right), own_page,
                                     paragraph.page_start, paragraph.bold, paragraph.y0))
    if cur is not None:
        formats.append(cur)
    return formats


def _assign_tables(formats: List[Format], tables: Sequence[Table]) -> None:
    """Attach each PDF table to the format whose title page precedes it."""
    if not formats:
        return
    for table in tables:
        target: Optional[Format] = None
        for fmt in formats:
            if not fmt.start_page:
                continue
            if fmt.start_page <= table.page:
                target = fmt
            else:
                break
        if target is not None and table.rows:
            target.tables.append(table.rows)
            target.table_spans.append((table.page, table.bbox[1] if table.bbox else 0.0))


def build_template(paras: List[Paragraph], tables: Sequence[Table] = ()) -> BidTemplate:
    """Parse the bid-document template (cover / TOC / formats) from paragraphs."""
    chapter = find_format_chapter(paras)
    if chapter is None:
        return BidTemplate(None, [], [], [])

    seg = paras[chapter + 1:]  # drop the chapter title line itself
    toc_start = next((i for i, p in enumerate(seg) if "投标文件目录" in p.text), None)

    if toc_start is None:
        return BidTemplate(chapter, [p.text for p in seg], [], [])

    cover = [p.text for p in seg[:toc_start]]
    fmt_start = next(
        (i for i, p in enumerate(seg[toc_start + 1:], start=toc_start + 1)
         if _FORMAT_RE.match(p.text.strip())),
        len(seg),
    )
    toc_items = [p.text.strip() for p in seg[toc_start + 1:fmt_start] if _TOC_RE.match(p.text.strip())]

    left = min((p.x0 for p in paras), default=0.0)
    right = max((p.x1 for p in paras), default=0.0)
    own_pages = independent_pages(paras)
    formats = _parse_formats(seg[fmt_start:], left, right, own_pages)
    _assign_tables(formats, tables)
    return BidTemplate(chapter, cover, toc_items, formats)
