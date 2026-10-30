from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from connector_router import analyze_connector_routes, routed_edge_ratio
from collision_detector import detect_collisions
from schema import Diagram
from visual_rules import DEFAULT_LIMITS, RULES


def run_visual_quality_check(diagram: Diagram, output_vsdx: Path | None = None) -> tuple[list[dict], bool]:
    results: list[dict] = []

    margin = diagram.template_fidelity.page_margin if diagram.template_fidelity.enabled else max(0.45, diagram.page.margin)
    bounds = _diagram_bounds(diagram)
    if bounds is None:
        _add(results, "canvas_fit_rule", "失败", "图中没有可检查的节点。")
    else:
        left, bottom, right, top = bounds
        page_w, page_h = diagram.page.width, diagram.page.height
        content_w, content_h = right - left, top - bottom
        fill_ratio = max(content_w / page_w, content_h / page_h)
        centered = abs(((left + right) / 2) - page_w / 2) <= page_w * DEFAULT_LIMITS["center_tolerance_ratio"]
        centered = centered and abs(((bottom + top) / 2) - page_h / 2) <= page_h * DEFAULT_LIMITS["center_tolerance_ratio"]
        fits = left >= margin * 0.55 and bottom >= margin * 0.35 and right <= page_w - margin * 0.35 and top <= page_h - margin * 0.25
        _add(results, "canvas_fit_rule", "通过" if fits and fill_ratio <= DEFAULT_LIMITS["max_content_fill_ratio"] else "需要修复", f"边界={bounds}，填充比例={fill_ratio:.2f}")
        _add(results, "center_alignment_rule", "通过" if centered else "需要修复", "整体中心接近页面中心。" if centered else "整体存在明显偏移，需要居中。")

    icon_nodes = [node for node in diagram.nodes if node.icon]
    safe_zone_ok = diagram.template_fidelity.icon_safe_zone and diagram.template_fidelity.text_safe_zone
    _add(results, "safe_zone_rule", "通过" if not icon_nodes or safe_zone_ok else "需要修复", f"图标节点数量={len(icon_nodes)}，安全区启用={safe_zone_ok}")

    routed_ratio = routed_edge_ratio(diagram)
    _add(results, "connector_quality_rule", "通过" if routed_ratio >= DEFAULT_LIMITS["min_routed_edge_ratio"] else "需要修复", f"正交/指定路由比例={routed_ratio:.2f}")
    connector_issues = analyze_connector_routes(diagram)
    excessive_turns = [item for item in connector_issues if item["type"] == "excessive_connector_turns"]
    short_segments = [item for item in connector_issues if item["type"] == "short_meaningless_segments"]
    ugly_bends = [item for item in connector_issues if item["type"] == "ugly_connector_bends"]
    anchor_issues = [item for item in connector_issues if item["type"] == "connector_anchor_not_natural"]
    avoidable_non_straight = [item for item in connector_issues if item["type"] == "avoidable_non_straight_connector"]
    avoidable_doglegs = [item for item in connector_issues if item["type"] == "avoidable_dogleg_connector"]
    micro_doglegs = [item for item in connector_issues if item["type"] == "micro_dogleg_near_node"]
    _add(
        results,
        "connector_beauty_rule",
        "通过" if not ugly_bends and not short_segments else "需要修复",
        "连接线未发现明显丑折线。" if not ugly_bends and not short_segments else _format_issue_summary(ugly_bends + short_segments),
    )
    _add(
        results,
        "connector_route_simplify_rule",
        "通过" if not excessive_turns and not short_segments else "需要修复",
        "连接线拐点数量和短线段正常。" if not excessive_turns and not short_segments else _format_issue_summary(excessive_turns + short_segments),
    )
    _add(
        results,
        "connector_anchor_rule",
        "通过" if not anchor_issues else "需要修复",
        "连接锚点方向自然。" if not anchor_issues else _format_issue_summary(anchor_issues),
    )
    _add(
        results,
        "connector_straightness_rule",
        "通过" if not avoidable_non_straight and not avoidable_doglegs else "需要修复",
        "可共线连接和轻微错位连接已优先使用直线。" if not avoidable_non_straight and not avoidable_doglegs else _format_issue_summary(avoidable_non_straight + avoidable_doglegs),
    )
    _add(
        results,
        "no_micro_dogleg_rule",
        "通过" if not micro_doglegs else "需要修复",
        "未发现节点边缘附近的微小折角。" if not micro_doglegs else _format_issue_summary(micro_doglegs),
    )

    unclear = [f"{edge.from_}->{edge.to}" for edge in diagram.edges if (edge.style == "dashed" or edge.line_type in {"aux", "status_feedback"}) and edge.semantic is None]
    _add(results, "semantic_element_rule", "通过" if not unclear else "失败", "无无意义虚线。" if not unclear else "无语义虚线：" + ", ".join(unclear))

    dense_nodes = [node.id for node in diagram.nodes if len(node.text) > max(34, node.width * node.height * 18)]
    _add(results, "readability_rule", "通过" if not dense_nodes else "警告", "文本密度正常。" if not dense_nodes else "文本偏密节点：" + ", ".join(dense_nodes))
    font_risk_nodes = [
        node.id
        for node in diagram.nodes
        if node.icon and (node.height < 0.92 or node.width < 2.42)
    ]
    hierarchy_risk_nodes = [
        node.id
        for node in diagram.nodes
        if node.icon and len([line for line in node.text.splitlines() if line.strip()]) >= 2 and node.height < 0.96
    ]
    resize_risk_nodes = [
        node.id
        for node in diagram.nodes
        if node.icon and len(node.text) > max(28, node.width * node.height * 16)
    ]
    _add(
        results,
        "typography_readability_rule",
        "通过" if not font_risk_nodes else "需要修复",
        "节点尺寸支持当前默认可读字号。" if not font_risk_nodes else "字体可读性风险节点：" + ", ".join(font_risk_nodes),
    )
    _add(
        results,
        "text_hierarchy_rule",
        "通过" if not hierarchy_risk_nodes else "警告",
        "标题与说明有足够层级空间。" if not hierarchy_risk_nodes else "标题/说明层级空间偏紧节点：" + ", ".join(hierarchy_risk_nodes),
    )
    _add(
        results,
        "safe_resize_rule",
        "通过" if not resize_risk_nodes else "警告",
        "放大字体后未发现明显溢出风险。" if not resize_risk_nodes else "建议文本重排节点：" + ", ".join(resize_risk_nodes),
    )

    styles = {node.style for node in diagram.nodes if node.style}
    _add(results, "style_consistency_rule", "通过" if len(styles) <= 8 else "警告", f"节点样式数量={len(styles)}")

    if diagram.template_fidelity.enabled:
        _add(results, "template_fidelity_rule", "通过" if diagram.template_fidelity.preserve_layout else "需要修复", "参考图复刻布局锁定已启用。")
        _add(results, "false_completion", "通过" if diagram.template_fidelity.avoid_free_layout else "失败", "参考图复刻保护已启用。" if diagram.template_fidelity.avoid_free_layout else "参考图复刻仍可能被自由布局替代。")
        _add(results, "group_layout_failure", "通过" if len(diagram.groups) >= 3 else "需要修复", f"大分组数量={len(diagram.groups)}")
        collision_issues = detect_collisions(diagram)
        dense = [item for item in collision_issues if item["type"] == "dense_region_collision"]
        icon_text = [item for item in collision_issues if item["type"] == "icon_text_collision"]
        routing = [item for item in collision_issues if item["type"] == "connector_routing_failure"]
        legend = [item for item in collision_issues if item["type"] == "semantic_legend_failure"]
        _add(results, "dense_region_collision", "通过" if not dense else "失败", "未发现密集区域节点重叠。" if not dense else _format_collision_summary(dense))
        _add(results, "icon_text_collision", "通过" if not icon_text else "失败", "未发现图标文字安全区碰撞。" if not icon_text else _format_collision_summary(icon_text))
        _add(results, "connector_routing_failure", "通过" if not routing else "失败", "未发现连接线穿过节点或文字。" if not routing else _format_collision_summary(routing))
        _add(results, "semantic_legend_failure", "通过" if not legend else "失败", "图例未与主图发生重叠。" if not legend else _format_collision_summary(legend))
    else:
        _add(results, "template_fidelity_rule", "通过", "非参考图复刻模式。")

    polish_log_expected = output_vsdx is not None and (output_vsdx.parent / "polish_log.md").exists()
    _add(results, "polish_pass_rule", "通过" if polish_log_expected or diagram.optimization.enabled else "警告", "已执行或已启用绘图后美化。")

    has_serious = any(item["status"] in {"失败", "需要修复"} for item in results)
    return results, has_serious


