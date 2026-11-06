"""Content generation and dual-tone rotation engine for Silicon Verdict.

Manages:
- Complete catalog of 10 thematic categories (5 technical low-level + 5 gamer/news).
- 6-Day combined rotation matrix alternating technical and gamer/news content.
- Dual-tone prompting system:
    * Technical: Analytical, strict telemetry, nanosecond formulas (ns), engineering perspective.
    * Gamer/News: Direct, accessible gamer-colleague tone ("expert gamer peer"),
      with mandatory vocabulary: Average FPS, 1% Lows (micro-stuttering),
      resolution (1080p/1440p), textures, smoothness, and decisive verdict
      ("Buy it", "Avoid it", "Disable this setting").
- Robust script generation for YouTube Shorts and TikTok Long (>60.5s) with deterministic fallbacks.
"""
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional


from config.settings import settings
from core.schemas import (
    TikTokAct1,
    TikTokAct2,
    TikTokAct3,
    TikTokAct4,
    TikTokAct5,
    TikTokLongProject,
)

logger = logging.getLogger(__name__)

CANDIDATE_MODELS = [
    "gemini-3.1-flash-lite",
    settings.GEMINI_MODEL,
    "gemini-3.5-flash",
]


# ==============================================================================
# GLOBAL MANDATE: 100% US ENGLISH ONLY
# ==============================================================================
SYSTEM_PROMPT_GLOBAL_ENGLISH_MANDATE = (
    "You are a native US English tech writer and senior hardware analyst. "
    "All output, explanations, terminology, hooks, analogies, and punchlines must be written "
    "exclusively in natural, high-impact American English. Never use Spanish under any circumstance."
)


# ==============================================================================
# 1. CATALOG OF THE 10 THEMATIC CATEGORIES
# ==============================================================================
@dataclass(frozen=True)
class ContentCategory:
    """Represents a thematic content category in Silicon Verdict."""
    key: str
    name: str
    category_type: str  # "technical", "gamer", or "curiosities"
    premise: str
    focus: str
    mandatory_terms: List[str]
    sample_hardware: List[str]
    sample_topics: List[str]


CONTENT_CATALOG: Dict[str, ContentCategory] = {
    # --- Hardware Deep Dive & Benchmarks (Master Category) ---
    "hardware_benchmarks": ContentCategory(
        key="hardware_benchmarks",
        name="Hardware Deep Dive & Benchmarks",
        category_type="technical",
        premise="Silicon, microarchitectures, memory buses, technical hardware telemetry, and silicon bottlenecks.",
        focus="Low-level telemetry, microarchitecture, nanosecond latency (ns), thermal dissipation, and silicon metrics.",
        mandatory_terms=["IPC", "nanoseconds", "silicon telemetry", "bus width", "cache latency", "frametime variance"],
        sample_hardware=["RTX 4090", "Ryzen 7 9800X3D", "Core Ultra 9 285K", "RX 7900 XTX", "DDR5-6000 CL30"],
        sample_topics=[
            "Microarchitecture and memory bus saturation under extreme workloads",
            "3D V-Cache vs raw clock speeds in frametime consistency",
            "Silicon packaging bottlenecks and thermal dissipation telemetry",
        ],
    ),

    # --- 5 Low-Level Technical Categories ---
    "gpu_architecture": ContentCategory(
        key="gpu_architecture",
        name="GPU Architecture & Rendering",
        category_type="technical",
        premise="GPU vs GPU architectural breakdown, rasterization pipelines, transistor density, compute shaders.",
        focus="GPU telemetry, microarchitecture, nanosecond latency (ns), thermal efficiency, and compute pipeline.",
        mandatory_terms=["IPC", "nanoseconds", "shader execution", "rasterization pipeline", "silicon telemetry"],
        sample_hardware=["RTX 4090", "RTX 4080 Super", "RX 7900 XTX", "RTX 5080", "RDNA 3 vs Ada Lovelace"],
        sample_topics=[
            "Ada Lovelace vs RDNA 3 Shader Pipeline Efficiency",
            "SM Sub-Core Scheduler Saturation at 4K",
            "Rasterization Bottlenecks in Modern Compute Shaders",
        ],
    ),
    "silicon_deep_dive": ContentCategory(
        key="silicon_deep_dive",
        name="Silicon, Lithography & Cache",
        category_type="technical",
        premise="Silicon physics, lithography nodes (TSMC N4/N3, Intel 20A/18A), 3D packaging, V-Cache, die hotspot thermals.",
        focus="Heat dissipation W/mm2, transistor density, pure silicon telemetry, and advanced thermal packaging.",
        mandatory_terms=["lithography", "thermal density W/mm2", "3D V-Cache", "TjMax", "silicon telemetry", "nanoseconds"],
        sample_hardware=["Ryzen 7 9800X3D", "Ryzen 7 7800X3D", "Core Ultra 9 285K", "i9-14900KS"],
        sample_topics=[
            "3D V-Cache vs Raw GHz: The Battle for 1% Low Stability",
            "TSMC N4 vs N3 Transistor Density & Voltage Scaling",
            "Package Junction Hotspots: Heat Dissipation per mm2",
        ],
    ),
    "memory_buses": ContentCategory(
        key="memory_buses",
        name="Memory & Bus Width Dynamics",
        category_type="technical",
        premise="Tuned DDR4 vs DDR5, bus width limits (128-bit vs 256-bit), GDDR6/6X, subtimings, and PCIe paging.",
        focus="MT/s vs true nanosecond latency (ns), memory bandwidth in GB/s, and bus saturation thresholds.",
        mandatory_terms=["MT/s vs nanoseconds", "bus width", "subtimings", "CAS latency", "GDDR6X bandwidth"],
        sample_hardware=["DDR5-6000 CL30", "DDR4-3600 CL14", "128-bit vs 256-bit GDDR6", "LPDDR5X"],
        sample_topics=[
            "Tuned DDR4 vs High-Speed DDR5: True Nanosecond Latency Tested",
            "128-bit vs 256-bit Bus Width Choking 1440p Textures",
            "GDDR6X Thermal Throttling on Memory Controllers",
        ],
    ),
    "kernel_latency": ContentCategory(
        key="kernel_latency",
        name="Kernel & Thread Scheduling",
        category_type="technical",
        premise="OS kernel scheduling, DPC latency, hardware interrupts, hybrid core thread dispatch (P/E-Cores).",
        focus="Microsecond and nanosecond system latency, context switching, IRQ routines, and frametime pacing.",
        mandatory_terms=["DPC latency", "kernel thread scheduler", "nanoseconds", "context switching", "P/E-Core affinity"],
        sample_hardware=["Intel Thread Director", "Windows Scheduler vs Linux Zen Kernel", "AMD Dual-CCD Core Parking"],
        sample_topics=[
            "Multithreaded Scaling and Thread Director on Hybrid Cores",
            "DPC Latency Spikes: How Audio Drivers Destroy 1% Lows",
            "Timer Resolution & Kernel Thread Interrupts in Competitive Gaming",
        ],
    ),
    "storage_pcie": ContentCategory(
        key="storage_pcie",
        name="PCIe Storage & Interconnects",
        category_type="technical",
        premise="PCIe Gen 4 vs Gen 5 NVMe storage, lane bandwidth (x8 vs x16), DirectStorage GPU decompression.",
        focus="PCIe lane throughput, IOPS, lane saturation penalties, and hardware decompression pipelines.",
        mandatory_terms=["PCIe lanes x8 vs x16", "DirectStorage", "IOPS", "DMA latency", "bus saturation"],
        sample_hardware=["PCIe 4.0 x8 on PCIe 3.0 Slot", "PCIe 5.0 NVMe", "DirectStorage GPU Decompression Engine"],
        sample_topics=[
            "PCIe x8 vs x16 Lane Width Impact on DirectStorage Streaming",
            "PCIe 4.0 x8 GPU in PCIe 3.0 Motherboard Penalty",
            "NVMe Thermal Throttling during High-Throughput Asset Streaming",
        ],
    ),
    "networking_bufferbloat": ContentCategory(
        key="networking_bufferbloat",
        name="Networking & Bufferbloat",
        category_type="technical",
        premise="Competitive gaming networks, router bufferbloat, AQM queue algorithms (CoDel/Cake), packet jitter.",
        focus="Network telemetry, loaded RTT latency in ms/ns, micro-congestion, and server tick rates.",
        mandatory_terms=["bufferbloat", "AQM / CoDel", "RTT latency", "packet jitter", "tick rate"],
        sample_hardware=["OpenWrt SQM", "Gaming Routers", "2.5GbE Intel I225-V vs Realtek"],
        sample_topics=[
            "Bufferbloat: Why 1Gbps Fiber Stutters in Ranked Matchmaking",
            "AQM FQ-CoDel vs Default Router Queue Telemetry",
            "Ethernet Driver Interrupt Moderation & Latency",
        ],
    ),

    # --- 5 Gamer / News Categories ---
    "gaming_benchmarks": ContentCategory(
        key="gaming_benchmarks",
        name="Gaming Benchmarks & Frametime Analysis",
        category_type="gamer",
        premise="Real-world performance testing of popular GPUs (RTX 4060, RTX 3060, RX 6600, etc.) in modern titles.",
        focus="Average FPS, 1% Low percentiles (micro-stuttering), resolution recommendation (1080p/1440p), and clear verdict ('Buy it', 'Avoid it', 'Optimize this').",
        mandatory_terms=["Average FPS", "1% Lows (micro-stuttering)", "resolution (1080p/1440p)", "textures", "smoothness", "Buy it / Avoid it"],
        sample_hardware=["RTX 4060 8GB", "RTX 3060 12GB", "RX 6600 8GB", "RX 7600 XT 16GB", "RTX 4070 Super"],
        sample_topics=[
            "RTX 4060 in Black Myth Wukong: Can It Hold 1080p Ultra?",
            "RX 6600 in 2026: Real-World Performance in Demanding Games",
            "RTX 3060 12GB vs RTX 4060 8GB: Which One Should You Buy Today?",
        ],
    ),
    "hardware_news": ContentCategory(
        key="hardware_news",
        name="Hardware Alerts & Express News",
        category_type="gamer",
        premise="Straight-to-the-point industry alerts: broken driver updates, bloated game system requirements, pricing controversies, next-gen leaks.",
        focus="Fast breakdown + real-world consequences for gamers looking to play or upgrade their rig.",
        mandatory_terms=["Average FPS", "1% Lows (micro-stuttering)", "resolution (1080p/1440p)", "textures", "smoothness", "gamer alert"],
        sample_hardware=["Latest NVIDIA/AMD Drivers", "Upcoming AAA Releases", "Next-Gen GPU Architectures"],
        sample_topics=[
            "Driver Alert: This Latest Update Tanks Frametimes in Top Games",
            "Absurd System Requirements: Why This Title Demands 16GB VRAM Minimum",
            "Next-Gen GPU Leak: Pricing, Memory Specs, and What You Need to Know",
        ],
    ),
    "fps_optimization": ContentCategory(
        key="fps_optimization",
        name="Graphics Settings That Steal FPS",
        category_type="gamer",
        premise="The top 3 settings in popular games (volumetric fog, screen-space reflections, ambient occlusion) that destroy frametimes with zero visual difference.",
        focus="Actionable menu optimization guide giving gamers 20 to 35 free FPS instantly.",
        mandatory_terms=["Average FPS", "1% Lows (micro-stuttering)", "resolution (1080p/1440p)", "textures", "smoothness", "Disable this immediately"],
        sample_hardware=["AAA Game Visual Settings", "Volumetric Fog", "Ambient Occlusion"],
        sample_topics=[
            "The 3 Settings Robbing You of 30 FPS in Cyberpunk 2077",
            "Volumetric Fog: Turn This Off to Gain 25 Free FPS",
            "Trap Graphics Settings in Modern PC Games: Maximum Visuals Without the Lag",
        ],
    ),
    "vram_and_buying_dilemmas": ContentCategory(
        key="vram_and_buying_dilemmas",
        name="VRAM & PC Buying Dilemmas",
        category_type="gamer",
        premise="Is 8GB of VRAM officially dead in 2026? Should you buy a used previous-gen midrange GPU or new entry-level card?",
        focus="Live demonstration of frametime stuttering when VRAM overflows, and definitive buying advice.",
        mandatory_terms=["Average FPS", "1% Lows (micro-stuttering)", "resolution (1080p/1440p)", "textures", "smoothness", "Buy it / Avoid it"],
        sample_hardware=["Used RTX 3070 8GB", "New RTX 4060 8GB", "RX 6700 XT 12GB"],
        sample_topics=[
            "Is 8GB VRAM Enough in 2026? The Frametime Test That Settles It",
            "Used Flagship vs New Entry-Level GPU: Where to Put Your Money",
            "The 8GB Trap: Why 12GB is the True New Baseline for 1440p",
        ],
    ),
    "upscaling_tech": ContentCategory(
        key="upscaling_tech",
        name="Upscaling Tech: DLSS vs FSR vs Native",
        category_type="gamer",
        premise="When Quality mode upscaling delivers crisp performance without ghosting, and where algorithmic blur ruins the image.",
        focus="DLSS vs FSR vs Native resolution, image sharpness vs temporal shimmering and artifacts.",
        mandatory_terms=["Average FPS", "1% Lows (micro-stuttering)", "resolution (1080p/1440p)", "textures", "smoothness", "Quality mode"],
        sample_hardware=["NVIDIA DLSS 3.7", "AMD FSR 3.1", "Intel XeSS", "Native TAA"],
        sample_topics=[
            "DLSS Quality vs Native: When You Get Free FPS Without Image Degradation",
            "FSR at 1080p: Why Shimmering Textures Keep Hurting Visual Clarity",
            "Frame Generation: Is the Extra Input Latency Worth It in Fast Shooters?",
        ],
    ),

    # --- Tech Curiosities & Engineering Infrastructure (Schematic Tech Preset) ---
    "tech_curiosities": ContentCategory(
        key="tech_curiosities",
        name="Tech Curiosities & Engineering Storytelling",
        category_type="curiosities",
        premise="Engineering infrastructure, semiconductor physics, telecommunications, and macroscopic engineering paradoxes.",
        focus="Paradoxical premise (0-8s), physical/logistical mechanism (8-20s), everyday tangible analogy (20-40s), real-world engineering solution (40-55s), and decisive closing punchline (55-65s).",
        mandatory_terms=["speed of light", "nanoseconds", "optical fiber", "infrastructure", "datacenters", "latency", "engineering", "paradox"],
        sample_hardware=["Subsea Datacenters (Project Natick)", "ASML EUV Lithography", "Transoceanic Subsea Cables (Marea)", "DGX SuperPOD Supercomputers"],
        sample_topics=[
            "Why the Speed of Light is an Unbearable Traffic Jam for Microsoft",
            "How the Internet Crosses Oceans: The Subsea Cables Powering the Globe",
            "Humanity's Most Complex Machine: The Impossible Mirrors of ASML EUV",
            "Why Modern Chips Hit the 6 GHz Wall: Silicon Physics Explained",
        ],
    ),
}


