from __future__ import annotations

from pathlib import Path


def select_template_strategy(project_root: Path) -> str:
    if (project_root / "input" / "template.vsdx").exists():
        return "visio_template"
    for name in ("template.png", "template.jpg", "template.jpeg"):
        if (project_root / "input" / name).exists():
            return "image_reference"
    return "from_scratch"


def needs_reference_fidelity(user_text: str) -> bool:
    markers = ["参考图", "模板图", "复现", "照这个图", "不像参考图", "版式", "样式"]
    return any(marker in user_text for marker in markers)
