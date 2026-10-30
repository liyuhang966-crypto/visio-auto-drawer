from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


DiagramType = Literal[
    "flowchart",
    "architecture",
    "er_diagram",
    "module_diagram",
    "network_topology",
    "technical_route",
    "template_fill",
]

LayoutType = Literal[
    "top_down",
    "left_right",
    "grid",
    "radial",
    "radial_balanced",
    "hub_spoke",
    "paper_architecture",
    "symmetric_left_right",
]

ShapeType = Literal[
    "box",
    "rounded_box",
    "process",
    "decision",
    "terminator",
    "database",
    "actor",
    "cloud",
    "block3d",
    "image",
]


DEFAULT_LAYOUT_BY_TYPE: dict[str, LayoutType] = {
    "flowchart": "top_down",
    "architecture": "paper_architecture",
    "er_diagram": "left_right",
    "module_diagram": "symmetric_left_right",
    "network_topology": "radial",
    "technical_route": "top_down",
    "template_fill": "grid",
}


class Page(BaseModel):
    width: float = Field(default=13.0, gt=0)
    height: float = Field(default=9.0, gt=0)
    margin: float = Field(default=0.5, ge=0)


class Animation(BaseModel):
    enabled: bool = True
    delay_seconds: float = Field(default=0.4, ge=0, le=10)


class Node(BaseModel):
    id: str = Field(min_length=1)
    text: str = ""
    shape: ShapeType = "box"
    icon: str | None = None
    image: str | None = None
    x: float | None = None
    y: float | None = None
    width: float = Field(default=2.2, gt=0)
    height: float = Field(default=0.8, gt=0)
    style: str = "default"


class Edge(BaseModel):
    from_: str = Field(alias="from", min_length=1)
    to: str = Field(min_length=1)
    text: str = ""
    style: str = "arrow"
    route: str | None = None
    line_type: Literal["data", "control", "feedback", "fire_feedback", "status_feedback", "aux"] = "data"
    semantic: Literal["data_flow", "control_flow", "feedback", "status_feedback", "auxiliary"] | None = None
    route_y: float | None = None
    label_x: float | None = None
    label_y: float | None = None
    route_points: list[list[float]] | None = None

    class Config:
        populate_by_name = True


class Group(BaseModel):
    id: str = Field(min_length=1)
    text: str = ""
    node_ids: list[str] = Field(default_factory=list)
    style: str = "container"


class TemplateConfig(BaseModel):
    mode: Literal["visio_template", "image_template", "background_reference"] = "visio_template"
    source: str = "input/template.vsdx"
    preserve_style: bool = True
    fill_strategy: str = "placeholder"


class ContentSection(BaseModel):
    id: str = Field(min_length=1)
    title: str = ""
    body: str = ""


class TemplateContent(BaseModel):
    title: str = ""
    summary: str = ""
    sections: list[ContentSection] = Field(default_factory=list)


class Slot(BaseModel):
    id: str = Field(min_length=1)
    placeholder: str = Field(min_length=1)
    text: str = ""
    fit_text: bool = True


class Optimization(BaseModel):
    enabled: bool = True
    passes: int = Field(default=2, ge=0, le=8)
    expand_spacing: bool = True
    recenter_page: bool = True
    label_reposition: bool = True
    group_alignment: bool = True
    auto_wrap: bool = True
    auto_font_size: bool = True
    avoid_overlap: bool = True
    preserve_alignment: bool = True
    preserve_template_style: bool = True


class ExportOptions(BaseModel):
    png: bool = False
    pdf: bool = False
    transparent_background: bool = False


class TemplateFidelity(BaseModel):
    enabled: bool = False
    mode: Literal["reference_trace", "builtin_preset"] = "reference_trace"
    reference_image: str = "input/template.png"
    trace_file: str = "output/template_trace.json"
    preset: str = "scientific_layered_architecture"
    preserve_layout: bool = True
    preserve_style: bool = True
    use_normalized_coordinates: bool = True
    layout_similarity_target: float = Field(default=0.75, ge=0, le=1)
    allow_content_adaptation: bool = True
    avoid_free_layout: bool = True
    auto_fit_page: bool = True
    page_margin: float = Field(default=0.55, ge=0)
    recenter_after_draw: bool = True
    scale_to_balance: bool = True
    icon_safe_zone: bool = True
    text_safe_zone: bool = True
    min_icon_text_gap: float = Field(default=0.12, ge=0)
    icon_max_size_ratio: float = Field(default=0.42, gt=0, le=1)


class ReferenceLocked(BaseModel):
    enabled: bool = False
    reference_image: str = "input/template.png"
    trace_file: str = "output/template_trace.json"
    use_background_alignment: bool = False
    hide_background_on_export: bool = True
    preserve_relative_position: bool = True
    preserve_scale: bool = True
    allow_free_layout: bool = False


class Diagram(BaseModel):
    title: str = "Visio 自动绘图"
    type: DiagramType = "architecture"
    layout: LayoutType | None = None
    output: str = "output/result.vsdx"
    template: TemplateConfig | None = None
    content: TemplateContent | None = None
    slots: list[Slot] = Field(default_factory=list)
    optimization: Optimization = Field(default_factory=Optimization)
    export: ExportOptions = Field(default_factory=ExportOptions)
    template_fidelity: TemplateFidelity = Field(default_factory=TemplateFidelity)
    reference_locked: ReferenceLocked = Field(default_factory=ReferenceLocked)
    page: Page = Field(default_factory=Page)
    animation: Animation = Field(default_factory=Animation)
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    groups: list[Group] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_diagram(self) -> "Diagram":
        if self.layout is None:
            self.layout = DEFAULT_LAYOUT_BY_TYPE.get(self.type, "left_right")

        node_ids = [node.id for node in self.nodes]
        duplicates = sorted({node_id for node_id in node_ids if node_ids.count(node_id) > 1})
        if duplicates:
            raise ValueError(f"Duplicate node ids: {', '.join(duplicates)}")

        node_id_set = set(node_ids)
        for edge in self.edges:
            if edge.from_ not in node_id_set:
                raise ValueError(f"Edge source does not exist: {edge.from_}")
            if edge.to not in node_id_set:
                raise ValueError(f"Edge target does not exist: {edge.to}")

        for group in self.groups:
            missing = [node_id for node_id in group.node_ids if node_id not in node_id_set]
            if missing:
                raise ValueError(f"Group '{group.id}' references missing nodes: {', '.join(missing)}")

        return self
