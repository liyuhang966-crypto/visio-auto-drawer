from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import textwrap
import time
from typing import Any

from export_assets import export_png
from icon_library import draw_icon
from layout import apply_auto_layout
from drawdsl import write_drawdsl
from lesson_store import record_lesson
from preview_review import review_preview, write_preview_review
from quality_check import generate_quality_report
from reference_fidelity_check import run_reference_fidelity_check, write_reference_fidelity_report
from reference_reproduction_guard import enforce_reference_reproduction, is_reference_reproduction_task
from schema import Diagram, Node
from collision_detector import write_collision_report
from trace_repair_advisor import build_repair_suggestions, write_trace_repair_suggestions
from visual_rules import DEFAULT_LIMITS


STYLE_PALETTE = {
    "default": {"fill": "RGB(245,248,252)", "line": "RGB(86,102,120)"},
    "primary": {"fill": "RGB(224,238,255)", "line": "RGB(45,95,170)"},
    "main_blue": {"fill": "RGB(250,253,255)", "line": "RGB(20,67,135)"},
    "center_blue": {"fill": "RGB(241,248,255)", "line": "RGB(20,78,168)"},
    "success": {"fill": "RGB(229,246,236)", "line": "RGB(65,135,90)"},
    "warning": {"fill": "RGB(255,244,220)", "line": "RGB(170,120,35)"},
    "danger": {"fill": "RGB(255,232,232)", "line": "RGB(170,65,65)"},
    "soft_blue": {"fill": "RGB(239,247,255)", "line": "RGB(45,105,205)"},
    "soft_green": {"fill": "RGB(239,250,242)", "line": "RGB(54,145,78)"},
    "soft_orange": {"fill": "RGB(255,247,236)", "line": "RGB(210,120,38)"},
    "soft_red": {"fill": "RGB(255,239,239)", "line": "RGB(205,75,75)"},
    "container": {"fill": "RGB(250,250,250)", "line": "RGB(150,160,170)"},
    "blue_group": {"fill": "RGB(250,253,255)", "line": "RGB(72,134,220)"},
    "green_group": {"fill": "RGB(250,255,250)", "line": "RGB(76,160,88)"},
    "note": {"fill": "RGB(252,254,255)", "line": "RGB(50,116,205)"},
    "group_title": {"fill": "RGB(255,255,255)", "line": "RGB(255,255,255)"},
    "separator": {"fill": "RGB(255,255,255)", "line": "RGB(145,155,170)"},
    "nn_block": {"fill": "RGB(255,255,255)", "line": "RGB(28,45,78)"},
    "pool_orange": {"fill": "RGB(255,243,232)", "line": "RGB(255,205,168)"},
    "conv_blue": {"fill": "RGB(235,242,255)", "line": "RGB(145,172,220)"},
    "feature_blue": {"fill": "RGB(82,122,196)", "line": "RGB(22,48,92)"},
    "paper_blue": {"fill": "RGB(235,243,255)", "line": "RGB(53,83,135)"},
    "paper_green": {"fill": "RGB(229,247,216)", "line": "RGB(133,205,110)"},
    "paper_orange": {"fill": "RGB(255,236,222)", "line": "RGB(245,168,112)"},
    "paper_gray": {"fill": "RGB(255,255,255)", "line": "RGB(155,155,155)"},
    "loss_box": {"fill": "RGB(250,252,255)", "line": "RGB(45,64,105)"},
    "plain_label": {"fill": "RGB(255,255,255)", "line": "RGB(255,255,255)"},
}


def main() -> int:
    parser = argparse.ArgumentParser(description="在可见的 Microsoft Visio 中绘制图。")
    parser.add_argument("--diagram", default="output/diagram.json")
    parser.add_argument("--project-root", default=str(Path.cwd()))
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    diagram_path = Path(args.diagram)
    if not diagram_path.is_absolute():
        diagram_path = project_root / diagram_path

    try:
        diagram = load_diagram(diagram_path)
        if args.output:
            diagram.output = args.output
        diagram = apply_auto_layout(diagram)
    except Exception as exc:
        print(f"失败：无法读取或校验图结构 JSON: {diagram_path}")
        print(f"原因：{exc}")
        return 1

    output_path = Path(diagram.output)
    if not output_path.is_absolute():
        output_path = project_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import win32com.client  # type: ignore
    except ModuleNotFoundError:
        print("失败：ModuleNotFoundError: win32com。")
        print("请运行 scripts\\setup_env.ps1，在本地 .venv 中安装 pywin32。")
        return 2

    try:
        reference_passed = draw(diagram, output_path, project_root, diagram_path)
        if reference_passed is False:
            print(f"Visio 图纸已保存到 {output_path}")
            print("复刻未通过，需要继续调整。请查看 output\\reference_fidelity_report.md、output\\collision_report.md 和 output\\trace_repair_suggestions.md。")
            return 2
        else:
            print(f"成功：Visio 图纸已保存到 {output_path}")
        return 0
    except Exception as exc:
        print("失败：Visio COM 绘图过程出错。")
        print(f"原因：{exc}")
        print("排查建议：")
        print("- 确认安装的是 Microsoft Visio 桌面版，而不只是 Visio 网页版。")
        print("- 运行 scripts\\run_test.ps1，验证 Visio.Application 是否能启动。")
        print("- 如果 COM 激活失败，请检查 Python 与 Office/Visio 的位数兼容性。")
        return 3


