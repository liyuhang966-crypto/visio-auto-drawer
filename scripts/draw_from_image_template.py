from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any

from template_utils import build_slot_values, find_template_image, load_diagram_or_content, resolve_project_path, wrap_text


def main() -> int:
    parser = argparse.ArgumentParser(description="基于图片模板生成可编辑 Visio 图。")
    parser.add_argument("--project-root", default=str(Path.cwd()))
    parser.add_argument("--diagram", default="output/diagram.json")
    parser.add_argument("--detected", default="output/template_detected.json")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    image_path = find_template_image(project_root)
    if image_path is None:
        print("失败：未找到有效图片模板。请放入 input/template.png、input/template.jpg 或 input/template.jpeg。")
        return 1

    detected_path = resolve_project_path(project_root, args.detected)
    diagram = load_diagram_or_content(project_root, resolve_project_path(project_root, args.diagram))
    output_path = resolve_project_path(project_root, diagram.output or "output/filled_template.vsdx")
    if output_path.name == "result.vsdx":
        output_path = project_root / "output" / "filled_template.vsdx"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        try:
            output_path.unlink()
        except Exception as exc:
            print(f"失败：无法删除旧输出文件 {output_path}。请确认该文件没有在 Visio 中打开。原因：{exc}")
            return 3
    values = build_slot_values(diagram, project_root)

    try:
        detected = json.loads(detected_path.read_text(encoding="utf-8")) if detected_path.exists() else {}
    except Exception:
        detected = {}

    try:
        import win32com.client  # type: ignore
    except ModuleNotFoundError:
        print("失败：ModuleNotFoundError: win32com。请先运行 scripts\\setup_env.ps1。")
        return 2

    try:
        draw(project_root, image_path, output_path, detected, values, diagram.animation.delay_seconds)
        print(f"成功：图片模板可编辑 Visio 图已保存到 {output_path}")
        return 0
    except Exception as exc:
        print("失败：图片模板绘图过程出错。")
        print(f"原因：{exc}")
        print("排查建议：确认图片文件可读取，并运行 analyze_image_template.py 生成 template_detected.json。")
        return 3


def draw(project_root: Path, image_path: Path, output_path: Path, detected: dict, values: dict[str, str], delay: float) -> None:
    from PIL import Image
    import win32com.client  # type: ignore

    with Image.open(image_path) as img:
        pixel_width, pixel_height = img.size

    page_width = 13.0
    page_height = max(7.0, round(page_width * pixel_height / pixel_width, 2))

    visio = win32com.client.Dispatch("Visio.Application")
    visio.Visible = True
    try:
        visio.AlertResponse = 1
    except Exception:
        pass
    doc = visio.Documents.Add("")
    page = visio.ActivePage
    page.PageSheet.CellsU("PageWidth").ResultIU = page_width
    page.PageSheet.CellsU("PageHeight").ResultIU = page_height

    background = _import_background(page, image_path, project_root, page_width, page_height)
    _pause(visio, delay)

    regions = detected.get("possible_text_regions") or []
    if not regions:
        regions = _fallback_regions(pixel_width, pixel_height)

    slot_values = list(values.items())
    if not slot_values:
        slot_values = [("{{标题}}", "基于图片模板生成的图")]

    for index, (_, text) in enumerate(slot_values):
        region = regions[min(index, len(regions) - 1)]
        shape = _draw_region_shape(page, region, pixel_width, pixel_height, page_width, page_height)
        shape.Text = wrap_text(text, width=max(10, int(shape.CellsU("Width").ResultIU * 8)))
        _apply_overlay_style(shape, title=index == 0)
        _pause(visio, delay)

    doc.SaveAs(str(output_path))


def _import_background(page: Any, image_path: Path, project_root: Path, page_width: float, page_height: float) -> Any:
    background = page.DrawRectangle(0.0, 0.0, page_width, page_height)
    background.Text = f"图片模板参考画布\n{image_path.name}\n当前 Visio 图片导入不可用，已继续生成可编辑形状。"
    background.CellsU("FillForegnd").FormulaU = "RGB(248,249,252)"
    background.CellsU("LineColor").FormulaU = "RGB(190,195,205)"
    background.CellsU("Char.Size").FormulaU = "9 pt"
    background.SendToBack()
    print("警告：当前环境的 Visio 图片导入不可用，已使用参考画布并继续生成可编辑形状。")
    return background


def _draw_region_shape(page: Any, region: dict, pixel_width: int, pixel_height: int, page_width: float, page_height: float) -> Any:
    x = region.get("x", pixel_width * 0.1)
    y = region.get("y", pixel_height * 0.1)
    w = region.get("width", pixel_width * 0.8)
    h = region.get("height", pixel_height * 0.12)

    left = x / pixel_width * page_width
    right = (x + w) / pixel_width * page_width
    top = page_height - (y / pixel_height * page_height)
    bottom = page_height - ((y + h) / pixel_height * page_height)
    if right - left < 1.0:
        right = left + 1.0
    if top - bottom < 0.45:
        top = bottom + 0.45
    return page.DrawRectangle(left, bottom, right, top)


def _fallback_regions(pixel_width: int, pixel_height: int) -> list[dict]:
    return [
        {"x": int(pixel_width * 0.08), "y": int(pixel_height * 0.05), "width": int(pixel_width * 0.84), "height": int(pixel_height * 0.12), "role": "title"},
        {"x": int(pixel_width * 0.08), "y": int(pixel_height * 0.25), "width": int(pixel_width * 0.25), "height": int(pixel_height * 0.18), "role": "module"},
        {"x": int(pixel_width * 0.38), "y": int(pixel_height * 0.25), "width": int(pixel_width * 0.25), "height": int(pixel_height * 0.18), "role": "module"},
        {"x": int(pixel_width * 0.68), "y": int(pixel_height * 0.25), "width": int(pixel_width * 0.24), "height": int(pixel_height * 0.18), "role": "module"},
    ]


def _apply_overlay_style(shape: Any, title: bool = False) -> None:
    _try_set(shape, "FillForegnd", "RGB(255,255,255)")
    _try_set(shape, "FillTransparency", "12%")
    _try_set(shape, "LineColor", "RGB(70,90,115)")
    _try_set(shape, "LineWeight", "0.010 in")
    _try_set(shape, "Char.Size", "14 pt" if title else "10 pt")
    _try_set(shape, "Char.Font", '"Microsoft YaHei"')
    _try_set(shape, "Para.HorzAlign", "1")
    _try_set(shape, "VerticalAlign", "1")


def _try_set(shape: Any, cell_name: str, formula: str) -> None:
    try:
        shape.CellsU(cell_name).FormulaU = formula
    except Exception:
        pass


def _pause(visio: Any, delay: float) -> None:
    try:
        visio.ActiveWindow.Activate()
    except Exception:
        pass
    if delay > 0:
        time.sleep(delay)


if __name__ == "__main__":
    sys.exit(main())
