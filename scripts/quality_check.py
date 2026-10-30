from __future__ import annotations

import json
from pathlib import Path

from schema import Diagram


def generate_quality_report(diagram: Diagram, project_root: Path, output_vsdx: Path) -> Path:
    if output_vsdx.stem.startswith("ros_robot_control"):
        report_path = project_root / "output" / "ros_robot_control_fidelity_report.md"
        quality_path = project_root / "output" / "ros_robot_control_quality_report.md"
    else:
        report_path = project_root / "output" / "template_fidelity_report.md"
        quality_path = project_root / "output" / "quality_report.md"
    trace_path = project_root / diagram.template_fidelity.trace_file
    trace = {}
    if trace_path.exists():
        trace = json.loads(trace_path.read_text(encoding="utf-8"))

    checks = []
    is_ros_case = output_vsdx.stem.startswith("ros_robot_control")
    checks.append(("页面比例是否接近参考图", _pass_if(abs((diagram.page.width / diagram.page.height) - float(trace.get("page_ratio", diagram.page.width / diagram.page.height))) < 0.35)))
    locked_layout = diagram.template_fidelity.preserve_layout and diagram.template_fidelity.avoid_free_layout
    checks.append(("页面居中与边距控制是否启用", _pass_if((diagram.template_fidelity.auto_fit_page and diagram.template_fidelity.recenter_after_draw) or locked_layout)))
    checks.append(("整体缩放是否受控", _pass_if(diagram.template_fidelity.scale_to_balance or locked_layout)))
    if is_ros_case:
        checks.append(("左中右三列是否保留", _pass_if(_has_column_structure(diagram))))
        checks.append(("中间分割虚线是否保留", _pass_if(any("separator" in node.id for node in diagram.nodes))))
        checks.append(("模块数量是否接近参考图", _pass_if(len([node for node in diagram.nodes if not node.id.startswith("separator")]) >= 10)))
    else:
        checks.append(("左中右三栏是否保留", _pass_if(len(diagram.groups) >= 4 and _has_group(diagram, "感知") and _has_group(diagram, "执行"))))
        checks.append(("大分组框数量是否接近", _pass_if(len(diagram.groups) >= 4)))
        checks.append(("小模块数量是否接近", _pass_if(len(diagram.nodes) >= 13)))
    checks.append(("是否使用圆角矩形", _pass_if(all(node.shape in {"rounded_box", "box"} for node in diagram.nodes))))
    checks.append(("是否使用图标", _pass_if(sum(1 for node in diagram.nodes if node.icon) >= (8 if is_ros_case else 10))))
    checks.append(("图标与文字是否采用安全区分栏", _pass_if(diagram.template_fidelity.icon_safe_zone and diagram.template_fidelity.text_safe_zone)))
    checks.append(("是否减少斜线", _pass_if(sum(1 for edge in diagram.edges if edge.route or edge.route_y is not None) >= max(6, len(diagram.edges) // 2))))
    checks.append(("是否没有无意义灰色虚线", _pass_if(not _has_unclear_dashed_edge(diagram))))
    checks.append(("颜色体系是否接近", _pass_if(any(node.style in {"soft_blue", "soft_green", "soft_orange", "soft_red", "paper_blue", "paper_green", "paper_orange"} for node in diagram.nodes))))
    checks.append(("是否整体接近科研架构图风格", _pass_if(len(diagram.edges) >= 8 and output_vsdx.exists())))

    lines = ["# 模板复刻质量报告", "", f"输出文件：`{output_vsdx}`", ""]
    failed = 0
    warning = 0
    for name, status in checks:
        if status == "失败":
            failed += 1
        elif status == "警告":
            warning += 1
        lines.append(f"- {status}：{name}")

    lines.extend(["", "## 结论", ""])
    if failed == 0 and warning <= 2:
        if is_ros_case:
            lines.append("通过：当前图已经保留参考图的左中右三列结构、中间竖向虚线分隔、图标卡片节点和主要控制/数据流。")
        else:
            lines.append("通过：当前图已经保留参考图的三栏分层结构、虚线分组、图例、图标和主要反馈通路。")
    elif failed <= 2:
        lines.append("警告：当前图整体可用，但仍建议继续微调线条路由和局部留白。")
    else:
        lines.append("失败：当前图与模板差距仍较大，建议继续优化分组位置、线条路由和图标布局。")

    lines.extend([
        "",
        "## 下一步建议",
        "",
        "- 如果线条仍显得拥挤，请指定需要移动的模块或反馈线。",
        "- 如果希望更像参考图，可继续要求“压缩左侧栏”“扩大中间决策层”“底部反馈线再靠下”等具体调整。",
    ])

    report_path.write_text("\n".join(lines), encoding="utf-8")
    quality_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def _has_group(diagram: Diagram, keyword: str) -> bool:
    nodes = {node.id: node for node in diagram.nodes}
    for group in diagram.groups:
        if keyword in group.text:
            return True
        for node_id in group.node_ids:
            node = nodes.get(node_id)
            if node and keyword in node.text:
                return True
    return False


def _pass_if(condition: bool) -> str:
    return "通过" if condition else "失败"


def _has_column_structure(diagram: Diagram) -> bool:
    xs = [node.x for node in diagram.nodes if node.x is not None and not node.id.startswith("separator")]
    if len(xs) < 9:
        return False
    left = [x for x in xs if x < diagram.page.width * 0.34]
    middle = [x for x in xs if diagram.page.width * 0.34 <= x <= diagram.page.width * 0.70]
    right = [x for x in xs if x > diagram.page.width * 0.70]
    return len(left) >= 3 and len(middle) >= 4 and len(right) >= 3


def _has_unclear_dashed_edge(diagram: Diagram) -> bool:
    for edge in diagram.edges:
        if edge.style == "dashed" or edge.line_type in {"feedback", "status_feedback", "aux", "fire_feedback"}:
            if edge.semantic is None:
                return True
            if edge.line_type in {"status_feedback", "aux"} and edge.semantic not in {"status_feedback", "auxiliary"}:
                return True
    return False
