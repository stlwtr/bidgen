"""Repair CJK glyph artifacts coming from PDF text layers.

Chinese tender PDFs often use Kangxi Radicals (U+2F00-U+2FDF) and CJK Radicals
Supplement (U+2E80-U+2EFF) as the glyphs for ordinary Han characters, so the
extracted text looks like "投标⼈" instead of "投标人".

``NFKC`` normalisation repairs the Kangxi range but leaves the Radicals
Supplement range untouched, so an explicit map is applied afterwards.  The map
keys are the *post-NFKC* forms: Radicals Supplement characters survive NFKC
unchanged, while ``戶`` is what NFKC yields for U+2F3E (KANGXI RADICAL DOOR)
even though the simplified glyph ``户`` is intended.
"""

from __future__ import annotations

import os
import re
import unicodedata
import zipfile

# Keys are post-NFKC forms.
_RADICAL_FIX: dict[str, str] = {
    "\u2ea0": "民",  # ⺠ CJK RADICAL CIVILIAN
    "\u2ec5": "见",  # ⻅ CJK RADICAL C-SIMPLIFIED SEE
    "\u2ec6": "角",  # ⻆ CJK RADICAL SIMPLIFIED HORN
    "\u2ecb": "车",  # ⻋ CJK RADICAL C-SIMPLIFIED CART
    "\u2ed3": "长",  # ⻓ CJK RADICAL C-SIMPLIFIED LONG
    "\u2ed4": "门",  # ⻔ CJK RADICAL C-SIMPLIFIED GATE
    "\u2ed8": "青",  # ⻘ CJK RADICAL BLUE
    "\u2eda": "页",  # ⻚ CJK RADICAL C-SIMPLIFIED LEAF
    "\u2edb": "风",  # ⻛ CJK RADICAL C-SIMPLIFIED WIND
    "\u2edc": "飞",  # ⻜ CJK RADICAL C-SIMPLIFIED FLY
    "\u2edd": "食",  # ⻝ CJK RADICAL EAT ONE
    "\u2ee2": "马",  # ⻢ CJK RADICAL C-SIMPLIFIED HORSE
    "\u2ee3": "骨",  # ⻣ CJK RADICAL BONE
    "\u2ee5": "鱼",  # ⻥ CJK RADICAL C-SIMPLIFIED FISH
    "\u2ee8": "麦",  # ⻨ CJK RADICAL SIMPLIFIED WHEAT
    "\u2ee9": "黄",  # ⻩ CJK RADICAL SIMPLIFIED YELLOW
    "\u2eec": "齐",  # ⻬ CJK RADICAL C-SIMPLIFIED EVEN
    "\u2eee": "齿",  # ⻮ CJK RADICAL C-SIMPLIFIED TOOTH
    "\u2ef0": "龙",  # ⻰ CJK RADICAL C-SIMPLIFIED DRAGON
    "\u6236": "户",  # 戶 -> 户 (NFKC result of U+2F3E)
}

_TABLE = str.maketrans(_RADICAL_FIX)


def fix(text: str) -> str:
    """Return *text* with CJK glyph artifacts repaired (NFKC + radical map)."""
    if not text:
        return text
    return unicodedata.normalize("NFKC", text).translate(_TABLE)


# Convenience alias kept explicit for readability at call sites.
fix_text = fix


# Only these codepoints are ever rewritten inside a DOCX.  NFKC must NOT be
# applied to whole-document XML because it would also fold proper full-width
# punctuation (（），。) into half-width forms.
_DOCX_BAD_RE = re.compile(r"[\u2e80-\u2fdf\u6236]")


def fix_docx(path: str) -> str:
    """Rewrite a DOCX in place, repairing only CJK radical glyph artifacts."""
    with zipfile.ZipFile(path) as zin:
        data = {name: zin.read(name) for name in zin.namelist()}

    for name in list(data):
        if not (name.startswith("word/") and name.endswith(".xml")):
            continue
        try:
            xml = data[name].decode("utf-8")
        except UnicodeDecodeError:
            continue
        fixed = _DOCX_BAD_RE.sub(lambda m: fix(m.group(0)), xml)
        if fixed != xml:
            data[name] = fixed.encode("utf-8")

    tmp_path = path + ".tmp"
    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, blob in data.items():
            zout.writestr(name, blob)
    os.replace(tmp_path, path)
    return path
