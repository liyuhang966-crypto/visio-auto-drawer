---
name: visio-auto-drawer
description: 当用户需要根据自然语言、参考图、流程描述、ER 模型、系统架构、模块关系、网络拓扑、类 UML 结构或技术路线，在 Microsoft Visio 中创建、复现、编辑或优化图纸时使用。该 skill 会把需求转换为 diagram.json，并通过 Python COM 自动化在可见的 Visio 桌面应用中逐步绘制。
---

# visio-auto-drawer

当用户想用自然语言创建、复现、修改或细化 Microsoft Visio 图纸时，使用这个 skill。适用内容包括流程图、系统架构图、ER 图、模块关系图、网络拓扑图、技术路线图、论文配图、汇报图和工程设计图。

本 skill 同时支持模板模式：用户提供 `.vsdx` 模板或 PNG/JPG/JPEG 图片模板时，优先保留模板风格，并生成可编辑的 Visio 输出。

本 skill 还支持参考图版式复刻模式：用户提供参考图时，不只提取内容，还要尽量复刻页面比例、左中右区域、虚线分组框、模块相对位置、图标、箭头方向、图例和底部反馈线。复刻结果仍必须是可编辑 Visio 形状，不能只贴一张图片。

本 skill 的目标不是一次性画出一张图片，而是生成可编辑、可复用、可优化的 Visio 图。生成后必须执行质量检查；如果质量检查未通过，必须自动修复至少一轮，并输出 `quality_report.md` 和 `repair_log.md`。

本 skill 的长期架构采用 `intent -> analysis -> plan -> drawdsl -> backend -> preview -> review -> lesson` 流水线。第一阶段已经引入 `DrawDSL` 中间层、`visio_backend` COM 封装、PNG preview 自检和失败 lesson 存储；现有 `draw_visio.py` 仍保留可运行绘图能力，后续逐步迁移到更清晰的 planner / renderer / backend / checker / lesson 分层。

## 必须遵守

