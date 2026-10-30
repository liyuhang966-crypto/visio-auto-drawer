from __future__ import annotations

from schema import Diagram, Edge
from visual_rules import DEFAULT_LIMITS


SEMANTIC_BY_LINE_TYPE = {
    "data": "data_flow",
    "control": "control_flow",
    "feedback": "feedback",
    "status_feedback": "status_feedback",
    "fire_feedback": "feedback",
    "aux": "auxiliary",
}


def normalize_connector_routes(diagram: Diagram) -> Diagram:
    for edge in diagram.edges:
        if edge.semantic is None:
            edge.semantic = SEMANTIC_BY_LINE_TYPE.get(edge.line_type)
        if edge.route is None and edge.route_y is None:
            edge.route = _choose_simple_route(diagram, edge)
    diagram.edges = [edge for edge in diagram.edges if _edge_has_semantic(edge)]
    return diagram


def simplify_connector_routes(diagram: Diagram, preserve_layout: bool = True) -> tuple[Diagram, list[str]]:
    """只修正 edge.route，不移动节点，避免把既有版式重新打乱。"""
    log: list[str] = []
    node_by_id = {node.id: node for node in diagram.nodes}
    for edge in diagram.edges:
        old_route = edge.route
        suggested = _choose_simple_route(diagram, edge)
        if edge.route in {None, "right_then_down", "left_to_right", "vertical_control", "straight_horizontal", "straight_vertical"} or _route_needs_simplification(diagram, edge):
            edge.route = suggested
        if edge.route != old_route:
            log.append(f"line_simplification_pass：{edge.from_}->{edge.to} 路由 {old_route or 'auto'} -> {edge.route}。")

        source = node_by_id.get(edge.from_)
        target = node_by_id.get(edge.to)
        if source and target and edge.route_y is not None:
            if abs((source.y or 0) - (target.y or 0)) <= 0.22:
                edge.route_y = None
                log.append(f"line_simplification_pass：{edge.from_}->{edge.to} 移除不必要的 route_y。")
    if preserve_layout:
        log.append("line_simplification_pass：已保留节点坐标和整体缩放，只调整连接线意图。")
    return diagram, log


def analyze_connector_routes(diagram: Diagram) -> list[dict]:
    issues: list[dict] = []
    for edge in diagram.edges:
        points = estimate_route_points(diagram, edge)
        if len(points) < 2:
            continue
        simplified = simplify_points(points)
        turns = max(0, len(simplified) - 2)
        short_segments = _short_segment_count(simplified)
        route = edge.route or _choose_simple_route(diagram, edge)
        if turns > DEFAULT_LIMITS["max_connector_turns"]:
            issues.append({"edge": f"{edge.from_}->{edge.to}", "type": "excessive_connector_turns", "turns": turns})
        if short_segments:
            issues.append({"edge": f"{edge.from_}->{edge.to}", "type": "short_meaningless_segments", "count": short_segments})
        if _terminal_dogleg_count(simplified):
            issues.append({"edge": f"{edge.from_}->{edge.to}", "type": "micro_dogleg_near_node", "count": _terminal_dogleg_count(simplified)})
        if _can_straighten(diagram, edge) and route not in {"straight_horizontal", "straight_vertical"}:
            issues.append({"edge": f"{edge.from_}->{edge.to}", "type": "avoidable_non_straight_connector", "route": route})
        if _should_use_direct_straight(diagram, edge) and route != "direct_straight":
            issues.append({"edge": f"{edge.from_}->{edge.to}", "type": "avoidable_dogleg_connector", "route": route})
        if route == "right_then_down" and _choose_simple_route(diagram, edge) != "right_then_down":
            issues.append({"edge": f"{edge.from_}->{edge.to}", "type": "ugly_connector_bends", "route": route})
        if _anchor_not_natural(diagram, edge):
            issues.append({"edge": f"{edge.from_}->{edge.to}", "type": "connector_anchor_not_natural", "route": route})
    return issues


def estimate_route_points(diagram: Diagram, edge: Edge) -> list[tuple[float, float]]:
    nodes = {node.id: node for node in diagram.nodes}
    source = nodes.get(edge.from_)
    target = nodes.get(edge.to)
    if source is None or target is None or source.x is None or source.y is None or target.x is None or target.y is None:
        return []
    sx, sy, ex, ey = _anchor_points(source, target, edge.route or _choose_simple_route(diagram, edge))
    route = edge.route or _choose_simple_route(diagram, edge)
    if edge.route_y is not None:
        return simplify_points([(sx, sy), (sx, edge.route_y), (ex, edge.route_y), (ex, ey)])
    if route == "straight_horizontal":
        channel_y = _horizontal_channel(source, target)
        if channel_y is not None:
            sx, sy, ex, ey = _horizontal_anchor_points(source, target, channel_y)
            return [(sx, sy), (ex, ey)]
    if route == "straight_vertical":
        channel_x = _vertical_channel(source, target)
        if channel_x is not None:
            sx, sy, ex, ey = _vertical_anchor_points(source, target, channel_x)
            return [(sx, sy), (ex, ey)]
    if route == "direct_straight":
        return [(sx, sy), (ex, ey)]
    if route == "vertical_control":
        if abs(sx - ex) <= 0.12:
            return [(sx, sy), (ex, ey)]
        mid_y = (sy + ey) / 2
        return simplify_points([(sx, sy), (sx, mid_y), (ex, mid_y), (ex, ey)])
    if route in {"bottom_feedback", "dashed_feedback"}:
        bottom_y = min(sy, ey, 0.65)
        return simplify_points([(sx, sy), (sx, bottom_y), (ex, bottom_y), (ex, ey)])
    if abs(sy - ey) <= 0.12:
        return [(sx, sy), (ex, ey)]
    mid_x = (sx + ex) / 2
    return simplify_points([(sx, sy), (mid_x, sy), (mid_x, ey), (ex, ey)])


