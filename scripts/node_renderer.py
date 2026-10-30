from __future__ import annotations

"""
节点渲染策略说明。

当前实际绘制入口仍在 draw_visio.py 中；本模块作为稳定接口记录通用节点模板，
后续可逐步把 draw_visio.py 中的节点绘制逻辑迁移到这里。
"""


CARD_NODE_TEMPLATE = {
    "name": "left_icon_right_text_card",
    "icon_zone_ratio": 0.20,
    "text_zone_ratio": 0.80,
    "min_icon_text_gap": 0.12,
    "min_width": 2.55,
    "min_height": 0.98,
    "title_font_pt": 11.6,
    "body_font_pt": 9.2,
    "font_family": "Microsoft YaHei",
    "title_bold": True,
    "body_smaller": True,
    "rounded_corners": True,
    "auto_wrap": True,
    "safe_resize": True,
}


def safe_zones_for_node(x: float, y: float, width: float, height: float, has_icon: bool = True) -> dict:
    """返回节点内部安全区，供 trace、检测和渲染共用。"""
    left = x - width / 2
    right = x + width / 2
    bottom = y - height / 2
    top = y + height / 2
    if not has_icon:
        return {
            "node_bbox": (left, bottom, right, top),
            "icon_bbox": None,
            "text_bbox": (left + 0.10, bottom + 0.08, right - 0.10, top - 0.08),
        }
    icon_zone_width = min(width * CARD_NODE_TEMPLATE["icon_zone_ratio"], 0.52)
    icon_size = min(height * 0.48, icon_zone_width * 0.72, 0.34)
    icon_cx = left + icon_zone_width / 2 + 0.10
    return {
        "node_bbox": (left, bottom, right, top),
        "icon_bbox": (icon_cx - icon_size / 2, y - icon_size / 2, icon_cx + icon_size / 2, y + icon_size / 2),
        "text_bbox": (left + icon_zone_width + CARD_NODE_TEMPLATE["min_icon_text_gap"], bottom + 0.10, right - 0.10, top - 0.08),
    }


def validate_node_safe_zones(x: float, y: float, width: float, height: float, has_icon: bool = True) -> list[str]:
    zones = safe_zones_for_node(x, y, width, height, has_icon)
    node = zones["node_bbox"]
    text = zones["text_bbox"]
    icon = zones["icon_bbox"]
    issues: list[str] = []
    if icon and not _contains(node, icon):
        issues.append("icon_bbox 超出节点边界")
    if not _contains(node, text):
        issues.append("text_bbox 超出节点边界")
    if icon and _intersects(icon, text):
        issues.append("icon_bbox 与 text_bbox 重叠")
    return issues


def recommended_node_template(has_icon: bool) -> dict:
    if has_icon:
        return CARD_NODE_TEMPLATE.copy()
    return {
        "name": "text_only_card",
        "rounded_corners": True,
        "font_family": "Microsoft YaHei",
        "font_pt": 11.0,
        "auto_wrap": True,
    }


def _contains(outer: tuple[float, float, float, float], inner: tuple[float, float, float, float]) -> bool:
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def _intersects(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])