1. 不使用鼠标或键盘模拟点击 Visio。
2. 必须先生成或更新 `output/diagram.json`。
3. 必须通过 `pywin32` 和 Windows COM 控制 Visio，核心入口是 `win32com.client.Dispatch("Visio.Application")`。
4. 必须设置 `visio.Visible = True`，让用户能看到 Visio 桌面窗口。
5. 必须逐步绘制节点、分组、连接线和文字；每一步后按 `animation.delay_seconds` 短暂停顿。
6. 必须保留用户给出的中文节点名称、边说明和分组标题，不要擅自改写中文。
7. 如果用户描述不完整，按工程图、论文图、系统设计图的常见布局合理推断，不要频繁追问。
8. 不依赖特定 Visio stencil，优先使用 `DrawRectangle`、`DrawOval`、`DrawLine` 等基础 COM 绘制能力。
9. 模板模式不能覆盖用户原始模板，必须另存到 `output` 目录。
10. 图片模板不能只贴一张死图片就结束，必须尽量覆盖可编辑的 Visio 形状和文字。
11. 当用户说“照这个图”“这个图也一样”“复现模板风格”时，优先启用参考图版式复刻模式。
12. 不允许只针对当前图硬编码修复。用户反馈的“丑、乱、偏、遮挡、不像模板”等问题，应优先沉淀成通用规则。
13. 不允许为了模仿参考图生成无意义元素。所有线、框、虚线、图例都必须有语义。
14. 反复优化同一张图时，默认复用 `diagram.output` 指定的同一个 Visio 文件，不要连续打开新的 Visio 文档，不要随意制造 `_v2`、`_v3` 等版本文件。
15. 如果目标 `.vsdx` 已在 Visio 中打开，应清空当前第一页并在同一文档内重画，然后保存；只有用户明确要求保留多个版本，或目标文件确实无法复用时，才另存新文件，并说明原因。
16. 当参考图里有 Visio 基础形状难以复刻的小图片、立方体、设备图标或纹理块，且用户没有单独提供素材时，应从原参考图中裁剪对应区域，做适度放大、锐化、对比度和色彩增强，再作为 `image` 节点插入 Visio；不能因此把整张参考图当背景贴图糊弄过去。
17. 当用户提供参考图并要求“照着画”“复刻”“按这个模板”“样式接近”“格式接近”时，必须优先进入 reference-locked editable reconstruction mode，禁止直接使用普通自由布局重排参考图。
18. 复杂参考图的复刻优先级是：位置接近、比例接近、结构接近、样式接近、文字准确。不能只保证内容准确却把版式画崩。
19. reference-locked 模式必须优先读取 `output/template_trace.json`；如果没有正式 trace，应生成 `output/template_trace.draft.json`，并提示用户人工校正，而不是继续乱猜布局。
20. reference-locked 模式必须生成 `output/reference_fidelity_report.md`。如果主要区域、密度、箭头路径或小元素不像参考图，不能声称复刻成功。
21. 当用户提供参考图并要求“按这个图画”“复刻”“样式接近”“格式接近”“按模板画”“像参考图一样”时，必须触发 `reference_reproduction_guard`，禁止自由布局替代参考图复刻。
22. 参考图复刻输出前必须运行 `reference_fidelity_check` 和 `collision_detector`，并生成 `output/reference_fidelity_report.md`、`output/collision_report.md`、`output/trace_repair_suggestions.md`。
23. 如果出现大分组错位、节点重叠、图标文字重叠、连接线穿过文字或节点、图例缺失、视觉密度明显不一致、输出像自由重排等严重问题，必须报告“当前复刻未通过”。
24. 复刻未通过时，不允许说“复刻成功”“已完成复现”“效果接近”。必须列出失败原因、需要修正的 trace 字段和下一轮自动修复或人工校正建议。
25. 用户反馈的问题必须沉淀为通用规则和 benchmark；不能只移动当前图的某个坐标来掩盖问题。
26. 每次绘图应生成或更新 `output/drawdsl.json`，作为渲染前中间层契约。
27. 导出 PNG 后应生成 `output/preview_review.md`；如果预览为空白、尺寸异常或碰撞报告失败，应沉淀到 `output/lessons/failed_cases.jsonl` 和 skill lessons。

## 支持图类型

- `flowchart`
- `architecture`
- `er_diagram`
- `module_diagram`
- `network_topology`
- `technical_route`
- `template_fill`

同时支持科研网络结构图中的简洁 3D 特征块，例如 CNN、残差网络、池化层、卷积层等横向链式结构。此类图可使用 `block3d` 表达蓝色特征块，使用 `black_arrow` 表达论文图常见黑色直箭头。

如果参考图包含无法用基础 Visio 形状自然表达的小图片，可以使用 `image` 节点插入裁剪增强后的局部素材。素材应保存到项目 `output/assets/`，并在 `diagram.json` 的节点中写入 `image` 路径。

## 每次绘图流程

1. 解析用户需求，判断图类型。
2. 提取节点、连接关系、分组和布局偏好。
3. 写入 `output/diagram.json`，字段必须符合统一 JSON 结构。
4. 运行 `scripts/run_draw.ps1`。
5. 保存为 `diagram.output` 指定的 `.vsdx` 文件，默认是 `output/result.vsdx`。
6. 如果是继续优化同一张图，应继续使用同一个 `diagram.output`，不要临时换新文件名。
7. 如果失败，明确说明错误原因和下一步排查建议。

## 模板模式流程

优先级：

1. 如果存在 `input/template.vsdx`，走 Visio 模板占位符填充模式。
2. 否则如果存在 `input/template.png`、`input/template.jpg` 或 `input/template.jpeg`，先分析图片模板，再走背景参考 + 可编辑形状覆盖模式。
3. 如果没有模板文件，明确提示用户放入模板，不要从别处下载未知模板。

