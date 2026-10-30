from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from template_utils import find_template_image
from template_layout_trace import scientific_layered_architecture_trace


def main() -> int:
    parser = argparse.ArgumentParser(description="分析图片模板的版式结构。")
    parser.add_argument("--project-root", default=str(Path.cwd()))
    parser.add_argument("--image", default="")
    parser.add_argument("--output", default="output/template_detected.json")
    parser.add_argument("--trace-output", default="output/template_trace.json")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    image_path = Path(args.image) if args.image else find_template_image(project_root)
    if image_path is not None and not image_path.is_absolute():
        image_path = project_root / image_path
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = project_root / output_path
    trace_output_path = Path(args.trace_output)
    if not trace_output_path.is_absolute():
        trace_output_path = project_root / trace_output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if image_path is None or not image_path.exists() or image_path.stat().st_size == 0:
        result = fallback_result(None, "未找到有效图片模板，已进入背景参考模式。")
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        trace_output_path.parent.mkdir(parents=True, exist_ok=True)
        trace_output_path.write_text(json.dumps(scientific_layered_architecture_trace(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"警告：未找到有效图片模板，已生成退化配置：{output_path}")
        print(f"成功：模板版式追踪文件已保存到 {trace_output_path}")
        return 0

    try:
        result = analyze_image(image_path)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        trace_output_path.parent.mkdir(parents=True, exist_ok=True)
        trace_output_path.write_text(json.dumps(scientific_layered_architecture_trace(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"成功：图片模板分析结果已保存到 {output_path}")
        print(f"成功：模板版式追踪文件已保存到 {trace_output_path}")
        return 0
    except Exception as exc:
        result = fallback_result(str(image_path), f"图片分析失败，已退化为背景参考模式。原因：{exc}")
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        trace_output_path.parent.mkdir(parents=True, exist_ok=True)
        trace_output_path.write_text(json.dumps(scientific_layered_architecture_trace(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"警告：图片分析失败，已生成背景参考配置：{output_path}")
        print(f"原因：{exc}")
        return 0


def analyze_image(image_path: Path) -> dict:
    from PIL import Image
    import cv2
    import numpy as np

    with Image.open(image_path) as img:
        width, height = img.size

    image = cv2.imread(str(image_path))
    if image is None:
        return fallback_result(str(image_path), "OpenCV 无法读取图片，使用背景参考模式。")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blurred, 60, 160)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < (width * height * 0.002) or area > (width * height * 0.8):
            continue
        if w < 30 or h < 20:
            continue
        boxes.append({"x": int(x), "y": int(y), "width": int(w), "height": int(h), "confidence": 0.55})

    boxes = _dedupe_boxes(sorted(boxes, key=lambda item: (item["y"], item["x"])))[:24]

    detected_lines = []
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=90, minLineLength=max(40, width // 12), maxLineGap=12)
    if lines is not None:
        for line in lines[:40]:
            x1, y1, x2, y2 = line[0]
            detected_lines.append({"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2), "confidence": 0.45})

    text_regions = _suggest_text_regions(boxes, width, height)
    suggested_slots = []
    for index, region in enumerate(text_regions, start=1):
        placeholder = "{{标题}}" if index == 1 and region["role"] == "title" else f"{{{{模块{index}}}}}"
        suggested_slots.append({"id": f"slot_{index}", "placeholder": placeholder, "region": region})

    mode = "detected_layout" if boxes or detected_lines else "background_reference"
    return {
        "source": str(image_path),
        "mode": mode,
        "page_size": {"pixel_width": width, "pixel_height": height, "suggested_width": 13.0, "suggested_height": round(13.0 * height / width, 2)},
        "detected_boxes": boxes,
        "detected_lines": detected_lines,
        "possible_text_regions": text_regions,
        "suggested_slots": suggested_slots,
        "notes": "识别结果用于辅助排版，不代表像素级复刻。识别不可靠时可使用背景参考模式。",
    }


def fallback_result(source: str | None, note: str) -> dict:
    return {
        "source": source,
        "mode": "background_reference",
        "page_size": {"pixel_width": 0, "pixel_height": 0, "suggested_width": 13.0, "suggested_height": 9.0},
        "detected_boxes": [],
        "detected_lines": [],
        "possible_text_regions": [],
        "suggested_slots": [],
        "notes": note,
    }


def _suggest_text_regions(boxes: list[dict], width: int, height: int) -> list[dict]:
    regions = []
    title_region = {"x": int(width * 0.08), "y": int(height * 0.04), "width": int(width * 0.84), "height": int(height * 0.12), "role": "title"}
    regions.append(title_region)
    for box in boxes[:12]:
        role = "module" if box["height"] > 30 else "label"
        regions.append({**box, "role": role})
    return regions


def _dedupe_boxes(boxes: list[dict]) -> list[dict]:
    result = []
    for box in boxes:
        duplicate = False
        for existing in result:
            if _iou(box, existing) > 0.45:
                duplicate = True
                break
        if not duplicate:
            result.append(box)
    return result


def _iou(a: dict, b: dict) -> float:
    ax2 = a["x"] + a["width"]
    ay2 = a["y"] + a["height"]
    bx2 = b["x"] + b["width"]
    by2 = b["y"] + b["height"]
    ix1 = max(a["x"], b["x"])
    iy1 = max(a["y"], b["y"])
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    union = a["width"] * a["height"] + b["width"] * b["height"] - inter
    return inter / union if union else 0.0


if __name__ == "__main__":
    sys.exit(main())
