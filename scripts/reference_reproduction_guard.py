from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


REFERENCE_TRIGGER_WORDS = {
    "按这个图画",
    "复刻",
    "样式接近",
    "格式接近",
    "按模板画",
    "像参考图一样",
    "照着画",
    "参考图",
}


def is_reference_reproduction_task(raw: dict[str, Any], prompt: str = "") -> bool:
    if raw.get("reference_locked", {}).get("enabled"):
        return True
    fidelity = raw.get("template_fidelity", {})
    if fidelity.get("enabled") and fidelity.get("reference_image"):
        return True
    if raw.get("template", {}).get("mode") in {"image_template", "background_reference"}:
        return True
    return any(word in prompt for word in REFERENCE_TRIGGER_WORDS)


def enforce_reference_reproduction(raw: dict[str, Any], prompt: str = "") -> tuple[dict[str, Any], list[str]]:
    """为参考图复刻任务强制关闭自由布局，并要求 fidelity 检查。"""
    messages: list[str] = []
    if not is_reference_reproduction_task(raw, prompt):
        return raw, messages

    raw.setdefault("template_fidelity", {})
    raw["template_fidelity"]["enabled"] = True
    raw["template_fidelity"]["preserve_layout"] = True
    raw["template_fidelity"]["preserve_style"] = True
    raw["template_fidelity"]["avoid_free_layout"] = True
    raw["template_fidelity"]["use_normalized_coordinates"] = raw["template_fidelity"].get("use_normalized_coordinates", True)
    raw["template_fidelity"]["layout_similarity_target"] = max(float(raw["template_fidelity"].get("layout_similarity_target", 0.0)), 0.80)
    raw["layout"] = raw.get("layout") or "grid"
    messages.append("reference_reproduction_guard：已强制启用参考图复刻保护，禁止自由布局替代复刻。")

    raw.setdefault("reference_locked", {})
    raw["reference_locked"]["allow_free_layout"] = False
    raw["reference_locked"]["preserve_relative_position"] = True
    raw["reference_locked"]["preserve_scale"] = True
    return raw, messages


def main() -> int:
    parser = argparse.ArgumentParser(description="检查并强制参考图复刻保护。")
    parser.add_argument("--diagram", default="output/diagram.json")
    parser.add_argument("--prompt", default="")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    path = Path(args.diagram)
    raw = json.loads(path.read_text(encoding="utf-8"))
    updated, messages = enforce_reference_reproduction(raw, args.prompt)
    if args.write:
        path.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
    for message in messages or ["非参考图复刻任务，无需启用 guard。"]:
        print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
