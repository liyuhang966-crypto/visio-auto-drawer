from __future__ import annotations

import math
from collections import defaultdict, deque
from typing import Iterable

from schema import Diagram, Node


def apply_auto_layout(diagram: Diagram) -> Diagram:
    """补齐缺失坐标，同时保留用户手工指定的位置。"""
    if not diagram.nodes:
        return diagram

    if not (diagram.template_fidelity.enabled and diagram.template_fidelity.preserve_layout):
        _resize_nodes_for_text(diagram.nodes)
    layout = diagram.layout or "left_right"
    if layout == "top_down":
        positions = _top_down_positions(diagram)
    elif layout == "left_right":
        positions = _left_right_positions(diagram)
    elif layout == "symmetric_left_right":
        positions = _symmetric_left_right_positions(diagram)
    elif layout == "grid":
        positions = _grid_positions(diagram.nodes, diagram.page.width, diagram.page.height)
    elif layout in {"radial", "radial_balanced"}:
        positions = _radial_positions(diagram.nodes, diagram.page.width, diagram.page.height)
    elif layout in {"hub_spoke", "paper_architecture"}:
        positions = _paper_architecture_positions(diagram)
    else:
        positions = _grid_positions(diagram.nodes, diagram.page.width, diagram.page.height)

    for node in diagram.nodes:
        if node.x is None:
            node.x = positions[node.id][0]
        if node.y is None:
            node.y = positions[node.id][1]

    return diagram


def _resize_nodes_for_text(nodes: Iterable[Node]) -> None:
    for node in nodes:
        if node.shape in {"block3d", "image"} or node.image or node.style in {"nn_block", "pool_orange", "conv_blue", "feature_blue"}:
            continue
        longest = max((len(line) for line in node.text.splitlines()), default=len(node.text))
        lines = max(1, len(node.text.splitlines()))
        node.width = max(node.width, min(3.6, 1.55 + longest * 0.095))
        node.height = max(node.height, min(1.8, 0.55 + lines * 0.22))


def _top_down_positions(diagram: Diagram) -> dict[str, tuple[float, float]]:
    levels = _levels(diagram)
    return _positions_from_levels(levels, diagram.page.width, diagram.page.height, horizontal=False)


def _left_right_positions(diagram: Diagram) -> dict[str, tuple[float, float]]:
    levels = _levels(diagram)
    return _positions_from_levels(levels, diagram.page.width, diagram.page.height, horizontal=True)


def _symmetric_left_right_positions(diagram: Diagram) -> dict[str, tuple[float, float]]:
    center_y = diagram.page.height / 2
    margin = max(0.7, diagram.page.margin)
    left_x = margin + 1.7
    right_x = diagram.page.width - margin - 1.7
    center_x = diagram.page.width / 2
    hub = _choose_hub(diagram)
    positions: dict[str, tuple[float, float]] = {}
    if hub:
        positions[hub.id] = (center_x, center_y)
    others = [node for node in diagram.nodes if not hub or node.id != hub.id]
    half = (len(others) + 1) // 2
    left_nodes = others[:half]
    right_nodes = others[half:]
    for index, node in enumerate(left_nodes):
        positions[node.id] = (left_x, _spread(index, len(left_nodes), diagram.page.height - 1.55, 1.45))
    for index, node in enumerate(right_nodes):
        positions[node.id] = (right_x, _spread(index, len(right_nodes), diagram.page.height - 1.55, 1.45))
    return positions


def _paper_architecture_positions(diagram: Diagram) -> dict[str, tuple[float, float]]:
    margin = max(0.75, diagram.page.margin)
    width = diagram.page.width
    height = diagram.page.height
    center_x = width / 2
    center_y = height / 2
    hub = _choose_hub(diagram)
    positions: dict[str, tuple[float, float]] = {}
    if hub is None:
        return _radial_positions(diagram.nodes, width, height)

    positions[hub.id] = (center_x, center_y)
    others = [node for node in diagram.nodes if node.id != hub.id]

    slots = [
        (margin + 1.55, center_y + 1.55),
        (margin + 1.55, center_y - 1.55),
        (width - margin - 1.55, center_y + 1.55),
        (width - margin - 1.55, center_y - 1.55),
        (center_x, height - margin - 1.05),
        (center_x, margin + 1.05),
        (margin + 1.55, center_y),
        (width - margin - 1.55, center_y),
    ]

    preferred: dict[str, tuple[float, float]] = {}
    for node in others:
        key = f"{node.id} {node.text}".lower()
        if any(word in key for word in ["sensor", "传感", "rplidar", "camera", "摄像"]):
            preferred[node.id] = (margin + 1.55, center_y)
        elif any(word in key for word in ["stm32", "下位机"]):
            preferred[node.id] = (width - margin - 1.55, center_y)
        elif any(word in key for word in ["motor", "电机"]):
            preferred[node.id] = (width - margin - 1.55, center_y - 2.25)
        elif any(word in key for word in ["mobile", "移动端", "监控"]):
            preferred[node.id] = (center_x, height - margin - 1.0)
        elif any(word in key for word in ["fire", "灭火", "继电器", "水泵", "风扇"]):
            preferred[node.id] = (center_x, margin + 1.0)

    used: set[tuple[float, float]] = set()
    for node in others:
        if node.id in preferred:
            positions[node.id] = preferred[node.id]
            used.add(preferred[node.id])

    slot_index = 0
    for node in others:
        if node.id in positions:
            continue
        while slot_index < len(slots) and slots[slot_index] in used:
            slot_index += 1
        if slot_index < len(slots):
            positions[node.id] = slots[slot_index]
            used.add(slots[slot_index])
            slot_index += 1
        else:
            angle = 2 * math.pi * (slot_index + 1) / max(1, len(others))
            positions[node.id] = (
                center_x + math.cos(angle) * min(width, height) * 0.35,
                center_y + math.sin(angle) * min(width, height) * 0.35,
            )
            slot_index += 1

    return positions


