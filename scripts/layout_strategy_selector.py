from __future__ import annotations

from schema import Diagram


def select_layout_strategy(diagram: Diagram) -> str:
    if diagram.template_fidelity.enabled:
        return "template_reference"
    if diagram.template is not None:
        return "slot_based_template"
    if diagram.layout:
        return diagram.layout
    if diagram.type == "flowchart":
        return "top_down"
    if diagram.type == "architecture":
        return "paper_architecture"
    if diagram.type == "module_diagram":
        return "symmetric_left_right"
    if diagram.type == "technical_route":
        return "top_down"
    if diagram.type == "er_diagram":
        return "grid"
    return "grid"