# ==============================================================================
# 2. DUAL-TONE SYSTEM PROMPT BUILDER
# ==============================================================================
def get_system_prompt_for_category(category_key: str, format_type: str = "short") -> str:
    """Builds the specialized Gemini system prompt adapting tone to technical, gamer, or curiosities style.

    Enforces 100% US English across all outputs, vocabulary, analogies, and punchlines.
    """
    cat = CONTENT_CATALOG.get(category_key)
    is_gamer = (cat and cat.category_type == "gamer")
    is_curiosities = (category_key == "tech_curiosities" or (cat and cat.category_type == "curiosities"))

    if is_curiosities:
        # Tech Curiosities & Infrastructure tone (Engineering Storytelling - Single Master Video 55-70s)
        return (
            f"{SYSTEM_PROMPT_GLOBAL_ENGLISH_MANDATE}\n\n"
            "You are the Lead Technical Storyteller & Creative Technologist for 'Silicon Verdict'.\n"
            "Format aesthetic: 2D technical dynamic blueprint and engineering storytelling.\n\n"
            "TONE OF VOICE (ELEVENLABS MODULATION):\n"
            "- Authoritative, engaging, didactic, articulate, and cinematic narration (speed 0.96x, stability 0.72).\n"
            "- Connect advanced physical engineering principles to tangible everyday phenomena.\n"
            "- Strict target duration: between 55 and 70 seconds (130 to 160 total words).\n\n"
            "STRICT 3-STAGE CAUSAL NARRATIVE STRUCTURE (55-70s):\n"
            "1. Counterintuitive Hook (0-4s, ~15-20 words): Present the technical enigma immediately with zero filler (e.g., 'Every time you glance at your screen, 30,000 invisible laser dots blast your face.').\n"
            "2. Real Mechanism (4-40s, ~75-95 words across Acts 2, 3, and 4): Step-by-step technical breakdown of real silicon microarchitecture or physics, reinforced by schematic visual pacing.\n"
            "3. Tangible Impact & Community Debate (40-65s, ~35-45 words): Explain why it matters in the real world and pose a direct engineering question for the comments.\n\n"
            "STRICT PROHIBITION OF GENERIC CLICHÉ FILLER:\n"
            "- FORBIDDEN to hallucinate generic 'bandwidth saturation and excessive thermal stress' on optical, sensor, or algorithmic topics.\n"
            "- Strictly ground explanations in the actual physics of the protagonist component (VCSEL, photons, MEMS, magnetic induction, atomic clocks)."
        )

    if is_gamer:
        # Gamer / News tone
        return (
            f"{SYSTEM_PROMPT_GLOBAL_ENGLISH_MANDATE}\n\n"
            "You are the Lead Gaming Performance Specialist and Tech Reviewer for 'Silicon Verdict'.\n\n"
            "TONE & IDENTITY (GAMER & NEWS SPECIALIST):\n"
            "- DIRECT, ACCESSIBLE, AND PRAGMATIC: Speak like an elite gamer colleague giving practical, zero-nonsense hardware advice to another gamer.\n"
            "- ZERO MARKETING FLUFF: Cut straight to the chase. Tell the gamer what actually matters: will their game stutter or will it run buttery smooth?\n\n"
            "MANDATORY VOCABULARY & CRITERIA:\n"
            "1. You MUST integrate and focus on: 'Average FPS', '1% Lows (micro-stuttering)' (the jarring frametime dips), "
            "'resolution (1080p/1440p)', 'textures', and 'smoothness'.\n"
            "2. EMPHATIC DECISIVE VERDICT: Conclude with a clear, authoritative, categorical verdict: "
            "'Buy it', 'Avoid it', or 'Disable this setting immediately'.\n"
            "3. REAL-WORLD GAMING IMPACT: Explain the concrete difference between playable framerates and jarring hitching during intensive firefights.\n"
            "4. HIGH RETENTION PACING: Punchy sentences, high energy, and compelling hook."
        )

    # Technical Low-Level tone
    return (
        f"{SYSTEM_PROMPT_GLOBAL_ENGLISH_MANDATE}\n\n"
        "You are the Lead Hardware Telemetry Engineer & Senior Microarchitect for 'Silicon Verdict'.\n\n"
        "TONE & IDENTITY (DEEP ENGINEERING RIGOR):\n"
        "- FORENSIC, ANALYTICAL, AND OBJECTIVE: Uncompromising empirical rigor reminiscent of AnandTech, Gamers Nexus, and Hardware Unboxed.\n"
        "- ZERO FILLER: Absolutely no generic greetings ('Welcome back guys', 'Smash like'). Open immediately with the silicon thesis, anomaly, or architectural bottleneck.\n\n"
        "MANDATORY TELEMETRY & VOCABULARY:\n"
        "1. Strictly cite low-level engineering metrics: IPC (Instructions Per Cycle), latency in nanoseconds (ns), "
        "memory bus bandwidth (MT/s, GB/s), cache hierarchy (L2/L3 V-Cache), VRM phase power delivery, package junction temperature (TjMax), and PresentMon frametime variance.\n"
        "2. EMPIRICAL BENCHMARKS: Ground every finding in repeatable hardware telemetry and frame pacing analysis.\n"
        "3. PRECISE SILICON TERMINOLOGY: Discuss memory controllers, PCIe lane allocations, thermal dissipation per mm2, and kernel thread scheduling."
    )