def simplify_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    cleaned: list[tuple[float, float]] = []
    min_segment = DEFAULT_LIMITS["min_connector_segment"]
    for point in points:
        if cleaned and _distance(cleaned[-1], point) < min_segment:
            cleaned[-1] = point
        else:
            cleaned.append(point)
    index = 1
    while index < len(cleaned) - 1:
        prev_p, curr_p, next_p = cleaned[index - 1], cleaned[index], cleaned[index + 1]
        same_x = abs(prev_p[0] - curr_p[0]) < 0.03 and abs(curr_p[0] - next_p[0]) < 0.03
        same_y = abs(prev_p[1] - curr_p[1]) < 0.03 and abs(curr_p[1] - next_p[1]) < 0.03
        if same_x or same_y:
            cleaned.pop(index)
        else:
            index += 1
    return cleaned


def _edge_has_semantic(edge: Edge) -> bool:
    if edge.line_type in {"aux", "status_feedback"} and edge.semantic is None:
        return False
    return True


def routed_edge_ratio(diagram: Diagram) -> float:
    if not diagram.edges:
        return 1.0
    routed = sum(1 for edge in diagram.edges if edge.route or edge.route_y is not None)
    return routed / len(diagram.edges)


def _choose_simple_route(diagram: Diagram, edge: Edge) -> str:
    nodes = {node.id: node for node in diagram.nodes}
    source = nodes.get(edge.from_)
    target = nodes.get(edge.to)
    if edge.line_type in {"feedback", "status_feedback", "fire_feedback"} and edge.style == "dashed":
        return "dashed_feedback"
    if edge.line_type in {"feedback", "status_feedback"}:
        return "bottom_feedback"
    if source is None or target is None or source.x is None or source.y is None or target.x is None or target.y is None:
        return "left_to_right" if edge.line_type == "data" else "right_then_down"
    dx = (target.x or 0) - (source.x or 0)
    dy = (target.y or 0) - (source.y or 0)
    if abs(dx) >= abs(dy) and _horizontal_channel(source, target) is not None:
        return "straight_horizontal"
    if abs(dy) > abs(dx) and _vertical_channel(source, target) is not None:
        return "straight_vertical"
    if _should_use_direct_straight(diagram, edge):
        return "direct_straight"
    if abs(dy) > abs(dx) * 1.15:
        return "vertical_control"
    if abs(dx) >= abs(dy) * 0.75:
        return "left_to_right"
    return "right_then_down"


def _route_needs_simplification(diagram: Diagram, edge: Edge) -> bool:
    points = estimate_route_points(diagram, edge)
    if not points:
        return False
    simplified = simplify_points(points)
    return len(points) != len(simplified) or max(0, len(simplified) - 2) > DEFAULT_LIMITS["max_connector_turns"] or _short_segment_count(simplified) > 0


def _anchor_points(source, target, route: str) -> tuple[float, float, float, float]:
    sx, sy = source.x or 0, source.y or 0
    tx, ty = target.x or 0, target.y or 0
    if route == "straight_horizontal":
        channel_y = _horizontal_channel(source, target)
        if channel_y is not None:
            return _horizontal_anchor_points(source, target, channel_y)
    if route == "straight_vertical":
        channel_x = _vertical_channel(source, target)
        if channel_x is not None:
            return _vertical_anchor_points(source, target, channel_x)
    if route == "direct_straight":
        return _direct_anchor_points(source, target)
    if route == "vertical_control":
        return (
            sx,
            sy + (source.height / 2 if ty >= sy else -source.height / 2),
            tx,
            ty - (target.height / 2 if ty >= sy else -target.height / 2),
        )
    return (
        sx + (source.width / 2 if tx >= sx else -source.width / 2),
        sy,
        tx - (target.width / 2 if tx >= sx else -target.width / 2),
        ty,
    )


def _short_segment_count(points: list[tuple[float, float]]) -> int:
    min_segment = DEFAULT_LIMITS["min_connector_segment"]
    return sum(1 for a, b in zip(points, points[1:]) if _distance(a, b) < min_segment)


