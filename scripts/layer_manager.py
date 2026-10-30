from __future__ import annotations

from typing import Any


LAYER_Z_ORDER = {
    "background_reference": 0,
    "group_background": 5,
    "group_border": 10,
    "connector": 20,
    "node_card": 30,
    "node_icon": 40,
    "node_text": 45,
    "connector_label": 48,
    "legend": 50,
}


def send_to_layer(shape: Any, layer_name: str) -> None:
    """在 Visio COM 能力范围内尽量调整 z-order。"""
    target = LAYER_Z_ORDER.get(layer_name, 30)
    try:
        if target <= 10:
            shape.SendToBack()
        elif target >= 40:
            shape.BringToFront()
    except Exception:
        pass


def normalize_z_order(groups: list[Any], connectors: list[Any], nodes: list[Any], overlays: list[Any] | None = None) -> None:
    for shape in groups:
        send_to_layer(shape, "group_background")
    for shape in connectors:
        send_to_layer(shape, "connector")
    for shape in nodes:
        send_to_layer(shape, "node_card")
    for shape in overlays or []:
        send_to_layer(shape, "legend")
