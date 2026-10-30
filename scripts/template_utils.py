from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path
from typing import Any

from schema import ContentSection, Diagram, TemplateContent


def resolve_project_path(project_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return project_root / path


def load_diagram_or_content(project_root: Path, diagram_path: Path | None = None) -> Diagram:
    path = diagram_path or project_root / "output" / "diagram.json"
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return Diagram.model_validate(json.load(f))

    content = parse_content_md(project_root / "input" / "content.md")
    return Diagram(
        title=content.title or "基于模板生成的图",
        type="template_fill",
        output="output/filled_template.vsdx",
        content=content,
    )


def parse_content_md(path: Path) -> TemplateContent:
    if not path.exists():
        return TemplateContent()

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = ""
    summary_lines: list[str] = []
    sections: list[ContentSection] = []
    current_title = ""
    current_body: list[str] = []

    def flush_section() -> None:
        nonlocal current_title, current_body
        if current_title:
            section_id = f"section_{len(sections) + 1}"
            sections.append(
                ContentSection(
                    id=section_id,
                    title=current_title.strip(),
                    body="\n".join(line for line in current_body).strip(),
                )
            )
        current_title = ""
        current_body = []

    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("# "):
            if not title:
                title = line[2:].strip()
            else:
                flush_section()
                current_title = line[2:].strip()
        elif line.startswith("## "):
            flush_section()
            current_title = line[3:].strip()
        else:
            if current_title:
                current_body.append(raw_line)
            elif line:
                summary_lines.append(raw_line)

    flush_section()
    return TemplateContent(title=title, summary="\n".join(summary_lines).strip(), sections=sections)


def build_slot_values(diagram: Diagram, project_root: Path) -> dict[str, str]:
    content = diagram.content or parse_content_md(project_root / "input" / "content.md")
    values: dict[str, str] = {}

    if content.title:
        values["{{标题}}"] = content.title
    elif diagram.title:
        values["{{标题}}"] = diagram.title

    if content.summary:
        values["{{摘要}}"] = content.summary
        values["{{说明}}"] = content.summary

    for index, section in enumerate(content.sections, start=1):
        values[f"{{{{模块{index}}}}}"] = section.title
        values[f"{{{{模块{index}说明}}}}"] = section.body
        values[f"{{{{步骤{index}}}}}"] = section.body or section.title

    for slot in diagram.slots:
        values[slot.placeholder] = slot.text

    return values


def find_template_image(project_root: Path) -> Path | None:
    for name in ("template.png", "template.jpg", "template.jpeg"):
        path = project_root / "input" / name
        if path.exists() and path.stat().st_size > 0:
            return path
    return None


def wrap_text(text: str, width: int = 18) -> str:
    if not text:
        return ""
    lines: list[str] = []
    for line in str(text).splitlines():
        if len(line) <= width:
            lines.append(line)
        else:
            lines.extend(textwrap.wrap(line, width=width, break_long_words=False, replace_whitespace=False))
    return "\n".join(lines)


def replace_placeholders(text: str, values: dict[str, str]) -> tuple[str, bool]:
    new_text = text
    changed = False
    for placeholder, value in values.items():
        if placeholder in new_text:
            new_text = new_text.replace(placeholder, value)
            changed = True
    return new_text, changed


def extract_placeholders(text: str) -> list[str]:
    return re.findall(r"\{\{[^{}]+\}\}", text or "")


def shape_bounds(shape: Any) -> tuple[float, float, float, float]:
    pin_x = shape.CellsU("PinX").ResultIU
    pin_y = shape.CellsU("PinY").ResultIU
    width = shape.CellsU("Width").ResultIU
    height = shape.CellsU("Height").ResultIU
    return (pin_x - width / 2, pin_y - height / 2, pin_x + width / 2, pin_y + height / 2)


def boxes_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])
