from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from PIL import Image, ImageStat


def review_preview(png_path: Path, drawdsl_path: Path | None = None, collision_report: Path | None = None) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    metrics: dict[str, Any] = {}
    if not png_path.exists():
        return {"passed": False, "metrics": metrics, "issues": [{"type": "missing_preview", "severity": "严重", "message": f"未找到 PNG 预览：{png_path}"}]}

    with Image.open(png_path) as image:
        metrics["width_px"] = image.width
        metrics["height_px"] = image.height
        metrics["aspect_ratio"] = round(image.width / max(1, image.height), 4)
        stat = ImageStat.Stat(image.convert("L"))
        metrics["brightness_stddev"] = round(float(stat.stddev[0]), 3)
        if image.width < 300 or image.height < 200:
            issues.append({"type": "preview_too_small", "severity": "严重", "message": "导出 PNG 尺寸过小，无法作为有效预览。"})
        if stat.stddev[0] < 3:
            issues.append({"type": "blank_preview", "severity": "严重", "message": "导出 PNG 近似空白。"})

    if drawdsl_path and drawdsl_path.exists():
        drawdsl = json.loads(drawdsl_path.read_text(encoding="utf-8"))
        metrics["drawdsl_nodes"] = len(drawdsl.get("nodes", []))
        metrics["drawdsl_connectors"] = len(drawdsl.get("connectors", []))
        if metrics["drawdsl_nodes"] == 0:
            issues.append({"type": "empty_drawdsl", "severity": "严重", "message": "DrawDSL 中没有节点。"})

    if collision_report and collision_report.exists():
        text = collision_report.read_text(encoding="utf-8")
        if "复刻未通过" in text or "严重 /" in text:
            issues.append({"type": "collision_report_failed", "severity": "严重", "message": "碰撞检测报告显示当前复刻未通过。"})

    passed = not any(issue["severity"] == "严重" for issue in issues)
    return {"passed": passed, "metrics": metrics, "issues": issues}


def write_preview_review(result: dict[str, Any], output_path: Path, png_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# PNG Preview 自检报告", "", f"预览图：`{png_path}`", "", f"结论：{'通过' if result['passed'] else '未通过'}", "", "## 指标", ""]
    for key, value in result.get("metrics", {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## 问题", ""])
    if not result.get("issues"):
        lines.append("- 通过：未发现空白图、尺寸过小或碰撞报告失败。")
    else:
        for issue in result["issues"]:
            lines.append(f"- {issue['severity']} / {issue['type']}：{issue['message']}")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="读取导出 PNG 并生成 preview review。")
    parser.add_argument("--png", required=True)
    parser.add_argument("--drawdsl", default="output/drawdsl.json")
    parser.add_argument("--collision-report", default="output/collision_report.md")
    parser.add_argument("--output", default="output/preview_review.md")
    args = parser.parse_args()
    result = review_preview(Path(args.png), Path(args.drawdsl), Path(args.collision_report))
    write_preview_review(result, Path(args.output), Path(args.png))
    print(f"PNG preview 自检完成：{args.output}")
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
