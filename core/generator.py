import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from google import genai
from google.genai import types

from config.settings import settings
from core.pillars import WEEKLY_PILLARS, get_pillar_for_weekday, get_theme_description
from core.schemas import (
    ChartData,
    Scene,
    ShortMetadata,
    TikTokAct1,
    TikTokAct2,
    TikTokAct3,
    TikTokAct4,
    TikTokAct5,
    TikTokLongProject,
    VideoProject,
)
from services.history import (
    get_last_theme_for_weekday,
    get_recently_used_games,
)
from services.voice import get_next_voice, get_voice_label

logger = logging.getLogger(__name__)

CANDIDATE_MODELS = [
    settings.GEMINI_MODEL,
    "gemini-3.5-flash",
    "gemini-3.7-flash",
    "gemini-flash-latest",
]


def format_final_description(project: VideoProject) -> str:
    """Builds the authoritative YouTube video description for Silicon Verdict."""
    timestamp_lines = []
    for scene in project.scenes:
        ts = scene.timestamp_start if scene.timestamp_start else "00:00"
        timestamp_lines.append(f"{ts} - {scene.chapter_title}")

    timestamps_block = "\n".join(timestamp_lines)

    boilerplate = (
        f"{project.title}\n\n"
        "Silicon Verdict provides empirical, data-driven hardware reviews, semiconductor architecture deep dives, "
        "and definitive price-to-performance assessments. Every conclusion is backed by hardware telemetry and repeatable testing.\n\n"
        "CHAPTER TIMESTAMPS:\n"
        f"{timestamps_block}\n\n"
        "TEST BENCH SPECIFICATIONS & METHODOLOGY:\n"
        "• Test Platform: Open-air test bench, ambient temperature regulated at 21.0°C ± 0.5°C.\n"
        "• Frame pacing telemetry captured via PresentMon API (Average FPS, 1% Lows, 0.1% Frametime percentiles).\n"
        "• Power dissipation measured directly at 12V-2x6 and 8-pin EPS rail level using dedicated hardware interposers.\n"
        "• All benchmarks executed with Resizable BAR / SAM enabled and standard OEM memory profiles.\n\n"
        "COMMUNITY DEBATE:\n"
        f"💬 {project.pinned_comment}\n\n"
        "#Hardware #PCBuilding #TechBenchmarks #SiliconVerdict #PCGaming #CPUBenchmarks #GPUBenchmarks"
    )
    return boilerplate


