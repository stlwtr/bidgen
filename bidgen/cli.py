"""Command-line entry point for bidgen."""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from . import config, docx_builder, extract, pdf_reader, pdf_to_docx, reflow, sanitize, structure, textfix
from .style import StyleSpec


def _build_context(pdf: str, supplier_path: Optional[str], spec: StyleSpec) -> docx_builder.BidContext:
    tables = pdf_reader.read_tables(pdf)
    lines = pdf_reader.read_lines(pdf, tables)
    paragraphs = reflow.rebuild_paras(lines)
    template = structure.build_template(paragraphs, tables)
    fields = extract.extract_fields(lines)
    return docx_builder.BidContext(
        template=template,
        fields=fields,
        supplier=config.load_supplier(supplier_path),
        qualification=extract.extract_qualification(tables),
        compliance=extract.extract_compliance(tables),
        scoring=extract.extract_scoring(tables),
        purchase=extract.extract_purchase_items(tables),
        tech=extract.extract_tech_requirements(tables),
        spec=spec,
    )


def _default_name(pdf: str, suffix: str, out: Optional[str]) -> str:
    if out:
        return out
    base = os.path.splitext(os.path.basename(pdf))[0]
    return base + suffix


def _convert(pdf: str, out: str, do_sanitize: bool) -> str:
    pdf_to_docx.convert(pdf, out)
    textfix.fix_docx(out)
    if do_sanitize:
        sanitize.sanitize_docx(out)
    return out


def _generate(pdf: str, out: str, supplier: Optional[str], do_sanitize: bool) -> str:
    ctx = _build_context(pdf, supplier, StyleSpec())
    document = docx_builder.build_bid_document(ctx)
    document.save(out)
    if do_sanitize:
        sanitize.sanitize_docx(out)
    return out


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bidgen", description="投标文件生成助手")
    sub = parser.add_subparsers(dest="command", required=True)

    p_conv = sub.add_parser("convert", help="将招标文件 PDF 转为 Word")
    p_conv.add_argument("pdf", help="招标文件 PDF 路径")
    p_conv.add_argument("-o", "--out", help="输出 .docx 路径")
    p_conv.add_argument("--no-sanitize", action="store_true", help="不清理元数据")

    p_gen = sub.add_parser("generate", help="生成投标文件 Word 初稿")
    p_gen.add_argument("pdf", help="招标文件 PDF 路径")
    p_gen.add_argument("--supplier", help="供应商配置 (supplier.yaml)")
    p_gen.add_argument("-o", "--out", help="输出 .docx 路径")
    p_gen.add_argument("--no-sanitize", action="store_true", help="不清理元数据")

    p_all = sub.add_parser("all", help="同时产出招标 Word 与投标 Word")
    p_all.add_argument("pdf", help="招标文件 PDF 路径")
    p_all.add_argument("--supplier", help="供应商配置 (supplier.yaml)")
    p_all.add_argument("--out-dir", default="out", help="输出目录 (默认 out)")
    p_all.add_argument("--no-sanitize", action="store_true", help="不清理元数据")

    p_san = sub.add_parser("sanitize", help="清理已有 Word 的机器码 / 用户信息")
    p_san.add_argument("docx", help="待清理的 .docx 路径")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "convert":
            out = _default_name(args.pdf, ".docx", args.out)
            path = _convert(args.pdf, out, not args.no_sanitize)
            print(f"已生成：{path}")
        elif args.command == "generate":
            out = _default_name(args.pdf, ".bid.docx", args.out)
            path = _generate(args.pdf, out, args.supplier, not args.no_sanitize)
            print(f"已生成：{path}")
        elif args.command == "all":
            os.makedirs(args.out_dir, exist_ok=True)
            tender = os.path.join(args.out_dir, "招标文件.docx")
            bid = os.path.join(args.out_dir, "投标文件.docx")
            _convert(args.pdf, tender, not args.no_sanitize)
            print(f"已生成：{tender}")
            _generate(args.pdf, bid, args.supplier, not args.no_sanitize)
            print(f"已生成：{bid}")
        elif args.command == "sanitize":
            sanitize.sanitize_docx(args.docx)
            print(f"已清理：{args.docx}")
    except FileNotFoundError as exc:
        print(f"错误：找不到文件 {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - surface a readable message
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