Visio 模板文件模式：

- 打开 `input/template.vsdx`。
- 另存为 `output/filled_template.vsdx`。
- 遍历页面所有 Shape，包括分组内部 Shape。
- 查找 `Shape.Text` 中的占位符，例如 `{{标题}}`、`{{模块1}}`、`{{模块2}}`、`{{说明}}`、`{{步骤1}}`。
- 使用 `output/diagram.json` 的 `slots`，或从 `input/content.md` 解析出的内容替换占位符。
- 保留原位置、大小、颜色、线条、字体和对齐。
- 如果文字太长，自动换行、适当缩小字号，必要时轻微扩大文本框或微调位置。
- 每填充一个区域后短暂停顿，让用户看到过程。

图片模板模式：

- 使用 `analyze_image_template.py` 读取图片尺寸，并尝试识别矩形框、线条、轮廓、标题区和文本区。
- 输出 `output/template_detected.json`。
- 如果识别失败，不报废流程，退化为背景参考模式。
- 使用 `draw_from_image_template.py` 将图片插入 Visio 页面作为背景参考，并锁定或尽量避免误编辑。
- 在背景图上覆盖可编辑的 Visio 文本框、矩形和箭头。
- 第一版允许近似复刻，但要尽量保持布局比例、模块位置、层级关系和视觉风格。

参考图版式复刻模式：

- 先读取参考图，生成或更新 `output/template_trace.draft.json`，再形成正式 `output/template_trace.json`。
- `template_trace.json` 必须使用归一化坐标记录页面比例、大分组框、小模块、图标区、文本区、连接线路由、图例、颜色风格、层级顺序和通道。
- 对复杂论文模型图、深度学习网络结构图、算法结构图，优先使用 reference-locked editable reconstruction mode。
- reference-locked 模式使用 `template_trace.json` 的归一化坐标锁定区域、模块、箭头路径和样式，不允许普通自动布局覆盖 trace。
- 如果自动生成的 trace 不准，应输出 `template_trace.draft.json` 并建议人工校正；后续渲染以人工校正后的 `template_trace.json` 为准。
- 优先保留参考图的三栏结构、虚线分组、模块数量、相对位置、颜色体系、图例和反馈线。
- 对科研分层架构图，默认使用内置 `scientific_layered_architecture` 版式。
- 模块应使用圆角矩形，分组框使用浅色虚线框，连接线尽量使用水平/垂直折线。
- 节点左侧应尽量加入统一风格的简洁图标。
- 绘图后生成 `output/template_fidelity_report.md`，报告页面比例、分组数量、图标、图例、线型等是否接近参考图。
- reference-locked 渲染后生成 `output/reference_fidelity_report.md`，报告区域位置、模块密度、虚线框、背景色块、箭头路径、小元素和人工校正建议。
- 如果报告出现明显失败项，应继续调整一次布局，而不是直接结束。
- 必须检测并记录以下失败类型：`group_layout_failure`、`layer_hierarchy_failure`、`dense_region_collision`、`connector_routing_failure`、`semantic_legend_failure`、`reference_density_mismatch`、`icon_text_collision`、`false_completion`。
- 如果检查仍失败，应生成 `output/trace_repair_suggestions.md`，提示优先修 `groups[].bbox`、`nodes[].bbox`、`nodes[].icon_bbox`、`nodes[].text_bbox`、`connectors[].route_points`、`connectors[].channel` 和 `legend.bbox`。

reference-locked 推荐工作流：

1. 把参考图放入 `input/template.png`，或在运行脚本时指定参考图路径。
2. 建立 `output/template_trace.draft.json`，识别或手动定义页面比例、大分组框、小模块、图标区、文本区、连接线路由、图例、颜色风格、层级顺序和通道。
3. 检查并人工校正 draft trace，另存为 `output/template_trace.json`。
4. 根据 trace 渲染可编辑 Visio 图，导出 PNG。
5. 运行 `reference_fidelity_check` 和 `collision_detector`。
6. 如果失败，执行自动修复或生成 `trace_repair_suggestions.md`。
7. 再次导出和检查。
8. 如果仍然失败，必须报告“当前复刻未通过”，并建议人工校正 `template_trace.json`。