def write_quality_report(results: list[dict], output_path: Path, repair_executed: bool = False) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# 通用视觉质量报告", ""]
    for item in results:
        rule = RULES[item["rule_id"]]
        lines.append(f"- {item['status']}：{rule.name}")
        lines.append(f"  - 说明：{item['message']}")
    lines.extend(["", "## 自动修复建议", ""])
    if any(item["status"] in {"失败", "需要修复"} for item in results):
        lines.append("需要修复：建议运行 auto_repair.py 或对应 run_* 脚本触发自动修复。")
    else:
        lines.append("通过：当前未发现必须自动修复的问题。")
    lines.append(f"自动修复执行结果：{'已执行' if repair_executed else '未执行'}")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _add(results: list[dict], rule_id: str, status: str, message: str) -> None:
    results.append({"rule_id": rule_id, "status": status, "message": message})


def _format_issue_summary(issues: list[dict]) -> str:
    if not issues:
        return "未发现问题。"
    summary = []
    for item in issues[:8]:
        detail = item.get("edge", "未知连接")
        issue_type = item.get("type", "unknown")
        summary.append(f"{detail}({issue_type})")
    if len(issues) > 8:
        summary.append(f"另有 {len(issues) - 8} 项")
    return "；".join(summary)


def _format_collision_summary(issues: list[dict]) -> str:
    if not issues:
        return "未发现碰撞。"
    return "；".join(item.get("message", item.get("type", "未知碰撞")) for item in issues[:8])


def _diagram_bounds(diagram: Diagram) -> tuple[float, float, float, float] | None:
    nodes = [node for node in diagram.nodes if node.x is not None and node.y is not None]
    if not nodes:
        return None
    return (
        min((node.x or 0) - node.width / 2 for node in nodes),
        min((node.y or 0) - node.height / 2 for node in nodes),
        max((node.x or 0) + node.width / 2 for node in nodes),
        max((node.y or 0) + node.height / 2 for node in nodes),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="运行通用视觉质量检查。")
    parser.add_argument("--diagram", default="output/diagram.json")
    parser.add_argument("--output", default="output/quality_report.md")
    parser.add_argument("--vsdx", default="")
    args = parser.parse_args()
    with Path(args.diagram).open("r", encoding="utf-8") as f:
        diagram = Diagram.model_validate(json.load(f))
    output_vsdx = Path(args.vsdx) if args.vsdx else None
    results, has_serious = run_visual_quality_check(diagram, output_vsdx)
    write_quality_report(results, Path(args.output))
    print(f"质量检查完成：{args.output}")
    return 2 if has_serious else 0


if __name__ == "__main__":
    sys.exit(main())