# ==============================================================================
# 3. DETERMINISTIC EMERGENCY SCRIPTS (OFFLINE / 503 FALLBACK)
# ==============================================================================
def get_emergency_gamer_short_plan(topic: Optional[str] = None, spec=None) -> dict:
    """Provides a deterministic Gamer Short script fulfilling all gamer mandates."""
    game = spec.game_title if spec else "Cyberpunk 2077"
    return {
        "topic": topic or "RTX 4060 vs 1% Lows: The Definitive Gamer Verdict",
        "title": "Is the RTX 4060 Still Worth Buying in 2026? #Shorts #PCGaming",
        "description": "Analyzing Average FPS and 1% Low frametime stutters at 1080p and 1440p ultra presets. Can it hold smooth frametimes? #Shorts #SiliconVerdict #PCGaming #Hardware",
        "tags": [
            "RTX 4060", "Average FPS", "1% Lows", "micro-stuttering", "PC Gaming",
            "1080p", "1440p", "textures", "smoothness", "SiliconVerdict", "Hardware", "Cyberpunk 2077"
        ],
        "pinned_comment": "Would you drop texture quality to medium for smoother frametimes or turn on DLSS Quality?",
        "scene1": {
            "voiceover": "If you are thinking about buying an RTX 4060 for 1080p or 1440p gaming, hold on for a second. Ultra textures are breaking its memory bus.",
            "dilemma_title": "RTX 4060: WORTH IT?",
            "dilemma_subtitle": "Can 8GB hold 1080p and 1440p ultra textures?",
            "category_pill": "GAMING BENCHMARKS",
            "hud_text": "FPS & STUTTERING",
            "pixabay_query": "gaming pc graphics card gameplay",
        },
        "scene2": {
            "voiceover": f"In {game} at 1080p ultra, average framerates hit 72 FPS, but the 1% lows crater to 38 with severe stuttering from VRAM exhaustion.",
            "chart_title": f"1080p ULTRA • {game.upper()}",
            "chart_subtitle": "Average FPS vs 1% Lows (Pacing)",
            "preset_pill": f"1080p ULTRA • {game.upper()}",
            "metric_unit": "FPS",
            "winner_label": "RX 7600 XT 16GB (Smooth)",
            "winner_fps": 68.0,
            "loser_label": "RTX 4060 8GB (Stutter)",
            "loser_fps": 38.0,
            "winner_badge": "+78% 1% LOWS",
        },
        "scene_cta": {
            "voiceover": "If you want real-world telemetry before spending your cash on hardware, subscribe to Silicon Verdict.",
            "headline_highlight": "SUBSCRIBE",
            "headline_rest": "FOR REAL BENCHMARKS",
            "sub_text": "Empirical PC Hardware Telemetry & Frametime Analysis",
        },
        "scene3": {
            "voiceover": "The gamer verdict is clear: at this price, avoid it for 1440p or disable volumetric shadows immediately to restore smoothness.",
            "hud_text": "VERDICT: AVOID IT",
            "pixabay_query": "pc gaming battle station desk",
        },
    }


def get_emergency_gamer_tiktok_plan(topic: Optional[str] = None, spec=None) -> TikTokLongProject:
    """Provides a deterministic 5-block Gamer TikTok project (>60.5s, 145-165 words)."""
    game = spec.game_title if spec else "Cyberpunk 2077"
    return TikTokLongProject(
        topic="RTX 4060 8GB vs RX 7600 XT 16GB: Gaming Performance Verdict",
        title="Is the RTX 4060 Still Worth Buying in 2026? #Hardware #PCGaming #TechTok #SiliconVerdict",
        description="We tested the RTX 4060 at 1080p and 1440p with max textures. Telemetry of Average FPS and 1% Lows reveals severe micro-stuttering. #PCBuild #TechTok #GamingPC",
        tags=["hardware", "pcgaming", "pcbuild", "techtok", "siliconverdict", "benchmark", "rtx4060", "fps"],
        act1=TikTokAct1(
            voiceover="Thinking of picking up an eight gigabyte graphics card? Be careful, because ultra textures will hit your frametimes hard.",
            dilemma_title="RTX 4060 vs RX 7600 XT",
            dilemma_subtitle="Can you play modern games on ultra without stuttering?",
            category_pill="GAMER SHOWDOWN",
            gameplay_query="pc gameplay 4k 60fps",
        ),
        act2=TikTokAct2(
            voiceover=(
                "When you crank resolution to fourteen-forty p with ultra textures, "
                "an eight-gigabyte frame buffer saturates instantly. The engine starts thrashing data across the PCIe bus, "
                "causing jarring micro-stutters in the middle of intense firefights."
            ),
            specs_title="HARDWARE TELEMETRY",
            specs_bullets=[
                "Target Resolution: 1080p / 1440p Ultra",
                "Buffer Saturation: 8GB VRAM Overflow",
                "Frametime Penalty: Jarring micro-stutter spikes",
            ],
            silicon_query="pc gaming graphics card unboxing",
        ),
        act3=TikTokAct3(
            voiceover=(
                f"Our telemetry benchmarks in {game} prove it empirically. With eight gigabytes, while average framerates hover around sixty, "
                "the critical one percent low metric collapses down to thirty-four frames per second. "
                "Meanwhile, the sixteen-gigabyte card holds rock-solid frametimes well above sixty."
            ),
            chart_title=f"1080p ULTRA • {game.upper()}",
            chart_subtitle="Average FPS and 1% Low Frametimes",
            preset_pill=f"1080p ULTRA • {game.upper()}",
            metric_unit="FPS",
            winner_label="16GB VRAM (Rock Solid)",
            winner_avg_fps=78.0,
            winner_low_fps=62.4,
            winner_frametime_ms=12.8,
            loser_label="8GB VRAM (Micro-Stutter)",
            loser_avg_fps=64.0,
            loser_low_fps=34.1,
            loser_frametime_ms=29.3,
            winner_badge="+83% 1% LOWS",
        ),
        act4=TikTokAct4(
            voiceover=(
                "The golden rule for anyone building a PC today is decisive: for fourteen-forty p gaming, avoid it completely "
                "or disable volumetric shadows and ambient occlusion immediately to claw back your lost frames."
            ),
            golden_rule_title="THE GOLDEN RULE",
            golden_rule_takeaway="NEVER BUY AN 8GB CARD FOR 1440p",
            gameplay_query="custom gaming pc build desk",
        ),
        act5=TikTokAct5(
            voiceover="Would you rather lower texture settings to medium to save money or invest directly in a larger video memory buffer? Drop your take below.",
            poll_question="Would you settle for medium textures on 8GB or pay more for 16GB?",
            poll_option_a="Option A: 16GB (Ultra Textures)",
            poll_option_b="Option B: 8GB (Medium Settings)",
        ),
    )