`diagram.json` 可以使用以下配置启用 reference-locked：

```json
{
  "reference_locked": {
    "enabled": true,
    "reference_image": "input/template.png",
    "trace_file": "output/template_trace.json",
    "use_background_alignment": true,
    "hide_background_on_export": true,
    "preserve_relative_position": true,
    "preserve_scale": true,
    "allow_free_layout": false
  }
}
```

新版 `template_trace.json` 应支持以下字段：

```json
{
  "groups": [
    {
      "id": "perception_layer",
      "title": "感知输入层",
      "bbox": [0.01, 0.05, 0.16, 0.92],
      "style": "blue_dashed_group",
      "z_order": 10,
      "padding": 0.02
    }
  ],
  "nodes": [
    {
      "id": "lidar_node",
      "group": "perception_layer",
      "bbox": [0.03, 0.12, 0.14, 0.22],
      "icon_bbox": [0.035, 0.14, 0.055, 0.18],
      "text_bbox": [0.060, 0.13, 0.135, 0.20],
      "title": "激光雷达",
      "body": "环境轮廓信息\n障碍物距离",
      "style": "blue_card",
      "z_order": 30
    }
  ],
  "connectors": [
    {
      "id": "lidar_to_map",
      "from": "lidar_node",
      "to": "map_node",
      "semantic": "data_flow",
      "style": "blue_solid_arrow",
      "route_points": [[0.14, 0.17], [0.20, 0.17], [0.22, 0.17]],
      "channel": "left_to_middle",
      "z_order": 25,
      "label": "环境轮廓信息",
      "label_bbox": [0.16, 0.14, 0.21, 0.16]
    }
  ],
  "legend": {
    "bbox": [0.02, 0.88, 0.20, 0.97],
    "items": [
      {"label": "数据流", "style": "blue_solid_arrow"},
      {"label": "控制流", "style": "green_solid_arrow"},
      {"label": "火焰执行反馈", "style": "orange_dashed_arrow"}
    ],
    "z_order": 50
  }
}
```

Benchmark / 回归测试：

- 对反复打磨的参考图个例，应建立 `benchmarks/<case_name>/` 目录。
- benchmark 至少包含参考说明、目标内容 JSON、模板追踪 JSON、验收标准和 fidelity 报告。
- 每次优化 skill 后，应用同一 benchmark 重新生成输出，检查是否出现版式退化。
- 如果用户说“把这个个例作为 benchmark 继续逼近参考图”，必须把问题沉淀到脚本能力和验收报告中，而不是只做一次性手工移动。

## 通用质量规则

当用户指出问题时，按以下方式处理：

- “整体偏左上”：触发 `canvas_fit_rule`、`center_alignment_rule` 和 `polish_pass_rule`。
- “图标遮挡文字”：触发 `safe_zone_rule`，节点应改为左图标右文字安全区。
- “箭头太丑 / 折线不好看 / 线太乱 / 箭头不直 / 小折角”：触发 `connector_quality_rule`、`connector_beauty_rule`、`connector_route_simplify_rule`、`connector_anchor_rule`、`connector_straightness_rule` 和 `no_micro_dogleg_rule`，优先直线或共线正交路由，减少无意义拐点，禁止节点边缘附近的小折角和箭头前短折段，并选择更自然的节点边缘锚点。
- “字体太小 / 字不清楚 / 标题说明层级弱”：触发 `typography_readability_rule`、`text_hierarchy_rule` 和 `safe_resize_rule`，优先放大默认字号、优化换行、保留中文字体和文本留白，必要时轻微增高节点。
- “有条线不知道干嘛”：触发 `semantic_element_rule`，无语义线或虚线默认不生成。
- “不像参考图”：触发 `template_fidelity_rule`，检查版式、比例、分组、颜色、线型和视觉语言。
- “文字太挤”：触发 `readability_rule`，调整换行、字号和节点尺寸。
- 如果用户明确说当前布局、整体位置或缩放已经不错，应设置 `preserve_layout_position`、`preserve_global_scale` 和 `preserve_page_balance` 的处理思路：不大幅重排节点，只局部修复连接线、字体、文本区和安全尺寸。

