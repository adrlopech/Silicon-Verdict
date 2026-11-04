from typing import List, Optional
from pydantic import BaseModel, Field


class ChartData(BaseModel):
    """Specification for technical benchmark bar charts."""
    title: str = Field(..., description="Chart title (e.g. 'GAMING PERFORMANCE', '1080p Ultra 1% Lows')")
    metric_unit: str = Field(..., description="Unit of measurement (e.g. 'FPS', 'Watts', 'GB/s', 'ms', '°C')")
    labels: List[str] = Field(..., description="List of hardware models or configurations compared")
    values: List[float] = Field(..., description="Corresponding benchmark numerical values")
    subtitle: Optional[str] = Field(default=None, description="Optional subtitle or comparison description (e.g. '8GB vs 16GB VRAM')")
    preset_pill: Optional[str] = Field(default=None, description="Optional preset badge text (e.g. '1080p ULTRA • CYBERPUNK 2077')")
    winner_badge: Optional[str] = Field(default=None, description="Optional custom badge for the winning hardware (e.g. '+38% FASTER')")


class Scene(BaseModel):
    """Represents a modular technical chapter/scene within the Silicon Verdict video."""
    scene_id: int = Field(..., description="Sequential chapter index starting from 1")
    timestamp_start: str = Field(..., description="Estimated chapter start timestamp formatted as 'MM:SS'")
    chapter_title: str = Field(..., description="Concise chapter name for YouTube timestamp index")
    voiceover_text: str = Field(
        ...,
        description="High-density, objective technical voiceover in fluent native English. No filler greetings."
    )
    visual_search_terms: List[str] = Field(
        ...,
        description="English keywords tailored for stock footage (e.g. ['semiconductor wafer closeup', 'gpu die heatpipe'])"
    )
    on_screen_text: str = Field(
        ...,
        description="Punchy 3-6 word text callout highlighting critical architectural specs or verdict"
    )
    is_short_highlight: bool = Field(
        default=False,
        description="True if this segment represents an autonomous high-impact hook for a 9:16 vertical Short"
    )
    chart_data: Optional[ChartData] = Field(
        default=None,
        description="Quantitative benchmark comparison data for this scene, rendered via technical matplotlib charts"
    )


class ShortMetadata(BaseModel):
    """Metadata specifically optimized for autonomous 9:16 vertical YouTube Shorts."""
    title: str = Field(
        ...,
        max_length=60,
        description="Direct, high-curiosity English title ending with #Shorts (under 60 chars)"
    )
    description: str = Field(
        ...,
        description="SEO-rich English Short description with relevant technical hashtags"
    )
    hook_text: str = Field(
        ...,
        description="High-contrast overlay text displayed during the first 2 seconds of the Short"
    )


class VideoProject(BaseModel):
    """Complete production manifest for a Silicon Verdict documentary-style video."""
    title: str = Field(
        ...,
        max_length=70,
        description="High-CTR, authoritative title in Silicon Verdict style (under 70 chars)"
    )
    description: str = Field(
        ...,
        description="Full YouTube video description with chapter timestamps, technical methodology, and hashtags"
    )
    tags: List[str] = Field(
        ...,
        min_length=12,
        max_length=25,
        description="15-20 technical SEO tags in English"
    )
    pinned_comment: str = Field(
        ...,
        description="Provocative, community-engaging technical debate question for the pinned comment"
    )
    thumbnail_prompt: str = Field(
        ...,
        description="Cinematic image generation prompt (Midjourney/Flux) with Obsidian Black & Neon Cyan tech aesthetics"
    )
    scenes: List[Scene] = Field(
        ...,
        description="Ordered sequence of 8-12 modular scenes comprising the complete technical narrative"
    )
    shorts: List[ShortMetadata] = Field(
        ...,
        description="List of 2-3 tailored metadata objects matching the scenes marked with is_short_highlight=True"
    )


class MarketTopic(BaseModel):
    """Autonomous high-CTR topic in the PC Hardware & Semiconductor niche."""
    topic: str = Field(..., description="Main video topic focused on PC hardware, purchase dilemmas or architecture")
    hook_angle: str = Field(..., description="Psychological or market hook to maximize click-through rate and retention")
    target_audience: str = Field(..., description="Target demographic (e.g., '1440p PC Gamers', 'Hardware Enthusiasts')")
    suggested_benchmarks: List[str] = Field(
        ...,
        description="Key hardware comparisons and metric benchmarks to highlight (e.g. ['1% Lows at 1440p', 'FPS per Dollar', 'Package Power'])"
    )


# ==============================================================================
# TIKTOK CREATOR REWARDS & VERTICAL LONG VIDEO (61-68s, 5 ACTS)
# ==============================================================================
class TikTokAct1(BaseModel):
    """Act 1 [00:00 - 00:05]: Technical Hook debunking a myth or exposing an anomaly."""
    voiceover: str = Field(..., description="High-energy hook (12-16 words, ~5s runtime)")
    dilemma_title: str = Field(..., description="Floating dilemma title (e.g. '128-BIT vs 256-BIT BUS')")
    dilemma_subtitle: str = Field(..., description="Core architectural dilemma question")
    category_pill: str = Field(default="HARDWARE SHOWDOWN", description="Category pill text")
    gameplay_query: str = Field(default="gaming pc benchmark 4k", description="Stock footage query")