def _terminal_dogleg_count(points: list[tuple[float, float]]) -> int:
    if len(points) <= 2:
        return 0
    min_terminal = DEFAULT_LIMITS["min_terminal_segment"]
    segments = [_distance(a, b) for a, b in zip(points, points[1:])]
    count = 0
    if segments and segments[0] < min_terminal:
        count += 1
    if len(segments) > 1 and segments[-1] < min_terminal:
        count += 1
    return count


def _can_straighten(diagram: Diagram, edge: Edge) -> bool:
    nodes = {node.id: node for node in diagram.nodes}
    source = nodes.get(edge.from_)
    target = nodes.get(edge.to)
    if source is None or target is None:
        return False
    if _horizontal_channel(source, target) is not None or _vertical_channel(source, target) is not None:
        return False
    dx = abs((target.x or 0) - (source.x or 0))
    dy = abs((target.y or 0) - (source.y or 0))
    return (dx >= dy and _horizontal_channel(source, target) is not None) or (dy > dx and _vertical_channel(source, target) is not None)


def _should_use_direct_straight(diagram: Diagram, edge: Edge) -> bool:
    if edge.line_type in {"feedback", "status_feedback", "fire_feedback", "aux"}:
        return False
    nodes = {node.id: node for node in diagram.nodes}
    source = nodes.get(edge.from_)
    target = nodes.get(edge.to)
    if source is None or target is None:
        return False
    if _horizontal_channel(source, target) is not None or _vertical_channel(source, target) is not None:
        return False
    dx = abs((target.x or 0) - (source.x or 0))
    dy = abs((target.y or 0) - (source.y or 0))
    if dx < 0.01 or dy < 0.01:
        return False
    slope = min(dx, dy) / max(dx, dy)
    return slope <= 0.42


def _anchor_not_natural(diagram: Diagram, edge: Edge) -> bool:
    nodes = {node.id: node for node in diagram.nodes}
    source = nodes.get(edge.from_)
    target = nodes.get(edge.to)
    if source is None or target is None or source.x is None or source.y is None or target.x is None or target.y is None:
        return False
    dx = abs((target.x or 0) - (source.x or 0))
    dy = abs((target.y or 0) - (source.y or 0))
    route = edge.route or _choose_simple_route(diagram, edge)
    return (dx > dy * 1.25 and route == "vertical_control") or (dy > dx * 1.25 and route == "left_to_right")


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _horizontal_channel(source, target) -> float | None:
    padding = DEFAULT_LIMITS["axis_overlap_padding"]
    source_low = (source.y or 0) - source.height / 2 + padding
    source_high = (source.y or 0) + source.height / 2 - padding
    target_low = (target.y or 0) - target.height / 2 + padding
    target_high = (target.y or 0) + target.height / 2 - padding
    low = max(source_low, target_low)
    high = min(source_high, target_high)
    if low <= high:
        return _clamp(((source.y or 0) + (target.y or 0)) / 2, low, high)
    return None


def _vertical_channel(source, target) -> float | None:
    padding = DEFAULT_LIMITS["axis_overlap_padding"]
    source_low = (source.x or 0) - source.width / 2 + padding
    source_high = (source.x or 0) + source.width / 2 - padding
    target_low = (target.x or 0) - target.width / 2 + padding
    target_high = (target.x or 0) + target.width / 2 - padding
    low = max(source_low, target_low)
    high = min(source_high, target_high)
    if low <= high:
        return _clamp(((source.x or 0) + (target.x or 0)) / 2, low, high)
    return None


def _horizontal_anchor_points(source, target, channel_y: float) -> tuple[float, float, float, float]:
    sx = (source.x or 0) + (source.width / 2 if (target.x or 0) >= (source.x or 0) else -source.width / 2)
    ex = (target.x or 0) - (target.width / 2 if (target.x or 0) >= (source.x or 0) else -target.width / 2)
    return sx, channel_y, ex, channel_y


def _vertical_anchor_points(source, target, channel_x: float) -> tuple[float, float, float, float]:
    sy = (source.y or 0) + (source.height / 2 if (target.y or 0) >= (source.y or 0) else -source.height / 2)
    ey = (target.y or 0) - (target.height / 2 if (target.y or 0) >= (source.y or 0) else -target.height / 2)
    return channel_x, sy, channel_x, ey


def _direct_anchor_points(source, target) -> tuple[float, float, float, float]:
    sx, sy = source.x or 0, source.y or 0
    tx, ty = target.x or 0, target.y or 0
    if abs(tx - sx) >= abs(ty - sy):
        return (
            sx + (source.width / 2 if tx >= sx else -source.width / 2),
            sy,
            tx - (target.width / 2 if tx >= sx else -target.width / 2),
            ty,
        )
    return (
        sx,
        sy + (source.height / 2 if ty >= sy else -source.height / 2),
        tx,
        ty - (target.height / 2 if ty >= sy else -target.height / 2),
    )


def _clamp(value: float, low: float, high: float) -> float:
    if low > high:
        low, high = high, low
    return max(low, min(high, value))
