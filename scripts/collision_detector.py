from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from schema import Diagram


BBox = tuple[float, float, float, float]
Point = tuple[float, float]


def detect_collisions(diagram: Diagram, trace: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """检测参考图复刻中常见的遮挡、重叠和穿线问题。"""
    issues: list[dict[str, Any]] = []
    node_boxes = _node_boxes(diagram)
    text_boxes = _text_boxes(diagram)
    icon_boxes = _icon_boxes(diagram)
    legend_box = _legend_box(diagram, trace)

    for left_id, left_box in node_boxes.items():
        for right_id, right_box in node_boxes.items():
            if left_id >= right_id:
                continue
            area = _intersection_area(left_box, right_box)
            if area > 0.015:
                issues.append({
                    "type": "dense_region_collision",
                    "severity": "严重",
                    "items": [left_id, right_id],
                    "message": f"节点发生明显重叠：{left_id} 与 {right_id}",
                })

    for node_id in node_boxes:
        icon_box = icon_boxes.get(node_id)
        text_box = text_boxes.get(node_id)
        if icon_box and text_box and _intersects(icon_box, text_box, padding=0.01):
            issues.append({
                "type": "icon_text_collision",
                "severity": "严重",
                "items": [node_id],
                "message": f"图标区与文字区重叠或距离过近：{node_id}",
            })
        if icon_box and not _contains(node_boxes[node_id], icon_box):
            issues.append({
                "type": "icon_text_collision",
                "severity": "严重",
                "items": [node_id],
                "message": f"图标区超出节点边界：{node_id}",
            })
        if text_box and not _contains(node_boxes[node_id], text_box):
            issues.append({
                "type": "icon_text_collision",
                "severity": "严重",
                "items": [node_id],
                "message": f"文字区超出节点边界：{node_id}",
            })

    for edge in diagram.edges:
        points = _edge_points(diagram, edge)
        if len(points) < 2:
            issues.append({
                "type": "connector_routing_failure",
                "severity": "警告",
                "items": [f"{edge.from_}->{edge.to}"],
                "message": "连接线缺少可检查的 route_points 或可推断路径。",
            })
            continue
        for node_id, box in node_boxes.items():
            if node_id in {edge.from_, edge.to}:
                continue
            if _polyline_intersects_box(points, box, padding=0.02):
                issues.append({
                    "type": "connector_routing_failure",
                    "severity": "严重",
                    "items": [f"{edge.from_}->{edge.to}", node_id],
                    "message": f"连接线穿过节点：{edge.from_}->{edge.to} 穿过 {node_id}",
                })
        for node_id, box in text_boxes.items():
            if node_id in {edge.from_, edge.to}:
                continue
            if _polyline_intersects_box(points, box, padding=0.01):
                issues.append({
                    "type": "connector_routing_failure",
                    "severity": "严重",
                    "items": [f"{edge.from_}->{edge.to}", node_id],
                    "message": f"连接线穿过文字安全区：{edge.from_}->{edge.to} 穿过 {node_id}",
                })
        if legend_box and _polyline_intersects_box(points, legend_box, padding=0.02):
            issues.append({
                "type": "semantic_legend_failure",
                "severity": "严重",
                "items": [f"{edge.from_}->{edge.to}", "legend"],
                "message": f"连接线穿过图例区域：{edge.from_}->{edge.to}",
            })

    if legend_box:
        for node_id, box in node_boxes.items():
            if "legend" in node_id.lower():
                continue
            if _intersects(legend_box, box, padding=0.02):
                issues.append({
                    "type": "semantic_legend_failure",
                    "severity": "严重",
                    "items": ["legend", node_id],
                    "message": f"图例与主图节点重叠：{node_id}",
                })

    return issues


def write_collision_report(issues: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# 碰撞检测报告", ""]
    if not issues:
        lines.append("通过：未发现节点、图标、文字、连接线或图例的明显碰撞。")
    else:
        lines.append("复刻未通过：检测到以下碰撞或穿线问题。")
        lines.append("")
        for issue in issues:
            lines.append(f"- {issue['severity']} / {issue['type']}：{issue['message']}")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _node_boxes(diagram: Diagram) -> dict[str, BBox]:
    boxes: dict[str, BBox] = {}
    for node in diagram.nodes:
        if node.x is None or node.y is None:
            continue
        boxes[node.id] = (
            node.x - node.width / 2,
            node.y - node.height / 2,
            node.x + node.width / 2,
            node.y + node.height / 2,
        )
    return boxes


def _icon_boxes(diagram: Diagram) -> dict[str, BBox]:
    boxes: dict[str, BBox] = {}
    for node in diagram.nodes:
        if not node.icon or node.x is None or node.y is None:
            continue
        left = node.x - node.width / 2
        icon_w = min(node.width * 0.20, 0.52)
        icon_size = min(node.height * 0.48, icon_w * 0.72, 0.34)
        cx = left + icon_w / 2 + 0.10
        boxes[node.id] = (cx - icon_size / 2, node.y - icon_size / 2, cx + icon_size / 2, node.y + icon_size / 2)
    return boxes


def _text_boxes(diagram: Diagram) -> dict[str, BBox]:
    boxes: dict[str, BBox] = {}
    for node in diagram.nodes:
        if node.x is None or node.y is None:
            continue
        left = node.x - node.width / 2
        right = node.x + node.width / 2
        bottom = node.y - node.height / 2
        top = node.y + node.height / 2
        if node.icon:
            icon_w = min(node.width * 0.20, 0.52)
            text_left = left + icon_w + 0.10
            boxes[node.id] = (text_left, bottom + 0.10, right - 0.10, top - 0.08)
        else:
            boxes[node.id] = (left + 0.10, bottom + 0.08, right - 0.10, top - 0.08)
    return boxes


def _legend_box(diagram: Diagram, trace: dict[str, Any] | None) -> BBox | None:
    if trace and trace.get("legend", {}).get("bbox"):
        return _norm_to_page(tuple(trace["legend"]["bbox"]), diagram.page.width, diagram.page.height)
    legend_nodes = [node for node in diagram.nodes if "legend" in node.id.lower() or "图例" in node.text]
    if not legend_nodes:
        return None
    node = legend_nodes[0]
    if node.x is None or node.y is None:
        return None
    return (node.x - node.width / 2, node.y - node.height / 2, node.x + node.width / 2, node.y + node.height / 2)


def _edge_points(diagram: Diagram, edge: Any) -> list[Point]:
    if getattr(edge, "route_points", None):
        return [(float(point[0]), float(point[1])) for point in edge.route_points]
    by_id = {node.id: node for node in diagram.nodes}
    start = by_id.get(edge.from_)
    end = by_id.get(edge.to)
    if not start or not end or start.x is None or start.y is None or end.x is None or end.y is None:
        return []
    sx, sy = start.x, start.y
    ex, ey = end.x, end.y
    if abs(ex - sx) >= abs(ey - sy):
        sx = sx + (start.width / 2 if ex >= sx else -start.width / 2)
        ex = ex - (end.width / 2 if ex >= sx else -end.width / 2)
    else:
        sy = sy + (start.height / 2 if ey >= sy else -start.height / 2)
        ey = ey - (end.height / 2 if ey >= sy else -end.height / 2)
    if edge.route in {"right_then_down", "left_to_right"} and abs(sy - ey) > 0.08:
        mid_x = (sx + ex) / 2
        return [(sx, sy), (mid_x, sy), (mid_x, ey), (ex, ey)]
    if edge.route in {"bottom_feedback", "dashed_feedback"}:
        bottom_y = 0.65
        return [(sx, sy), (sx, bottom_y), (ex, bottom_y), (ex, ey)]
    if edge.route == "straight_vertical":
        return [(start.x, sy), (end.x, ey)]
    return [(sx, sy), (ex, ey)]


def _polyline_intersects_box(points: list[Point], box: BBox, padding: float = 0.0) -> bool:
    padded = (box[0] - padding, box[1] - padding, box[2] + padding, box[3] + padding)
    return any(_segment_intersects_box(a, b, padded) for a, b in zip(points, points[1:]))


def _segment_intersects_box(a: Point, b: Point, box: BBox) -> bool:
    if _point_in_box(a, box) or _point_in_box(b, box):
        return True
    x1, y1, x2, y2 = box
    edges = [((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)), ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))]
    return any(_segments_intersect(a, b, c, d) for c, d in edges)


