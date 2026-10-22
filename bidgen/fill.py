"""Fill standard blanks in commitment-letter templates with tender / supplier values.

The blanks come from the tender's own templates and vary in form (a trailing
blank after a label, an empty bracket, a gap in a sentence).  Rather than
hard-code one tender document, a small set of generic patterns is applied to
every template line; anything that does not match is left untouched.

Values that represent a filled-in entry (project name / code / bidder name) are
wrapped in private-use sentinels so the DOCX builder can render them underlined;
:func:`fill_line` strips the sentinels and :func:`split_markup` exposes them.
"""

from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional, Tuple

PLACEHOLDER = "______"

# Private-use sentinels for "render this span underlined".  Never written to the
# DOCX: split_markup()/fill_line() consume them first.
UL_START = "\uE000"
UL_END = "\uE001"

_UL_RE = re.compile(re.escape(UL_START) + r"(.*?)" + re.escape(UL_END), re.S)


def _ul(value: str) -> str:
    # 占位符用“空格 + 单下划线格式”呈现（Word 画一条单下划线），避免字面下划线
    # 字符与 underline 格式叠加成“双线/加粗”效果。
    if value == PLACEHOLDER:
        value = "      "
    return f"{UL_START}{value}{UL_END}"


def _pick(value: Optional[str]) -> str:
    return value if value not in (None, "") else PLACEHOLDER


def build_values(fields: Dict[str, Optional[str]], supplier: Dict[str, str]) -> Dict[str, str]:
    """Collect the values used by the fill rules (missing ones become placeholders)."""
    return {
        "purchaser": _pick(fields.get("purchaser")),
        "agency": _pick(fields.get("agency")),
        "project_name": _pick(fields.get("project_name")),
        "project_code": _pick(fields.get("project_code")),
        "company": _pick(supplier.get("company_name")),
        "address": _pick(supplier.get("address")),
        "postal_code": _pick(supplier.get("postal_code")),
        "phone": _pick(supplier.get("phone")),
        "email": _pick(supplier.get("email")),
        "bank_name": _pick(supplier.get("bank_name")),
        "bank_account": _pick(supplier.get("bank_account")),
        "date": _pick(supplier.get("date")),
    }


# Each rule: (pattern, replacement).  Ordered so labels are handled before the
# generic bracket rules.  Project name / code / bidder name are underlined.
_RULES: List[Tuple[re.Pattern, Callable[[Dict[str, str]], str]]] = [
    # 采购人、采购代理机构名称：____
    (
        re.compile(r"^采购人[、,]?采购代理机构名称\s*[：:].*$"),
        lambda v: f"采购人、采购代理机构名称：{v['purchaser']}、{v['agency']}",
    ),
    # （项目编号：____）  (value underlined)
    (
        re.compile(r"[（(]\s*项目编号\s*[：:]?\s*[）)]"),
        lambda v: f"（项目编号：{_ul(v['project_code'])}）",
    ),
    # （投标人名称：____） / （投标人名称）  (value underlined)
    (
        re.compile(r"[（(]\s*投标人名称\s*[：:]?\s*[）)]"),
        lambda v: f"（投标人名称：{_ul(v['company'])}）",
    ),
    # （项目名称）= 项目名称  (value underlined)
    (
        re.compile(r"[（(]\s*项目名称\s*[：:]?\s*[）)]"),
        lambda v: f"（{_ul(v['project_name'])}）",
    ),
    # （单位名称）= 采购人
    (
        re.compile(r"[（(]\s*单位名称\s*[：:]?\s*[）)]"),
        lambda v: f"（{v['purchaser']}）",
    ),
    # 按照已收到的 ____ 项目  (value underlined)
    (
        re.compile(r"已收到的\s*项目"),
        lambda v: f"已收到的{_ul(v['project_name'])}项目",
    ),
    # 详细地址：____  邮政编码：____  (tab-separated so it survives punctuation)
    (
        re.compile(r"详细地址\s*[：:]\s*_*\s*邮政编码\s*[：:]\s*_*"),
        lambda v: f"详细地址:{v['address']}\t邮政编码:{v['postal_code']}",
    ),
    # 电话：____  电子函件：____
    (
        re.compile(r"电\s*话\s*[：:]\s*_*\s*电子\s*函件\s*[：:]\s*_*"),
        lambda v: f"电话:{v['phone']}\t电子函件:{v['email']}",
    ),
    # 投标人开户银行：____  账号/行号：____
    (
        re.compile(r"投标人开户银行\s*[：:]\s*_*\s*账号\s*[/／]\s*行号\s*[：:]\s*_*"),
        lambda v: f"投标人开户银行:{v['bank_name']}\t账号/行号:{v['bank_account']}",
    ),
    # 投标人名称（加盖公章）：____
    (
        re.compile(r"投标人名称\s*[（(]\s*加盖公章\s*[）)]\s*[：:]\s*_*"),
        lambda v: f"投标人名称（加盖公章）:{_ul(v['company'])}",
    ),
    # 日期：____年____月____日 / 日期：年月日 / 日期：____  (value underlined)
    # 锚定行首，避免误匹配“投标截止日期”等中间含“日期”的文本。
    (
        re.compile(r"^日\s*期\s*[：:][\s_]*(?:年[\s_]*月?[\s_]*日?|_)"),
        lambda v: f"日期:{_ul(v['date'])}",
    ),
]


_VALUE_KEYS = (
    "purchaser", "agency", "project_name", "project_code", "company",
    "address", "postal_code", "phone", "email", "bank_name", "bank_account", "date",
)


def _ensure(values: Dict[str, str]) -> Dict[str, str]:
    """Make sure every value key exists so rule lambdas can index directly."""
    return {key: (values.get(key) or PLACEHOLDER) for key in _VALUE_KEYS}


def _apply(text: str, values: Dict[str, str]) -> str:
    values = _ensure(values)
    for pattern, replacement in _RULES:
        text = pattern.sub(replacement(values), text)
    return text


def split_markup(text: str) -> List[Tuple[str, bool]]:
    """Split *text* into ``(segment, underlined)`` pieces."""
    if text is None:
        return []
    segments: List[Tuple[str, bool]] = []
    pos = 0
    for match in _UL_RE.finditer(text):
        if match.start() > pos:
            segments.append((text[pos:match.start()], False))
        segments.append((match.group(1), True))
        pos = match.end()
    if pos < len(text):
        segments.append((text[pos:], False))
    return segments or ([(text, False)] if text == "" else [])


def fill_marked(text: str, values: Dict[str, str]) -> str:
    """Apply all fill rules, keeping the underline sentinels in place."""
    if not text:
        return text
    return _apply(text, values)


def fill_line(text: str, values: Dict[str, str]) -> str:
    """Apply all fill rules to a single line, returning plain text (no sentinels)."""
    if not text:
        return text
    return "".join(segment for segment, _ in split_markup(fill_marked(text, values)))
