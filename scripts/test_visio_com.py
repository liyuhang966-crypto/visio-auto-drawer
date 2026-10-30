from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(description="测试 Microsoft Visio COM 自动化。")
    parser.add_argument("--project-root", default=str(Path.cwd()))
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    output_path = project_root / "output" / "com_test.vsdx"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import win32com.client  # type: ignore
    except ModuleNotFoundError:
        print("失败：ModuleNotFoundError: win32com。请先运行 scripts\\setup_env.ps1。")
        return 1

    try:
        visio = win32com.client.Dispatch("Visio.Application")
        visio.Visible = True
        doc = visio.Documents.Add("")
        page = visio.ActivePage
        page.PageSheet.CellsU("PageWidth").ResultIU = 8.5
        page.PageSheet.CellsU("PageHeight").ResultIU = 6.0

        shape = page.DrawRectangle(2.0, 3.0, 6.5, 4.2)
        shape.Text = "Visio COM 测试成功"
        shape.CellsU("Char.Size").FormulaU = "14 pt"
        shape.CellsU("Para.HorzAlign").FormulaU = "1"
        shape.CellsU("VerticalAlign").FormulaU = "1"
        shape.CellsU("FillForegnd").FormulaU = "RGB(230,242,255)"
        shape.CellsU("LineColor").FormulaU = "RGB(65,105,180)"

        time.sleep(0.5)
        doc.SaveAs(str(output_path))
        print(f"成功：Visio COM 测试文件已保存到 {output_path}")
        return 0
    except Exception as exc:
        print("失败：无法通过 COM 自动控制 Microsoft Visio。")
        print(f"原因：{exc}")
        print("请确认已安装 Microsoft Visio 桌面版，并且 Visio 已正确注册 COM。")
        return 2


if __name__ == "__main__":
    sys.exit(main())
