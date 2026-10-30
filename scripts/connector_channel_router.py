from __future__ import annotations

from typing import Any


CHANNELS = {
    "left_to_middle",
    "middle_internal",
    "middle_to_right",
    "right_internal",
    "bottom_feedback",
    "vertical_feedback",
    "legend_line",
}


def infer_channel(source_box: tuple[float, float, float, float], target_box: tuple[float, float, float, float], semantic: str = "") -> str:
    sx = (source_box[0] + source_box[2]) / 2
    tx = (target_box[0] + target_box[2]) / 2
    sy = (source_box[1] + source_box[3]) / 2
    ty = (target_box[1] + target_box[3]) / 2
    if "legend" in semantic:
        return "legend_line"
    if "feedback" in semantic and min(sy, ty) < 0.25:
        return "bottom_feedback"
    if abs(sx - tx) < 0.08:
        return "vertical_feedback"
    if sx < 0.34 and tx < 0.72:
        return "left_to_middle"
    if sx < 0.72 <= tx:
        return "middle_to_right"
    if sx >= 0.70 and tx >= 0.70:
        return "right_internal"
    return "middle_internal"


def route_for_channel(source_box: tuple[float, float, float, float], target_box: tuple[float, float, float, float], channel: str) -> list[list[float]]:
    """按归一化 bbox 生成通道路径；显式 route_points 永远优先于本函数。"""
    sx = source_box[2]
    sy = (source_box[1] + source_box[3]) / 2
    ex = target_box[0]
    ey = (target_box[1] + target_box[3]) / 2
    if channel == "right_internal":
        sx = (source_box[0] + source_box[2]) / 2
        ex = (target_box[0] + target_box[2]) / 2
        return [[sx, source_box[3]], [sx, ey], [ex, ey]]
    if channel == "vertical_feedback":
        sx = (source_box[0] + source_box[2]) / 2
        ex = (target_box[0] + target_box[2]) / 2
        return [[sx, source_box[3]], [ex, target_box[1]]]
    if channel == "bottom_feedback":
        y = 0.94
        sx = (source_box[0] + source_box[2]) / 2
        ex = (target_box[0] + target_box[2]) / 2
        return [[sx, source_box[3]], [sx, y], [ex, y], [ex, target_box[3]]]
    mid_x = (sx + ex) / 2
    if abs(sy - ey) < 0.03:
        return [[sx, sy], [ex, ey]]
    return [[sx, sy], [mid_x, sy], [mid_x, ey], [ex, ey]]


def ensure_connector_channels(trace: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    nodes = {item["id"]: item for item in trace.get("nodes", trace.get("elements", [])) if item.get("id") and item.get("bbox")}
    for connector in trace.get("connectors", []):
        if connector.get("channel") not in CHANNELS:
            source = nodes.get(connector.get("from"))
            target = nodes.get(connector.get("to"))
            if source and target:
                connector["channel"] = infer_channel(tuple(source["bbox"]), tuple(target["bbox"]), connector.get("semantic", ""))
            else:
                connector["channel"] = "middle_internal"
                warnings.append(f"连接线缺少可推断通道的节点：{connector.get('id')}")
        if not connector.get("route_points"):
            source = nodes.get(connector.get("from"))
            target = nodes.get(connector.get("to"))
            if source and target:
                connector["route_points"] = route_for_channel(tuple(source["bbox"]), tuple(target["bbox"]), connector["channel"])
            else:
                warnings.append(f"连接线缺少 route_points，且无法自动生成：{connector.get('id')}")
    return warnings