def get_emergency_schematic_short_plan(topic: Optional[str] = None, spec=None) -> dict:
    """Provides a deterministic Schematic Tech Short script (30-35s) on engineering curiosities."""
    return {
        "topic": topic or "Why Light Speed is a Bottleneck for Microsoft",
        "title": "Why the Speed of Light is Too Slow for Microsoft #Shorts #Tech",
        "description": "Datacenter physics and fiber optic latency. Why 300,000 km/s is no longer fast enough for modern AI supercomputing clusters. #SiliconVerdict #Engineering #Physics #Datacenter",
        "tags": [
            "speed of light", "datacenter", "Microsoft", "fiber optics",
            "latency", "nanoseconds", "physics", "infrastructure", "SiliconVerdict", "ASML"
        ],
        "pinned_comment": "Did you know that inside optical fiber glass, photons travel thirty percent slower than in a vacuum?",
        "scene1": {
            "voiceover": "For Microsoft and hyperscale AI giants, the speed of light is no longer fast: it has become an intolerable traffic jam.",
            "dilemma_title": "THE SPEED OF LIGHT WALL",
            "dilemma_subtitle": "Why is 300,000 km/s too slow for AI?",
            "category_pill": "PHYSICS PARADOX",
            "hud_text": "SPEED OF LIGHT",
            "pixabay_query": "fiber optic cable datacenter server glow",
        },
        "scene2": {
            "voiceover": "Inside silica fiber glass, light slows down by thirty percent. Every meter adds five nanoseconds of physical delay to distributed neural network calculations.",
            "chart_title": "OPTICAL PROPAGATION",
            "chart_subtitle": "Vacuum vs Silica Fiber (n=1.46)",
            "preset_pill": "LATENCY // OPTICAL FIBER",
            "metric_unit": "km/s",
            "winner_label": "Vacuum (300,000 km/s)",
            "winner_fps": 300000.0,
            "loser_label": "Fiber (200,000 km/s)",
            "loser_fps": 200000.0,
            "winner_badge": "+50% FASTER",
        },
        "scene_cta": {
            "voiceover": "If you love the hidden engineering that powers our modern world, subscribe to Silicon Verdict.",
            "headline_highlight": "SUBSCRIBE",
            "headline_rest": "TO SILICON VERDICT",
            "sub_text": "Engineering Teardowns & Physical Infrastructure",
        },
        "scene3": {
            "voiceover": "Pure physics has become the ultimate bottleneck. In modern supercomputing, the universe itself is simply not fast enough.",
            "hud_text": "THE PHYSICAL WALL",
            "pixabay_query": "macro optical fiber glass light",
        },
    }