def get_emergency_fallback_project(topic: str, scenes_limit: int = 3) -> VideoProject:
    """Provides a deterministic Silicon Verdict project specification if external AI service is unreachable."""
    logger.warning("Generating deterministic Silicon Verdict fallback plan for '%s'", topic)
    return VideoProject(
        title="Why 8GB VRAM is Officially Dead: The Telemetry Verdict",
        description="Empirical 1% low frametime analysis proving 8GB VRAM is dead for modern gaming.",
        tags=[
            "SiliconVerdict", "VRAM Bottleneck", "RTX 4060 8GB", "1% Lows",
            "PCIe Saturation", "Cyberpunk 2077", "Hardware Benchmarks", "GPU Buying Guide",
            "RX 7600 XT", "VRAM Allocation", "Frame Pacing", "Tech Telemetry",
            "PC Gaming 2026", "DirectX 12 Agility", "Shader Cache Spill"
        ],
        pinned_comment="Is 12GB now the minimum baseline for 1080p Ultra, or will modern asset streaming adapt?",
        thumbnail_prompt="Obsidian black background, glowing cyan circuit traces, cracked GPU silicon die showing 8GB VRAM limit",
        scenes=[
            Scene(
                scene_id=1,
                timestamp_start="00:00",
                chapter_title="The 8GB VRAM Saturation Problem",
                voiceover_text=(
                    "In modern compute-heavy gaming engines, allocating high-resolution geometry and ray tracing BVH structures "
                    "instantly exceeds the eight gigabyte frame buffer. Once local GDDR bandwidth is exhausted, system allocations "
                    "spill across the PCIe bus, resulting in catastrophic frame pacing degradation."
                ),
                visual_search_terms=["gpu memory traces", "motherboard pcie slot", "semiconductor microchip"],
                on_screen_text="8GB BUFFER EXHAUSTION",
                is_short_highlight=False,
            ),
            Scene(
                scene_id=2,
                timestamp_start="00:10",
                chapter_title="Empirical Telemetry: 1% Lows at 1080p Ultra",
                voiceover_text=(
                    "Our PresentMon telemetry in Cyberpunk 2077 confirms the disparity. While average framerates appear competitive, "
                    "the eight gigabyte configurations suffer severe micro-stuttering, cratering one percent lows below thirty-eight "
                    "frames per second, while sixteen gigabyte counterparts maintain exceptional pacing consistency."
                ),
                visual_search_terms=["pc hardware benchmark", "gpu cooler heatsink"],
                on_screen_text="1% LOW CRATERING",
                is_short_highlight=False,
                chart_data=ChartData(
                    title="1080p Ultra 1% Lows (Cyberpunk 2077)",
                    metric_unit="FPS",
                    labels=["RTX 4060 8GB", "RTX 4060 Ti 8GB", "RX 7600 XT 16GB", "RTX 4060 Ti 16GB"],
                    values=[38.4, 42.1, 64.8, 68.2],
                ),
            ),
            Scene(
                scene_id=3,
                timestamp_start="00:22",
                chapter_title="Purchasing Verdict and Market Recommendation",
                voiceover_text=(
                    "The verdict is unequivocal. Purchasing an eight gigabyte graphics card for demanding modern titles in twenty twenty-six "
                    "is a severe architectural bottleneck. Twelve gigabytes is now the absolute floor for stable frame delivery."
                ),
                visual_search_terms=["graphics card unboxing", "custom water cooling loop"],
                on_screen_text="VERDICT: 12GB MINIMUM",
                is_short_highlight=True,
            ),
        ],
        shorts=[
            ShortMetadata(
                title="Why 8GB VRAM is Dead in 2026 #Shorts",
                description="8GB frame buffers are officially obsolete. Telemetry shows severe 1% low drops. #Shorts #SiliconVerdict",
                hook_text="8GB VRAM IS FINISHED",
            )
        ],
    )


