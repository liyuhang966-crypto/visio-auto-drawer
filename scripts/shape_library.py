from __future__ import annotations

"""
复杂论文模型图的通用元素命名表。

本模块只定义元素类型和语义，实际绘制由 reference_locked_renderer.py
或 draw_visio.py 根据 trace / diagram.json 执行。
"""


PAPER_MODEL_ELEMENT_TYPES = {
    "image_patch": "源域、目标域等二维图像补丁。",
    "image_cube": "带叠层效果的图像立方体，可由参考图裁剪素材或彩色块模拟。",
    "support_query_group": "支持集 / 查询集两个小框的组合。",
    "dashed_background_region": "浅色背景和虚线边框的大区域。",
    "conv3d_block": "小型 3D 卷积或特征块。",
    "vertical_operation_block": "最大池化、3D 卷积等竖排文字操作块。",
    "loss_box": "L_d2、L_d3、L_cls 等小损失函数框。",
    "distance_block": "欧式距离等距离计算模块。",
    "prototype_alignment_block": "原型对齐模块。",
    "branch_stack": "右侧分支中的多层小条块。",
}


REFERENCE_LOCKED_REQUIRED_FIELDS = {
    "regions": ["id", "type", "bbox", "style"],
    "elements": ["id", "type", "bbox", "text", "style_ref", "semantic"],
    "connectors": ["id", "from", "to", "route_points", "style", "preserve_route"],
}
