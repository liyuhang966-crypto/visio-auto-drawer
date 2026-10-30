from __future__ import annotations

import argparse
import json
from pathlib import Path

from template_style_extractor import scientific_layered_palette


def scientific_layered_architecture_trace() -> dict:
    trace = {
        "preset": "scientific_layered_architecture",
        "page_ratio": 1.78,
        "title_slot": None,
        "group_slots": [
            {"id": "perception_input", "title": "感知输入层", "x": 0.015, "y": 0.08, "w": 0.23, "h": 0.70, "color": "blue"},
            {"id": "environment_layer", "title": "环境感知与地图构建层", "x": 0.29, "y": 0.08, "w": 0.31, "h": 0.40, "color": "blue"},
            {"id": "decision_layer", "title": "决策与控制层", "x": 0.29, "y": 0.51, "w": 0.31, "h": 0.34, "color": "blue"},
            {"id": "execution_layer", "title": "执行层", "x": 0.74, "y": 0.08, "w": 0.23, "h": 0.74, "color": "green"}
        ],
        "module_slots": [
            {"id": "lidar", "group": "perception_input", "x": 0.035, "y": 0.16, "w": 0.185, "h": 0.12, "icon": "lidar"},
            {"id": "camera", "group": "perception_input", "x": 0.035, "y": 0.36, "w": 0.185, "h": 0.12, "icon": "camera"},
            {"id": "inertial_encoder", "group": "perception_input", "x": 0.035, "y": 0.56, "w": 0.185, "h": 0.15, "icon": "imu_encoder"},
            {"id": "map_module", "group": "environment_layer", "x": 0.315, "y": 0.15, "w": 0.255, "h": 0.105, "icon": "map_grid"},
            {"id": "fire_detect", "group": "environment_layer", "x": 0.315, "y": 0.28, "w": 0.255, "h": 0.115, "icon": "fire"},
            {"id": "state_estimate", "group": "environment_layer", "x": 0.315, "y": 0.41, "w": 0.255, "h": 0.115, "icon": "robot"},
            {"id": "planner", "group": "decision_layer", "x": 0.315, "y": 0.56, "w": 0.255, "h": 0.105, "icon": "path_planning"},
            {"id": "fire_control", "group": "decision_layer", "x": 0.315, "y": 0.68, "w": 0.255, "h": 0.105, "icon": "target"},
            {"id": "safety", "group": "decision_layer", "x": 0.315, "y": 0.80, "w": 0.255, "h": 0.105, "icon": "shield"},
            {"id": "serial", "group": "execution_layer", "x": 0.765, "y": 0.18, "w": 0.185, "h": 0.105, "icon": "serial_port"},
            {"id": "stm32", "group": "execution_layer", "x": 0.765, "y": 0.34, "w": 0.185, "h": 0.13, "icon": "chip"},
            {"id": "movement", "group": "execution_layer", "x": 0.765, "y": 0.53, "w": 0.185, "h": 0.12, "icon": "motor"},
            {"id": "extinguish", "group": "execution_layer", "x": 0.765, "y": 0.71, "w": 0.185, "h": 0.15, "icon": "fan"}
        ],
        "icon_slots": [],
        "legend_slots": [
            {"id": "legend", "x": 0.05, "y": 0.88, "w": 0.36, "h": 0.06},
            {"id": "bottom_feedback", "x": 0.28, "y": 0.91, "w": 0.65, "h": 0.06}
        ],
        "connector_routes": [
            {"id": "bottom_feedback", "route": "bottom_feedback", "style": "orange_red_dashed"}
        ],
    }
    trace.update(scientific_layered_palette())
    return trace


def main() -> int:
    parser = argparse.ArgumentParser(description="生成参考图版式追踪文件。")
    parser.add_argument("--output", default="output/template_trace.json")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scientific_layered_architecture_trace(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"成功：模板版式追踪文件已生成：{output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