相关脚本：

- `drawdsl.py`：把 `diagram.json` 转换为 DrawDSL 中间层，记录页面、节点 bbox、安全区、连接线通道、图例和 z-order。
- `visio_backend.py`：封装 Visio COM 原子操作，包括新增形状、连线、图片导入、保存和导出。
- `preview_review.py`：读取导出 PNG 做预览自检，检查空白图、尺寸异常、DrawDSL 节点数和 collision 报告。
- `lesson_store.py`：把失败预览写入 `output/lessons/failed_cases.jsonl` 和 `lessons/reference_reproduction_lessons.md`。
- `visual_rules.py`：通用视觉规则定义。
- `connector_router.py`：连接线语义、锚点和路由简化规则。
- `visual_quality_check.py`：通用质量检查，输出 `output/quality_report.md`，包括拐点数量、短折线、锚点自然度、字体可读性和文本层级检查。
- `reference_reproduction_guard.py`：判断并强制参考图复刻模式，禁止自由布局替代复刻。
- `reference_fidelity_check.py`：检查区域、密度、层级、图例、连线和碰撞，失败时禁止声称复刻成功。
- `collision_detector.py`：检测节点重叠、图标文字碰撞、文字裁切风险、连接线穿过节点或图例。
- `connector_channel_router.py`：定义 `left_to_middle`、`middle_internal`、`middle_to_right`、`right_internal`、`bottom_feedback`、`vertical_feedback`、`legend_line` 等通道。
- `layer_manager.py`：统一管理背景、分组、连接线、节点、图标、文字、标签和图例的 z-order。
- `trace_repair_advisor.py`：根据失败报告给出需要修改的 trace 字段建议。
- `legend_renderer.py`：稳定绘制数据流、控制流、反馈流、灭火执行反馈等图例。
- `group_renderer.py`：稳定绘制大分组虚线框、浅色背景、标题和内边距。
- `auto_repair.py`：根据质量检查自动修复 `diagram.json`，输出 `output/repair_log.md`，包括 `line_simplification_pass`、`font_enlargement_pass` 和 `node_text_refit_pass`。
- `benchmark_runner.py`：扫描和验证 benchmark 目录。
- `feedback_to_rules.py`：把用户反馈映射为通用规则。

## 科研绘图风格原则

生成论文级、科研汇报级系统图时，优先采用以下原则：

1. 主要流程方向稳定，通常从左到右或从上到下，不让读者来回寻找箭头。
2. 可共线连接的节点必须优先使用单段水平或垂直直线；轻微错位但不需要避障时，可使用单段 `direct_straight` 直连，避免硬折线。
3. 折线最多保留必要拐点，禁止节点边缘附近的小横段、小竖段和箭头前短折段。
4. 线宽、箭头、颜色和虚实线含义保持一致，数据流、控制流、反馈流不得混用风格。
5. 中文字体优先 `Microsoft YaHei`，标题和说明都要达到缩放截图后仍可读的程度。
6. 标题明显大于说明文字，但说明文字不能过小；节点内部留白要足够，避免贴边。
7. 如果布局已经均衡，不为了局部美化大幅重排整张图，优先只修线路由、锚点、字号、换行和安全尺寸。

## 自然语言转 JSON 规则

图类型判断：