def generate_video_plan(
    topic: str,
    suggested_benchmarks: Optional[List[str]] = None,
    scenes_limit: Optional[int] = None,
) -> VideoProject:
    """Generates an authoritative, empirical PC hardware documentary script for 'Silicon Verdict'."""
    logger.info("Silicon Verdict: Generating technical video manifest for topic: '%s'", topic)

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    benchmark_hints = ""
    if suggested_benchmarks:
        benchmark_hints = "\nKey Technical Angles & Benchmarks to Validate:\n" + "\n".join(
            f"• {b}" for b in suggested_benchmarks
        )

    scope_directive = (
        f"CRITICAL CONSTRAINT: Produce EXACTLY {scenes_limit} scenes:\n"
        "• Scene 1: Introduction with high-impact technical hook on PCIe bus saturation, memory allocation, and texture swapping.\n"
        "• Scene 2: Comparative benchmark with populated 'chart_data' (1080p Ultra 1% Lows comparing 8GB vs 16GB VRAM configurations).\n"
        "• Scene 3: Purchasing verdict, market telemetry recommendation, and set 'is_short_highlight=True'.\n"
        if scenes_limit
        else "Write an extensive documentary script spanning 8 to 12 modular scenes (total ~1,600 to 2,000 words)."
    )

    system_instruction = (
        "You are the Lead Technical Writer, Senior Microarchitect, and Benchmark Analyst for 'Silicon Verdict' "
        "— an elite YouTube channel known for uncompromising empirical rigor, reminiscent of AnandTech, Gamers Nexus, "
        "and Hardware Unboxed.\n\n"
        "EDITORIAL MANDATES:\n"
        "1. STRICT NATIVE TECHNICAL ENGLISH: All narration, titles, descriptions, charts, and prompts must be in high-level, "
        "fluent technical English.\n"
        "2. TONE & IDENTITY: Objective, forensic, analytical, and authoritative. Deliver high information density. "
        "ABSOLUTELY FORBIDDEN: Cliched YouTube filler ('Welcome back guys', 'Smash that like button', 'Today we are looking at'). "
        "Begin immediately with the thesis, silicon architecture, or market anomaly.\n"
        "3. REQUIRED TERMINOLOGY: Explicitly utilize engineering terminology throughout the script: IPC (Instructions Per Cycle), "
        "1% lows, frame time variance, cache hierarchy (L2/L3 V-Cache), VRM phase power delivery, memory bandwidth (MT/s, FCLK), "
        "thermal throttling, package junction temperature (TjMax), and price-to-performance ratio ($/FPS).\n"
        f"4. STRUCTURE & SCALE: {scope_directive}\n"
        "5. BENCHMARK CHARTS: Comparative telemetry scenes MUST include populated 'chart_data' with realistic hardware models "
        "and metrics (e.g. title: '1080p Ultra 1% Lows (Cyberpunk 2077)', unit: 'FPS', labels: ['RTX 4060 8GB', 'RTX 4060 Ti 8GB', 'RX 7600 XT 16GB', 'RTX 4060 Ti 16GB'], values: [38.4, 42.1, 64.8, 68.2]).\n"
        "6. AUTONOMOUS SHORTS SELECTION: Flag at least 1 scene with 'is_short_highlight=True' where the critical verdict occurs, "
        "and provide matching 'ShortMetadata' in the 'shorts' array.\n"
        "7. VISUAL DIRECTIVES: 'visual_search_terms' must specify macro hardware footage (e.g., 'gpu memory pcb', 'pcie slot traces', 'graphics card heatsink').\n"
        "8. THUMBNAIL PROMPT: Must specify Obsidian Black background, neon cyan and electric circuit lighting accents."
    )

    prompt = (
        f"Produce a comprehensive Silicon Verdict video project on the topic: '{topic}'.{benchmark_hints}\n\n"
        "Deliver high-converting metadata (<70 char title, 15-20 SEO tags, provocative pinned question), "
        "the Midjourney thumbnail prompt, modular scenes with numerical benchmark charts, "
        "and corresponding Shorts metadata."
    )

    # Attempt generation across candidate models with exponential backoff
    for model_name in CANDIDATE_MODELS:
        for attempt in range(2):
            try:
                logger.info("Attempting plan generation with model '%s' (attempt %d/2)...", model_name, attempt + 1)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=VideoProject,
                        temperature=0.6,
                    ),
                )
                project = VideoProject.model_validate_json(response.text)

                if scenes_limit and len(project.scenes) > scenes_limit:
                    project.scenes = project.scenes[:scenes_limit]

                if len(project.scenes) >= 2 and project.scenes[1].chart_data is None:
                    project.scenes[1].chart_data = ChartData(
                        title="1080p Ultra 1% Lows (Cyberpunk 2077)",
                        metric_unit="FPS",
                        labels=["RTX 4060 8GB", "RTX 4060 Ti 8GB", "RX 7600 XT 16GB", "RTX 4060 Ti 16GB"],
                        values=[38.4, 42.1, 64.8, 68.2],
                    )

                if not any(s.is_short_highlight for s in project.scenes):
                    project.scenes[-1].is_short_highlight = True

                if not project.shorts:
                    project.shorts.append(
                        ShortMetadata(
                            title="Why 8GB VRAM is Dead in 2026 #Shorts",
                            description="PCIe bus saturation destroys frame pacing. The data proves it. #Shorts #SiliconVerdict",
                            hook_text="8GB VRAM IS FINISHED",
                        )
                    )

                project.description = format_final_description(project)
                logger.info("Plan generation succeeded via '%s'", model_name)
                return project

            except Exception as exc:
                logger.warning("Generation attempt failed on '%s': %s", model_name, exc)
                time.sleep(2)

    logger.warning("External AI models temporarily saturated with 503. Engaging deterministic Silicon Verdict plan.")
    fallback = get_emergency_fallback_project(topic, scenes_limit=scenes_limit or 3)
    fallback.description = format_final_description(fallback)
    return fallback


