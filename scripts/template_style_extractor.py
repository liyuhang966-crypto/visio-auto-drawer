from __future__ import annotations

import json
from pathlib import Path


def scientific_layered_palette() -> dict:
    return {
        "color_palette": {
            "blue": "RGB(45,105,205)",
            "light_blue": "RGB(239,247,255)",
            "green": "RGB(54,145,78)",
            "light_green": "RGB(239,250,242)",
            "orange": "RGB(210,120,38)",
            "light_orange": "RGB(255,247,236)",
            "red": "RGB(205,75,75)",
            "light_red": "RGB(255,239,239)",
            "text": "RGB(20,35,60)",
            "background": "RGB(255,255,255)"
        },
        "line_styles": {
            "group": "dashed",
            "module": "solid",
            "data": "blue_solid",
            "control": "green_solid",
            "feedback": "orange_red_dashed"
        },
        "font_hierarchy": {
            "group_title": 11,
            "module_title": 10.5,
            "module_body": 8.5,
            "edge_label": 7.5,
            "legend": 7.5
        }
    }


def write_style_trace(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(scientific_layered_palette(), ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    write_style_trace(Path("output/template_style.json"))
