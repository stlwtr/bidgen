"""界面样式（QSS）：浅色卡片风、主色 / 状态色、基础字号可调。"""

from __future__ import annotations

PRIMARY = "#4a7dff"
PRIMARY_HOVER = "#3b6fe0"
PRIMARY_DISABLED = "#a9bcd8"
SUCCESS = "#2f9e44"
DANGER = "#e03131"
WARNING = "#f08c00"
BG = "#f4f6fb"
CARD_BG = "#ffffff"
BORDER = "#e4e8f0"
TEXT = "#1f2733"
TEXT_MUTED = "#6b7a90"

_FONT_SCALE = 1.0


def base_font_px() -> int:
    return round(15 * _FONT_SCALE)


def set_font_scale(scale: float) -> None:
    """调整全局字号倍率（0.8 ~ 1.6）。"""
    global _FONT_SCALE
    _FONT_SCALE = max(0.8, min(1.6, scale))


def qss() -> str:
    px = base_font_px()
    title_px = round(px * 1.6)
    btn_px = round(px * 1.1)
    return f"""
QMainWindow, QWidget {{
    background: {BG};
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: {px}px; color: {TEXT};
}}
QLabel#title {{ font-size: {title_px}px; font-weight: 800; color: #17202b; }}
QLabel#subtitle {{ color: {TEXT_MUTED}; margin-bottom: 4px; }}
QGroupBox {{
    background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 10px;
    margin-top: 16px; padding: 18px 12px 10px; font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 12px; top: 0px;
    padding: 0 6px; background: {CARD_BG}; color: #4a5568;
}}
QLineEdit, QComboBox {{
    background: #f8fafc; border: 1px solid #d7dee9; border-radius: 6px; padding: 7px 9px;
    selection-background-color: {PRIMARY};
}}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {PRIMARY}; background: #ffffff; }}
QPushButton {{
    background: #eef1f7; border: 1px solid #d7dee9; border-radius: 6px;
    padding: 7px 14px; color: #2d3748;
}}
QPushButton:hover {{ background: #e2e8f5; }}
QPushButton#primary {{
    background: {PRIMARY}; color: #ffffff; border: none;
    font-size: {btn_px}px; font-weight: 700; padding: 11px; border-radius: 8px;
}}
QPushButton#primary:hover {{ background: {PRIMARY_HOVER}; }}
QPushButton#primary:disabled {{ background: {PRIMARY_DISABLED}; }}
QProgressBar {{
    border: 1px solid #d7dee9; border-radius: 6px; background: #eef1f7;
    height: 16px; text-align: center; color: #2d3748;
}}
QProgressBar::chunk {{ background: {PRIMARY}; border-radius: 5px; }}
QTextEdit, QListWidget {{ background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 8px; padding: 6px; }}
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{ background: transparent; padding: 8px 20px; border-radius: 6px; color: #4a5568; }}
QTabBar::tab:selected {{ background: {PRIMARY}; color: #ffffff; }}
QCheckBox {{ color: #2d3748; }}
QMenuBar {{ background: {CARD_BG}; border-bottom: 1px solid {BORDER}; }}
QMenu {{ background: {CARD_BG}; border: 1px solid {BORDER}; }}
QMenu::item:selected {{ background: {PRIMARY}; color: #ffffff; }}
QListWidget#nav {{
    background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 10px;
    outline: none;
}}
QListWidget#nav::item {{ padding: 10px 12px; border-radius: 6px; margin: 2px 6px; }}
QListWidget#nav::item:selected {{ background: {PRIMARY}; color: #ffffff; }}
QListWidget#nav::item:hover {{ background: #eef1f7; }}
QFrame#banner {{ border-radius: 8px; }}
QFrame#banner[ok="true"] {{ background: #e7f5ec; border: 1px solid {SUCCESS}; }}
QFrame#banner[err="true"] {{ background: #fdecec; border: 1px solid {DANGER}; }}
"""