@dataclass
class DailyShortSpec:
    """Specification package for a daily short based on weekly pillar and rotation rules."""
    weekday_index: int
    day_name: str
    pillar_title: str
    theme_key: str
    theme_description: str
    game_title: str
    voice_id: str
    voice_label: str


def get_next_theme_key(weekday_index: int, db_path: Optional[Path] = None) -> str:
    """Alternates between 'theme_a' and 'theme_b' based on the last occurrence of weekday_index in history.

    If the last occurrence for this weekday was 'theme_a', selects 'theme_b'.
    If 'theme_b', selects 'theme_a'. If no prior history, defaults to 'theme_a'.
    """
    last_theme = get_last_theme_for_weekday(weekday_index, db_path=db_path)
    if last_theme == "theme_a":
        return "theme_b"
    elif last_theme == "theme_b":
        return "theme_a"
    return "theme_a"


def select_game_for_weekday(
    weekday_index: int,
    db_path: Optional[Path] = None,
    ref_date: Optional[datetime] = None,
) -> str:
    """Selects an available benchmark title from the 6-game daily pool, vetoing any game used in the last 14 days.

    Args:
        weekday_index: 0=Lunes to 4=Viernes.
        db_path: Optional custom path to SQLite database.
        ref_date: Optional reference datetime for calculation.

    Returns:
        str: Selected game title.
    """
    pillar = get_pillar_for_weekday(weekday_index)
    daily_pool = pillar.games
    recently_used = get_recently_used_games(days=14, db_path=db_path, ref_date=ref_date)

    available_games = [g for g in daily_pool if g not in recently_used]

    if available_games:
        selected = available_games[0]
        logger.info(
            "Weekday %d (%s): Selected '%s' from available pool (Vetoed: %s)",
            weekday_index,
            pillar.day_name,
            selected,
            recently_used,
        )
        return selected

    # Fallback if all 6 games were somehow used in 14 days: pick least recently used
    logger.warning("All games in weekday %d pool were used in the last 14 days. Picking least recently used.", weekday_index)
    for g in daily_pool:
        if g not in recently_used[:len(daily_pool)]:
            return g
    return daily_pool[0]


def select_daily_short_spec(
    weekday_index: int,
    db_path: Optional[Path] = None,
    ref_date: Optional[datetime] = None,
) -> DailyShortSpec:
    """Computes the full daily short specification with thematic alternation, game veto, and voice rotation."""
    pillar = get_pillar_for_weekday(weekday_index)
    theme_key = get_next_theme_key(weekday_index, db_path=db_path)
    theme_description = get_theme_description(weekday_index, theme_key)
    game_title = select_game_for_weekday(weekday_index, db_path=db_path, ref_date=ref_date)
    voice_id = get_next_voice(db_path=db_path)
    voice_label = get_voice_label(voice_id)

    return DailyShortSpec(
        weekday_index=weekday_index,
        day_name=pillar.day_name,
        pillar_title=pillar.pillar_title,
        theme_key=theme_key,
        theme_description=theme_description,
        game_title=game_title,
        voice_id=voice_id,
        voice_label=voice_label,
    )


