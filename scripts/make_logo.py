"""生成应用 logo（蓝色圆角方块 + 白色文档 + 右下对勾），输出 PNG / ICO / ICNS。

用法：python3 scripts/make_logo.py
输出：
  - assets/logo.png   （窗口图标 / 标题区显示）
  - assets/logo.ico   （Windows 打包图标）
  - assets/logo.icns  （macOS 打包图标）
"""

from __future__ import annotations

import os
import subprocess

from PIL import Image, ImageDraw

SIZE = 256
BG = "#4a7dff"
WHITE = "#ffffff"
OUT_DIR = "assets"

_ICON_SIZES = [16, 32, 48, 64, 128, 256]


def make_logo(size: int = SIZE) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 蓝色圆角背景
    d.rounded_rectangle([0, 0, size, size], radius=round(size * 0.22), fill=BG)
    # 白色文档（描边圆角矩形 + 三条横线）
    doc_w, doc_h = size * 0.36, size * 0.46
    x0, y0 = size * 0.32, size * 0.18
    lw = round(size * 0.028)
    d.rounded_rectangle(
        [x0, y0, x0 + doc_w, y0 + doc_h],
        radius=round(size * 0.03),
        outline=WHITE,
        width=lw,
    )
    for yy in (0.32, 0.43, 0.54):
        y = size * yy
        d.line(
            [x0 + doc_w * 0.2, y, x0 + doc_w * 0.8, y],
            fill=WHITE,
            width=round(size * 0.02),
        )
    # 右下对勾圆（白圆 + 蓝色对勾）
    cr = size * 0.17
    cx, cy = size * 0.72, size * 0.72
    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=WHITE)
    tick_w = round(size * 0.032)
    d.line([cx - cr * 0.55, cy, cx - cr * 0.08, cy + cr * 0.42], fill=BG, width=tick_w)
    d.line([cx - cr * 0.08, cy + cr * 0.42, cx + cr * 0.6, cy - cr * 0.5], fill=BG, width=tick_w)
    return img


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    logo = make_logo()

    png_path = os.path.join(OUT_DIR, "logo.png")
    logo.save(png_path)
    print("生成", png_path)

    ico_path = os.path.join(OUT_DIR, "logo.ico")
    logo.save(ico_path, sizes=[(s, s) for s in _ICON_SIZES])
    print("生成", ico_path)

    # macOS .icns（iconutil，需 iconset 目录）
    iconset = os.path.join(OUT_DIR, "logo.iconset")
    os.makedirs(iconset, exist_ok=True)
    for s in (16, 32, 128, 256, 512):
        make_logo(s * 2 if s >= 128 else s * 2).save(
            os.path.join(iconset, f"icon_{s}x{s}@2x.png" if s >= 128 else f"icon_{s}x{s}.png")
        )
        if s < 128:
            make_logo(s * 2).save(os.path.join(iconset, f"icon_{s}x{s}@2x.png"))
    icns_path = os.path.join(OUT_DIR, "logo.icns")
    try:
        subprocess.run(["iconutil", "-c", "icns", iconset, "-o", icns_path], check=True)
        print("生成", icns_path)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("跳过 .icns（iconutil 不可用，仅 macOS 可生成）")


if __name__ == "__main__":
    main()
