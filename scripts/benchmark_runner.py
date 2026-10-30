from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ISSUE_TYPES = {
    "ugly_connector_bends",
    "too_small_font",
    "weak_text_hierarchy",
    "excessive_connector_turns",
    "connector_anchor_not_natural",
    "short_meaningless_segments",
    "avoidable_non_straight_connector",
    "avoidable_dogleg_connector",
    "micro_dogleg_near_node",
    "group_layout_failure",
    "layer_hierarchy_failure",
    "dense_region_collision",
    "connector_routing_failure",
    "semantic_legend_failure",
    "reference_density_mismatch",
    "icon_text_collision",
    "false_completion",
}


def discover_benchmarks(root: Path) -> list[Path]:
    cases_dir = root / "benchmarks" / "cases"
    legacy_dir = root / "benchmarks"
    cases: list[Path] = []
    if cases_dir.exists():
        cases.extend(path for path in cases_dir.iterdir() if path.is_dir())
    if legacy_dir.exists():
        cases.extend(path for path in legacy_dir.iterdir() if path.is_dir() and path.name != "cases")
    return sorted(set(cases))


def run_benchmark_scan(root: Path) -> dict:
    cases = discover_benchmarks(root)
    results = []
    for case in cases:
        criteria = case / "acceptance_criteria.json"
        legacy_criteria = case / "fidelity_criteria.json"
        target = criteria if criteria.exists() else legacy_criteria
        criteria_data = _read_json(target) if target.exists() else {}
        known_issues_text = _read_text(case / "known_issues.md")
        results.append({
            "case": case.name,
            "path": str(case),
            "has_case_doc": (case / "case.md").exists() or (case / "reference_notes.md").exists(),
            "has_target_content": (case / "target_content.json").exists(),
            "has_acceptance_criteria": target.exists(),
            "generic_rules": criteria_data.get("generic_rules", []),
            "issue_types_present": sorted(issue for issue in ISSUE_TYPES if issue in known_issues_text),
            "has_connector_quality_regression": any(issue in known_issues_text for issue in {"ugly_connector_bends", "excessive_connector_turns", "connector_anchor_not_natural", "avoidable_non_straight_connector", "avoidable_dogleg_connector", "micro_dogleg_near_node"}),
            "has_typography_regression": any(issue in known_issues_text for issue in {"too_small_font", "weak_text_hierarchy"}),
        })
    return {"case_count": len(results), "cases": results}


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="扫描并验证 benchmark 目录。")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output", default="output/benchmark_report.json")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    report = run_benchmark_scan(root)
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"benchmark 扫描完成：{output}")
    return 0 if report["case_count"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
