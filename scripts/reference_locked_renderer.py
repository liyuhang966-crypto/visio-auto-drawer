from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image


DEFAULT_PALETTE = {
    "green": "#9bd27f",
    "orange": "#f6a36f",
    "blue": "#8bb7e6",
    "gray": "#888888",
    "background_green": "#e8f6dc",
    "background_orange": "#fff0e5",
    "background_blue": "#eaf2ff",
    "white": "#ffffff",
}


STYLE_PRESETS = {
    "green_dashed_background": {"fill": "background_green", "line": "green", "dash": True, "transparency": 25},
    "orange_dashed_background": {"fill": "background_orange", "line": "orange", "dash": True, "transparency": 25},
    "gray_dashed_group": {"fill": "white", "line": "gray", "dash": True, "transparency": 100},
    "blue_module": {"fill": "background_blue", "line": "blue", "dash": False, "transparency": 0},
    "green_module": {"fill": "background_green", "line": "green", "dash": False, "transparency": 0},
    "orange_module": {"fill": "background_orange", "line": "orange", "dash": False, "transparency": 0},
    "loss_box": {"fill": "white", "line": "gray", "dash": False, "transparency": 0},
    "plain": {"fill": "white", "line": "gray", "dash": False, "transparency": 100},
}


def main() -> int:
    parser = argparse.ArgumentParser(description="按 reference-locked trace 复刻参考图为可编辑 Visio 图。")
    parser.add_argument("--reference-image", default="input/template.png")
    parser.add_argument("--trace", default="output/template_trace.json")
    parser.add_argument("--draft-trace", default="output/template_trace.draft.json")
    parser.add_argument("--output", default="output/reference_locked_result.vsdx")
    parser.add_argument("--project-root", default=str(Path.cwd()))
    parser.add_argument("--use-background-alignment", action="store_true")
    parser.add_argument("--hide-background-on-export", action="store_true")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    reference_image = _resolve(project_root, args.reference_image)
    trace_path = _resolve(project_root, args.trace)
    draft_trace_path = _resolve(project_root, args.draft_trace)
    output_path = _resolve(project_root, args.output)

    if not reference_image.exists():
        print(f"失败：未找到参考图：{reference_image}")
        return 1

    if trace_path.exists():
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        trace_source = trace_path
    else:
        trace = generate_draft_trace(reference_image)
        draft_trace_path.parent.mkdir(parents=True, exist_ok=True)
        draft_trace_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
        trace_source = draft_trace_path
        print(f"提示：未找到正式 trace，已生成草稿：{draft_trace_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    draw_reference_locked(trace, reference_image, output_path, args.use_background_alignment, args.hide_background_on_export)
    write_reference_fidelity_report(trace, reference_image, output_path, trace_source)
    print(f"成功：reference-locked 可编辑 Visio 图已生成：{output_path}")
    return 0


def generate_draft_trace(reference_image: Path) -> dict:
    with Image.open(reference_image) as image:
        width_px, height_px = image.size
    aspect_ratio = width_px / max(1, height_px)
    return {
        "page": {
            "width_px": width_px,
            "height_px": height_px,
            "aspect_ratio": round(aspect_ratio, 4),
        },
        "coordinate_mode": "normalized",
        "layout_signature": {
            "type": "paper_model_architecture",
            "main_direction": "left_to_right",
            "density": "compact",
            "preserve_density": True,
            "preserve_relative_positions": True,
            "allow_free_layout": False,
        },
        "regions": [
            {"id": "source_domain_region", "type": "input_image_group", "bbox": [0.02, 0.18, 0.22, 0.43], "style": "green_dashed_background"},
            {"id": "target_domain_region", "type": "input_image_group", "bbox": [0.02, 0.56, 0.22, 0.82], "style": "orange_dashed_background"},
            {"id": "main_network_region", "type": "dashed_group", "bbox": [0.26, 0.16, 0.66, 0.62], "style": "gray_dashed_group"},
            {"id": "source_branch_region", "type": "branch_group", "bbox": [0.70, 0.05, 0.82, 0.42], "style": "green_dashed_background"},
            {"id": "target_branch_region", "type": "branch_group", "bbox": [0.70, 0.58, 0.82, 0.96], "style": "orange_dashed_background"},
        ],
        "elements": [
            {"id": "source_image", "type": "image_placeholder", "bbox": [0.035, 0.25, 0.09, 0.40], "text": "", "style_ref": "plain", "semantic": "source domain image"},
            {"id": "target_image", "type": "image_placeholder", "bbox": [0.035, 0.63, 0.09, 0.79], "text": "", "style_ref": "plain", "semantic": "target domain image"},
            {"id": "main_backbone", "type": "dashed_group", "bbox": [0.26, 0.16, 0.66, 0.62], "text": "", "style_ref": "gray_dashed_group", "semantic": "main network region"},
            {"id": "backbone_placeholder", "type": "label", "bbox": [0.38, 0.36, 0.54, 0.45], "text": "主干网络结构\n请人工校正 elements 与 connectors", "style_ref": "blue_module", "semantic": "draft placeholder"},
        ],
        "connectors": [],
        "style_palette": DEFAULT_PALETTE,
        "manual_trace_required": True,
        "manual_trace_notes": [
            "这是自动草稿，只包含主要区域和占位元素。",
            "复杂论文模型图需要人工补充 elements.bbox 和 connectors.route_points。",
            "优先修正 regions、elements、connectors，而不是让程序自由布局。",
        ],
    }


def draw_reference_locked(trace: dict, reference_image: Path, output_path: Path, use_background: bool, hide_background: bool) -> None:
    import win32com.client  # type: ignore

    visio = win32com.client.Dispatch("Visio.Application")
    visio.Visible = True
    try:
        visio.AlertResponse = 1
    except Exception:
        pass

    doc, page = _get_or_create_document(visio, output_path)
    page_w, page_h = _page_size(trace)
    page.PageSheet.CellsU("PageWidth").ResultIU = page_w
    page.PageSheet.CellsU("PageHeight").ResultIU = page_h

    background = None
    if use_background:
        background = page.Import(str(reference_image))
        background.CellsU("PinX").ResultIU = page_w / 2
        background.CellsU("PinY").ResultIU = page_h / 2
        background.CellsU("Width").ResultIU = page_w
        background.CellsU("Height").ResultIU = page_h
        _try_set(background, "Transparency", "65%")
        background.SendToBack()

    shape_by_id: dict[str, Any] = {}
    for region in trace.get("regions", []):
        shape = _draw_element(page, region, trace, page_w, page_h, is_region=True)
        shape_by_id[region["id"]] = shape
        try:
            shape.SendToBack()
        except Exception:
            pass
        if background is not None:
            try:
                background.SendToBack()
            except Exception:
                pass

    for element in trace.get("elements", []):
        shape = _draw_element(page, element, trace, page_w, page_h, is_region=False)
        shape_by_id[element["id"]] = shape

    for connector in trace.get("connectors", []):
        _draw_connector(page, connector, trace, page_w, page_h)

    if background is not None and hide_background:
        try:
            background.Delete()
        except Exception:
            pass

    if output_path.exists():
        doc.Save()
    else:
        doc.SaveAs(str(output_path))

    png_path = output_path.with_suffix(".png")
    try:
        page.Export(str(png_path))
        print(f"成功：PNG 已导出：{png_path}")
    except Exception as exc:
        print(f"警告：PNG 导出失败：{exc}")


def _draw_element(page: Any, item: dict, trace: dict, page_w: float, page_h: float, is_region: bool) -> Any:
    item_type = item.get("type", "rounded_rect")
    left, bottom, right, top = _bbox_to_visio(item["bbox"], page_w, page_h)
    text = item.get("text", "")
    style_ref = item.get("style_ref") or item.get("style") or ("gray_dashed_group" if is_region else "blue_module")

    if item_type in {"image_placeholder", "image_patch", "image_cube"} and item.get("image"):
        shape = page.Import(str(Path(item["image"]).expanduser()))
        shape.CellsU("PinX").ResultIU = (left + right) / 2
        shape.CellsU("PinY").ResultIU = (bottom + top) / 2
        shape.CellsU("Width").ResultIU = right - left
        shape.CellsU("Height").ResultIU = top - bottom
        return shape

    if item_type in {"cube", "conv3d_block", "image_cube"}:
        shape = _draw_cube(page, left, bottom, right, top)
    else:
        shape = page.DrawRectangle(left, bottom, right, top)
        shape.Text = text

    _apply_trace_style(shape, trace, style_ref, item_type, is_region)
    if item_type in {"vertical_text", "vertical_operation_block"}:
        shape.Text = _verticalize(text)
    if item_type == "label":
        _try_set(shape, "LinePattern", "0")
        _try_set(shape, "FillPattern", "0")
    return shape


def _draw_connector(page: Any, connector: dict, trace: dict, page_w: float, page_h: float) -> list[Any]:
    route_points = connector.get("route_points") or []
    if len(route_points) < 2:
        return []
    points = [_point_to_visio(point, page_w, page_h) for point in route_points]
    lines = []
    for index, (start, end) in enumerate(zip(points, points[1:])):
        line = page.DrawLine(start[0], start[1], end[0], end[1])
        _apply_connector_style(line, connector.get("style", "black_arrow"), arrow=index == len(points) - 2)
        lines.append(line)
    return lines


def write_reference_fidelity_report(trace: dict, reference_image: Path, output_path: Path, trace_source: Path) -> None:
    output = output_path.parent / "reference_fidelity_report.md"
    regions = trace.get("regions", [])
    elements = trace.get("elements", [])
    connectors = trace.get("connectors", [])
    manual_required = bool(trace.get("manual_trace_required")) or not connectors or len(elements) < 6
    checks = [
        ("页面比例是否记录", "通过" if trace.get("page", {}).get("aspect_ratio") else "失败"),
        ("主方向是否锁定", "通过" if trace.get("layout_signature", {}).get("main_direction") else "失败"),
        ("主要区域位置是否由 trace 描述", "通过" if len(regions) >= 3 else "需要修正"),
        ("主要元素是否由 trace 描述", "通过" if len(elements) >= 6 else "需要修正"),
        ("箭头路径是否由 route_points 描述", "通过" if connectors and all(c.get("route_points") for c in connectors) else "需要人工校正"),
        ("是否禁止自由布局", "通过" if trace.get("layout_signature", {}).get("allow_free_layout") is False else "失败"),
        ("是否需要人工校正 template_trace.json", "是" if manual_required else "否"),
    ]
    lines = [
        "# Reference Locked 复刻质量报告",
        "",
        f"参考图：`{reference_image}`",
        f"trace 来源：`{trace_source}`",
        f"输出文件：`{output_path}`",
        "",
        "## 检查项",
        "",
    ]
    for name, status in checks:
        lines.append(f"- {status}：{name}")
    lines.extend(["", "## 结论", ""])
    if manual_required:
        lines.append("需要人工校正：当前 trace 仍偏草稿，复杂论文图应优先补充元素 bbox 和连接线 route_points。")
    else:
        lines.append("通过：当前 trace 已包含主要区域、元素和连接线，可继续微调局部坐标提升相似度。")
    lines.extend([
        "",
        "## 建议优先修改的字段",
        "",
        "- `regions[].bbox`：控制源域、目标域、主干网络、右侧分支等大区域的位置和比例。",
        "- `elements[].bbox`：控制小模块、损失框、竖排操作块、图像占位块的位置和大小。",
        "- `connectors[].route_points`：控制箭头路径，避免程序自由路由。",
        "- `style_palette` 和 `style_ref`：控制浅色背景、虚线框、箭头颜色和模块配色。",
    ])
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"成功：reference_fidelity_report 已生成：{output}")


