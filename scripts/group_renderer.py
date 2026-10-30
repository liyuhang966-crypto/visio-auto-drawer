from __future__ import annotations

from typing import Any


GROUP_STYLES = {
    "blue_dashed_group": ("RGB(250,253,255)", "RGB(72,134,220)"),
    "green_dashed_group": ("RGB(250,255,250)", "RGB(76,160,88)"),
    "orange_dashed_group": ("RGB(255,249,244)", "RGB(245,168,112)"),
    "gray_dashed_group": ("RGB(255,255,255)", "RGB(155,155,155)"),
}


def draw_group(page: Any, group: dict[str, Any], page_w: float, page_h: float) -> list[Any]:
    left, bottom, right, top = _bbox_to_visio(tuple(group["bbox"]), page_w, page_h)
    fill, line = GROUP_STYLES.get(group.get("style", "blue_dashed_group"), GROUP_STYLES["blue_dashed_group"])
    background = page.DrawRectangle(left, bottom, right, top)
    background.Text = ""
    _try_set(background, "FillForegnd", fill)
    _try_set(background, "FillTransparency", "35%")
    _try_set(background, "LineColor", line)
    _try_set(background, "LinePattern", "2")
    _try_set(background, "LineWeight", "0.010 in")
    try:
        background.SendToBack()
    except Exception:
        pass
    shapes = [background]
    title = group.get("title")
    if title:
        title_box = page.DrawRectangle(left + 0.05, top - 0.33, right - 0.05, top - 0.05)
        title_box.Text = title
        _try_set(title_box, "LinePattern", "0")
        _try_set(title_box, "FillPattern", "0")
        _try_set(title_box, "Char.Size", "9.5 pt")
        _try_set(title_box, "Char.Style", "1")
        _try_set(title_box, "Char.Color", line)
        shapes.append(title_box)
    return shapes


def _bbox_to_visio(bbox: tuple[float, float, float, float], page_w: float, page_h: float) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = bbox
    return x1 * page_w, (1 - y2) * page_h, x2 * page_w, (1 - y1) * page_h


def _try_set(shape: Any, cell_name: str, formula: str) -> None:
    try:
        shape.CellsU(cell_name).FormulaU = formula
    except Exception:
        pass
