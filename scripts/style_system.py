from __future__ import annotations


STYLE_PRESETS = {
    "paper_clean": {
        "description": "论文插图优先，浅色、规整、留白充足。",
        "node": "soft_blue",
        "control": "soft_green",
        "warning": "soft_orange",
        "danger": "soft_red",
    },
    "academic_blue": {
        "description": "科研汇报常用蓝灰风格。",
        "node": "soft_blue",
        "control": "soft_green",
        "warning": "soft_orange",
        "danger": "soft_red",
    },
    "grayscale_print": {
        "description": "黑白打印友好，减少对颜色的依赖。",
        "node": "default",
        "control": "default",
        "warning": "default",
        "danger": "default",
    },
    "engineering_light": {
        "description": "工程汇报风，浅色、现代但克制。",
        "node": "soft_blue",
        "control": "soft_green",
        "warning": "soft_orange",
        "danger": "soft_red",
    },
    "template_match": {
        "description": "参考图复刻优先，尽量沿用模板视觉语言。",
        "node": "soft_blue",
        "control": "soft_green",
        "warning": "soft_orange",
        "danger": "soft_red",
    },
}


TYPOGRAPHY_PRESETS = {
    "paper_readable": {
        "font_family": "Microsoft YaHei",
        "title_font_pt": 11.6,
        "body_font_pt": 9.2,
        "edge_label_font_pt": 8.8,
        "title_body_gap_in": 0.04,
        "inner_padding_in": 0.12,
    }
}


def choose_style_preset(diagram_type: str, template_fidelity_enabled: bool = False, requested: str | None = None) -> str:
    if requested and requested in STYLE_PRESETS:
        return requested
    if template_fidelity_enabled:
        return "template_match"
    if diagram_type in {"architecture", "module_diagram", "technical_route"}:
        return "paper_clean"
    return "academic_blue"


def typography_preset(name: str = "paper_readable") -> dict:
    return TYPOGRAPHY_PRESETS.get(name, TYPOGRAPHY_PRESETS["paper_readable"]).copy()