def _get_or_create_document(visio: Any, output_path: Path) -> tuple[Any, Any]:
    output_path = output_path.resolve()
    for index in range(1, visio.Documents.Count + 1):
        doc = visio.Documents.Item(index)
        try:
            if Path(str(doc.FullName)).resolve() == output_path:
                page = doc.Pages.Item(1)
                _clear_page(page)
                print(f"复用已打开的 Visio 文件：{output_path}")
                return doc, page
        except Exception:
            pass
    if output_path.exists():
        doc = visio.Documents.Open(str(output_path))
        page = doc.Pages.Item(1)
        _clear_page(page)
        print(f"打开并复用已有 Visio 文件：{output_path}")
        return doc, page
    doc = visio.Documents.Add("")
    page = doc.Pages.Item(1)
    print("创建新的 Visio 文件。")
    return doc, page


def _clear_page(page: Any) -> None:
    for index in range(page.Shapes.Count, 0, -1):
        try:
            page.Shapes.Item(index).Delete()
        except Exception:
            pass


def _page_size(trace: dict) -> tuple[float, float]:
    aspect = float(trace.get("page", {}).get("aspect_ratio") or 1.78)
    width = 13.0
    return width, width / max(0.1, aspect)


def _bbox_to_visio(bbox: list[float], page_w: float, page_h: float) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = bbox
    return x1 * page_w, (1 - y2) * page_h, x2 * page_w, (1 - y1) * page_h