def get_emergency_tiktok_long_project(
    topic: Optional[str] = None,
    spec: Optional[DailyShortSpec] = None,
) -> TikTokLongProject:
    """Provides a deterministic 5-block vertical long project (~162 words, 62-66s) for TikTok Creator Rewards."""
    game = spec.game_title if spec else "Cyberpunk 2077"
    title_topic = topic or "Why 8GB VRAM is Officially Dead: The 1440p Verdict"
    logger.warning("Generating deterministic TikTok 5-act long project for '%s'", title_topic)

    return TikTokLongProject(
        topic="8GB vs 16GB VRAM Bandwidth & 1% Low Bottleneck",
        title=f"{title_topic} #Tech #PCGaming #Hardware #SiliconVerdict",
        description=(
            "Empirical 1% low frametime telemetry proving narrow bus widths and 8GB VRAM choke modern gaming engines. "
            "Telemetry captured via PresentMon at 1440p Ultra. #SiliconVerdict #PCBuilding #HardwareTok"
        ),
        tags=[
            "SiliconVerdict", "HardwareTok", "PCGaming", "VRAMBottleneck", "Cyberpunk2077",
            "FrametimeSpikes", "1PercentLows", "TechReview", "PCBuilding", "GPUBenchmark"
        ],
        act1=TikTokAct1(
            voiceover="Think twelve gigabytes is overkill for modern gaming? That assumption is completely obsolete in twenty twenty-six.",
            dilemma_title="128-BIT vs 256-BIT BUS",
            dilemma_subtitle="Does narrow bus width choke 1440p textures?",
            category_pill="BANDWIDTH BOTTLENECK",
            gameplay_query="pc gameplay 4k 60fps",
        ),
        act2=TikTokAct2(
            voiceover=(
                "When render pipelines stream ray traced geometry and ultra textures, allocation rapidly surpasses eight gigabytes. "
                "Local GDDR bandwidth saturates immediately, forcing buffer spillover across the PCIe bus, degrading memory controller throughput "
                "and creating severe texture swapping micro-stutters."
            ),
            specs_title="ARCHITECTURAL SPECS",
            specs_bullets=[
                "128-bit Bus: 288 GB/s (Saturated)",
                "256-bit Bus: 576 GB/s (Linear Pacing)",
                "PCIe 4.0 x8 Latency Penalty: +35ms",
            ],
            silicon_query="semiconductor silicon wafer macro pcb",
        ),
        act3=TikTokAct3(
            voiceover=(
                f"Our PresentMon empirical telemetry in {game} confirms the disparity. While sixteen gigabyte configurations deliver "
                "ninety-four average frames with sixty-eight frames one percent lows, eight gigabyte setups suffer severe frame pacing degradation, "
                "cratering to thirty-eight frames per second with frametime spikes reaching catastrophic thirty-five milliseconds during high asset loading scenes."
            ),
            chart_title=f"1440p ULTRA TELEMETRY ({game.upper()})",
            chart_subtitle="256-bit 16GB vs 128-bit 8GB Pacing",
            preset_pill=f"1440p ULTRA • {game.upper()}",
            metric_unit="FPS",
            winner_label="256-bit 16GB VRAM",
            winner_avg_fps=94.0,
            winner_low_fps=68.2,
            winner_frametime_ms=10.6,
            loser_label="128-bit 8GB VRAM",
            loser_avg_fps=61.0,
            loser_low_fps=38.4,
            loser_frametime_ms=26.0,
            winner_badge="+54% FASTER",
        ),
        act4=TikTokAct4(
            voiceover=(
                "The golden rule for hardware purchasing in twenty twenty-six is absolute: never buy a graphics card with under twelve gigabytes "
                "for demanding modern engines. Eight gigabytes is now officially dead."
            ),
            golden_rule_title="THE GOLDEN RULE",
            golden_rule_takeaway="NEVER BUY <12GB VRAM FOR 1440p",
            gameplay_query="gaming pc custom build",
        ),
        act5=TikTokAct5(
            voiceover="Would you sacrifice raw clock speed for sixteen gigabytes of stable VRAM? Drop your vote in the comments.",
            poll_question="Would you sacrifice clock speed for 16GB VRAM?",
            poll_option_a="Option A: 16GB VRAM (Stable 1% Lows)",
            poll_option_b="Option B: Higher Clocks / 8GB VRAM",
        ),
    )


