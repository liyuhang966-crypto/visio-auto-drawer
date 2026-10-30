from __future__ import annotations

from typing import Any


LEGEND_STYLES = {
    "blue_solid_arrow": ("RGB(40,103,205)", "1"),
    "green_solid_arrow": ("RGB(48,145,72)", "1"),
    "gray_dashed_arrow": ("RGB(105,115,130)", "2"),
    "orange_dashed_arrow": ("RGB(225,102,45)", "2"),
}


def draw_legend(page: Any, bbox: tuple[float, float, float, float], items: list[dict[str, str]], page_w: float, page_h: float) -> list[Any]:
    left, bottom, right, top = _bbox_to_visio(bbox, page_w, page_h)
    shapes: list[Any] = []
    box = page.DrawRectangle(left, bottom, right, top)
    box.Text = "图例"
    _try_set(box, "FillForegnd", "RGB(255,255,255)")
    _try_set(box, "LineColor", "RGB(120,145,190)")
    _try_set(box, "LineWeight", "0.010 in")
    _try_set(box, "Char.Size", "8.5 pt")
    shapes.append(box)
    row_h = (top - bottom) / max(1, len(items) + 1)
    for index, item in enumerate(items):
        y = top - row_h * (index + 1.35)
        line = page.DrawLine(left + 0.15, y, left + 0.55, y)
        color, pattern = LEGEND_STYLES.get(item.get("style", "blue_solid_arrow"), LEGEND_STYLES["blue_solid_arrow"])
        _try_set(line, "LineColor", color)
        _try_set(line, "LinePattern", pattern)
        _try_set(line, "EndArrow", "13")
        label = page.DrawRectangle(left + 0.62, y - row_h * 0.30, right - 0.10, y + row_h * 0.30)
        label.Text = item.get("label", "")
        _try_set(label, "LinePattern", "0")
        _try_set(label, "FillPattern", "0")
        _try_set(label, "Char.Size", "8 pt")
        shapes.extend([line, label])
    return shapes


def _bbox_to_visio(bbox: tuple[float, float, float, float], page_w: float, page_h: float) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = bbox
    return x1 * page_w, (1 - y2) * page_h, x2 * page_w, (1 - y1) * page_h


def _try_set(shape: Any, cell_name: str, formula: str) -> None:
    try:
        shape.CellsU(cell_name).FormulaU = formula
    except Exception:
        pass