def _point_to_visio(point: list[float], page_w: float, page_h: float) -> tuple[float, float]:
    return point[0] * page_w, (1 - point[1]) * page_h


def _draw_cube(page: Any, left: float, bottom: float, right: float, top: float) -> Any:
    depth_x = min((right - left) * 0.28, 0.18)
    depth_y = min((top - bottom) * 0.40, 0.16)
    back = page.DrawRectangle(left + depth_x, bottom + depth_y, right, top)
    front = page.DrawRectangle(left, bottom, right - depth_x, top - depth_y)
    for shape, fill in [(back, "RGB(118,154,218)"), (front, "RGB(76,118,196)")]:
        _try_set(shape, "FillForegnd", fill)
        _try_set(shape, "LineColor", "RGB(24,48,92)")
        _try_set(shape, "LineWeight", "0.014 in")
    for line in [
        page.DrawLine(left, top - depth_y, left + depth_x, top),
        page.DrawLine(right - depth_x, top - depth_y, right, top),
        page.DrawLine(right - depth_x, bottom, right, bottom + depth_y),
    ]:
        _try_set(line, "LineColor", "RGB(24,48,92)")
        _try_set(line, "LineWeight", "0.014 in")
    return front


def _apply_trace_style(shape: Any, trace: dict, style_ref: str, item_type: str, is_region: bool) -> None:
    palette = {**DEFAULT_PALETTE, **trace.get("style_palette", {})}
    preset = STYLE_PRESETS.get(style_ref, STYLE_PRESETS.get("blue_module", {}))
    fill = _hex_to_rgb_formula(palette.get(preset.get("fill", "white"), preset.get("fill", "#ffffff")))
    line = _hex_to_rgb_formula(palette.get(preset.get("line", "gray"), preset.get("line", "#888888")))
    _try_set(shape, "FillForegnd", fill)
    _try_set(shape, "LineColor", line)
    _try_set(shape, "LineWeight", "0.010 in" if is_region else "0.014 in")
    _try_set(shape, "LinePattern", "2" if preset.get("dash") else "1")
    if preset.get("transparency", 0):
        _try_set(shape, "FillTransparency", f"{preset['transparency']}%")
    _try_set(shape, "Char.Font", '"Microsoft YaHei"')
    _try_set(shape, "Char.Size", "8.5 pt" if item_type not in {"vertical_text", "vertical_operation_block"} else "9.5 pt")
    _try_set(shape, "Para.HorzAlign", "1")
    _try_set(shape, "VerticalAlign", "1")
    _try_set(shape, "Rounding", "0.04 in")