def load_diagram(path: Path) -> Diagram:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    raw, messages = enforce_reference_reproduction(raw)
    for message in messages:
        print(message)
    return Diagram.model_validate(raw)


def draw(diagram: Diagram, output_path: Path, project_root: Path, diagram_path: Path) -> bool | None:
    import win32com.client  # type: ignore

    drawdsl_path = project_root / "output" / "drawdsl.json"
    write_drawdsl(diagram, drawdsl_path)
    print(f"成功：DrawDSL 已生成：{drawdsl_path}")

    visio = win32com.client.Dispatch("Visio.Application")
    visio.Visible = True
    try:
        visio.AlertResponse = 1
    except Exception:
        pass
    doc, page = _get_reusable_document(visio, output_path)
    page.PageSheet.CellsU("PageWidth").ResultIU = diagram.page.width
    page.PageSheet.CellsU("PageHeight").ResultIU = diagram.page.height

    delay = diagram.animation.delay_seconds if diagram.animation.enabled else 0

    drawn_shapes: list[Any] = []

    group_shapes = draw_groups(page, diagram)
    drawn_shapes.extend(group_shapes)
    for shape in group_shapes:
        _pause(visio, delay)

    shapes: dict[str, Any] = {}
    for node in diagram.nodes:
        shape, parts = draw_node(page, node)
        shapes[node.id] = shape
        drawn_shapes.append(shape)
        drawn_shapes.extend(parts)
        _pause(visio, delay)

    for edge in diagram.edges:
        begin = shapes[edge.from_]
        end = shapes[edge.to]
        edge_shape = draw_edge(page, begin, end, edge)
        if isinstance(edge_shape, list):
            drawn_shapes.extend(edge_shape)
        elif edge_shape is not None:
            drawn_shapes.append(edge_shape)
        _pause(visio, delay)

    if diagram.title:
        title = page.DrawRectangle(0.3, diagram.page.height - 0.55, diagram.page.width - 0.3, diagram.page.height - 0.12)
        title.Text = diagram.title
        title.CellsU("LinePattern").FormulaU = "0"
        title.CellsU("FillPattern").FormulaU = "0"
        title.CellsU("Char.Size").FormulaU = "15 pt"
        title.CellsU("Char.Style").FormulaU = "1"
        title.CellsU("Para.HorzAlign").FormulaU = "1"
        title.CellsU("VerticalAlign").FormulaU = "1"
        drawn_shapes.append(title)
        _pause(visio, delay)

    if diagram.template_fidelity.enabled or diagram.optimization.enabled:
        polish_page(page, diagram, output_path, drawn_shapes)

    _clear_selection(visio)

    if output_path.exists():
        doc.Save()
    else:
        doc.SaveAs(str(output_path))
    preview_passed = True
    if diagram.export.png:
        ok, result = export_png(doc, output_path)
        if ok:
            print(f"成功：PNG 已导出到 {result}")
            if not diagram.template_fidelity.enabled:
                preview_passed = run_preview_review(project_root, Path(result), drawdsl_path, output_path)
        else:
            print(f"警告：{result}")
            preview_passed = False
    if diagram.template_fidelity.enabled:
        report_path = generate_quality_report(diagram, output_path.parents[1], output_path)
        print(f"成功：模板复刻质量报告已生成：{report_path}")
        reference_passed = run_reference_reports(diagram, project_root, diagram_path)
        png_path = output_path.with_suffix(".png")
        if png_path.exists():
            preview_passed = run_preview_review(project_root, png_path, drawdsl_path, output_path)
            reference_passed = reference_passed and preview_passed
        return reference_passed and preview_passed
    return None if preview_passed else False


def _clear_selection(visio: Any) -> None:
    try:
        visio.ActiveWindow.DeselectAll()
        return
    except Exception:
        pass
    try:
        selection = visio.ActiveWindow.Selection
        selection.DeselectAll()
    except Exception:
        pass


def run_preview_review(project_root: Path, png_path: Path, drawdsl_path: Path, output_path: Path) -> bool:
    collision_report = project_root / "output" / "collision_report.md"
    result = review_preview(png_path, drawdsl_path, collision_report)
    review_path = project_root / "output" / "preview_review.md"
    review_json_path = project_root / "output" / "preview_review.json"
    write_preview_review(result, review_path, png_path)
    review_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"成功：PNG preview 自检报告已生成：{review_path}")
    lesson_md = project_root / "output" / "lessons" / "reference_reproduction_lessons.md"
    recorded = record_lesson(output_path.stem, result, project_root / "output" / "lessons", lesson_md)
    if recorded:
        print(f"提示：已沉淀失败 lesson：{lesson_md}")
    return bool(result["passed"])


