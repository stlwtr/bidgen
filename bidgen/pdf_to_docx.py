"""Convert a tender PDF into a DOCX using pdf2docx."""

from __future__ import annotations

from pdf2docx import Converter


def convert(pdf_path: str, docx_path: str) -> str:
    """Convert *pdf_path* to *docx_path* and return the output path."""
    converter = Converter(pdf_path)
    try:
        converter.convert(docx_path)
    finally:
        converter.close()
    return docx_path