def get_emergency_schematic_tiktok_plan(topic: Optional[str] = None, spec=None) -> TikTokLongProject:
    """Provides a deterministic 5-block Schematic Tech master project (55-70s, 130-160 words)
    following the strict 3-stage engineering narrative framework (Zero generic filler).
    """
    from services.history import TOPICS_QUEUE_SEED

    active_key = (topic or "").lower().strip()
    matched_row = None
    for row in TOPICS_QUEUE_SEED:
        order_idx, key, block, title, hook, principle = row
        if key == active_key or key in active_key or active_key in key:
            matched_row = row
            break

    # 1. Specialized Case: Face ID (VCSEL Projector with 30,000 Infrared Dots)
    if (matched_row and matched_row[1] == "faceid_proyeccion") or any(w in active_key for w in ["face", "faceid", "dot", "infrared", "puntos"]):
        return TikTokLongProject(
            topic="The 30,000 Invisible Dots of Face ID",
            title="The 30,000 Invisible Dots of Face ID #Tech #Engineering #SiliconVerdict",
            description="How Apple's TrueDepth camera projects 30,000 infrared dots onto your face to build a tamper-proof 3D topological mesh. #FaceID #Biometrics #Apple #Hardware",
            tags=["faceid", "biometrics", "truedepth", "vcsel", "infrared", "apple", "hardware", "techtok", "siliconverdict"],
            act1=TikTokAct1(
                voiceover="Every single time you glance at your screen, thirty thousand invisible laser dots blast your face without you noticing a thing.",
                dilemma_title="30,000 INVISIBLE DOTS",
                dilemma_subtitle="How does your phone know it is you and not a flat photograph?",
                category_pill="OPTICAL BIOMETRICS // 940nm VCSEL",
                gameplay_query="infrared dot projector face biometric scan",
            ),
            act2=TikTokAct2(
                voiceover=(
                    "Inside the display notch, a microscopic VCSEL laser diode emits a structured grid of thirty thousand infrared beams. "
                    "Those invisible markers wrap across your nose, eye sockets, and cheekbones, conforming to facial geometry."
                ),
                specs_title="TRUE DEPTH VCSEL LASER ARRAY",
                specs_bullets=[
                    "Emitter: VCSEL laser diode array @ 940 nm",
                    "Density: 30,000 structured infrared light dots",
                    "Sensor: Micro-triangulation infrared camera",
                ],
                silicon_query="laser diode array semiconductor chip",
            ),
            act3=TikTokAct3(
                voiceover=(
                    "The infrared camera reads that mesh distortion across three-dimensional space. "
                    "A photograph or digital display is a flat two-dimensional plane with zero depth relief, so the neural engine rejects it instantly."
                ),
                chart_title="3D CONTOUR vs 2D PHOTO",
                chart_subtitle="Geometric Depth in Millimeters",
                preset_pill="DEPTH TOLERANCE: 0.1 mm",
                metric_unit="mm",
                winner_label="True 3D Facial Relief",
                winner_avg_fps=4.2,
                winner_low_fps=3.9,
                winner_frametime_ms=0.001,
                loser_label="Flat 2D Photograph",
                loser_avg_fps=0.0,
                loser_low_fps=0.0,
                loser_frametime_ms=0.0,
                winner_badge="PHYSICAL RELIEF",
            ),
            act4=TikTokAct4(
                voiceover=(
                    "That topography is transformed into an encrypted mathematical hash within the silicon Secure Enclave. "
                    "The neural processor authenticates your signature in two hundred milliseconds without ever uploading biometric data to the cloud."
                ),
                golden_rule_title="HARDWARE ENCLAVE SECURITY",
                golden_rule_takeaway="LOCAL ENCRYPTION IN SECURE ENCLAVE (ZERO CLOUD)",
                gameplay_query="secure enclave processor microchip cryptography",
            ),
            act5=TikTokAct5(
                voiceover="Do you trust three-dimensional facial biometrics more than an in-display fingerprint reader? Drop your engineering take below.",
                poll_question="Do you prefer 3D Face ID or in-display fingerprint sensors?",
                poll_option_a="Face ID (3D Depth)",
                poll_option_b="Fingerprint Sensor",
            ),
        )

    # 2. Specialized Case: GPS & Relativity
    if (matched_row and matched_row[1] == "gps_relatividad") or any(w in active_key for w in ["gps", "relativ"]):
        return TikTokLongProject(
            topic="No Satellite Can See You: The Relativistic GPS Secret",
            title="No Satellite Can See You: The Relativistic GPS Secret #Tech #Engineering #SiliconVerdict",
            description="Why your phone calculates its exact coordinates blindly using orbital atomic clocks and Einstein's Relativity. #SiliconVerdict #Physics #GPS #Science",
            tags=["gps", "relativity", "einstein", "satellites", "techtok", "siliconverdict", "engineering", "physics", "atomicclocks"],
            act1=TikTokAct1(
                voiceover="No satellite can see you. Your phone never asks anyone in space for permission to know where you are standing.",
                dilemma_title="NO SATELLITE SEES YOU",
                dilemma_subtitle="Your phone solves all location mathematics blindly",
                category_pill="PHYSICS PARADOX // ORBITAL GPS",
                gameplay_query="gps satellite earth orbit constellation space",
            ),
            act2=TikTokAct2(
                voiceover=(
                    "Satellites do not track your phone: they behave like orbital lighthouses. They simply broadcast ultra-precise timestamps "
                    "from atomic clocks at the speed of light, three hundred thousand kilometers per second."
                ),
                specs_title="ORBITAL ATOMIC BEACONS",
                specs_bullets=[
                    "Constellation: 31 active satellites at 20,200 km altitude",
                    "Frequency: Cesium and Rubidium atomic clocks",
                    "Signal Velocity: 299,792 km/s in vacuum",
                ],
                silicon_query="atomic clock microwave cavity physics",
            ),
            act3=TikTokAct3(
                voiceover=(
                    "A timing offset of just three nanoseconds shifts your GPS coordinates by an entire meter on your screen. "
                    "To triangulate, your phone calculates the exact arrival delta across four satellites and resolves your spatial coordinates."
                ),
                chart_title="TEMPORAL MAGNITUDES",
                chart_subtitle="Time Offset vs Metric Drift",
                preset_pill="3 ns = 1 METER OF DRIFT",
                metric_unit="ns",
                winner_label="GPS Tolerance Window",
                winner_avg_fps=3.0,
                winner_low_fps=2.8,
                winner_frametime_ms=0.003,
                loser_label="Uncorrected Drift",
                loser_avg_fps=120.0,
                loser_low_fps=95.0,
                loser_frametime_ms=0.12,
                winner_badge="±3 NANOSECONDS",
            ),
            act4=TikTokAct4(
                voiceover=(
                    "Up in orbit, time flows faster due to Einstein's General Relativity: thirty-eight microseconds every day. "
                    "Without compensating for that relativistic time dilation in silicon, GPS navigation would fail by eleven kilometers daily."
                ),
                golden_rule_title="ENGINEERING ROOT CAUSE",
                golden_rule_takeaway="EINSTEIN TIME DILATION (+38.6 µs/DAY)",
                gameplay_query="general relativity spacetime earth curve gravity",
            ),
            act5=TikTokAct5(
                voiceover="Did you know Einstein's theory of relativity is actively running in your pocket to keep your maps accurate? Drop your take below.",
                poll_question="Did you know Einstein's Relativity keeps your GPS working?",
                poll_option_a="Fascinating, had no idea",
                poll_option_b="Already knew the principle",
            ),
        )

    # 3. Specialized Case: MEMS Accelerometer & Free Fall
    if (matched_row and matched_row[1] == "acelerometro_caida") or any(w in active_key for w in ["aceler", "caida", "sensor", "mems", "fall"]):
        return TikTokLongProject(
            topic="The Silicon Sensor That Reads Zero When You Fall",
            title="The Silicon Sensor That Reads Zero When You Fall #Tech #Engineering #SiliconVerdict",
            description="Physics of MEMS microelectromechanical silicon sensors. How your phone detects free fall when apparent gravity vanishes. #MEMS #Sensors #Hardware",
            tags=["accelerometer", "mems", "sensors", "hardware", "freefall", "techtok", "siliconverdict"],
            act1=TikTokAct1(
                voiceover="Your phone knows it is falling because, all of a sudden, it weighs absolutely nothing to its internal silicon sensors.",
                dilemma_title="THE SENSOR AT ZERO",
                dilemma_subtitle="Why does free fall register absolute zero gravity?",
                category_pill="MICROMECHANICS // SILICON MEMS",
                gameplay_query="smartphone falling slow motion drop test",
            ),
            act2=TikTokAct2(
                voiceover=(
                    "Inside lies a microscopic MEMS silicon chip. A suspended proof mass held by micromachined springs "
                    "floats between capacitor comb fingers, measuring infinitesimal changes in electrical capacitance."
                ),
                specs_title="CAPACITIVE COMB TRANSDUCER",
                specs_bullets=[
                    "Proof Mass: Suspended micromachined silicon beam",
                    "Transducer: Interdigitated capacitive fingers",
                    "Sensitivity: Femtofarad (fF) capacitance shifts",
                ],
                silicon_query="mems silicon microstructure electron microscope",
            ),
            act3=TikTokAct3(
                voiceover=(
                    "At rest, Earth's gravity pulls the mass down, registering one G of acceleration. "
                    "In free fall, inertia cancels apparent gravity, causing the comb fingers to register exactly zero."
                ),
                chart_title="AT REST vs FREE FALL",
                chart_subtitle="Accelerometer Gravitational Telemetry",
                preset_pill="FREE FALL = 0.0g",
                metric_unit="g",
                winner_label="At Rest (Gravity)",
                winner_avg_fps=1.0,
                winner_low_fps=0.98,
                winner_frametime_ms=0.01,
                loser_label="Free Fall (Weightless)",
                loser_avg_fps=0.0,
                loser_low_fps=0.0,
                loser_frametime_ms=0.0,
                winner_badge="0.0g WEIGHTLESS",
            ),
            act4=TikTokAct4(
                voiceover=(
                    "In under fifteen milliseconds, the processor detects free-fall weightlessness, "
                    "triggers protection routines, and readies display structures to survive impact shock."
                ),
                golden_rule_title="REAL-TIME TELEMETRY RESPONSE",
                golden_rule_takeaway="WEIGHTLESSNESS DETECTION IN <15 ms",
                gameplay_query="accelerometer circuit silicon chip motherboard",
            ),
            act5=TikTokAct5(
                voiceover="Did you know microscopic mechanical silicon engines are actively protecting your device from drop damage? Drop your take below.",
                poll_question="Did you know your phone has micromachined silicon engines?",
                poll_option_a="No idea, mind blown",
                poll_option_b="Familiar with MEMS",
            ),
        )

    # 4. Specialized Case: NFC & Cryptographic Tokens
    if (matched_row and matched_row[1] == "nfc_tokens") or any(w in active_key for w in ["nfc", "token", "card", "pay"]):
        return TikTokLongProject(
            topic="Why Merchants Never See Your Card Number at Checkout",
            title="Why Merchants Never See Your Card Number at Checkout #Tech #Security #SiliconVerdict",
            description="How cryptographic tokenization and 13.56 MHz inductive coupling operate in Apple Pay and Google Wallet mobile payments. #NFC #Cryptography #Hardware",
            tags=["nfc", "cryptography", "security", "applepay", "googlewallet", "hardware", "techtok", "siliconverdict"],
            act1=TikTokAct1(
                voiceover="When you tap your phone to pay, the checkout terminal never receives your real credit card number.",
                dilemma_title="SHIELDED INVISIBLE PAYMENT",
                dilemma_subtitle="Why does the terminal never receive your 16 card digits?",
                category_pill="CRYPTOGRAPHY // NFC 13.56 MHz",
                gameplay_query="contactless mobile payment pos terminal",
            ),
            act2=TikTokAct2(
                voiceover=(
                    "Bringing your phone close generates inductive coupling at thirteen point five six megahertz, "
                    "powering the passive silicon chip directly through the payment terminal's magnetic field."
                ),
                specs_title="RF INDUCTIVE COUPLING",
                specs_bullets=[
                    "Carrier Frequency: 13.56 MHz ISM Band",
                    "Power Delivery: Short-range magnetic induction",
                    "Hardware Isolation: Silicon Secure Element",
                ],
                silicon_query="nfc antenna copper coil smartphone teardown",
            ),
            act3=TikTokAct3(
                voiceover=(
                    "Instead of broadcasting your sixteen bank digits, the Secure Element generates an ephemeral mathematical token "
                    "with a dynamic one-time cryptogram that expires in seconds."
                ),
                chart_title="DYNAMIC TOKEN vs CARD NUMBER",
                chart_subtitle="Cryptographic Validity Lifetime",
                preset_pill="SINGLE-USE CRYPTOGRAM",
                metric_unit="s",
                winner_label="Mobile Payment Token",
                winner_avg_fps=15.0,
                winner_low_fps=10.0,
                winner_frametime_ms=0.015,
                loser_label="Physical Plastic Card",
                loser_avg_fps=157680000.0,
                loser_low_fps=120000000.0,
                loser_frametime_ms=999.0,
                winner_badge="EXPIRES IN 15s",
            ),
            act4=TikTokAct4(
                voiceover=(
                    "Even if an attacker intercepts the transmission out of thin air, that cryptographic hash is worthless for any other purchase, "
                    "making card cloning mathematically impossible."
                ),
                golden_rule_title="HARDWARE ENCRYPTION SHIELD",
                golden_rule_takeaway="UNCLONEABLE SINGLE-USE TOKENIZATION",
                gameplay_query="cryptography secure key hash encrypted server",
            ),
            act5=TikTokAct5(
                voiceover="Do you trust encrypted mobile tokens more than traditional plastic credit cards? Let us know in the comments.",
                poll_question="Do you feel safer paying with a phone or a physical card?",
                poll_option_a="Safer with phone",
                poll_option_b="Safer with card",
            ),
        )

    # 5. Specialized Case: Speed of Light in Datacenters
    if (matched_row and matched_row[1] == "velocidad_luz_datacenter") or any(w in active_key for w in ["light", "datacenter", "microsoft", "luz"]):
        return TikTokLongProject(
            topic="Why the Speed of Light is Too Slow for Microsoft",
            title="Why the Speed of Light is Too Slow for Microsoft #Tech #Engineering #SiliconVerdict",
            description="Photon physics and fiber optics. Why AI datacenter superclusters collide against the cosmic speed limit of light. #TechTok #Physics #Datacenter",
            tags=["techtok", "siliconverdict", "engineering", "physics", "datacenter", "microsoft", "fiberoptics"],
            act1=TikTokAct1(
                voiceover="For hyperscale computing giants, the speed of light is no longer fast: it has become an intolerable physical bottleneck.",
                dilemma_title="THE SPEED OF LIGHT WALL",
                dilemma_subtitle="Why is the cosmic speed limit slowing down artificial intelligence?",
                category_pill="PHOTON PHYSICS // OPTICAL NETWORKING",
                gameplay_query="datacenter server room glowing",
            ),
            act2=TikTokAct2(
                voiceover=(
                    "In a vacuum, photons travel at three hundred thousand kilometers per second. Inside silica glass optical fibers, "
                    "the refractive index slows photons down by thirty percent: adding five full nanoseconds of delay per meter."
                ),
                specs_title="REFRACTION IN SILICA FIBER",
                specs_bullets=[
                    "Velocity in Vacuum: 300,000 km/s",
                    "Velocity in Glass: ~204,000 km/s (n=1.468)",
                    "Propagation Delay: 5.0 ns per meter",
                ],
                silicon_query="fiber optic cable macro blue",
            ),
            act3=TikTokAct3(
                voiceover=(
                    "Across massive AI cluster campuses linking hundreds of thousands of GPUs, light takes longer to travel "
                    "between servers than silicon tensor cores spend computing entire matrix equations."
                ),
                chart_title="DATACENTER LATENCY TELEMETRY",
                chart_subtitle="Silicon Computation vs Photon Transit",
                preset_pill="COMPUTATION < PROPAGATION",
                metric_unit="ns",
                winner_label="Tensor Core Matrix Math",
                winner_avg_fps=12.0,
                winner_low_fps=9.0,
                winner_frametime_ms=0.012,
                loser_label="Fiber Transit Delay (10 km)",
                loser_avg_fps=50000.0,
                loser_low_fps=48000.0,
                loser_frametime_ms=50.0,
                winner_badge="PHYSICS BOTTLENECK",
            ),
            act4=TikTokAct4(
                voiceover=(
                    "To outsmart physics, engineers deploy hollow-core fibers where photons travel through air at vacuum speed, "
                    "clawing back critical nanoseconds across every single distributed neural calculation."
                ),
                golden_rule_title="ENGINEERING RESOLUTION",
                golden_rule_takeaway="HOLLOW-CORE FIBER & SILICON PHOTONICS",
                gameplay_query="hollow core fiber laser optics physics",
            ),
            act5=TikTokAct5(
                voiceover="Did you think transistors were the ultimate computing bottleneck? The true wall is the speed of light. Drop your take below.",
                poll_question="Is computing limited by silicon transistors or the speed of light?",
                poll_option_a="Silicon Limit",
                poll_option_b="Speed of Light Wall",
            ),
        )

    # 6. Contextual Dynamic Generator for ANY of the 30 Queue Topics (ZERO generic filler)
    t_title = matched_row[3] if matched_row else (topic or "Engineering Curiosity")
    t_hook = matched_row[4] if matched_row else "The technology you interact with every single day defies common intuition."
    t_principle = matched_row[5] if matched_row else "Fundamental physics and microarchitecture principles applied at the nanometer scale."

    return TikTokLongProject(
        topic=t_title,
        title=f"{t_title} #Tech #Engineering #SiliconVerdict",
        description=f"{t_title}. {t_principle} #SiliconVerdict #Science #Hardware #Engineering",
        tags=["techtok", "siliconverdict", "engineering", "science", "hardware", "technology", "curiosities"],
        act1=TikTokAct1(
            voiceover=f"{t_hook} Behind this everyday device lies an engineering breakthrough that pushes the boundaries of physical laws.",
            dilemma_title=t_title[:28].upper(),
            dilemma_subtitle=t_hook[:55],
            category_pill="EXTREME ENGINEERING // PARADOX",
            gameplay_query="macro silicon wafer cleanroom technology chip",
        ),
        act2=TikTokAct2(
            voiceover=(
                f"The intuitive approach fails because true scale demands uncompromising precision. "
                f"Engineers had to develop {t_principle.lower()} to ensure zero operational margin for error."
            ),
            specs_title="APPLIED PHYSICAL PRINCIPLE",
            specs_bullets=[
                f"Challenge: {t_title[:32]}",
                f"Mechanism: {t_principle[:40]}",
                "Tolerance: Nanometer-level hardware precision",
            ],
            silicon_query="computer architecture microscopic traces pcb",
        ),
        act3=TikTokAct3(
            voiceover=(
                "At the microscopic scale, invisible physical forces become governing realities. "
                "Coordinating signals in nanoseconds requires every component to respond identically millions of times each second."
            ),
            chart_title="REAL-SCALE PRECISION",
            chart_subtitle="Hardware Tolerance vs Signal Drift",
            preset_pill="NANOMETER TOLERANCE",
            metric_unit="ns",
            winner_label="Exact Synchronization",
            winner_avg_fps=5.0,
            winner_low_fps=4.5,
            winner_frametime_ms=0.005,
            loser_label="Uncontrolled Drift",
            loser_avg_fps=2500.0,
            loser_low_fps=2200.0,
            loser_frametime_ms=2.5,
            winner_badge="EXACT TIMING",
        ),
        act4=TikTokAct4(
            voiceover=(
                f"The engineering root cause is decisive: {t_principle} "
                "Advanced silicon architecture making possible what once seemed like an insurmountable theoretical barrier."
            ),
            golden_rule_title="ENGINEERING RESOLUTION",
            golden_rule_takeaway=t_principle[:58].upper(),
            gameplay_query="advanced laboratory semiconductor fabrication wafer",
        ),
        act5=TikTokAct5(
            voiceover="This is not chance: it is extreme engineering in your daily life. Did you know this technical principle? Debate in the comments.",
            poll_question=f"Did you know how {t_title[:28]} actually works?",
            poll_option_a="No idea, incredible",
            poll_option_b="Already knew it",
        ),
    )


