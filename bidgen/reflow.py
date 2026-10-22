"""Rebuild semantic paragraphs from visual PDF lines.

A PDF line is a physical layout line, not a paragraph, so writing lines directly
into Word would explode every wrapped clause into its own paragraph.  This
module groups visual lines back into paragraphs:

* drop running headers / footers (e.g. ``-第8页-``)
* cluster lines into text columns by their left edge and compute a per-column
  right bound
* start a new paragraph when a line begins with a clause marker, jumps to
  another column, or follows a line that ended a sentence / was not full
* otherwise merge the line into the current paragraph (Chinese joins without a
  space; ASCII word boundaries get one space), including across page breaks

See design.md §4.7.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Sequence

from .pdf_reader import Line

_FOOTER_RE = re.compile(r"^\s*[-—]?\s*第\s*\d+\s*[页⻚]\s*[-—]?\s*$")
_PAGE_NUM_RE = re.compile(r"^\s*\d{1,3}\s*$")

_CLAUSE_RE = re.compile(
    r"^\s*(?:"
    r"\d+(?:\.\d+)+"                       # 1.2 / 12.1
    r"|\d+[.、](?=\D|$)"                   # 1. 说明 (not 3.5)
    r"|[（(]\d+[）)]"                       # （1）
    r"|[（(][一二三四五六七八九十]+[）)]"     # （一）
    r"|[一二三四五六七八九十]+[、.]"          # 一、
    r"|第[一二三四五六七八九十百]+[章节条]"    # 第三章
    r"|格式[一二三四五六七八九十]+"            # 格式一
    r"|[★☆▲●◆]"                            # bullets
    r")"
)

_SENTENCE_END = ("。", "！", "？", "；", "…")

_COLUMN_WIDTH = 40.0      # bucket width for clustering by left edge
_COLUMN_JUMP = 40.0       # x0 delta that counts as a different column
_FULL_EPS = 14.0          # tolerance under the column right bound


def _is_footer(text: str) -> bool:
    return bool(_FOOTER_RE.match(text) or _PAGE_NUM_RE.match(text))


def _column_key(x0: float) -> int:
    return int(round(x0 / _COLUMN_WIDTH))


def _is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return 0x3000 <= cp <= 0x303F or 0x4E00 <= cp <= 0x9FFF or 0xFF00 <= cp <= 0xFFEF


def _ascii_word_boundary(left: str, right: str) -> bool:
    """Only a letter-to-letter wrap gets a space (English words); digits never do."""
    return (
        bool(left)
        and bool(right)
        and left.isascii()
        and right.isascii()
        and left.isalpha()
        and right.isalpha()
    )


def _continues_token(prev_text: str, cur_text: str) -> bool:
    """True when a Latin/numeric token (e.g. "141") was split across two lines."""
    prev_char = prev_text.rstrip()[-1:] if prev_text and prev_text.strip() else ""
    cur_char = cur_text.lstrip()[:1] if cur_text else ""
    return (
        bool(prev_char)
        and bool(cur_char)
        and prev_char.isascii()
        and prev_char.isalnum()
        and cur_char.isascii()
        and cur_char.isalnum()
    )


def _join(current: str, nxt: str) -> str:
    if _ascii_word_boundary(current[-1], nxt[0]):
        return current + " " + nxt
    return current + nxt


def _column_right_bounds(lines: Sequence[Line]) -> Dict[int, float]:
    """Per-column right bound = high percentile of x1 within that column."""
    buckets: Dict[int, List[float]] = {}
    for ln in lines:
        buckets.setdefault(_column_key(ln.x0), []).append(ln.x1)
    bounds: Dict[int, float] = {}
    for key, xs in buckets.items():
        xs.sort()
        # 80th percentile: robust against the few over-wide lines (headers,
        # table fragments) that would otherwise inflate the bound and make real
        # full-width lines look "short".
        idx = min(len(xs) - 1, int(0.8 * (len(xs) - 1)))
        bounds[key] = xs[idx]
    return bounds


def _starts_new(prev: Line, cur: Line, right_bounds: Dict[int, float]) -> bool:
    if _CLAUSE_RE.match(cur.text):                # clause / list marker
        return True
    if _continues_token(prev.text, cur.text):     # a split token (e.g. "141") → merge
        return False
    prev_right = right_bounds.get(_column_key(prev.x0), prev.x1)
    if abs(cur.x0 - prev.x0) > _COLUMN_JUMP:      # jumped to another column
        return True
    if prev.text and prev.text.rstrip()[-1:] in _SENTENCE_END:
        return True
    if prev.x1 < prev_right - _FULL_EPS:          # previous line was not full
        return True
    return False


@dataclass
class Paragraph:
    """A rebuilt paragraph with its extent and page span in the PDF."""

    text: str
    x0: float
    x1: float
    page_start: int = 0
    page_end: int = 0
    bold: bool = False
    y0: float = 0.0


def rebuild_paras(lines: Sequence[Line]) -> List[Paragraph]:
    """Group visual *lines* into paragraphs, keeping each paragraph's x extent."""
    body = [ln for ln in lines
            if ln.text.strip() and not _is_footer(ln.text) and not ln.in_table]
    if not body:
        return []
    right_bounds = _column_right_bounds(body)

    paragraphs: List[Paragraph] = []
    prev: Line | None = None
    for cur in body:
        if prev is None or _starts_new(prev, cur, right_bounds):
            paragraphs.append(Paragraph(cur.text.strip(), cur.x0, cur.x1,
                                        cur.page, cur.page, cur.bold, cur.y0))
        else:
            last = paragraphs[-1]
            last.text = _join(last.text, cur.text.strip())
            last.x1 = max(last.x1, cur.x1)
            last.page_end = cur.page
        prev = cur
    return paragraphs


# A page whose whole text fits under this many characters *and* that no
# paragraph crosses is treated as a self-contained ("own") page — e.g. a tender's
# "附件 1：…" sheet that should keep its own page in the generated bid document.
_OWN_PAGE_MAX_CHARS = 700


def independent_pages(paras: Sequence[Paragraph], max_chars: int = _OWN_PAGE_MAX_CHARS) -> set:
    """Return page numbers that are occupied solely by a small, closed block."""
    if not paras:
        return set()
    pages = set()
    for p in paras:
        pages.update(range(p.page_start, p.page_end + 1))

    independent = set()
    for page in pages:
        crossing = any(
            (p.page_start < page <= p.page_end) or (p.page_start <= page < p.page_end)
            for p in paras
        )
        if crossing:
            continue
        contained = [p for p in paras if p.page_start == page and p.page_end == page]
        if contained and sum(len(p.text) for p in contained) < max_chars:
            independent.add(page)
    return independent


def rebuild(lines: Sequence[Line]) -> List[str]:
    """Group visual *lines* into a list of paragraph strings."""
    return [p.text for p in rebuild_paras(lines)]
