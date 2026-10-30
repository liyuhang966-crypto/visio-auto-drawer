from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


def build_repair_suggestions(fidelity: dict[str, Any] | None = None, collisions: list[dict[str, Any]] | None = None, trace: dict[str, Any] | None = None) -> list[str]:
    suggestions: list[str] = []
    seen: set[str] = set()
    collisions = collisions or []
    trace = trace or {}

    for issue in collisions:
        issue_type = issue.get("type")
        items = ", ".join(issue.get("items", []))
        if issue_type == "dense_region_collision":
            _add_unique(suggestions, seen, f"调整相关节点或父级 group 的 bbox，增加区域内间距：{items}")
        elif issue_type == "icon_text_collision":
            _add_unique(suggestions, seen, f"拆分或修正 node.icon_bbox 与 node.text_bbox，必要时增大节点 bbox：{items}")
        elif issue_type == "connector_routing_failure":
            connector = issue.get("items", ["未知连接"])[0]
            _add_unique(suggestions, seen, f"为连接线补充或修正 route_points，并指定 channel 避开节点和文字：{connector}")
        elif issue_type == "semantic_legend_failure":
            _add_unique(suggestions, seen, f"调整 legend.bbox 或相关连接线通道，避免图例与主图重叠：{items}")

    groups = trace.get("groups") or trace.get("regions") or []
    if groups and not all(item.get("bbox") for item in groups):
        _add_unique(suggestions, seen, "补全 groups[].bbox，所有大分组框必须使用归一化坐标记录位置和比例。")
    nodes = trace.get("nodes") or trace.get("elements") or []
    missing_safe_zone = [item.get("id", "unknown") for item in nodes if item.get("type") not in {"label"} and (not item.get("icon_bbox") or not item.get("text_bbox"))]
    if missing_safe_zone:
        _add_unique(suggestions, seen, "为节点补充 icon_bbox 与 text_bbox，避免图标文字互压：" + ", ".join(missing_safe_zone[:10]))
    connectors = trace.get("connectors") or []
    missing_routes = [item.get("id", "unknown") for item in connectors if not item.get("route_points") or not item.get("channel")]
    if missing_routes:
        _add_unique(suggestions, seen, "为连接线补充 route_points 与 channel：" + ", ".join(missing_routes[:10]))
    if not trace.get("legend"):
        _add_unique(suggestions, seen, "补充 legend.bbox 和 legend.items，图例必须独立管理。")

    if not suggestions:
        suggestions.append("当前没有生成强制修复建议；可继续微调 groups[].bbox、nodes[].bbox 和 connectors[].route_points 提升相似度。")
    return suggestions


def _add_unique(suggestions: list[str], seen: set[str], item: str) -> None:
    if item in seen:
        return
    seen.add(item)
    suggestions.append(item)


def write_trace_repair_suggestions(suggestions: list[str], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Trace 修复建议", ""]
    for index, item in enumerate(suggestions, start=1):
        lines.append(f"{index}. {item}")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="根据复刻失败结果生成 template_trace 修复建议。")
    parser.add_argument("--trace", default="output/template_trace.json")
    parser.add_argument("--collisions", default="output/collision_issues.json")
    parser.add_argument("--output", default="output/trace_repair_suggestions.md")
    args = parser.parse_args()
    trace_path = Path(args.trace)
    trace = json.loads(trace_path.read_text(encoding="utf-8")) if trace_path.exists() else {}
    collision_path = Path(args.collisions)
    collisions = json.loads(collision_path.read_text(encoding="utf-8")) if collision_path.exists() else []
    suggestions = build_repair_suggestions(collisions=collisions, trace=trace)
    write_trace_repair_suggestions(suggestions, Path(args.output))
    print(f"trace 修复建议已生成：{args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