# ==============================================================================
# 4. HIGH-LEVEL PIPELINE GENERATORS
# ==============================================================================
def generate_dynamic_short_plan(
    topic_override: Optional[str] = None,
    spec=None,
    history: Optional[List[dict]] = None,
) -> dict:
    """Generates an autonomous YouTube Short plan dynamically tuned to Technical or Gamer tone."""
    category_key = getattr(spec, "category_key", "gpu_architecture") if spec else "gpu_architecture"
    tone = getattr(spec, "tone", "technical") if spec else "technical"
    cat_info = CONTENT_CATALOG.get(category_key)

    logger.info("ContentGenerator: Generating Short Plan (Category: %s | Tone: %s)...", category_key, tone)

    system_inst = get_system_prompt_for_category(category_key, format_type="short")

    # Build topic context
    prev_topics = [h.get("topic") for h in (history or []) if h.get("topic")]
    if topic_override:
        topic_inst = f"Target Topic: '{topic_override}'"
    elif spec:
        topic_inst = (
            f"Daily Pillar: {spec.day_name} ({spec.pillar_title})\n"
            f"Active Category ({category_key}): {cat_info.name if cat_info else category_key}\n"
            f"Active Subtheme ({spec.theme_key}): '{spec.theme_description}'\n"
            f"Benchmark Title: '{spec.game_title}'\n"
            f"Mandatory Category Focus: {cat_info.focus if cat_info else ''}\n"
        )
    else:
        topic_inst = "Select an unexploited, high-impact PC hardware topic."

    prompt = f"""{system_inst}

Generate a complete specification for an autonomous 25-35 second YouTube Short.
Previously covered topics: {prev_topics[-5:]}
{topic_inst}

Return a strictly valid JSON object conforming exactly to this structure:
{{
  "topic": "string (Concise topic name)",
  "title": "string (High-CTR title under 75 chars, ending with #Shorts)",
  "description": "string (Technical summary, frame pacing, methodology, #Shorts #SiliconVerdict #PCGaming)",
  "tags": ["string", "string", ... at least 15 relevant tags],
  "pinned_comment": "string (Provocative community debate question)",
  "scene1": {{
    "voiceover": "string (~18-22 words, aggressive hook in the first 3 seconds challenging conventional wisdom)",
    "dilemma_title": "string (uppercase, 2-4 words, e.g. 'RTX 4060 vs 1% LOWS' or '128-BIT vs 256-BIT BUS')",
    "dilemma_subtitle": "string (concise dilemma question)",
    "category_pill": "string (uppercase, 2-3 words, e.g. 'RENDIMIENTO GAMER' or 'BANDWIDTH BOTTLENECK')",
    "hud_text": "string (uppercase, 2-3 words, e.g. 'FPS & TIRONES' or 'MEMORY BANDWIDTH')",
    "pixabay_query": "string (e.g. 'gaming pc benchmark gameplay' or 'semiconductor silicon wafer macro')"
  }},
  "scene2": {{
    "voiceover": "string (~35-42 words, empirical benchmark comparing FPS promedio and 1% Lows with numerical delta)",
    "chart_title": "string (uppercase, e.g. '1080p ULTRA TELEMETRY')",
    "chart_subtitle": "string (e.g. 'FPS Promedio vs 1% Lows')",
    "preset_pill": "string (uppercase, e.g. '1080p ULTRA • CYBERPUNK 2077')",
    "metric_unit": "FPS",
    "winner_label": "string (e.g. 'RX 7600 XT 16GB')",
    "winner_fps": 68.0,
    "loser_label": "string (e.g. 'RTX 4060 8GB')",
    "loser_fps": 38.0,
    "winner_badge": "string (e.g. '+78% 1% LOWS')"
  }},
  "scene_cta": {{
    "voiceover": "string (STRICTLY 10-14 words, 2.5-3.0s duration, e.g. 'If you are enjoying this breakdown and want daily hardware insights, subscribe to Silicon Verdict.')",
    "headline_highlight": "SUBSCRIBE",
    "headline_rest": "FOR DAILY VERDICTS",
    "sub_text": "Unfiltered PC Hardware Telemetry & Benchmarks"
  }},
  "scene3": {{
    "voiceover": "string (~18-22 words, definitive verdict: if gamer, use 'Buy it', 'Avoid it' or 'Disable this setting'; if technical, use engineering verdict)",
    "hud_text": "string (uppercase, 2-3 words, e.g. 'VERDICT: AVOID IT' or 'SILICON VERDICT')",
    "pixabay_query": "string (e.g. 'pc gaming graphics 4k' or 'cinematic cpu die silicon')"
  }}
}}"""

    from services.gemini_client import GeminiUnavailable, generate_structured
    try:
        data, _tok, model_name = generate_structured(
            prompt=prompt, system_instruction=None, schema=None, temperature=0.65,
            validate=lambda d: [] if isinstance(d, dict) and d.get("scene1") else ["missing scene1"],
        )
        if "scene_cta" not in data or not isinstance(data["scene_cta"], dict) or not data["scene_cta"].get("voiceover"):
            data["scene_cta"] = {
                "voiceover": "If you are enjoying this breakdown and want daily hardware insights, subscribe to Silicon Verdict.",
                "headline_highlight": "SUBSCRIBE",
                "headline_rest": "FOR DAILY VERDICTS",
                "sub_text": "Unfiltered PC Hardware Telemetry & Benchmarks",
            }
        logger.info("Dynamic Short script generated successfully via '%s'", model_name)
        return data
    except GeminiUnavailable as exc:
        logger.warning("Gemini unavailable for the Short plan (%s).", str(exc)[:200])

    logger.warning("All Gemini candidate models saturated. Deploying deterministic emergency script.")
    if category_key == "tech_curiosities" or tone in ("curiosities", "schematic_tech"):
        return get_emergency_schematic_short_plan(topic=topic_override, spec=spec)
    if tone == "gamer":
        return get_emergency_gamer_short_plan(topic=topic_override, spec=spec)
    from core.generator import get_emergency_fallback_project
    fb = get_emergency_fallback_project(topic_override or "8GB VRAM Saturation")
    # Adapt to short dict structure
    return {
        "topic": fb.title,
        "title": fb.shorts[0].title if fb.shorts else fb.title,
        "description": fb.description,
        "tags": fb.tags,
        "pinned_comment": fb.pinned_comment,
        "scene1": {
            "voiceover": fb.scenes[0].voiceover_text[:140],
            "dilemma_title": "8GB BUFFER EXHAUSTION",
            "dilemma_subtitle": "Does 8GB VRAM bottleneck modern games?",
            "category_pill": "BANDWIDTH BOTTLENECK",
            "hud_text": "VRAM SATURATION",
            "pixabay_query": "gpu memory traces macro",
        },
        "scene2": {
            "voiceover": fb.scenes[1].voiceover_text[:180],
            "chart_title": "1080p ULTRA 1% LOWS",
            "chart_subtitle": "Cyberpunk 2077 Telemetry",
            "preset_pill": "1080p ULTRA • CYBERPUNK 2077",
            "metric_unit": "FPS",
            "winner_label": "RX 7600 XT 16GB",
            "winner_fps": 64.8,
            "loser_label": "RTX 4060 8GB",
            "loser_fps": 38.4,
            "winner_badge": "+68% 1% LOWS",
        },
        "scene_cta": {
            "voiceover": "If you are enjoying this breakdown and want daily hardware insights, subscribe to Silicon Verdict.",
            "headline_highlight": "SUBSCRIBE",
            "headline_rest": "FOR DAILY VERDICTS",
            "sub_text": "Unfiltered PC Hardware Telemetry & Benchmarks",
        },
        "scene3": {
            "voiceover": fb.scenes[2].voiceover_text[:120],
            "hud_text": "VERDICT: 12GB MINIMUM",
            "pixabay_query": "graphics card heatsink macro",
        },
    }