def run_reference_reports(diagram: Diagram, project_root: Path, diagram_path: Path) -> bool:
    trace_path = project_root / diagram.template_fidelity.trace_file
    trace = {}
    if trace_path.exists():
        try:
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"警告：template_trace.json 读取失败：{exc}")
    if not is_reference_reproduction_task({"template_fidelity": diagram.template_fidelity.model_dump(), "reference_locked": diagram.reference_locked.model_dump()}):
        return True

    result = run_reference_fidelity_check(diagram, trace)
    report_path = project_root / "output" / "reference_fidelity_report.md"
    collision_path = project_root / "output" / "collision_report.md"
    collision_json_path = project_root / "output" / "collision_issues.json"
    repair_path = project_root / "output" / "trace_repair_suggestions.md"
    write_reference_fidelity_report(result, report_path, diagram_path, trace_path if trace_path.exists() else None)
    write_collision_report(result["collisions"], collision_path)
    collision_json_path.write_text(json.dumps(result["collisions"], ensure_ascii=False, indent=2), encoding="utf-8")
    suggestions = build_repair_suggestions(collisions=result["collisions"], trace=trace)
    write_trace_repair_suggestions(suggestions, repair_path)
    print(f"成功：reference fidelity 报告已生成：{report_path}")
    print(f"成功：碰撞检测报告已生成：{collision_path}")
    print(f"成功：trace 修复建议已生成：{repair_path}")
    return bool(result["passed"])


def _get_reusable_document(visio: Any, output_path: Path) -> tuple[Any, Any]:
    output_path = output_path.resolve()
    doc = _find_open_document(visio, output_path)
    if doc is not None:
        print(f"复用已打开的 Visio 文件：{output_path}")
    elif output_path.exists():
        print(f"打开并复用已有 Visio 文件：{output_path}")
        doc = visio.Documents.Open(str(output_path))
    else:
        print("创建新的 Visio 文件。")
        doc = visio.Documents.Add("")
    page = doc.Pages.Item(1)
    try:
        visio.ActiveWindow.Page = page
    except Exception:
        pass
    _clear_page(page)
    return doc, page


def _find_open_document(visio: Any, output_path: Path) -> Any | None:
    for index in range(1, visio.Documents.Count + 1):
        doc = visio.Documents.Item(index)
        try:
            full_name = Path(str(doc.FullName)).resolve()
        except Exception:
            continue
        if full_name == output_path:
            return doc
    return None


def _document_has_path(doc: Any) -> bool:
    try:
        return bool(str(doc.FullName))
    except Exception:
        return False


def _clear_page(page: Any) -> None:
    for index in range(page.Shapes.Count, 0, -1):
        try:
            page.Shapes.Item(index).Delete()
        except Exception:
            pass


def draw_groups(page: Any, diagram: Diagram) -> list[Any]:
    shapes = []
    nodes = {node.id: node for node in diagram.nodes}
    for group in diagram.groups:
        group_nodes = [nodes[node_id] for node_id in group.node_ids if node_id in nodes]
        if not group_nodes:
            continue

        left = min((node.x or 0) - node.width / 2 for node in group_nodes) - 0.35
        right = max((node.x or 0) + node.width / 2 for node in group_nodes) + 0.35
        bottom = min((node.y or 0) - node.height / 2 for node in group_nodes) - 0.35
        top = max((node.y or 0) + node.height / 2 for node in group_nodes) + 0.6
        shape = page.DrawRectangle(left, bottom, right, top)
        shape.Text = group.text
        shape.SendToBack()
        _apply_style(shape, group.style or "container", is_group=True)
        shapes.append(shape)
    return shapes


def draw_node(page: Any, node: Node) -> tuple[Any, list[Any]]:
    x = node.x or 1.0
    y = node.y or 1.0
    left = x - node.width / 2
    right = x + node.width / 2
    bottom = y - node.height / 2
    top = y + node.height / 2

    parts: list[Any] = []
    if node.shape == "image" or node.image:
        shape = _draw_image_node(page, node, left, bottom, right, top)
        return shape, parts
    if node.shape == "block3d":
        shape, parts = _draw_3d_block(page, left, bottom, right, top, node.style)
        return shape, parts
    if node.shape in {"database", "actor", "cloud"}:
        shape = page.DrawOval(left, bottom, right, top)
    elif node.shape == "decision":
        shape = _draw_diamond(page, x, y, node.width, node.height)
    else:
        shape = page.DrawRectangle(left, bottom, right, top)
        if node.shape in {"rounded_box", "terminator"}:
            _try_set(shape, "Rounding", "0.18 in")

    _apply_style(shape, node.style)
    if node.icon:
        shape.Text = ""
        icon_zone_width = min(node.width * 0.20, 0.52)
        icon_x = left + icon_zone_width / 2 + 0.10
        icon_size = min(node.height * 0.48, icon_zone_width * 0.72, 0.34)
        parts.extend(draw_icon(page, node.icon, icon_x, y, size=icon_size, color=_style_line_color(node.style)))

        title, body = _split_title_body(node.text)
        text_left = left + icon_zone_width + 0.10
        text_right = right - 0.12
        title_h = min(0.38, max(0.33, node.height * 0.40))
        title_box = page.DrawRectangle(text_left, y + 0.04, text_right, y + 0.04 + title_h)
        title_box.Text = _wrap_text(title, width=max(9, int((text_right - text_left) * 6.4)))
        title_font = max(DEFAULT_LIMITS["title_font_min"], 11.2 if node.height < 1.02 else 11.8)
        _apply_inner_text_style(title_box, bold=True, font_size=title_font)
        body_box = page.DrawRectangle(text_left, bottom + 0.13, text_right, y + 0.00)
        body_box.Text = _wrap_text(body, width=max(9, int((text_right - text_left) * 6.2)))
        body_font = max(DEFAULT_LIMITS["body_font_min"], 9.0 if len(body) > 24 else 9.4)
        _apply_inner_text_style(body_box, bold=False, font_size=body_font)
        parts.extend([title_box, body_box])
    else:
        shape.Text = _wrap_text(node.text)
    return shape, parts


