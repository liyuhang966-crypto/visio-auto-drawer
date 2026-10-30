from __future__ import annotations

from pathlib import Path
from typing import Any


class VisioBackend:
    """Visio COM 的薄封装。

    第一阶段只封装稳定原子操作，现有 draw_visio.py 仍可保留高层绘图逻辑。
    """

    def __init__(self, visible: bool = True) -> None:
        import win32com.client  # type: ignore

        self.app = win32com.client.Dispatch("Visio.Application")
        self.app.Visible = visible
        try:
            self.app.AlertResponse = 1
        except Exception:
            pass

    def get_reusable_document(self, output_path: Path) -> tuple[Any, Any]:
        output_path = output_path.resolve()
        doc = self.find_open_document(output_path)
        if doc is None and output_path.exists():
            doc = self.app.Documents.Open(str(output_path))
        if doc is None:
            doc = self.app.Documents.Add("")
        page = doc.Pages.Item(1)
        self.clear_page(page)
        try:
            self.app.ActiveWindow.Page = page
        except Exception:
            pass
        return doc, page

    def find_open_document(self, output_path: Path) -> Any | None:
        for index in range(1, self.app.Documents.Count + 1):
            doc = self.app.Documents.Item(index)
            try:
                if Path(str(doc.FullName)).resolve() == output_path:
                    return doc
            except Exception:
                continue
        return None

    def clear_page(self, page: Any) -> None:
        for index in range(page.Shapes.Count, 0, -1):
            try:
                page.Shapes.Item(index).Delete()
            except Exception:
                pass

    def add_rectangle(self, page: Any, left: float, bottom: float, right: float, top: float, text: str = "") -> Any:
        shape = page.DrawRectangle(left, bottom, right, top)
        shape.Text = text
        return shape

    def add_oval(self, page: Any, left: float, bottom: float, right: float, top: float, text: str = "") -> Any:
        shape = page.DrawOval(left, bottom, right, top)
        shape.Text = text
        return shape

    def add_line(self, page: Any, x1: float, y1: float, x2: float, y2: float) -> Any:
        return page.DrawLine(x1, y1, x2, y2)

    def import_image(self, page: Any, image_path: Path, pin_x: float, pin_y: float, width: float, height: float) -> Any:
        shape = page.Import(str(image_path))
        shape.CellsU("PinX").ResultIU = pin_x
        shape.CellsU("PinY").ResultIU = pin_y
        shape.CellsU("Width").ResultIU = width
        shape.CellsU("Height").ResultIU = height
        return shape

    def set_cell(self, shape: Any, cell_name: str, formula: str) -> None:
        try:
            shape.CellsU(cell_name).FormulaU = formula
        except Exception:
            pass

    def save(self, doc: Any, output_path: Path) -> None:
        if output_path.exists():
            doc.Save()
        else:
            doc.SaveAs(str(output_path))

    def export_png(self, doc: Any, output_path: Path) -> Path:
        png_path = output_path.with_suffix(".png")
        page = doc.Pages.Item(1)
        page.Export(str(png_path))
        return png_path
