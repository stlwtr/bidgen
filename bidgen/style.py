"""Typography and page-layout specification for the generated bid document.

All values are centralised here so the whole look can be overridden in one
place. See design.md §4.8 for the rationale behind the defaults.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StyleSpec:
    # Fonts (Chinese / Latin)
    body_font: str = "宋体"
    heading_font: str = "黑体"
    latin_font: str = "Times New Roman"

    # Font sizes (pt)
    cover_title_size: int = 36     # 小初
    cover_info_size: int = 16      # 三号
    h1_size: int = 16              # 三号
    h2_size: int = 14              # 四号
    h3_size: int = 12              # 小四
    body_size: int = 12            # 小四
    table_size: float = 10.5       # 五号
    header_size: float = 10.5

    # Paragraph
    body_line_spacing: float = 1.5
    heading_line_spacing: float = 1.0
    first_line_indent_chars: int = 2

    # Page layout (cm)
    margin_top_cm: float = 2.54
    margin_bottom_cm: float = 2.54
    margin_left_cm: float = 3.17
    margin_right_cm: float = 3.17
    header_distance_cm: float = 1.5
    footer_distance_cm: float = 1.75

    # Header / footer text
    header_text: str = ""