def _draw_image_node(page: Any, node: Node, left: float, bottom: float, right: float, top: float) -> Any:
    if not node.image:
        shape = page.DrawRectangle(left, bottom, right, top)
        shape.Text = _wrap_text(node.text)
        _apply_style(shape, node.style)
        return shape
    image_path = Path(node.image).expanduser()
    if not image_path.is_absolute():
        image_path = Path.cwd() / image_path
    shape = page.Import(str(image_path))
    shape.CellsU("PinX").ResultIU = (left + right) / 2
    shape.CellsU("PinY").ResultIU = (bottom + top) / 2
    shape.CellsU("Width").ResultIU = right - left
    shape.CellsU("Height").ResultIU = top - bottom
    try:
        shape.Text = ""
    except Exception:
        pass
    return shape


def _draw_3d_block(page: Any, left: float, bottom: float, right: float, top: float, style_name: str) -> tuple[Any, list[Any]]:
    width = right - left
    height = top - bottom
    depth_x = min(width * 0.28, 0.22)
    depth_y = min(height * 0.42, 0.20)
    front_right = right - depth_x
    back_left = left + depth_x
    front_top = top - depth_y
    back_bottom = bottom + depth_y

    back = page.DrawRectangle(back_left, back_bottom, right, top)
    front = page.DrawRectangle(left, bottom, front_right, front_top)
    _try_set(back, "FillForegnd", "RGB(118,154,218)")
    _try_set(front, "FillForegnd", "RGB(76,118,196)")
    for shape in [back, front]:
        _try_set(shape, "LineColor", "RGB(24,48,92)")
        _try_set(shape, "LineWeight", "0.018 in")
        _try_set(shape, "Char.Size", "1 pt")

    edges = [
        page.DrawLine(left, front_top, back_left, top),
        page.DrawLine(front_right, front_top, right, top),
        page.DrawLine(front_right, bottom, right, back_bottom),
    ]
    for line in edges:
        _try_set(line, "LineColor", "RGB(24,48,92)")
        _try_set(line, "LineWeight", "0.018 in")
    anchor = page.DrawRectangle(left, bottom, right, top)
    anchor.Text = ""
    _try_set(anchor, "LinePattern", "0")
    _try_set(anchor, "FillPattern", "0")
    return anchor, [back, front, *edges]


def draw_edge(page: Any, begin_shape: Any, end_shape: Any, edge: Any) -> Any:
    if edge.line_type in {"status_feedback", "aux"} and edge.semantic is None:
        print(f"警告：跳过无明确语义的辅助/状态线：{edge.from_} -> {edge.to}")
        return None
    if edge.route_points and len(edge.route_points) >= 2:
        lines = []
        points = [(float(point[0]), float(point[1])) for point in edge.route_points]
        points = _simplify_route_points(points)
        for index in range(len(points) - 1):
            line = page.DrawLine(points[index][0], points[index][1], points[index + 1][0], points[index + 1][1])
            _style_edge(line, edge, arrow=index == len(points) - 2)
            lines.append(line)
        if edge.text:
            label_x = edge.label_x if edge.label_x is not None else (points[0][0] + points[-1][0]) / 2
            label_y = edge.label_y if edge.label_y is not None else (points[0][1] + points[-1][1]) / 2 + 0.18
            _draw_edge_label(page, label_x, label_y, edge.text)
        return lines
    if edge.route in {"right_then_down", "left_to_right", "bottom_feedback", "dashed_feedback", "vertical_control", "straight_horizontal", "straight_vertical", "direct_straight"}:
        return _draw_routed_edge(page, begin_shape, end_shape, edge)

    begin_x = begin_shape.CellsU("PinX").ResultIU
    begin_y = begin_shape.CellsU("PinY").ResultIU
    end_x = end_shape.CellsU("PinX").ResultIU
    end_y = end_shape.CellsU("PinY").ResultIU
    begin_w = begin_shape.CellsU("Width").ResultIU
    end_w = end_shape.CellsU("Width").ResultIU

    if edge.route_y is not None:
        route_y = edge.route_y
        if begin_x <= end_x:
            begin_x = begin_x + begin_w / 2
            end_x = end_x - end_w / 2
        else:
            begin_x = begin_x - begin_w / 2
            end_x = end_x + end_w / 2
        begin_y = route_y
        end_y = route_y

    line = page.DrawLine(begin_x, begin_y, end_x, end_y)
    _style_edge(line, edge)

    if edge.text:
        label_x = edge.label_x if edge.label_x is not None else (begin_x + end_x) / 2
        label_y = edge.label_y if edge.label_y is not None else (begin_y + end_y) / 2
        _draw_edge_label(page, label_x, label_y, edge.text)

    return line


