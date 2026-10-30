from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Severity = Literal["通过", "警告", "失败", "需要修复"]


@dataclass(frozen=True)
class VisualRule:
    id: str
    name: str
    description: str
    fail_message: str


RULES: dict[str, VisualRule] = {
    "canvas_fit_rule": VisualRule(
        "canvas_fit_rule",
        "画布适配规则",
        "图形应位于页面安全边距内，不能贴边、过大或过小。",
        "图形存在贴边、过大、过小或缩放不合理问题。",
    ),
    "center_alignment_rule": VisualRule(
        "center_alignment_rule",
        "整体居中规则",
        "所有主要元素组成的整体边界应接近页面中心。",
        "图形整体存在明显偏移，通常表现为偏左上或留白不均。",
    ),
    "safe_zone_rule": VisualRule(
        "safe_zone_rule",
        "图标与文字安全区规则",
        "有图标的节点必须采用左图标右文字结构，图标不能压住文字。",
        "图标和文字区域没有明确分隔，存在遮挡风险。",
    ),
    "connector_quality_rule": VisualRule(
        "connector_quality_rule",
        "连接线美观规则",
        "系统图和参考图复刻应优先使用正交折线，并减少无意义拐点。",
        "连接线过乱、斜线过多或连接点不规整。",
    ),
    "semantic_element_rule": VisualRule(
        "semantic_element_rule",
        "元素语义规则",
        "所有线、虚线框、图例和辅助元素都必须有明确语义。",
        "存在无明确语义的虚线、辅助线或装饰元素。",
    ),
    "template_fidelity_rule": VisualRule(
        "template_fidelity_rule",
        "参考图相似度规则",
        "参考图复刻模式应保留页面比例、区域布局、分组、节点样式和视觉语言。",
        "输出与参考图在版式或样式上差距明显。",
    ),
    "readability_rule": VisualRule(
        "readability_rule",
        "文本可读性规则",
        "节点标题和说明应层级清楚，避免过小、过密、裁切。",
        "文本存在过密、过小、层级不清或裁切风险。",
    ),
    "style_consistency_rule": VisualRule(
        "style_consistency_rule",
        "风格一致性规则",
        "节点、线条、颜色、图标应保持同一视觉语言。",
        "存在明显风格混杂或颜色线型不统一。",
    ),
    "polish_pass_rule": VisualRule(
        "polish_pass_rule",
        "绘图后美化规则",
        "绘制后应执行居中、缩放、边距和安全区后处理。",
        "未执行绘图后美化或未生成后处理日志。",
    ),
    "regression_rule": VisualRule(
        "regression_rule",
        "失败案例回归测试规则",
        "反复暴露的问题应加入 benchmark，避免后续退化。",
        "失败案例未沉淀为 benchmark 或验收标准。",
    ),
    "connector_beauty_rule": VisualRule(
        "connector_beauty_rule",
        "连接线美观规则",
        "连线应规整、自然、少拐点，避免看起来像随便绕线。",
        "存在不自然折线、连接点别扭或视觉生硬的问题。",
    ),
    "connector_route_simplify_rule": VisualRule(
        "connector_route_simplify_rule",
        "连接线路由简化规则",
        "能用简单水平/垂直连接时，不应使用复杂折线。",
        "存在可简化但未简化的复杂连接线。",
    ),
    "connector_anchor_rule": VisualRule(
        "connector_anchor_rule",
        "连接锚点规则",
        "左右关系从左右边缘连接，上下关系从上下边缘连接。",
        "连接锚点不自然，导致线条从奇怪位置发出。",
    ),
    "connector_straightness_rule": VisualRule(
        "connector_straightness_rule",
        "连接线直线优先规则",
        "当两个节点可以共线连接时，应优先使用一条水平或垂直直线，避免轻微错位造成折线。",
        "存在本可直连却被画成折线或斜歪短段的问题。",
    ),
    "no_micro_dogleg_rule": VisualRule(
        "no_micro_dogleg_rule",
        "禁止微小折角规则",
        "节点边缘附近不能出现短小横竖折角、贴边绕线或箭头前的小折段。",
        "存在节点旁边的短小折角或箭头前微小狗腿线。",
    ),
    "typography_readability_rule": VisualRule(
        "typography_readability_rule",
        "字体可读性规则",
        "标题和说明文字应达到论文截图可读级别。",
        "字体偏小或阅读吃力。",
    ),
    "text_hierarchy_rule": VisualRule(
        "text_hierarchy_rule",
        "文本层级规则",
        "标题应比说明更醒目，说明也必须清楚可读。",
        "标题与说明层级不清晰。",
    ),
    "safe_resize_rule": VisualRule(
        "safe_resize_rule",
        "安全放大规则",
        "放大字体时应检查换行、溢出、图标遮挡和节点高度。",
        "字体放大可能导致溢出、遮挡或节点过挤。",
    ),
    "reference_locked_reconstruction_rule": VisualRule(
        "reference_locked_reconstruction_rule",
        "参考图锁定式复刻规则",
        "参考图复刻应优先锁定区域、比例、密度和模块相对位置，而不是自由重排。",
        "输出图像像重新排版，未保留参考图版式骨架。",
    ),
    "trace_first_rule": VisualRule(
        "trace_first_rule",
        "Trace 优先规则",
        "复杂参考图应优先依据 template_trace.json 渲染，自动识别不可靠时允许人工修正 trace。",
        "复杂参考图未使用 trace，或自动识别失败后继续乱猜布局。",
    ),
    "preserve_layout_skeleton_rule": VisualRule(
        "preserve_layout_skeleton_rule",
        "版式骨架保留规则",
        "主要区域、虚线框、分支结构和主干流程的位置关系应接近参考图。",
        "主要区域相对位置、分支结构或主干流程与参考图差距过大。",
    ),
    "preserve_density_rule": VisualRule(
        "preserve_density_rule",
        "视觉密度保留规则",
        "模块数量、模块尺寸和页面占用密度应接近参考图。",
        "模块被错误放大、简化或稀疏化，导致密度不像参考图。",
    ),
    "preserve_connector_route_rule": VisualRule(
        "preserve_connector_route_rule",
        "箭头路径保留规则",
        "reference-locked 模式应优先使用 trace 中的 route_points 绘制箭头。",
        "箭头路径被自动路由改写，或缺少 route_points 且未报告。",
    ),
    "reference_fidelity_report_rule": VisualRule(
        "reference_fidelity_report_rule",
        "参考复刻报告规则",
        "每次 reference-locked 渲染后必须生成 reference_fidelity_report.md。",
        "缺少参考复刻质量报告，或报告未说明不像参考图的原因。",
    ),
    "group_layout_failure": VisualRule(
        "group_layout_failure",
        "大分组框比例规则",
        "参考图复刻必须保留主要大分组的位置、比例、尺寸和标题层级。",
        "大分组框位置、比例或尺寸与参考图明显不一致。",
    ),
    "layer_hierarchy_failure": VisualRule(
        "layer_hierarchy_failure",
        "层级遮挡规则",
        "背景、分组、连接线、节点、图标、文字、图例必须按稳定 z-order 绘制。",
        "分组框、节点、图标、文字或连接线层级混乱，导致遮挡或压叠。",
    ),
    "dense_region_collision": VisualRule(
        "dense_region_collision",
        "密集区域碰撞规则",
        "密集区域内部模块应有足够间距，不允许节点、文字、图标互相重叠。",
        "某个区域内部过密，出现节点、图标、文字或连接线碰撞。",
    ),
    "connector_routing_failure": VisualRule(
        "connector_routing_failure",
        "连接线通道规则",
        "复杂参考图连接线必须使用 route_points 或 channel，不能穿过节点、文字、图标或图例。",
        "连接线路由不合格，线穿过节点、文字、图标或重要区域。",
    ),
    "semantic_legend_failure": VisualRule(
        "semantic_legend_failure",
        "语义图例规则",
        "图例必须单独管理位置、颜色、线型和说明，并且不能与主图重叠。",
        "图例缺失、样式错误或与主图发生重叠。",
    ),
    "reference_density_mismatch": VisualRule(
        "reference_density_mismatch",
        "参考密度匹配规则",
        "输出图的元素数量、模块尺寸和区域密度应接近参考图。",
        "输出图过挤、过空或视觉密度明显不像参考图。",
    ),
    "icon_text_collision": VisualRule(
        "icon_text_collision",
        "图标文字碰撞规则",
        "节点必须区分 icon_bbox 和 text_bbox，图标和文字不能互压或贴得太近。",
        "图标与文字没有安全区，发生遮挡或距离过近。",
    ),
    "false_completion": VisualRule(
        "false_completion",
        "禁止误报完成规则",
        "复刻检查不通过时，只能报告未通过和修复建议，不能声称复刻成功。",
        "生成结果明显不像参考图，但系统仍然报告完成或复刻成功。",
    ),
}


DEFAULT_LIMITS = {
    "page_margin": 0.55,
    "center_tolerance_ratio": 0.09,
    "max_content_fill_ratio": 0.88,
    "min_routed_edge_ratio": 0.70,
    "min_icon_text_gap": 0.12,
    "icon_zone_ratio": 0.20,
    "text_zone_ratio": 0.80,
    "title_font_min": 11.2,
    "body_font_min": 8.9,
    "edge_label_font_min": 8.8,
    "max_connector_turns": 2,
    "min_connector_segment": 0.28,
    "min_terminal_segment": 0.42,
    "straight_snap_tolerance": 0.24,
    "axis_overlap_padding": 0.08,
}


def rule_ids() -> list[str]:
    return list(RULES)