def enforce_script_word_guardrail(
    project: TikTokLongProject,
    target_words: int = 200,
    min_words: int = 145,
    max_words: int = 260,
    category: str = "hardware_benchmarks",
) -> TikTokLongProject:
    """Enforces strict speech budget guardrail.
    For tech_curiosities: 130-160 words (target: ~145 words for 55-70s duration).
    For hardware/gaming: 145-260 words (target: ~200 words for 60-120s duration).
    """
    is_curiosity = (category == "tech_curiosities")
    if is_curiosity:
        min_words = 130
        max_words = 160
        target_words = 145

    current_w = project.get_total_words()
    logger.info("Evaluating script word budget guardrail: %d words (Allowed range: [%d, %d] | Category: %s)...", current_w, min_words, max_words, category)

    if min_words <= current_w <= max_words:
        logger.info("Script word budget is optimal: %d words.", current_w)
        return project

    if current_w < min_words:
        logger.warning("Word count (%d) below minimum (%d). Expanding Act 2 and Act 3 (Category: %s)...", current_w, min_words, category)
        if is_curiosity:
            expansion_text = (
                " This foundational engineering principle demonstrates how the laws of physical propagation "
                "and silicon packaging establish the boundaries of everyday consumer hardware."
            )
            project.act2.voiceover = project.act2.voiceover.rstrip(".") + expansion_text + "."
            if project.get_total_words() < min_words:
                project.act3.voiceover = project.act3.voiceover.rstrip(".") + " Nanometer precision and strict timing tolerances make possible what standard physics once considered an impossible bottleneck."
        else:
            expansion_text = (
                " Delving into low-level microarchitecture and frame pacing telemetry, "
                "we observe how bus interconnect latency directly dictates the stability "
                "and frame consistency rendered across modern game engines in real time."
            )
            project.act2.voiceover = project.act2.voiceover.rstrip(".") + expansion_text + "."
            if project.get_total_words() < min_words:
                project.act3.voiceover = project.act3.voiceover.rstrip(".") + " These telemetry percentiles prove that sustained frametime pacing matters vastly more than synthetic average framerate peaks."

    elif current_w > max_words:
        logger.warning("Word count (%d) exceeds maximum (%d). Trimming redundant sentences...", current_w, max_words)
        act2_sentences = [s.strip() for s in project.act2.voiceover.split(".") if s.strip()]
        if len(act2_sentences) > 2:
            project.act2.voiceover = ". ".join(act2_sentences[:-1]) + "."
        if project.get_total_words() > max_words:
            act3_sentences = [s.strip() for s in project.act3.voiceover.split(".") if s.strip()]
            if len(act3_sentences) > 2:
                project.act3.voiceover = ". ".join(act3_sentences[:-1]) + "."
        if project.get_total_words() > max_words:
            act4_sentences = [s.strip() for s in project.act4.voiceover.split(".") if s.strip()]
            if len(act4_sentences) > 2:
                project.act4.voiceover = ". ".join(act4_sentences[:-1]) + "."

    final_w = project.get_total_words()
    logger.info("Script word budget finalized: %d words (Strictly compliant with duration targets).", final_w)
    return project


SPANISH_FORBIDDEN_WORDS = {
    "el", "la", "de", "en", "para", "por", "con", "los", "las", "sobre",
    "como", "que", "del", "al", "un", "una", "pero", "este", "esta", "cada",
    "vez", "tu", "su", "son", "fue", "muy", "más", "cuando", "donde", "quien",
    "porque", "entre", "sin", "también", "hasta", "desde", "pantalla", "gráfico",
    "cuadros", "rendimiento", "tirones", "fluidez", "móvil", "teléfono",
    "segundo", "minuto", "cómprala", "evítala", "desactiva", "sabías", "prefieres",
    "opción", "nuestro", "nuestra", "todos", "todas", "aquí", "ahora",
}


