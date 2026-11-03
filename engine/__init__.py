"""Video and motion graphics rendering engine."""
from .renderer import (
    RenderedOutputs,
    VideoRenderer,
    create_golden_rule_card,
    create_introductory_dilemma_card,
    create_silicon_specs_card,
    create_vision_pro_hud_pill,
    create_voting_poll_card,
    render_composite_overlay_clip,
)
from .charts import (
    render_benchmark_chart,
    render_animated_benchmark_video,
    render_apple_liquid_glass_cta_frame,
    render_animated_cta_video,
    generate_glass_whoosh_sfx,
)

__all__ = [
    "VideoRenderer",
    "RenderedOutputs",
    "create_introductory_dilemma_card",
    "create_silicon_specs_card",
    "create_golden_rule_card",
    "create_voting_poll_card",
    "create_vision_pro_hud_pill",
    "render_composite_overlay_clip",
    "render_benchmark_chart",
    "render_animated_benchmark_video",
    "render_apple_liquid_glass_cta_frame",
    "render_animated_cta_video",
    "generate_glass_whoosh_sfx",
]
