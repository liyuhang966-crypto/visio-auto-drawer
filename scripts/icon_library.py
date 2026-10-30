from __future__ import annotations

from typing import Any


ICON_SYMBOLS = {
    "lidar": "⌁",
    "camera": "▣",
    "imu_encoder": "⚙",
    "map_grid": "▦",
    "fire": "▲",
    "robot": "♙",
    "path_planning": "⌁",
    "target": "◎",
    "shield": "▰",
    "serial_port": "▥",
    "chip": "▣",
    "motor": "▤",
    "fan": "✣",
    "mobile": "▯",
    "database": "▭",
    "cloud": "☁",
}


def draw_icon(page: Any, icon: str | None, x: float, y: float, size: float = 0.38, color: str = "RGB(36,96,180)") -> list[Any]:
    """用 Visio 基础形状和统一符号绘制轻量图标。"""
    if not icon:
        return []

    icon = icon.lower()
    shapes: list[Any] = []
    circle = page.DrawOval(x - size / 2, y - size / 2, x + size / 2, y + size / 2)
    circle.CellsU("FillForegnd").FormulaU = "RGB(255,255,255)"
    circle.CellsU("LineColor").FormulaU = color
    circle.CellsU("LineWeight").FormulaU = "0.010 in"
    shapes.append(circle)

    symbol = ICON_SYMBOLS.get(icon, "•")
    text = page.DrawRectangle(x - size * 0.42, y - size * 0.36, x + size * 0.42, y + size * 0.36)
    text.Text = symbol
    text.CellsU("LinePattern").FormulaU = "0"
    text.CellsU("FillPattern").FormulaU = "0"
    text.CellsU("Char.Size").FormulaU = "13 pt"
    text.CellsU("Char.Style").FormulaU = "1"
    text.CellsU("Char.Color").FormulaU = color
    text.CellsU("Para.HorzAlign").FormulaU = "1"
    text.CellsU("VerticalAlign").FormulaU = "1"
    shapes.append(text)
    return shapes