def _draw_routed_edge(page: Any, begin_shape: Any, end_shape: Any, edge: Any) -> Any:
    route = edge.route or "left_to_right"

    if route == "straight_horizontal":
        points = _straight_horizontal_points(begin_shape, end_shape) or _fallback_points(begin_shape, end_shape, "left_to_right")
    elif route == "straight_vertical":
        points = _straight_vertical_points(begin_shape, end_shape) or _fallback_points(begin_shape, end_shape, "vertical_control")
    elif route == "direct_straight":
        sx, sy = _edge_point(begin_shape, end_shape, "auto")
        ex, ey = _edge_point(end_shape, begin_shape, "auto")
        points = [(sx, sy), (ex, ey)]
    elif route == "vertical_control":
        straight_points = _straight_vertical_points(begin_shape, end_shape)
        if straight_points:
            points = straight_points
        else:
            sx, sy = _edge_point(begin_shape, end_shape, route)
            ex, ey = _edge_point(end_shape, begin_shape, route)
            if abs(sx - ex) <= 0.12:
                points = [(sx, sy), (ex, ey)]
            else:
                mid_y = (sy + ey) / 2
                points = [(sx, sy), (sx, mid_y), (ex, mid_y), (ex, ey)]
    elif route == "left_to_right":
        straight_points = _straight_horizontal_points(begin_shape, end_shape)
        if straight_points:
            points = straight_points
        else:
            sx, sy = _edge_point(begin_shape, end_shape, route)
            ex, ey = _edge_point(end_shape, begin_shape, route)
            if abs(sy - ey) <= 0.12:
                points = [(sx, sy), (ex, ey)]
            else:
                mid_x = (sx + ex) / 2
                points = [(sx, sy), (mid_x, sy), (mid_x, ey), (ex, ey)]
    elif route == "right_then_down":
        straight_points = _straight_horizontal_points(begin_shape, end_shape)
        if straight_points:
            points = straight_points
        else:
            sx, sy = _edge_point(begin_shape, end_shape, route)
            ex, ey = _edge_point(end_shape, begin_shape, route)
            if abs(sy - ey) <= 0.12:
                points = [(sx, sy), (ex, ey)]
            else:
                points = [(sx, sy), (ex, sy), (ex, ey)]
    elif route in {"bottom_feedback", "dashed_feedback"}:
        sx, sy = _edge_point(begin_shape, end_shape, route)
        ex, ey = _edge_point(end_shape, begin_shape, route)
        bottom_y = 0.65
        points = [(sx, sy), (sx, bottom_y), (ex, bottom_y), (ex, ey)]
    else:
        sx, sy = _edge_point(begin_shape, end_shape, route)
        ex, ey = _edge_point(end_shape, begin_shape, route)
        if abs(sx - ex) <= 0.12:
            points = [(sx, sy), (ex, ey)]
        else:
            mid_x = (sx + ex) / 2
            points = [(sx, sy), (mid_x, sy), (mid_x, ey), (ex, ey)]
    points = _simplify_route_points(points)

    last_line = None
    lines = []
    for index in range(len(points) - 1):
        last_line = page.DrawLine(points[index][0], points[index][1], points[index + 1][0], points[index + 1][1])
        _style_edge(last_line, edge, arrow=index == len(points) - 2)
        lines.append(last_line)

    if edge.text:
        label_anchor_a = points[min(1, len(points) - 1)]
        label_anchor_b = points[max(0, len(points) - 2)]
        label_x = edge.label_x if edge.label_x is not None else (label_anchor_a[0] + label_anchor_b[0]) / 2
        label_y = edge.label_y if edge.label_y is not None else (label_anchor_a[1] + label_anchor_b[1]) / 2 + 0.18
        _draw_edge_label(page, label_x, label_y, edge.text)

    return lines


def _edge_point(source: Any, target: Any, route: str = "auto") -> tuple[float, float]:
    sx = source.CellsU("PinX").ResultIU
    sy = source.CellsU("PinY").ResultIU
    sw = source.CellsU("Width").ResultIU
    sh = source.CellsU("Height").ResultIU
    tx = target.CellsU("PinX").ResultIU
    ty = target.CellsU("PinY").ResultIU
    if route == "vertical_control":
        return (sx, sy + (sh / 2 if ty >= sy else -sh / 2))
    if route in {"left_to_right", "right_then_down"}:
        return (sx + (sw / 2 if tx >= sx else -sw / 2), sy)
    if abs(tx - sx) >= abs(ty - sy):
        return (sx + (sw / 2 if tx >= sx else -sw / 2), sy)
    return (sx, sy + (sh / 2 if ty >= sy else -sh / 2))