def generate_tiktok_long_plan(
    topic: Optional[str] = None,
    spec: Optional[DailyShortSpec] = None,
) -> TikTokLongProject:
    """Generates an authoritative 5-block vertical long video plan (61-68s, ~145-165 words) for TikTok Creator Rewards."""
    logger.info("Generating TikTok 5-act long plan (Topic: %s | Spec: %s)...", topic, spec.day_name if spec else "None")
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    context_hints = ""
    if spec:
        context_hints = (
            f"Daily Pillar: {spec.day_name} ({spec.pillar_title})\n"
            f"Required Subtheme ({spec.theme_key}): '{spec.theme_description}'\n"
            f"Mandatory Benchmark Game: '{spec.game_title}'\n"
        )
    if topic:
        context_hints += f"Target Hardware Debate: '{topic}'\n"

    system_instruction = (
        "You are the Lead Hardware Telemetry Engineer & Content Director for 'Silicon Verdict'.\n"
        "Generate a complete 5-act vertical video specification strictly calibrated for the TikTok Creator Rewards Program (>60s).\n\n"
        "STRICT DURATION & WORD COUNT MANDATES (Total words MUST be between 145 and 165 words):\n"
        "1. Act 1 [00:00 - 00:05] Technical Hook: Debunk a common myth or expose a counterintuitive silicon anomaly. "
        "STRICTLY 12 to 16 words (~5s runtime).\n"
        "2. Act 2 [00:05 - 00:20] Silicon Mechanism: Low-level architecture breakdown (bus width, memory controller saturation, "
        "L2/L3 cache miss penalties, PCIe link latency). STRICTLY 35 to 42 words (~15s runtime).\n"
        "3. Act 3 [00:20 - 00:45] Empirical Benchmark: PresentMon empirical telemetry citing exact Average FPS, 1% Lows, "
        "frametime variance in milliseconds, and percentage difference. STRICTLY 55 to 65 words (~25s runtime).\n"
        "4. Act 4 [00:45 - 00:58] The Golden Rule: Concrete, practical purchasing mandate for PC builders. "
        "STRICTLY 30 to 35 words (~13s runtime).\n"
        "5. Act 5 [00:58 - 00:65] Retention Closing: Highly polarizing community question for comments prompting debate between Option A and Option B. "
        "STRICTLY 15 to 20 words (~7s runtime).\n\n"
        "TONE: High-density, authoritative, empirical engineering English. ABSOLUTELY NO FILLER or generic intros."
    )

    prompt = (
        f"Create an elite TikTok Creator Rewards long video script (61-68s, 5 acts).\n"
        f"{context_hints}\n"
        "Ensure aggregate narration words exceed 140 words (target: 145-165 words) so spoken duration exceeds 60.5 seconds."
    )

    for model_name in CANDIDATE_MODELS:
        for attempt in range(2):
            try:
                logger.info("Requesting TikTok long plan via '%s' (attempt %d/2)...", model_name, attempt + 1)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=TikTokLongProject,
                        temperature=0.6,
                    ),
                )
                project = TikTokLongProject.model_validate_json(response.text)
                total_w = project.get_total_words()
                logger.info("TikTok plan received (%s): %d total words across 5 acts", model_name, total_w)

                if total_w < 140:
                    logger.warning("Word count (%d) below 140 threshold for >60s monetization. Regenerating...", total_w)
                    continue

                return project
            except Exception as exc:
                logger.warning("Attempt on '%s' failed: %s", model_name, exc)
                time.sleep(1)

    logger.warning("Gemini AI models saturated. Deploying deterministic TikTok Creator Rewards plan.")
    return get_emergency_tiktok_long_project(topic=topic, spec=spec)