class TikTokAct2(BaseModel):
    """Act 2 [00:05 - 00:20]: Silicon Mechanism low-level architectural deep-dive."""
    voiceover: str = Field(..., description="Low-level architecture breakdown (35-42 words, ~15s runtime)")
    specs_title: str = Field(default="ARCHITECTURAL TELEMETRY", description="Side card title")
    specs_bullets: List[str] = Field(
        default_factory=lambda: ["128-bit Bus @ 288 GB/s", "256-bit Bus @ 576 GB/s", "PCIe 4.0 x8 Overflow Penalty"],
        description="2-3 key technical specifications"
    )
    silicon_query: str = Field(default="semiconductor silicon wafer macro", description="Stock silicon query")


class TikTokAct3(BaseModel):
    """Act 3 [00:20 - 00:45]: Empirical Benchmark Telemetry (FPS, frametime, 1% Lows)."""
    voiceover: str = Field(..., description="Empirical comparison citing FPS and 1% Lows (55-65 words, ~25s runtime)")
    chart_title: str = Field(..., description="Chart title (e.g. '1440p ULTRA TELEMETRY')")
    chart_subtitle: str = Field(default="Direct Hardware Telemetry", description="Chart subtitle")
    preset_pill: str = Field(..., description="Preset badge (e.g. '1440p ULTRA • CYBERPUNK 2077')")
    metric_unit: str = Field(default="FPS")
    winner_label: str = Field(..., description="Winning configuration label")
    winner_avg_fps: float = Field(..., description="Winning average FPS")
    winner_low_fps: float = Field(..., description="Winning 1% Low FPS")
    winner_frametime_ms: float = Field(..., description="Winning frametime in ms")
    loser_label: str = Field(..., description="Runner-up configuration label")
    loser_avg_fps: float = Field(..., description="Runner-up average FPS")
    loser_low_fps: float = Field(..., description="Runner-up 1% Low FPS")
    loser_frametime_ms: float = Field(..., description="Runner-up frametime in ms")
    winner_badge: str = Field(default="+38% FASTER", description="Visual badge on winning bar")


class TikTokAct4(BaseModel):
    """Act 4 [00:45 - 00:58]: The Golden Rule practical purchasing takeaway."""
    voiceover: str = Field(..., description="Definitive user purchasing conclusion (30-35 words, ~13s runtime)")
    golden_rule_title: str = Field(default="THE GOLDEN RULE", description="Card header")
    golden_rule_takeaway: str = Field(..., description="Practical buying mandate (e.g. 'NEVER BUY 8GB VRAM FOR 1440p')")
    gameplay_query: str = Field(default="gaming pc graphics gameplay", description="Stock gameplay query")


class TikTokAct5(BaseModel):
    """Act 5 [00:58 - 00:65]: Retention closing debate question for comments (A vs B)."""
    voiceover: str = Field(..., description="Polarizing community question (15-20 words, ~7s runtime)")
    poll_question: str = Field(..., description="Provocative debate prompt")
    poll_option_a: str = Field(..., description="Option A (e.g. 'Option A: 16GB VRAM (Stable 1% Lows)')")
    poll_option_b: str = Field(..., description="Option B (e.g. 'Option B: Faster GPU / 8GB VRAM')")


class TikTokLongProject(BaseModel):
    """Complete 61-68s specification for TikTok Creator Rewards Program."""
    topic: str
    title: str = Field(..., max_length=150, description="High-CTR TikTok title with hashtags")
    description: str = Field(..., description="TikTok description")
    tags: List[str] = Field(..., description="Technical and viral hashtags")
    act1: TikTokAct1
    act2: TikTokAct2
    act3: TikTokAct3
    act4: TikTokAct4
    act5: TikTokAct5
    gemini_input_tokens: int = Field(default=0)
    gemini_output_tokens: int = Field(default=0)
    entities: List[str] = Field(default_factory=list)

    def get_full_script_text(self) -> str:
        """Returns the concatenated narration text of all 5 acts."""
        return " ".join([
            self.act1.voiceover,
            self.act2.voiceover,
            self.act3.voiceover,
            self.act4.voiceover,
            self.act5.voiceover,
        ])

    def get_total_words(self) -> int:
        """Computes aggregate narration word count across all 5 acts."""
        return len(self.get_full_script_text().split())

    def get_entities(self) -> List[str]:
        """Returns semantic hardware entities extracted or inferred from topic and tags."""
        if self.entities:
            return self.entities
        extracted = []
        for t in [self.topic] + self.tags:
            for w in t.lower().replace("#", "").replace("_", " ").replace("-", " ").split():
                if len(w) > 2 and w not in ["the", "and", "for", "with", "por", "que", "con", "los", "las"]:
                    extracted.append(w)
        return list(dict.fromkeys(extracted))[:8]