def _segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
    def orient(p: Point, q: Point, r: Point) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    o1 = orient(a, b, c)
    o2 = orient(a, b, d)
    o3 = orient(c, d, a)
    o4 = orient(c, d, b)
    return (o1 == 0 or o2 == 0 or o1 * o2 < 0) and (o3 == 0 or o4 == 0 or o3 * o4 < 0)


def _point_in_box(point: Point, box: BBox) -> bool:
    return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]


def _intersects(a: BBox, b: BBox, padding: float = 0.0) -> bool:
    return not (a[2] + padding <= b[0] or b[2] + padding <= a[0] or a[3] + padding <= b[1] or b[3] + padding <= a[1])


def _contains(outer: BBox, inner: BBox) -> bool:
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def _intersection_area(a: BBox, b: BBox) -> float:
    w = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    h = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return w * h


def _norm_to_page(bbox: tuple[float, float, float, float], page_w: float, page_h: float) -> BBox:
    x1, y1, x2, y2 = bbox
    return (x1 * page_w, (1 - y2) * page_h, x2 * page_w, (1 - y1) * page_h)


def main() -> int:
    parser = argparse.ArgumentParser(description="检测节点、文字、图标、连接线和图例碰撞。")
    parser.add_argument("--diagram", default="output/diagram.json")
    parser.add_argument("--trace", default="output/template_trace.json")
    parser.add_argument("--output", default="output/collision_report.md")
    args = parser.parse_args()
    diagram = Diagram.model_validate(json.loads(Path(args.diagram).read_text(encoding="utf-8")))
    trace_path = Path(args.trace)
    trace = json.loads(trace_path.read_text(encoding="utf-8")) if trace_path.exists() else {}
    issues = detect_collisions(diagram, trace)
    write_collision_report(issues, Path(args.output))
    print(f"碰撞检测完成：{args.output}")
    return 2 if any(issue["severity"] == "严重" for issue in issues) else 0


if __name__ == "__main__":
    sys.exit(main())