def _apply_connector_style(line: Any, style: str, arrow: bool = True) -> None:
    colors = {
        "green_arrow": "RGB(128,205,105)",
        "orange_arrow": "RGB(245,145,80)",
        "black_arrow": "RGB(0,0,0)",
        "blue_arrow": "RGB(80,125,200)",
        "dashed_arrow": "RGB(120,120,120)",
    }
    _try_set(line, "LineColor", colors.get(style, "RGB(0,0,0)"))
    _try_set(line, "LineWeight", "0.014 in")
    if "dashed" in style:
        _try_set(line, "LinePattern", "2")
    if arrow:
        _try_set(line, "BeginArrow", "0")
        _try_set(line, "EndArrow", "13")
    else:
        _try_set(line, "EndArrow", "0")


def _verticalize(text: str) -> str:
    if "\n" in text:
        return text
    return "\n".join(text)


def _hex_to_rgb_formula(value: str) -> str:
    if not value or not value.startswith("#") or len(value) != 7:
        return value if value.startswith("RGB(") else "RGB(255,255,255)"
    r = int(value[1:3], 16)
    g = int(value[3:5], 16)
    b = int(value[5:7], 16)
    return f"RGB({r},{g},{b})"


def _try_set(shape: Any, cell_name: str, formula: str) -> None:
    try:
        shape.CellsU(cell_name).FormulaU = formula
    except Exception:
        pass


def _resolve(project_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return project_root / path


if __name__ == "__main__":
    raise SystemExit(main())