def _levels(diagram: Diagram) -> list[list[Node]]:
    by_id = {node.id: node for node in diagram.nodes}
    outgoing: dict[str, list[str]] = defaultdict(list)
    indegree = {node.id: 0 for node in diagram.nodes}

    for edge in diagram.edges:
        outgoing[edge.from_].append(edge.to)
        indegree[edge.to] += 1

    queue = deque([node_id for node_id, degree in indegree.items() if degree == 0])
    if not queue:
        return [diagram.nodes]

    depth: dict[str, int] = {node_id: 0 for node_id in queue}
    while queue:
        node_id = queue.popleft()
        for child_id in outgoing[node_id]:
            depth[child_id] = max(depth.get(child_id, 0), depth[node_id] + 1)
            indegree[child_id] -= 1
            if indegree[child_id] == 0:
                queue.append(child_id)

    for node in diagram.nodes:
        depth.setdefault(node.id, 0)

    max_depth = max(depth.values()) if depth else 0
    levels: list[list[Node]] = [[] for _ in range(max_depth + 1)]
    for node in diagram.nodes:
        levels[depth[node.id]].append(by_id[node.id])
    return [level for level in levels if level]


def _positions_from_levels(
    levels: list[list[Node]],
    page_width: float,
    page_height: float,
    horizontal: bool,
) -> dict[str, tuple[float, float]]:
    margin_x = 1.1
    margin_y = 1.0
    positions: dict[str, tuple[float, float]] = {}

    level_count = max(1, len(levels))
    for level_index, nodes in enumerate(levels):
        if horizontal:
            x = _spread(level_index, level_count, margin_x, page_width - margin_x)
            for item_index, node in enumerate(nodes):
                y = _spread(item_index, len(nodes), page_height - margin_y, margin_y)
                positions[node.id] = (x, y)
        else:
            y = _spread(level_index, level_count, page_height - margin_y, margin_y)
            for item_index, node in enumerate(nodes):
                x = _spread(item_index, len(nodes), margin_x, page_width - margin_x)
                positions[node.id] = (x, y)

    return positions


def _grid_positions(nodes: Iterable[Node], page_width: float, page_height: float) -> dict[str, tuple[float, float]]:
    node_list = list(nodes)
    count = len(node_list)
    cols = max(1, math.ceil(math.sqrt(count)))
    rows = max(1, math.ceil(count / cols))

    positions: dict[str, tuple[float, float]] = {}
    for index, node in enumerate(node_list):
        row = index // cols
        col = index % cols
        x = _spread(col, cols, 1.1, page_width - 1.1)
        y = _spread(row, rows, page_height - 1.0, 1.0)
        positions[node.id] = (x, y)
    return positions


def _radial_positions(nodes: Iterable[Node], page_width: float, page_height: float) -> dict[str, tuple[float, float]]:
    node_list = list(nodes)
    center_x = page_width / 2
    center_y = page_height / 2
    radius = max(2.0, min(page_width, page_height) * 0.34)

    positions: dict[str, tuple[float, float]] = {}
    if len(node_list) == 1:
        positions[node_list[0].id] = (center_x, center_y)
        return positions

    for index, node in enumerate(node_list):
        angle = (2 * math.pi * index / len(node_list)) + (math.pi / 2)
        positions[node.id] = (
            center_x + radius * math.cos(angle),
            center_y + radius * math.sin(angle),
        )
    return positions


def _choose_hub(diagram: Diagram) -> Node | None:
    if not diagram.nodes:
        return None
    degree = {node.id: 0 for node in diagram.nodes}
    for edge in diagram.edges:
        degree[edge.from_] = degree.get(edge.from_, 0) + 1
        degree[edge.to] = degree.get(edge.to, 0) + 1
    keywords = ["树莓派", "raspberry", "上位机", "server", "中心", "host", "控制器"]
    scored = []
    for node in diagram.nodes:
        keyword_bonus = 4 if any(word in f"{node.id} {node.text}".lower() for word in keywords) else 0
        scored.append((degree.get(node.id, 0) + keyword_bonus, node))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def _spread(index: int, count: int, start: float, end: float) -> float:
    if count <= 1:
        return (start + end) / 2
    return start + (end - start) * index / (count - 1)
