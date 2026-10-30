from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
import sys
from typing import Any


def record_lesson(case_id: str, review_result: dict[str, Any], output_dir: Path, lesson_md: Path) -> bool:
    failed = not review_result.get("passed", False)
    if not failed:
        return False
    output_dir.mkdir(parents=True, exist_ok=True)
    lesson_md.parent.mkdir(parents=True, exist_ok=True)
    item = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "case_id": case_id,
        "issues": review_result.get("issues", []),
        "metrics": review_result.get("metrics", {}),
        "lesson": "导出预览或碰撞检测失败时，不允许报告完成；应回到 DrawDSL / trace 修正节点安全区、连接线通道和图例位置。",
    }
    jsonl_path = output_dir / "failed_cases.jsonl"
    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    _append_lesson_md(lesson_md, item)
    return True


def _append_lesson_md(path: Path, item: dict[str, Any]) -> None:
    if not path.exists():
        path.write_text("# Reference Reproduction Lessons\n\n", encoding="utf-8")
    lines = [
        "",
        f"## {item['time']} / {item['case_id']}",
        "",
        item["lesson"],
        "",
        "问题：",
    ]
    for issue in item.get("issues", []):
        lines.append(f"- {issue.get('severity', '未知')} / {issue.get('type', 'unknown')}：{issue.get('message', '')}")
    with path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="记录失败案例 lesson。")
    parser.add_argument("--review", default="output/preview_review.json")
    parser.add_argument("--case-id", default="current")
    parser.add_argument("--output-dir", default="output/lessons")
    parser.add_argument("--lesson-md", default="output/lessons/reference_reproduction_lessons.md")
    args = parser.parse_args()
    review = json.loads(Path(args.review).read_text(encoding="utf-8"))
    recorded = record_lesson(args.case_id, review, Path(args.output_dir), Path(args.lesson_md))
    print("lesson 已记录。" if recorded else "预览通过，未记录失败 lesson。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
