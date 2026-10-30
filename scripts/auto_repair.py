from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from connector_router import normalize_connector_routes, simplify_connector_routes
from schema import Diagram
from visual_rules import DEFAULT_LIMITS
from visual_quality_check import run_visual_quality_check, write_quality_report


def repair_diagram(diagram: Diagram) -> tuple[Diagram, list[str]]:
    log: list[str] = []
    diagram = normalize_connector_routes(diagram)
    log.append("已规范化连接线语义和路由。")
    diagram, route_log = simplify_connector_routes(diagram, preserve_layout=True)
    log.extend(route_log or ["line_simplification_pass：未发现需要简化的连接线。"])

    if diagram.template_fidelity.enabled:
        diagram.template_fidelity.auto_fit_page = True
        diagram.template_fidelity.recenter_after_draw = True
        diagram.template_fidelity.scale_to_balance = True
        diagram.template_fidelity.icon_safe_zone = True
        diagram.template_fidelity.text_safe_zone = True
        log.append("已启用参考图复刻模式的画布适配、居中、缩放和安全区。")

    bounds = _diagram_bounds(diagram)
    if bounds is not None:
        left, bottom, right, top = bounds
        content_w = max(0.01, right - left)
        content_h = max(0.01, top - bottom)
        fill_ratio = max(content_w / diagram.page.width, content_h / diagram.page.height)
        if fill_ratio > DEFAULT_LIMITS["max_content_fill_ratio"]:
            target_ratio = max(0.78, DEFAULT_LIMITS["max_content_fill_ratio"] - 0.04)
            scale = target_ratio / fill_ratio
            cx = (left + right) / 2
            cy = (bottom + top) / 2
            for node in diagram.nodes:
                if node.x is not None:
                    node.x = cx + (node.x - cx) * scale
                if node.y is not None:
                    node.y = cy + (node.y - cy) * scale
                node.width = max(0.3, node.width * scale)
                node.height = max(0.24, node.height * scale)
            log.append(f"已按画布适配规则缩放节点：scale={scale:.3f}。")
            bounds = _diagram_bounds(diagram)
            if bounds is not None:
                left, bottom, right, top = bounds
        dx = diagram.page.width / 2 - (left + right) / 2
        dy = diagram.page.height / 2 - (bottom + top) / 2
        tolerance_x = diagram.page.width * DEFAULT_LIMITS["center_tolerance_ratio"]
        tolerance_y = diagram.page.height * DEFAULT_LIMITS["center_tolerance_ratio"]
        if abs(dx) > tolerance_x or abs(dy) > tolerance_y:
            for node in diagram.nodes:
                if node.x is not None:
                    node.x += dx
                if node.y is not None:
                    node.y += dy
            log.append(f"已将 diagram.json 坐标整体居中：dx={dx:.2f}, dy={dy:.2f}。")
        else:
            log.append("preserve_layout_position：整体位置已在容差内，未移动节点坐标。")

    before = len(diagram.edges)
    diagram.edges = [
        edge for edge in diagram.edges
        if not ((edge.style == "dashed" or edge.line_type in {"aux", "status_feedback"}) and edge.semantic is None)
    ]
    removed = before - len(diagram.edges)
    if removed:
        log.append(f"已删除 {removed} 条无明确语义的虚线/辅助线。")

    font_changes = 0
    for node in diagram.nodes:
        if node.icon:
            before = (node.width, node.height)
            node.width = max(node.width, 2.55)
            node.height = max(node.height, _recommended_node_height(node.text, node.height))
            if (node.width, node.height) != before:
                font_changes += 1
                log.append(f"font_enlargement_pass：节点 {node.id} 尺寸 {before[0]:.2f}x{before[1]:.2f} -> {node.width:.2f}x{node.height:.2f}。")
    if font_changes == 0:
        log.append("font_enlargement_pass：当前节点尺寸已满足可读字号要求，无需继续放大。")
    log.append("node_text_refit_pass：已为含图标节点保留标题、说明和图标安全区。")
    return diagram, log


def write_repair_log(path: Path, log: list[str], quality_failed: bool) -> None:
    lines = ["# 自动修复日志", "", f"质量检查是否仍有严重问题：{'是' if quality_failed else '否'}", ""]
    lines.extend(f"- {item}" for item in log)
    path.write_text("\n".join(lines), encoding="utf-8")


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


def _recommended_node_height(text: str, current: float) -> float:
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    if len(lines) <= 1:
        return max(current, 0.92)
    body_len = sum(len(line) for line in lines[1:])
    if body_len > 36 or len(lines) >= 4:
        return max(current, 1.16)
    if body_len > 18 or len(lines) >= 3:
        return max(current, 1.06)
    return max(current, 0.98)


def main() -> int:
    parser = argparse.ArgumentParser(description="根据通用视觉规则自动修复 diagram.json。")
    parser.add_argument("--diagram", default="output/diagram.json")
    parser.add_argument("--output-diagram", default="output/diagram.json")
    parser.add_argument("--quality-report", default="output/quality_report.md")
    parser.add_argument("--repair-log", default="output/repair_log.md")
    args = parser.parse_args()

    with Path(args.diagram).open("r", encoding="utf-8") as f:
        diagram = Diagram.model_validate(json.load(f))
    repaired, log = repair_diagram(diagram)
    results, has_serious = run_visual_quality_check(repaired)
    with Path(args.output_diagram).open("w", encoding="utf-8") as f:
        json.dump(repaired.model_dump(by_alias=True), f, ensure_ascii=False, indent=2)
    write_quality_report(results, Path(args.quality_report), repair_executed=True)
    write_repair_log(Path(args.repair_log), log, has_serious)
    print(f"自动修复完成：{args.output_diagram}")
    return 2 if has_serious else 0


if __name__ == "__main__":
    sys.exit(main())