def _fallback_points(begin_shape: Any, end_shape: Any, route: str) -> list[tuple[float, float]]:
    sx, sy = _edge_point(begin_shape, end_shape, route)
    ex, ey = _edge_point(end_shape, begin_shape, route)
    if route == "vertical_control":
        mid_y = (sy + ey) / 2
        return [(sx, sy), (sx, mid_y), (ex, mid_y), (ex, ey)]
    mid_x = (sx + ex) / 2
    return [(sx, sy), (mid_x, sy), (mid_x, ey), (ex, ey)]


def _straight_horizontal_points(begin_shape: Any, end_shape: Any) -> list[tuple[float, float]] | None:
    b_left, b_bottom, b_right, b_top = _shape_bounds(begin_shape)
    e_left, e_bottom, e_right, e_top = _shape_bounds(end_shape)
    padding = DEFAULT_LIMITS["axis_overlap_padding"]
    low = max(b_bottom + padding, e_bottom + padding)
    high = min(b_top - padding, e_top - padding)
    if low > high:
        return None
    by = begin_shape.CellsU("PinY").ResultIU
    ey = end_shape.CellsU("PinY").ResultIU
    y = _clamp((by + ey) / 2, low, high)
    if begin_shape.CellsU("PinX").ResultIU <= end_shape.CellsU("PinX").ResultIU:
        return [(b_right, y), (e_left, y)]
    return [(b_left, y), (e_right, y)]


def _straight_vertical_points(begin_shape: Any, end_shape: Any) -> list[tuple[float, float]] | None:
    b_left, b_bottom, b_right, b_top = _shape_bounds(begin_shape)
    e_left, e_bottom, e_right, e_top = _shape_bounds(end_shape)
    padding = DEFAULT_LIMITS["axis_overlap_padding"]
    low = max(b_left + padding, e_left + padding)
    high = min(b_right - padding, e_right - padding)
    if low > high:
        return None
    bx = begin_shape.CellsU("PinX").ResultIU
    ex = end_shape.CellsU("PinX").ResultIU
    x = _clamp((bx + ex) / 2, low, high)
    if begin_shape.CellsU("PinY").ResultIU <= end_shape.CellsU("PinY").ResultIU:
        return [(x, b_top), (x, e_bottom)]
    return [(x, b_bottom), (x, e_top)]


def _shape_bounds(shape: Any) -> tuple[float, float, float, float]:
    x = shape.CellsU("PinX").ResultIU
    y = shape.CellsU("PinY").ResultIU
    w = shape.CellsU("Width").ResultIU
    h = shape.CellsU("Height").ResultIU
    return x - w / 2, y - h / 2, x + w / 2, y + h / 2


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _simplify_route_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    cleaned: list[tuple[float, float]] = []
    min_segment = DEFAULT_LIMITS["min_connector_segment"]
    for point in points:
        if cleaned and _point_distance(cleaned[-1], point) < min_segment:
            cleaned[-1] = point
        else:
            cleaned.append(point)
    index = 1
    while index < len(cleaned) - 1:
        prev_p, curr_p, next_p = cleaned[index - 1], cleaned[index], cleaned[index + 1]
        if (abs(prev_p[0] - curr_p[0]) < 0.03 and abs(curr_p[0] - next_p[0]) < 0.03) or (
            abs(prev_p[1] - curr_p[1]) < 0.03 and abs(curr_p[1] - next_p[1]) < 0.03
        ):
            cleaned.pop(index)
        else:
            index += 1
    return cleaned


def _point_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _style_edge(line: Any, edge: Any, arrow: bool = True) -> None:
    color = {
        "data": "RGB(40,103,205)",
        "control": "RGB(48,145,72)",
        "feedback": "RGB(105,115,130)",
        "status_feedback": "RGB(105,115,130)",
        "fire_feedback": "RGB(225,102,45)",
        "aux": "RGB(125,135,150)",
    }.get(edge.line_type, "RGB(40,103,205)")
    if edge.style == "black_arrow":
        color = "RGB(0,0,0)"
    if edge.style == "green_arrow":
        color = "RGB(128,205,105)"
    if edge.style == "orange_arrow":
        color = "RGB(245,145,80)"
    if arrow:
        _try_set(line, "BeginArrow", "0")
        _try_set(line, "EndArrow", "13")
    _try_set(line, "LineWeight", "0.017 in" if edge.style in {"black_arrow", "green_arrow", "orange_arrow"} else "0.011 in")
    _try_set(line, "LineColor", color)
    if edge.style == "dashed" or edge.line_type in {"feedback", "status_feedback", "fire_feedback", "aux"}:
        _try_set(line, "LinePattern", "2")


def _draw_edge_label(page: Any, label_x: float, label_y: float, text: str) -> Any:
    label = page.DrawRectangle(label_x - 0.9, label_y - 0.16, label_x + 0.9, label_y + 0.16)
    label.Text = _wrap_text(text, width=13)
    label.CellsU("LinePattern").FormulaU = "0"
    label.CellsU("FillPattern").FormulaU = "0"
    label.CellsU("Char.Size").FormulaU = f"{DEFAULT_LIMITS['edge_label_font_min']} pt"
    label.CellsU("Para.HorzAlign").FormulaU = "1"
    _try_set(label, "Char.Font", '"Microsoft YaHei"')
    return label