- 流程顺序明显：`flowchart`
- 模块之间调用、依赖、包含：`module_diagram`
- 系统组件和数据流：`architecture`
- 数据表、字段、实体关系：`er_diagram`
- 设备、服务器、交换机、网络连接：`network_topology`
- 论文研究路线、实验步骤、技术路径：`technical_route`

节点提取：

- 每个主要对象生成一个 `node`。
- 节点文字保留中文。
- 长文本允许自动换行。
- 不要把一个概念拆得过碎，除非用户明确要求细化。

边提取：

- “传输”“控制”“调用”“反馈”“依赖”“包含”“输出”等关系转成 `edges`。
- 边有含义时写入 `text`。
- 没有明确含义时 `text` 可以为空字符串。

布局选择：

- `flowchart` 默认 `top_down`。
- `architecture` 默认 `left_right`。
- `er_diagram` 默认 `left_right` 或 `grid`。
- `module_diagram` 默认 `top_down`。
- `network_topology` 默认 `radial`。
- `technical_route` 默认 `top_down`。
- 如果用户说“像论文图一样”，默认清爽、对齐、留白充足。

## JSON 结构

```json
{
  "title": "图标题",
  "type": "architecture",
  "layout": "left_right",
  "output": "output/result.vsdx",
  "page": {
    "width": 13.0,
    "height": 9.0
  },
  "animation": {
    "enabled": true,
    "delay_seconds": 0.4
  },
  "nodes": [
    {
      "id": "node_id",
      "text": "节点文字",
      "shape": "box",
      "x": 1.5,
      "y": 7.0,
      "width": 2.2,
      "height": 0.8,
      "style": "default"
    }
  ],
  "edges": [
    {
      "from": "node_a",
      "to": "node_b",
      "text": "连接说明",
      "style": "arrow"
    }
  ],
  "groups": [
    {
      "id": "group_id",
      "text": "分组标题",
      "node_ids": ["a", "b", "c"],
      "style": "container"
    }
  ]
}
```

## 可用脚本

- `scripts/schema.py`：校验统一图结构。
- `scripts/layout.py`：补齐缺失坐标，支持 `top_down`、`left_right`、`grid`、`radial`。
- `scripts/draw_visio.py`：通过 COM 打开可见 Visio 并逐步绘图。
- `scripts/test_visio_com.py`：最小 Visio COM 测试。
- `scripts/fill_visio_template.py`：填充 `.vsdx` 模板中的占位符。
- `scripts/analyze_image_template.py`：分析 PNG/JPG/JPEG 图片模板并输出 `template_detected.json`。
- `scripts/draw_from_image_template.py`：把图片作为背景参考层并覆盖可编辑 Visio 形状。
- `scripts/template_layout_trace.py`：生成参考图版式追踪文件 `template_trace.json`。
- `scripts/reference_locked_renderer.py`：按 `template_trace.json` 的归一化坐标执行 reference-locked 可编辑复刻，输出 `reference_fidelity_report.md`。
- `scripts/template_style_extractor.py`：生成参考图颜色、线型和字体层级线索。
- `scripts/icon_library.py`：使用 Visio 基础形状绘制统一风格简洁图标。
- `scripts/shape_library.py`：复杂论文模型图常见元素类型定义。
- `scripts/quality_check.py`：生成模板复刻质量报告。

## 失败处理

如果绘图失败，先确认：

1. 是否已运行 `scripts/setup_env.ps1`。
2. 是否安装 Microsoft Visio 桌面版。
3. 是否只有 Visio 网页版，网页版不能用 COM 控制。
4. `output/diagram.json` 是否存在且 JSON 合法。
5. `edges.from` 和 `edges.to` 是否都能对应到现有节点。
6. 保存路径是否在项目 `output` 目录中。
7. 模板模式下，确认 `.vsdx` 模板不是空文件，且占位符存在于可编辑 Shape.Text 中。
8. 图片模板识别不准时，使用背景参考模式继续生成可编辑图形，并说明这是近似结果。
