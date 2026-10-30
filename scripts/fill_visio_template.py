from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time
from typing import Any, Iterable

from template_utils import (
    boxes_overlap,
    build_slot_values,
    load_diagram_or_content,
    replace_placeholders,
    resolve_project_path,
    shape_bounds,
    wrap_text,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="填充 Visio 模板文件中的占位符。")
    parser.add_argument("--project-root", default=str(Path.cwd()))
    parser.add_argument("--diagram", default="output/diagram.json")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    diagram_path = resolve_project_path(project_root, args.diagram)

    try:
        diagram = load_diagram_or_content(project_root, diagram_path)
        template_source = diagram.template.source if diagram.template else "input/template.vsdx"
        template_path = resolve_project_path(project_root, template_source)
        output_path = resolve_project_path(project_root, diagram.output or "output/filled_template.vsdx")
        if output_path.name == "result.vsdx":
            output_path = project_root / "output" / "filled_template.vsdx"
        values = build_slot_values(diagram, project_root)
    except Exception as exc:
        print(f"失败：无法读取模板填充配置。原因：{exc}")
        return 1

    if not template_path.exists() or template_path.stat().st_size == 0:
        print(f"失败：未找到有效的 Visio 模板文件：{template_path}")
        print("请把真实的 .vsdx 模板放到 input/template.vsdx，且不要使用空文件占位。")
        return 2

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _remove_existing_output(output_path)

    try:
        import win32com.client  # type: ignore
    except ModuleNotFoundError:
        print("失败：ModuleNotFoundError: win32com。请先运行 scripts\\setup_env.ps1。")
        return 3

    try:
        filled_count = fill_template(template_path, output_path, values, diagram.animation.delay_seconds)
        print(f"成功：已填充 {filled_count} 个模板区域，文件保存到 {output_path}")
        return 0
    except Exception as exc:
        print("失败：Visio 模板填充过程出错。")
        print(f"原因：{exc}")
        print("排查建议：确认模板是有效 .vsdx 文件，并且占位符写在可编辑 Shape.Text 中。")
        return 4


def fill_template(template_path: Path, output_path: Path, values: dict[str, str], delay: float) -> int:
    import win32com.client  # type: ignore

    visio = win32com.client.Dispatch("Visio.Application")
    visio.Visible = True
    try:
        visio.AlertResponse = 1
    except Exception:
        pass
    doc = visio.Documents.Open(str(template_path))
    doc.SaveAs(str(output_path))

    filled_shapes: list[Any] = []
    filled_count = 0
    for page in _iter_pages(doc):
        for shape in _iter_shapes(page.Shapes):
            try:
                original_text = str(shape.Text)
            except Exception:
                continue

            new_text, changed = replace_placeholders(original_text, values)
            if not changed:
                continue

            shape.Text = wrap_text(new_text, width=_estimate_wrap_width(shape))
            _fit_text(shape, len(new_text))
            _avoid_overlap(shape, filled_shapes)
            filled_shapes.append(shape)
            filled_count += 1
            _pause(visio, delay)

    doc.SaveAs(str(output_path))
    return filled_count


def _remove_existing_output(output_path: Path) -> None:
    if not output_path.exists():
        return
    try:
        output_path.unlink()
    except Exception as exc:
        raise RuntimeError(f"无法删除旧输出文件 {output_path}。请确认该文件没有在 Visio 中打开。原始错误：{exc}") from exc


def _iter_pages(doc: Any) -> Iterable[Any]:
    for index in range(1, doc.Pages.Count + 1):
        yield doc.Pages.Item(index)


def _iter_shapes(shapes: Any) -> Iterable[Any]:
    for index in range(1, shapes.Count + 1):
        shape = shapes.Item(index)
        yield shape
        try:
            if shape.Shapes.Count > 0:
                yield from _iter_shapes(shape.Shapes)
        except Exception:
            pass


def _estimate_wrap_width(shape: Any) -> int:
    try:
        width = shape.CellsU("Width").ResultIU
        return max(8, min(32, int(width * 9)))
    except Exception:
        return 18


def _fit_text(shape: Any, text_len: int) -> None:
    try:
        width = shape.CellsU("Width").ResultIU
        height = shape.CellsU("Height").ResultIU
        capacity = max(20, width * height * 26)
        if text_len > capacity * 1.7:
            shape.CellsU("Char.Size").FormulaU = "7.5 pt"
        elif text_len > capacity:
            shape.CellsU("Char.Size").FormulaU = "8.5 pt"
        elif text_len > capacity * 0.7:
            shape.CellsU("Char.Size").FormulaU = "9.5 pt"

        if text_len > capacity * 1.4:
            shape.CellsU("Height").ResultIU = min(height * 1.18, height + 0.35)
    except Exception:
        pass


def _avoid_overlap(shape: Any, previous_shapes: list[Any]) -> None:
    try:
        current = shape_bounds(shape)
        for other in previous_shapes:
            if boxes_overlap(current, shape_bounds(other)):
                pin_y = shape.CellsU("PinY").ResultIU
                shape.CellsU("PinY").ResultIU = pin_y - 0.12
                current = shape_bounds(shape)
    except Exception:
        pass


def _pause(visio: Any, delay: float) -> None:
    try:
        visio.ActiveWindow.Activate()
    except Exception:
        pass
    if delay > 0:
        time.sleep(delay)


if __name__ == "__main__":
    sys.exit(main())