def _split_title_body(text: str) -> tuple[str, str]:
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    if not lines:
        return "", ""
    return lines[0], "\n".join(lines[1:])


def _apply_inner_text_style(shape: Any, bold: bool, font_size: float) -> None:
    shape.CellsU("LinePattern").FormulaU = "0"
    shape.CellsU("FillPattern").FormulaU = "0"
    shape.CellsU("Char.Size").FormulaU = f"{font_size} pt"
    shape.CellsU("Para.HorzAlign").FormulaU = "0"
    shape.CellsU("VerticalAlign").FormulaU = "1"
    if bold:
        _try_set(shape, "Char.Style", "1")
    _try_set(shape, "Char.Font", '"Microsoft YaHei"')


def polish_page(page: Any, diagram: Diagram, output_path: Path, shapes: list[Any]) -> None:
    margin = diagram.template_fidelity.page_margin if diagram.template_fidelity.enabled else max(0.45, diagram.page.margin)
    before = _shape_collection_bounds(shapes)
    if before is None:
        return
    left, bottom, right, top = before
    content_w = max(0.01, right - left)
    content_h = max(0.01, top - bottom)
    available_w = max(0.01, diagram.page.width - margin * 2)
    available_h = max(0.01, diagram.page.height - margin * 2)
    scale = min(1.0, available_w / content_w, available_h / content_h)

    if diagram.template_fidelity.scale_to_balance and scale < 0.995:
        _scale_shapes(shapes, scale, (left + right) / 2, (bottom + top) / 2)

    after_scale = _shape_collection_bounds(shapes) or before
    left, bottom, right, top = after_scale
    center_x = (left + right) / 2
    center_y = (bottom + top) / 2
    target_x = diagram.page.width / 2
    target_y = diagram.page.height / 2
    dx = target_x - center_x
    dy = target_y - center_y

    if diagram.template_fidelity.recenter_after_draw or diagram.optimization.recenter_page:
        _move_shapes(shapes, dx, dy)

    after = _shape_collection_bounds(shapes) or after_scale
    log = [
        "# 绘图后处理日志",
        "",
        f"输出文件：`{output_path}`",
        f"页面尺寸：{diagram.page.width:.2f} x {diagram.page.height:.2f}",
        f"目标边距：{margin:.2f}",
        f"优化前边界：left={before[0]:.2f}, bottom={before[1]:.2f}, right={before[2]:.2f}, top={before[3]:.2f}",
        f"缩放比例：{scale:.3f}",
        f"平移量：dx={dx:.2f}, dy={dy:.2f}",
        f"优化后边界：left={after[0]:.2f}, bottom={after[1]:.2f}, right={after[2]:.2f}, top={after[3]:.2f}",
        "",
        "说明：本次后处理执行了页面居中、边距平衡和必要的整体缩放；节点内部采用左图标右文字安全区。",
    ]
    (output_path.parent / "polish_log.md").write_text("\n".join(log), encoding="utf-8")


def _shape_collection_bounds(shapes: list[Any]) -> tuple[float, float, float, float] | None:
    bounds: list[tuple[float, float, float, float]] = []
    for shape in shapes:
        try:
            pin_x = shape.CellsU("PinX").ResultIU
            pin_y = shape.CellsU("PinY").ResultIU
            width = shape.CellsU("Width").ResultIU
            height = shape.CellsU("Height").ResultIU
            bounds.append((pin_x - width / 2, pin_y - height / 2, pin_x + width / 2, pin_y + height / 2))
        except Exception:
            pass
    if not bounds:
        return None
    return (
        min(item[0] for item in bounds),
        min(item[1] for item in bounds),
        max(item[2] for item in bounds),
        max(item[3] for item in bounds),
    )


def _move_shapes(shapes: list[Any], dx: float, dy: float) -> None:
    for shape in shapes:
        try:
            shape.CellsU("PinX").ResultIU = shape.CellsU("PinX").ResultIU + dx
            shape.CellsU("PinY").ResultIU = shape.CellsU("PinY").ResultIU + dy
        except Exception:
            pass


def _scale_shapes(shapes: list[Any], scale: float, cx: float, cy: float) -> None:
    for shape in shapes:
        try:
            pin_x = shape.CellsU("PinX").ResultIU
            pin_y = shape.CellsU("PinY").ResultIU
            shape.CellsU("PinX").ResultIU = cx + (pin_x - cx) * scale
            shape.CellsU("PinY").ResultIU = cy + (pin_y - cy) * scale
            shape.CellsU("Width").ResultIU = shape.CellsU("Width").ResultIU * scale
            shape.CellsU("Height").ResultIU = shape.CellsU("Height").ResultIU * scale
        except Exception:
            pass


