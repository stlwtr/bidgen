"""Strip machine identifiers and user information from a DOCX package.

Removes the ``python-docx`` / ``Microsoft ... Word`` fingerprints in
``docProps``, the ``<w:rsids>`` revision-save ids and every ``w:rsid*``
attribute, plus any comments / people / custom-property parts.  Operates at the
zip level so it works on any DOCX, including pdf2docx output.

See design.md §4.10.
"""

from __future__ import annotations

import os
import re
import zipfile
from typing import Dict, List

_RSIDS_BLOCK_RE = re.compile(r"<w:rsids>.*?</w:rsids>", re.S)
_RSID_ATTR_RE = re.compile(r'\s+w:rsid[A-Za-z]*="[^"]*"')

_FIXED_TIMESTAMP = "2000-01-01T00:00:00Z"

_CORE_BLANK = ["title", "subject", "creator", "keywords", "description", "lastModifiedBy", "category"]
_APP_BLANK = ["Application", "Template", "Manager", "Company"]
_APP_ZERO = ["TotalTime"]

_DROP_PARTS = {
    "docProps/custom.xml",
    "word/people.xml",
    "word/comments.xml",
    "word/commentsExtended.xml",
    "word/commentsIds.xml",
    "word/commentsExtensible.xml",
}

_TEXT_PARTS_RE = re.compile(r"^word/(document|header\d*|footer\d*)\.xml$")


def _blank_tag(xml: str, tag: str) -> str:
    pattern = re.compile(
        r"(<(?:[A-Za-z0-9]+:)?" + tag + r"\b[^>]*>).*?(</(?:[A-Za-z0-9]+:)?" + tag + r">)",
        re.S,
    )
    xml = pattern.sub(r"\1\2", xml)
    # also turn self-closing <tag/> into an empty pair for readability
    return xml


def _set_tag(xml: str, tag: str, value: str) -> str:
    pattern = re.compile(
        r"(<(?:[A-Za-z0-9]+:)?" + tag + r"\b[^>]*>).*?(</(?:[A-Za-z0-9]+:)?" + tag + r">)",
        re.S,
    )
    return pattern.sub(lambda m: m.group(1) + value + m.group(2), xml)


def _sanitize_xml(name: str, xml: str) -> str:
    if name == "docProps/core.xml":
        for tag in _CORE_BLANK:
            xml = _blank_tag(xml, tag)
        xml = _set_tag(xml, "revision", "1")
        xml = _set_tag(xml, "created", _FIXED_TIMESTAMP)
        xml = _set_tag(xml, "modified", _FIXED_TIMESTAMP)
    elif name == "docProps/app.xml":
        for tag in _APP_BLANK:
            xml = _blank_tag(xml, tag)
        for tag in _APP_ZERO:
            xml = _set_tag(xml, tag, "0")
    elif name == "word/settings.xml":
        xml = _RSIDS_BLOCK_RE.sub("", xml)
    elif _TEXT_PARTS_RE.match(name):
        xml = _RSID_ATTR_RE.sub("", xml)
    return xml


def _drop_from_content_types(xml: str, parts: List[str]) -> str:
    for part in parts:
        name = "/" + part.lstrip("/")
        xml = re.sub(r'<Override\b[^>]*PartName="' + re.escape(name) + r'"[^>]*/>', "", xml)
    return xml


def _drop_from_rels(xml: str, parts: List[str]) -> str:
    targets = {os.path.basename(p) for p in parts}
    for target in targets:
        xml = re.sub(
            r'<Relationship\b[^>]*Target="[^"]*' + re.escape(target) + r'"[^>]*/>',
            "",
            xml,
        )
    return xml


def sanitize_docx(path: str) -> str:
    """Rewrite *path* in place with machine identifiers and user info removed."""
    with zipfile.ZipFile(path) as zin:
        names = zin.namelist()
        data: Dict[str, bytes] = {n: zin.read(n) for n in names}

    dropped = [n for n in data if n in _DROP_PARTS]
    for name in dropped:
        del data[name]

    for name in list(data):
        if not (name.endswith(".xml") or name.endswith(".rels")):
            continue
        try:
            xml = data[name].decode("utf-8")
        except UnicodeDecodeError:
            continue
        if name == "[Content_Types].xml" and dropped:
            xml = _drop_from_content_types(xml, dropped)
        elif name.endswith(".rels") and dropped:
            xml = _drop_from_rels(xml, dropped)
        xml = _sanitize_xml(name, xml)
        data[name] = xml.encode("utf-8")

    tmp_path = path + ".tmp"
    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, blob in data.items():
            zout.writestr(name, blob)
    os.replace(tmp_path, path)
    return path
