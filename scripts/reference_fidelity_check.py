from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from collision_detector import detect_collisions, write_collision_report
from connector_channel_router import CHANNELS
from schema import Diagram
from trace_repair_advisor import build_repair_suggestions, write_trace_repair_suggestions


FAILURE_TYPES = [
    "group_layout_failure",
    "layer_hierarchy_failure",
    "dense_region_collision",
    "connector_routing_failure",
    "semantic_legend_failure",
    "reference_density_mismatch",
    "icon_text_collision",
    "false_completion",
]


def run_reference_fidelity_check(diagram: Diagram, trace: dict[str, Any] | None = None) -> dict[str, Any]:
    trace = trace or {}
    collisions = detect_collisions(diagram, trace)
    failures: list[dict[str, Any]] = []

    groups = trace.get("groups") or trace.get("regions") or []
    nodes = trace.get("nodes") or trace.get("elements") or []
    connectors = trace.get("connectors") or []
    legend = trace.get("legend")

    if len(diagram.groups) < 3 and len(groups) < 3:
        failures.append(_failure("group_layout_failure", "严重", "缺少足够的大分组框，无法证明参考图主要区域被保留。", ["groups[].bbox"]))
    if diagram.template_fidelity.enabled and not diagram.template_fidelity.preserve_layout:
        failures.append(_failure("false_completion", "严重", "参考图复刻未锁定布局，存在自由排版风险。", ["template_fidelity.preserve_layout"]))
    if len(diagram.nodes) < 8 and len(nodes) < 8:
        failures.append(_failure("reference_density_mismatch", "严重", "输出元素数量过少，视觉密度明显不像复杂参考图。", ["nodes[].bbox", "elements[].bbox"]))
    if not _has_three_columns(diagram):
        failures.append(_failure("reference_density_mismatch", "严重", "未检测到稳定左中右结构，可能是重新排版而不是复刻。", ["groups[].bbox", "nodes[].bbox"]))
    if not _has_legend(diagram, legend):
        failures.append(_failure("semantic_legend_failure", "严重", "缺少独立图例或图例 trace。", ["legend.bbox", "legend.items"]))
    bad_connectors = [item for item in connectors if not item.get("route_points") or item.get("channel") not in CHANNELS]
    if connectors and bad_connectors:
        failures.append(_failure("connector_routing_failure", "严重", "部分 trace 连接线缺少 route_points 或 channel。", ["connectors[].route_points", "connectors[].channel"]))
    if not connectors and len(diagram.edges) >= 6:
        failures.append(_failure("connector_routing_failure", "警告", "diagram 中有多条连接线，但 trace 未记录连接线路由。", ["connectors[].route_points"]))

    for issue in collisions:
        failures.append(_failure(issue["type"], issue["severity"], issue["message"], _fields_for_issue(issue["type"])))

    serious = [item for item in failures if item["severity"] == "严重"]
    return {
        "passed": not serious,
        "failures": failures,
        "collisions": collisions,
        "summary": "通过" if not serious else "复刻未通过，需要继续调整。",
    }


def write_reference_fidelity_report(result: dict[str, Any], output_path: Path, diagram_path: Path, trace_path: Path | None = None) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Reference Fidelity 检查报告",
        "",
        f"diagram：`{diagram_path}`",
        f"trace：`{trace_path}`" if trace_path else "trace：未提供",
        "",
        f"结论：{result['summary']}",
        "",
        "## 失败模式",
        "",
    ]
    failures = result.get("failures", [])
    if not failures:
        lines.append("- 通过：未发现严重 reference reproduction 失败模式。")
    else:
        for item in failures:
            fields = "、".join(item.get("trace_fields", []))
            lines.append(f"- {item['severity']} / {item['type']}：{item['message']}")
            if fields:
                lines.append(f"  - 建议检查：{fields}")
    lines.extend([
        "",
        "## 通过条件",
        "",
        "- 无严重重叠。",
        "- 主结构相似。",
        "- 大分组位置相似。",
        "- 主要连线路由相似。",
        "- 图例位置正确。",
        "- 没有明显自由排版痕迹。",
    ])
    if not result["passed"]:
        lines.extend([
            "",
            "## 保护机制",
            "",
            "当前复刻未通过，禁止报告“复刻成功”。请先执行自动修复，或人工校正 `template_trace.json`。",
        ])
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _failure(issue_type: str, severity: str, message: str, trace_fields: list[str]) -> dict[str, Any]:
    return {"type": issue_type, "severity": severity, "message": message, "trace_fields": trace_fields}


def _fields_for_issue(issue_type: str) -> list[str]:
    return {
        "dense_region_collision": ["nodes[].bbox", "groups[].padding"],
        "icon_text_collision": ["nodes[].icon_bbox", "nodes[].text_bbox"],
        "connector_routing_failure": ["connectors[].route_points", "connectors[].channel"],
        "semantic_legend_failure": ["legend.bbox", "legend.items"],
    }.get(issue_type, ["template_trace.json"])


def _has_three_columns(diagram: Diagram) -> bool:
    xs = [node.x for node in diagram.nodes if node.x is not None and "legend" not in node.id.lower()]
    if len(xs) < 9:
        return False
    left = [x for x in xs if x < diagram.page.width * 0.32]
    middle = [x for x in xs if diagram.page.width * 0.32 <= x <= diagram.page.width * 0.72]
    right = [x for x in xs if x > diagram.page.width * 0.72]
    return len(left) >= 3 and len(middle) >= 4 and len(right) >= 3


def _has_legend(diagram: Diagram, legend: Any) -> bool:
    if legend and legend.get("bbox") and legend.get("items"):
        return True
    return any("legend" in node.id.lower() or "图例" in node.text for node in diagram.nodes)


def main() -> int:
    parser = argparse.ArgumentParser(description="运行参考图复刻 fidelity 检查。")
    parser.add_argument("--diagram", default="output/diagram.json")
    parser.add_argument("--trace", default="output/template_trace.json")
    parser.add_argument("--report", default="output/reference_fidelity_report.md")
    parser.add_argument("--collision-report", default="output/collision_report.md")
    parser.add_argument("--collision-json", default="output/collision_issues.json")
    parser.add_argument("--repair", default="output/trace_repair_suggestions.md")
    args = parser.parse_args()

    diagram_path = Path(args.diagram)
    diagram = Diagram.model_validate(json.loads(diagram_path.read_text(encoding="utf-8")))
    trace_path = Path(args.trace)
    trace = json.loads(trace_path.read_text(encoding="utf-8")) if trace_path.exists() else {}
    result = run_reference_fidelity_check(diagram, trace)
    write_reference_fidelity_report(result, Path(args.report), diagram_path, trace_path if trace_path.exists() else None)
    write_collision_report(result["collisions"], Path(args.collision_report))
    Path(args.collision_json).write_text(json.dumps(result["collisions"], ensure_ascii=False, indent=2), encoding="utf-8")
    suggestions = build_repair_suggestions(collisions=result["collisions"], trace=trace)
    write_trace_repair_suggestions(suggestions, Path(args.repair))
    print(f"reference fidelity 检查完成：{args.report}")
    if not result["passed"]:
        print("复刻未通过，需要继续调整。")
        return 2
    print("reference fidelity 检查通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
