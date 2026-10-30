# Visio Auto Drawer

通过自然语言、结构化 JSON 或参考图，在 **Microsoft Visio 桌面版** 中生成可编辑图纸的本地 AI skill 和 Python COM 工具集。

支持流程图、系统架构图、ER 图、模块图、网络拓扑、技术路线，以及 Visio 模板填充和参考图版式复刻。绘图采用基础 COM 形状，不依赖特定 stencil。

## 运行条件

- Windows，已安装并激活 Microsoft Visio 桌面版；仅网页版不可用。
- Python 3.10 或更新版本，建议 3.11/3.12。
- 核心依赖：pywin32、Pydantic 2、Pillow。
- 可选图片轮廓分析：OpenCV、NumPy。

本项目不包含 Visio，也不提供 Visio 许可证。JSON 校验与部分分析可独立运行；实际绘图需要 Windows COM。

## 快速开始

在 PowerShell 中执行：

```powershell
git clone https://github.com/liyuhang966-crypto/visio-auto-drawer.git
cd visio-auto-drawer
.\scripts\setup_env.ps1
.\scripts\run_test.ps1
New-Item -ItemType Directory -Force output | Out-Null
Copy-Item examples/flowchart.json output/diagram.json
.\scripts\run_draw.ps1
```

Visio 将显示逐步绘制过程，结果保存在 `output/result.vsdx`。重复绘制默认复用目标文件；需要保留原稿时先改 `diagram.output`。

启动脚本优先使用仓库内 `.venv`，未创建时使用 PATH 中的 Python。也可直接运行：

```powershell
python -m pip install -r requirements.txt
python scripts/draw_visio.py --project-root . --diagram examples/flowchart.json
```

若组织策略禁止执行 PowerShell 脚本，请使用上述 Python 命令；不需要修改系统执行策略。

## 作为 skill 使用

把仓库内容放到你使用的 agent 的技能目录下，目录名为 `visio-auto-drawer`；入口是根目录 `SKILL.md`，可选界面信息位于 `agents/openai.yaml`。调用示例：

> 使用 visio-auto-drawer，绘制一个包含输入、处理、存储和输出的系统架构图，输出可编辑 Visio 文件。

运行时工作目录是存放 `input/` 与 `output/` 的项目目录。脚本支持 `--project-root` 指定项目；不依赖某台机器的用户目录或技能安装层级。

自然语言理解、图像阅读和布局标定由调用本 skill 的 agent 完成，脚本本身不是自动图像识别模型，也不调用远程 AI API。

## 最小 JSON

```json
{
  "title": "处理流程",
  "type": "flowchart",
  "layout": "left_right",
  "output": "output/result.vsdx",
  "nodes": [
    {"id": "input", "text": "输入", "shape": "box"},
    {"id": "process", "text": "处理", "shape": "box"},
    {"id": "output", "text": "输出", "shape": "box"}
  ],
  "edges": [
    {"from": "input", "to": "process"},
    {"from": "process", "to": "output"}
  ]
}
```

完整字段见 `scripts/schema.py`，通用示例见 `examples/`。

## 参考图与模板

1. 将有权使用的参考图放入 `input/template.png`。
2. 由 agent 生成 `output/diagram.json` 和 `output/template_trace.draft.json`，检查标定后保存正式的 `output/template_trace.json`。
3. 在 diagram 中开启 `reference_locked.enabled`，再运行 `scripts/run_draw.ps1`；脚本会转到 reference-locked 渲染流程。
4. 检查导出的 PNG 与报告。参考图复刻需要人工视觉复核，结构检查通过不等于像素级一致。

当前 reference-locked 渲染器读取 trace 的 **`regions`、`elements`、`connectors`**。`bbox` 是 `[left, top, right, bottom]` 归一化坐标，`route_points` 使用同一坐标系；质量检查的 `diagram.nodes` 使用 Visio 页面坐标。二者应描述同一布局。`groups`、`nodes` 形式的扩展 trace 需先转换为渲染器字段，不能直接假定兼容。

```powershell
.\scripts\run_reference_locked.ps1 -Diagram output/diagram.json
```

只有草稿时，启动脚本会停止并要求补全正式 trace，不会把内置占位布局当成自动识别结果。

- `.vsdx` 占位符模板：`python scripts/fill_visio_template.py --project-root .`
- 可选图片轮廓分析：先安装 `requirements-image.txt`，再运行 `scripts/analyze_image_template.py`。该分析器的布局预设是辅助草稿，不能代替人工标定。
- `draw_from_image_template.py` 为早期的参考背景模式；复杂复刻优先使用 reference-locked 流程。

## 检查与当前限制

流水线：`intent → analysis → plan → DrawDSL → backend → preview → review → lesson`。

- `reference_reproduction_guard.py`：锁定参考布局意图。
- `collision_detector.py`：检查节点、文字和线路碰撞。
- `reference_fidelity_check.py`：检查结构、密度、层级与图例。
- `preview_review.py`：检查 PNG 非空、尺寸与碰撞状态。
- `auto_repair.py`：通用修复建议与处理。

这是一个持续演进的工具集。参考检查器目前偏向复杂三栏架构图，可能要求原图没有的三栏结构或图例；应核对适用性并记录原因，不能为了通过检查添加无意义内容。文字实际字形边界、局部图片精细程度和所有 Visio 主题差异仍需要视觉复核。小图片可作为局部素材嵌入，整张图片不能代替可编辑结构。

运行 `python -m unittest discover -s tests -v` 检查不依赖 Visio 的基础功能。GitHub Actions 运行这些检查，不宣称测试了云端 Visio COM。

## 隐私与贡献

发布包仅包含代码、技能说明和通用示例，不包含本地输入、输出图纸、裁剪素材、缓存或历史操作记录。运行报告可能含本机路径，默认写入 Git 忽略的 `output/`。分享前仍需检查内容。

提交问题或改进时请使用虚构示例，移除密钥、个人路径和私有图纸。详见 [发布与隐私说明](docs/PRIVACY.md)。

## 许可证

[MIT](LICENSE)。第三方依赖和 Microsoft Visio 分别遵循其自身许可证；本许可证不授权使用他人的参考图片或模板。