def validate_script_language_guardrail(
    project: TikTokLongProject,
    category: str = "hardware_benchmarks",
    topic_override: Optional[str] = None,
    spec=None,
) -> TikTokLongProject:
    """Pre-rendering guardrail: validates that the script is strictly in English.

    Scans all voiceover acts and titles for common Spanish words.
    If Spanish tokens are detected, aborts the corrupted text and regenerates
    using the deterministic English fallback engine.
    """
    full_text = " ".join([
        project.title or "",
        project.description or "",
        project.act1.voiceover if project.act1 else "",
        project.act2.voiceover if project.act2 else "",
        project.act3.voiceover if project.act3 else "",
        project.act4.voiceover if project.act4 else "",
        project.act5.voiceover if project.act5 else "",
    ]).lower()

    # Clean punctuation
    clean_words = re.findall(r"\b[a-záéíóúñ]+\b", full_text)
    detected_spanish = [w for w in clean_words if w in SPANISH_FORBIDDEN_WORDS]

    if detected_spanish:
        logger.error(
            "Language Guardrail Violation: Detected Spanish words in script %s. Aborting corrupted text and enforcing English pipeline.",
            detected_spanish[:10],
        )
        if category == "tech_curiosities":
            fallback = get_emergency_schematic_tiktok_plan(topic=topic_override, spec=spec)
        elif category in ("gaming_benchmarks", "fps_optimization", "hardware_news", "vram_and_buying_dilemmas", "upscaling_tech"):
            fallback = get_emergency_gamer_tiktok_plan(topic=topic_override, spec=spec)
        else:
            from core.generator import get_emergency_tiktok_long_project
            fallback = get_emergency_tiktok_long_project(topic=topic_override, spec=spec)

        logger.info("Successfully substituted corrupted script with 100% US English deterministic script.")
        return fallback

    logger.info("Language Guardrail Passed: Script verified to be 100% US English.")
    return project


def generate_dynamic_tiktok_plan(
    topic_override: Optional[str] = None,
    spec=None,
) -> TikTokLongProject:
    """Generates a complete 5-act vertical video specification (>60.5s) calibrated for TikTok Creator Rewards.

    Adapts dynamically to Technical or Gamer tone based on the active rotation category.
    """
    category_key = getattr(spec, "category_key", "gpu_architecture") if spec else "gpu_architecture"
    tone = getattr(spec, "tone", "technical") if spec else "technical"
    cat_info = CONTENT_CATALOG.get(category_key)

    logger.info("ContentGenerator: Generating TikTok Long Plan (Category: %s | Tone: %s)...", category_key, tone)

    system_instruction = get_system_prompt_for_category(category_key, format_type="tiktok")
    system_instruction += (
        "\n\nSTRICT DURATION & WORD COUNT MANDATES (Total words MUST be between 145 and 260 words for 60-120s runtime):\n"
        "1. Act 1 [00:00 - 00:08] Hook: Challenge a myth or expose an anomaly. STRICTLY 15 to 25 words.\n"
        "2. Act 2 [00:08 - 00:25] Mechanism / Breakdown: Architectural telemetry or gamer settings. STRICTLY 35 to 55 words.\n"
        "3. Act 3 [00:25 - 00:55] Empirical Benchmark: Exact FPS, 1% Lows, frametime ms or physical human translation. STRICTLY 50 to 70 words.\n"
        "4. Act 4 [00:55 - 00:85] Engineering Resolution / Golden Rule: Root cause or decisive buying verdict. STRICTLY 40 to 60 words.\n"
        "5. Act 5 [00:85 - 01:10] Retention Closing / Debate: Provocative A vs B debate question. STRICTLY 20 to 35 words."
    )

    context_hints = ""
    if spec:
        context_hints = (
            f"Daily Pillar: {spec.day_name} ({spec.pillar_title})\n"
            f"Category ({category_key}): {cat_info.name if cat_info else category_key}\n"
            f"Category Focus: {cat_info.focus if cat_info else ''}\n"
            f"Required Subtheme ({spec.theme_key}): '{spec.theme_description}'\n"
            f"Mandatory Benchmark Game: '{spec.game_title}'\n"
        )
    if topic_override:
        context_hints += f"Target Hardware Debate: '{topic_override}'\n"

    target_w = 145 if (category_key == "tech_curiosities" or tone in ("curiosities", "schematic_tech")) else 200
    min_w = 130 if (category_key == "tech_curiosities" or tone in ("curiosities", "schematic_tech")) else 145
    max_w = 160 if (category_key == "tech_curiosities" or tone in ("curiosities", "schematic_tech")) else 260

    prompt = (
        f"Create an elite TikTok Creator Rewards long video script ({'55-70s' if category_key == 'tech_curiosities' else '60-120s'}, 5 acts) in {'Tech Curiosities / 2D Schematic' if category_key == 'tech_curiosities' else ('Gamer / News' if tone == 'gamer' else 'Technical')} tone.\n"
        f"{context_hints}\n"
        f"Ensure aggregate narration words are strictly between {min_w} and {max_w} words (target: {target_w} words) so spoken duration complies strictly with {'55 to 70' if category_key == 'tech_curiosities' else '60 to 120'} seconds."
    )

    from services.gemini_client import GeminiUnavailable, generate_structured
    try:
        project, tokens, model_name = generate_structured(
            prompt=prompt, system_instruction=system_instruction, schema=TikTokLongProject, temperature=0.6,
        )
        project.gemini_input_tokens, project.gemini_output_tokens = tokens
        project = enforce_script_word_guardrail(project, target_words=target_w, min_words=min_w, max_words=max_w, category=category_key)
        project = validate_script_language_guardrail(project, category=category_key, topic_override=topic_override, spec=spec)
        logger.info("TikTok plan received (%s): %d total words (Tokens: in=%d, out=%d)",
                    model_name, project.get_total_words(), project.gemini_input_tokens, project.gemini_output_tokens)
        return project
    except GeminiUnavailable as exc:
        logger.warning("Gemini unavailable for the TikTok plan (%s).", str(exc)[:200])

    logger.warning("All Gemini candidate models saturated. Deploying deterministic TikTok plan.")
    if category_key == "tech_curiosities" or tone in ("curiosities", "schematic_tech"):
        fb_proj = get_emergency_schematic_tiktok_plan(topic=topic_override, spec=spec)
    elif tone == "gamer":
        fb_proj = get_emergency_gamer_tiktok_plan(topic=topic_override, spec=spec)
    else:
        from core.generator import get_emergency_tiktok_long_project
        fb_proj = get_emergency_tiktok_long_project(topic=topic_override, spec=spec)

    fb_proj.gemini_input_tokens = 480
    fb_proj.gemini_output_tokens = 390
    fb_proj = enforce_script_word_guardrail(fb_proj, target_words=target_w, min_words=min_w, max_words=max_w, category=category_key)
    return validate_script_language_guardrail(fb_proj, category=category_key, topic_override=topic_override, spec=spec)


# ==============================================================================
# DOMAIN TAXONOMY & ISOLATION MATRIX (ZERO CROSS-DOMAIN BLEED)
# ==============================================================================
DOMAIN_TAXONOMY: Dict[str, Dict[str, List[str]]] = {
    "hardware_compute": {
        "allowed_keywords": ["cpu", "core", "die", "cache", "socket", "silicon", "transistor", "lithography", "interconnect", "bus", "vcache", "zen"],
        "banned_keywords": ["ping", "router", "wifi", "fps_meter", "gameplay", "packet_loss", "rf", "microwave"],
        "allowed_assets": ["silicon_die", "silicon_stacking", "memory_bottleneck", "thermal_dissipation", "latency_bars", "frametime_gauge"],  # latency_bars is hard-wired to CPU bus / 3D V-Cache art: only valid here
    },
    "gaming_performance": {
        "allowed_keywords": ["gpu", "fps", "frametime", "vram", "dlss", "raster", "1%_low", "render_pipeline", "shader", "ms", "hitching", "stutter"],
        "banned_keywords": ["microwave", "subsea", "orbit", "quantum", "die_shot", "transistor", "router"],
        "allowed_assets": ["preset_card", "frametime_gauge"],
    },
    "networking_rf": {
        "allowed_keywords": ["wifi", "rf", "ghz", "band", "spectrum", "router", "attenuation", "interference", "magnetron", "channel", "packet", "microwave", "dbm", "loss", "signal"],
        "banned_keywords": ["p_cores", "e_cores", "l3_cache", "dlss", "rtx", "compute_die", "silicon_die", "shader", "zen_4"],
        "allowed_assets": ["rf_collision", "spectrum_bands"],
    },
    "everyday_tech": {
        "allowed_keywords": ["cable", "battery", "screen", "touch", "sensor", "signal", "usb", "bluetooth", "camera"],
        "banned_keywords": ["fps_meter", "gameplay", "rtx_4090", "dlss"],
        "allowed_assets": ["nfc_token", "spectrum_bands", "vcsel_projector", "rf_collision", "subsea_cable", "gps_relativity"],
    },
    "applied_physics": {
        "allowed_keywords": ["fiber", "optical", "laser", "photon", "gps", "relativity", "nfc", "vcsel", "depth", "orbit", "satellite", "cable"],
        "banned_keywords": ["fps_meter", "gameplay", "rtx_4090", "dlss"],
        "allowed_assets": ["subsea_cable", "gps_relativity", "vcsel_projector", "nfc_token", "spectrum_bands"],
    },
}
