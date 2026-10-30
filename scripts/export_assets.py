from __future__ import annotations

from pathlib import Path
from typing import Any


def export_png(doc: Any, output_vsdx: Path) -> tuple[bool, str]:
    png_path = output_vsdx.with_suffix(".png")
    settings = None
    previous_resolution = None
    previous_size = None
    try:
        settings = doc.Application.Settings
        previous_resolution = settings.GetRasterExportResolution()
        previous_size = settings.GetRasterExportSize()
        # Visio enums: custom resolution=3, pixels/inch=0, source size=2.
        # Explicit resolution avoids tiny previews caused by UI export defaults.
        settings.SetRasterExportResolution(3, 200, 200, 0)
        settings.SetRasterExportSize(2, 0, 0, 0)
        page = doc.Pages.Item(1)
        page.Export(str(png_path))
        return png_path.exists(), str(png_path)
    except Exception as exc:
        return False, f"PNG 导出失败：{exc}"
    finally:
        if settings is not None:
            if previous_resolution is not None:
                try:
                    settings.SetRasterExportResolution(*previous_resolution)
                except Exception:
                    pass
            if previous_size is not None:
                try:
                    settings.SetRasterExportSize(*previous_size)
                except Exception:
                    pass
