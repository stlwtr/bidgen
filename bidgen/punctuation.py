"""Convert half-width punctuation to full-width in Chinese context.

Only punctuation that sits in a Chinese (CJK) context is converted.  Anything
glued to numbers, ASCII words, units, chemical formulas, ratios or a pure
English sentence is left untouched, e.g.::

    金额3,649,020.00元,共100台.   ->  金额3,649,020.00元，共100台。
    屏幕比例16:10,分辨率高.        ->  屏幕比例16:10，分辨率高。
    规格8dB(A),符合(Cr)≤20        ->  规格8dB(A)，符合(Cr)≤20
    This is a test, do not change. ->  (unchanged)

See design.md §4.9 for the full rule set.
"""

from __future__ import annotations

import re

_PAIRS: dict[str, str] = {
    ",": "，",
    ".": "。",
    ":": "：",
    ";": "；",
    "!": "！",
    "?": "？",
}

# Characters that may legitimately precede a Chinese-context punctuation mark
# even though they are not Han characters themselves (closing brackets, percent).
_LEFT_ALLOWED_NON_CJK = ")]}%"

_BRACKETS_RE = re.compile(r"\(([^()]*)\)")

# Han ideographs.
_HAN_CLASS = r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]"
# CJK ideographs, CJK symbols/punctuation and full-width forms.
_CJK_CLASS = r"[\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff00-\uffef]"
# CJK sentence / clause marks; a space immediately before one of these is noise,
# unless it sits right after an opening bracket (a fill-in blank such as
# "（项目编号： ）" is preserved).
_END_PUNCT = r"[\u3002\uFF0C\u3001\uFF1B\uFF1A\uFF01\uFF1F]"
_OPEN_BRACKET = r"[(\[\uFF08\u3010\u3014\uFF5B\u300A]"
_ASCII_ALNUM = r"[0-9A-Za-z]"
# An ASCII / ideographic space with a Han neighbour (e.g. "采 购", "的 项目",
# "。 递", "加 （") is a PDF layout artifact and is dropped.  The same applies to
# a space between a Han character and an ASCII letter/digit ("USB 接口",
# "第 1 章", "500 万") so Chinese and Latin/numeric runs stay contiguous.
_CJK_SPACE_RE = re.compile(
    r"(?:(?<=" + _HAN_CLASS + r")[ \u3000]+(?=" + _CJK_CLASS + r"))"
    r"|(?:(?<=" + _CJK_CLASS + r")[ \u3000]+(?=" + _HAN_CLASS + r"))"
    r"|(?:(?<=" + _HAN_CLASS + r")[ \u3000]+(?=" + _ASCII_ALNUM + r"))"
    r"|(?:(?<=" + _ASCII_ALNUM + r")[ \u3000]+(?=" + _HAN_CLASS + r"))"
    r"|(?<!" + _OPEN_BRACKET + r")[ \u3000]+(?=" + _END_PUNCT + r")"
)


def _collapse_cjk_spaces(text: str) -> str:
    return _CJK_SPACE_RE.sub("", text)


def _is_cjk(ch: str) -> bool:
    if not ch:
        return False
    cp = ord(ch)
    return (
        0x4E00 <= cp <= 0x9FFF  # CJK unified ideographs
        or 0x3400 <= cp <= 0x4DBF  # CJK extension A
        or 0xF900 <= cp <= 0xFAFF  # CJK compatibility ideographs
        or 0x3000 <= cp <= 0x303F  # CJK symbols and punctuation
        or 0xFF00 <= cp <= 0xFFEF  # full-width forms
    )


def _should_convert(ch: str, left: str, right: str) -> bool:
    """Decide whether *ch* (half-width) sits in a Chinese context."""
    # A period right after a digit is a decimal point or a list marker ("1."),
    # never a Chinese full stop.
    if ch == "." and left.isdigit():
        return False
    # Never touch an ASCII token: letter glued on the left, or letter/digit
    # glued on the right (protects numbers, units, formulas and English text).
    if left and left.isascii() and left.isalpha():
        return False
    # A colon right after a Chinese label is a label separator ("电话：123"), so
    # an ASCII digit/letter on the right must not block it.  "16:10" stays safe
    # because its left neighbour is a digit, not CJK.
    if right and right.isascii() and right.isalnum() and ch != ":":
        return False

    left_ok = (
        _is_cjk(left)
        or (left.isdigit() if left else False)
        or (left != "" and left in _LEFT_ALLOWED_NON_CJK)
    )
    if not left_ok:
        return False

    if _is_cjk(right):
        return True
    if right == "" or right.isspace():
        # A trailing mark only becomes full-width when the sentence is Chinese.
        return _is_cjk(left)
    # Right neighbour is neither CJK nor blank (e.g. an underscore blank or
    # another ASCII punctuation); convert only in a Chinese context.
    return _is_cjk(left)


def _convert_brackets(text: str) -> str:
    """Turn ``(...)`` into ``（...）`` only when the content contains CJK."""

    def repl(match: "re.Match[str]") -> str:
        inner = match.group(1)
        if any(_is_cjk(c) for c in inner):
            return "（" + inner + "）"
        return match.group(0)

    return _BRACKETS_RE.sub(repl, text)


def normalize(text: str) -> str:
    """Return *text* with Chinese-context punctuation converted to full-width."""
    if not text:
        return text
    text = _convert_brackets(text)
    chars = list(text)
    for i, ch in enumerate(chars):
        if ch not in _PAIRS:
            continue
        left = chars[i - 1] if i > 0 else ""
        right = chars[i + 1] if i + 1 < len(chars) else ""
        if _should_convert(ch, left, right):
            chars[i] = _PAIRS[ch]
    return _collapse_cjk_spaces("".join(chars))


normalize_punct = normalize
