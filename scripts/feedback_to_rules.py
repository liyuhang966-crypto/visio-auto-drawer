from __future__ import annotations


FEEDBACK_RULE_MAP = {
    "图标遮挡文字": ["safe_zone_rule"],
    "整体偏左上": ["canvas_fit_rule", "center_alignment_rule", "polish_pass_rule"],
    "箭头太丑": ["connector_quality_rule", "connector_beauty_rule", "connector_route_simplify_rule", "connector_anchor_rule"],
    "折线不好看": ["connector_beauty_rule", "connector_route_simplify_rule", "connector_anchor_rule", "connector_straightness_rule", "no_micro_dogleg_rule"],
    "箭头不直": ["connector_straightness_rule", "no_micro_dogleg_rule", "connector_anchor_rule"],
    "小折角": ["no_micro_dogleg_rule", "connector_route_simplify_rule"],
    "箭头前面有折线": ["no_micro_dogleg_rule", "connector_straightness_rule"],
    "线太乱": ["connector_quality_rule", "connector_beauty_rule", "connector_route_simplify_rule"],
    "字体太小": ["typography_readability_rule", "text_hierarchy_rule", "safe_resize_rule"],
    "字不清楚": ["typography_readability_rule", "text_hierarchy_rule", "safe_resize_rule"],
    "标题说明层级弱": ["text_hierarchy_rule", "typography_readability_rule"],
    "不像参考图": ["template_fidelity_rule", "style_consistency_rule"],
    "无意义虚线": ["semantic_element_rule"],
    "文字太挤": ["readability_rule", "safe_zone_rule"],
    "不适合论文": ["style_consistency_rule", "readability_rule", "connector_quality_rule"],
}


def feedback_to_rule_ids(feedback: str) -> list[str]:
    matched: list[str] = []
    for marker, rules in FEEDBACK_RULE_MAP.items():
        if marker in feedback:
            matched.extend(rules)
    return sorted(set(matched))
