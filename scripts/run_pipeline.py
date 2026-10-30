"""Portable entry point; keep reference reconstruction separate from free layout."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from drawdsl import write_drawdsl
from reference_reproduction_guard import enforce_reference_reproduction
from schema import Diagram


def resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def reference_requested(raw: dict, forced: bool = False) -> bool:
    return bool(forced or raw.get("reference_locked", {}).get("enabled") or (
        raw.get("template_fidelity", {}).get("enabled")
        and raw.get("template_fidelity", {}).get("mode", "reference_trace") == "reference_trace"
    ))


def main() -> int:
    parser = argparse.ArgumentParser(description="绘图启动入口：普通绘图或锁定参考图布局。")
    parser.add_argument("--project-root", default=str(Path.cwd()))
    parser.add_argument("--diagram", default="output/diagram.json")
    parser.add_argument("--output", default="")
    parser.add_argument("--reference-locked", action="store_true")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    scripts = Path(__file__).resolve().parent
    path = resolve(root, args.diagram)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if args.output:
            raw["output"] = args.output
        if args.reference_locked:
            raw.setdefault("reference_locked", {})["enabled"] = True
        raw, _ = enforce_reference_reproduction(raw)
        diagram = Diagram.model_validate(raw)
    except (OSError, ValueError) as error:
        print(f"无法读取绘图配置：{error}")
        return 1

    def run(script: str, *arguments: str) -> int:
        return subprocess.run([sys.executable, str(scripts / script), *map(str, arguments)], cwd=root).returncode

    if not reference_requested(raw, args.reference_locked):
        parameters = ["--project-root", str(root), "--diagram", str(path)]
        if args.output:
            parameters += ["--output", args.output]
        return run("draw_visio.py", *parameters)

    config = diagram.reference_locked if diagram.reference_locked.enabled else diagram.template_fidelity
    trace_path = resolve(root, config.trace_file)
    reference = resolve(root, config.reference_image)
    output_dir = root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    if not trace_path.exists():
        print("缺少正式 template_trace.json。请先根据参考图标定并检查 draft trace；不会使用自由布局代替复刻。")
        return 2
    try:
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"无法读取 trace：{error}")
        return 2
    if trace.get("manual_trace_required") or not trace.get("elements"):
        print("trace 仍为草稿或缺少 elements；请标定实际元素，确认后再绘制。")
        return 2
    if not reference.is_file():
        print("缺少参考图片，请检查 reference_image。")
        return 2
    write_drawdsl(diagram, output_dir / "drawdsl.json")
    output_path = resolve(root, diagram.output)
    status = run("reference_locked_renderer.py", "--project-root", root,
                 "--reference-image", reference, "--trace", trace_path,
                 "--output", output_path, "--hide-background-on-export")
    if status:
        return status
    fidelity = run("reference_fidelity_check.py", "--diagram", path, "--trace", trace_path,
                   "--report", output_dir / "reference_fidelity_report.md",
                   "--collision-report", output_dir / "collision_report.md",
                   "--collision-json", output_dir / "collision_issues.json",
                   "--repair", output_dir / "trace_repair_suggestions.md")
    preview = run("preview_review.py", "--png", output_path.with_suffix(".png"),
                  "--drawdsl", output_dir / "drawdsl.json",
                  "--collision-report", output_dir / "collision_report.md",
                  "--output", output_dir / "preview_review.md")
    if fidelity or preview:
        print("图纸已保存，但当前复刻未通过。请检查报告、修正 trace 并重新绘制。")
        return 2
    print("结构与预览检查通过；仍需对照原图进行视觉复核。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
