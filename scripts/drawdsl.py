from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from schema import Diagram


DRAWDSL_VERSION = "0.1"


def diagram_to_drawdsl(diagram: Diagram) -> dict[str, Any]:
    """把 diagram.json 转换为稳定的 DrawDSL 中间层。

    第一阶段 DrawDSL 不替代现有渲染器，只作为 planner 与 backend 之间的可检查契约。
    """
    nodes = []
    for node in diagram.nodes:
        nodes.append({
            "id": node.id,
            "type": node.shape,
            "text": node.text,
            "icon": node.icon,
            "image": node.image,
            "bbox": _node_bbox(node),
            "style": node.style,
            "z_order": 30,
            "safe_zones": _safe_zones(node),
        })

    groups = []
    for group in diagram.groups:
        groups.append({
            "id": group.id,
            "title": group.text,
            "node_ids": group.node_ids,
            "style": group.style,
            "z_order": 10,
        })

    connectors = []
    for edge in diagram.edges:
        connectors.append({
            "id": f"{edge.from_}_to_{edge.to}",
            "from": edge.from_,
            "to": edge.to,
            "text": edge.text,
            "style": edge.style,
            "route": edge.route,
            "route_points": edge.route_points,
            "channel": _route_to_channel(edge.route, edge.line_type),
            "line_type": edge.line_type,
            "semantic": edge.semantic,
            "label": {"x": edge.label_x, "y": edge.label_y},
            "z_order": 20,
        })

    return {
        "drawdsl_version": DRAWDSL_VERSION,
        "intent": {
            "title": diagram.title,
            "type": diagram.type,
            "layout": diagram.layout,
            "output": diagram.output,
        },
        "page": {
            "width": diagram.page.width,
            "height": diagram.page.height,
            "margin": diagram.page.margin,
        },
        "workflow": {
            "stages": ["intent", "analysis", "plan", "drawdsl", "backend", "preview", "review", "lesson"],
            "reference_reproduction": diagram.template_fidelity.enabled,
            "avoid_free_layout": diagram.template_fidelity.avoid_free_layout,
        },
        "groups": groups,
        "nodes": nodes,
        "connectors": connectors,
        "legend": _infer_legend(diagram),
    }


def write_drawdsl(diagram: Diagram, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(diagram_to_drawdsl(diagram), ensure_ascii=False, indent=2), encoding="utf-8")


def _node_bbox(node: Any) -> list[float] | None:
    if node.x is None or node.y is None:
        return None
    return [
        round(node.x - node.width / 2, 4),
        round(node.y - node.height / 2, 4),
        round(node.x + node.width / 2, 4),
        round(node.y + node.height / 2, 4),
    ]


def _safe_zones(node: Any) -> dict[str, Any]:
    if node.x is None or node.y is None:
        return {"icon_bbox": None, "text_bbox": None}
    left = node.x - node.width / 2
    right = node.x + node.width / 2
    bottom = node.y - node.height / 2
    top = node.y + node.height / 2
    if not node.icon:
        return {"icon_bbox": None, "text_bbox": [round(left + 0.10, 4), round(bottom + 0.08, 4), round(right - 0.10, 4), round(top - 0.08, 4)]}
    icon_w = min(node.width * 0.20, 0.52)
    icon_size = min(node.height * 0.48, icon_w * 0.72, 0.34)
    icon_cx = left + icon_w / 2 + 0.10
    return {
        "icon_bbox": [round(icon_cx - icon_size / 2, 4), round(node.y - icon_size / 2, 4), round(icon_cx + icon_size / 2, 4), round(node.y + icon_size / 2, 4)],
        "text_bbox": [round(left + icon_w + 0.12, 4), round(bottom + 0.10, 4), round(right - 0.10, 4), round(top - 0.08, 4)],
    }


def _route_to_channel(route: str | None, line_type: str) -> str:
    if route in {"bottom_feedback", "dashed_feedback"}:
        return "bottom_feedback"
    if route == "straight_vertical":
        return "vertical_feedback"
    if line_type == "control":
        return "right_internal"
    if line_type in {"feedback", "status_feedback", "fire_feedback"}:
        return "vertical_feedback"
    return "middle_internal"


def _infer_legend(diagram: Diagram) -> dict[str, Any] | None:
    for node in diagram.nodes:
        if "legend" in node.id.lower() or "图例" in node.text:
            return {"node_id": node.id, "bbox": _node_bbox(node), "z_order": 50}
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="把 diagram.json 转换为 DrawDSL 中间层。")
    parser.add_argument("--diagram", default="output/diagram.json")
    parser.add_argument("--output", default="output/drawdsl.json")
    args = parser.parse_args()
    diagram = Diagram.model_validate(json.loads(Path(args.diagram).read_text(encoding="utf-8")))
    write_drawdsl(diagram, Path(args.output))
    print(f"DrawDSL 已生成：{args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