def _draw_diamond(page: Any, x: float, y: float, width: float, height: float) -> Any:
    # 不依赖 stencil：第一版用旋转椭圆表达判断节点，保证跨版本稳定。
    shape = page.DrawOval(x - width / 2, y - height / 2, x + width / 2, y + height / 2)
    shape.CellsU("Angle").FormulaU = "45 deg"
    return shape


def _apply_style(shape: Any, style_name: str, is_group: bool = False) -> None:
    style = STYLE_PALETTE.get(style_name, STYLE_PALETTE["default"])
    shape.CellsU("FillForegnd").FormulaU = style["fill"]
    shape.CellsU("LineColor").FormulaU = style["line"]
    shape.CellsU("LineWeight").FormulaU = "0.010 in" if is_group else "0.018 in"
    shape.CellsU("Char.Size").FormulaU = "10.5 pt"
    shape.CellsU("Para.HorzAlign").FormulaU = "1"
    shape.CellsU("VerticalAlign").FormulaU = "1"
    _try_set(shape, "Char.Font", '"Microsoft YaHei"')
    _try_set(shape, "Rounding", "0.16 in")
    if style_name in {"main_blue", "center_blue"}:
        shape.CellsU("Char.Size").FormulaU = "13 pt"
        _try_set(shape, "Char.Style", "1")
        _try_set(shape, "LineWeight", "0.020 in")
    if style_name == "note":
        _try_set(shape, "LinePattern", "2")
        _try_set(shape, "LineWeight", "0.010 in")
        shape.CellsU("Char.Size").FormulaU = "13 pt"
    if style_name == "group_title":
        _try_set(shape, "LinePattern", "0")
        _try_set(shape, "FillPattern", "0")
        _try_set(shape, "Char.Style", "1")
        _try_set(shape, "Char.Color", "RGB(35,95,185)")
        shape.CellsU("Char.Size").FormulaU = "10.5 pt"
    if style_name == "separator":
        _try_set(shape, "FillPattern", "0")
        _try_set(shape, "LinePattern", "2")
        _try_set(shape, "LineWeight", "0.008 in")
        shape.CellsU("Char.Size").FormulaU = "1 pt"
    if style_name == "nn_block":
        _try_set(shape, "FillForegnd", "RGB(255,255,255)")
        _try_set(shape, "LineColor", "RGB(28,45,78)")
        _try_set(shape, "LineWeight", "0.022 in")
        _try_set(shape, "Char.Style", "1")
        shape.CellsU("Char.Size").FormulaU = "17 pt"
        _try_set(shape, "Rounding", "0 in")
    if style_name == "pool_orange":
        _try_set(shape, "FillForegnd", "RGB(255,243,232)")
        _try_set(shape, "LineColor", "RGB(255,205,168)")
        _try_set(shape, "LineWeight", "0.020 in")
        _try_set(shape, "Char.Style", "1")
        shape.CellsU("Char.Size").FormulaU = "16 pt"
        _try_set(shape, "Rounding", "0 in")
    if style_name == "conv_blue":
        _try_set(shape, "FillForegnd", "RGB(235,242,255)")
        _try_set(shape, "LineColor", "RGB(145,172,220)")
        _try_set(shape, "LineWeight", "0.020 in")
        _try_set(shape, "Char.Style", "1")
        shape.CellsU("Char.Size").FormulaU = "15 pt"
        _try_set(shape, "Rounding", "0 in")
    if style_name in {"paper_blue", "paper_green", "paper_orange", "loss_box"}:
        _try_set(shape, "LineWeight", "0.014 in")
        shape.CellsU("Char.Size").FormulaU = "9.5 pt"
        _try_set(shape, "Rounding", "0.04 in")
    if style_name == "paper_gray":
        _try_set(shape, "FillPattern", "0")
        _try_set(shape, "LinePattern", "2")
        _try_set(shape, "LineWeight", "0.014 in")
        shape.CellsU("Char.Size").FormulaU = "1 pt"
    if style_name == "plain_label":
        _try_set(shape, "LinePattern", "0")
        _try_set(shape, "FillPattern", "0")
        shape.CellsU("Char.Size").FormulaU = "9 pt"
    if is_group:
        _try_set(shape, "FillTransparency", "35%")
        _try_set(shape, "LinePattern", "2")
        shape.CellsU("Char.Size").FormulaU = "9 pt"


def _style_line_color(style_name: str) -> str:
    return STYLE_PALETTE.get(style_name, STYLE_PALETTE["default"])["line"]


def _try_set(shape: Any, cell_name: str, formula: str) -> None:
    try:
        shape.CellsU(cell_name).FormulaU = formula
    except Exception:
        pass


def _wrap_text(text: str, width: int = 18) -> str:
    if not text:
        return ""
    lines = []
    for line in str(text).splitlines():
        if len(line) <= width:
            lines.append(line)
        else:
            lines.extend(textwrap.wrap(line, width=width, break_long_words=False, replace_whitespace=False))
    return "\n".join(lines)


def _pause(visio: Any, delay: float) -> None:
    try:
        visio.ActiveWindow.Activate()
    except Exception:
        pass
    if delay > 0:
        time.sleep(delay)


if __name__ == "__main__":
    sys.exit(main())