class MotionVisualTrigger(BaseModel):
    """Word-synchronized procedural visual trigger for Remotion."""
    asset_id: str = Field(..., description="ID of the procedural vector: silicon_die, latency_bars, frametime_gauge, preset_card, vcsel_projector, rf_collision, subsea_cable, gps_relativity, nfc_token, spectrum_bands")
    label: str = Field(..., description="Short uppercase telemetry badge text, e.g. 'ISM BAND 2.45 GHz CONFLICT'")
    word_anchor: str = Field(..., description="Key word or phrase in script where this graphic triggers")
    duration_seconds: float = Field(default=12.0, description="On-screen duration in seconds")
    motion_preset: str = Field(default="hero", description="hero, metric, or diagram")
    game_title: Optional[str] = Field(default=None, description="For asset_id 'game_frame': exact game name whose real screenshot is shown, e.g. 'DOOM' or 'Skyrim'")
    annotation: Optional[str] = Field(default=None, description="For 'game_frame': 2-6 word uppercase callout about the technical detail, e.g. 'ONE FRAME = 4,000 DRAW CALLS'")
    image_src: Optional[str] = Field(default=None, description="Set by the pipeline, never by the model")


class MotionStoryProject(BaseModel):
    """Complete unified project specification for Remotion Kinetic Motion Graphics (1080x1920 @ 60 FPS)."""
    topic: str
    category_id: int = Field(default=3, description="1: Hardware Deep Dive, 2: Gaming & Optimization, 3: Tech Curiosities")
    category_name: str = Field(..., description="Display category name: HARDWARE DEEP DIVE, GAMING OPTIMIZATION, TECH CURIOSITIES")
    header_banner: str = Field(..., description="Uppercase high-impact hook header, e.g. 'WHY MICROWAVES DESTROY 2.4 GHz WI-FI'")
    title: str = Field(..., max_length=150, description="High CTR YouTube / TikTok title with hashtags")
    description: str = Field(..., description="Video description with technical context")
    tags: List[str] = Field(..., description="Technical and algorithmic tags")
    pinned_comment: str = Field(..., description="High-engagement debate question for comments")
    full_script: str = Field(..., description="High-octane 140-160 word narration script in 100% US English with dramatic pacing")
    visual_triggers: List[MotionVisualTrigger] = Field(..., description="Synchronized vector graphic trigger points")
    gemini_input_tokens: int = Field(default=0)
    gemini_output_tokens: int = Field(default=0)

    def get_total_words(self) -> int:
        return len(self.full_script.split())



class StoryScene(BaseModel):
    """One visual beat of a mascot-led story video, triggered by a word in the script."""
    word_anchor: str = Field(..., description="Exact word from full_script where this beat starts")
    pose: str = Field(default="idle", description="Mascot pose: idle, surprised, point, shrug, think, wave, cheer")
    vector_type: str = Field(default="none", description="none, counter, bars, gauge, trio, flow, icon, big_text")
    icon: Optional[str] = Field(default=None, description="Icon name (bulb, mirror, clock, building, phone, wifi, chip, battery, cable, eye, smile, lock, bolt, cloud, magnifier, gear, heart, arrow, question, star, box, plane, wave, thermometer)")
    icon2: Optional[str] = Field(default=None, description="Second icon (flow target or trio item 2)")
    icon3: Optional[str] = Field(default=None, description="Third icon (trio item 3)")
    label: Optional[str] = Field(default=None, description="Short caption, max 3 words")
    label2: Optional[str] = Field(default=None, description="Second caption (bars row 2 or trio item 2)")
    label3: Optional[str] = Field(default=None, description="Third caption (trio item 3)")
    value_from: Optional[float] = Field(default=None, description="counter start value")
    value_to: Optional[float] = Field(default=None, description="counter end value; must appear in the script")
    a: Optional[float] = Field(default=None, description="0..1 fill of bars row 1, or gauge position")
    b: Optional[float] = Field(default=None, description="0..1 fill of bars row 2")
    text: Optional[str] = Field(default=None, description="big_text content, max 6 words")
    flash: bool = Field(default=False, description="Full-screen accent punch; use for the single key reveal only")


class StoryProject(BaseModel):
    """Mascot-led explainer: hook, narrated story, and a sequence of scenes."""
    topic: str
    category_name: str = Field(default="EVERYDAY CURIOSITIES")
    header_banner: str = Field(..., description="3-5 word uppercase hook shown for the first 3 seconds")
    title: str = Field(..., max_length=150)
    description: str
    tags: List[str]
    pinned_comment: str
    full_script: str = Field(..., description="150-175 words of natural spoken US English")
    scenes: List[StoryScene]
    visual_triggers: List[MotionVisualTrigger] = Field(default_factory=list)
    category_id: int = 3
    is_fallback: bool = Field(default=False, description="Set by the pipeline when the deterministic story was used")
    gemini_input_tokens: int = Field(default=0)
    gemini_output_tokens: int = Field(default=0)

    def get_total_words(self) -> int:
        return len(self.full_script.split())
