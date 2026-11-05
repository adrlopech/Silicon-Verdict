"""Weekly thematic pillars and game pools for Silicon Verdict.

Defines the 6-day balanced rotation matrix alternating evenly among the 3 pillars:
1. Hardware Benchmarks & Silicon (Technical / Liquid Glass) - Days 1 & 4
2. Gaming & Optimization (Gamer / Liquid Glass) - Days 2 & 5
3. Tech Curiosities & Infrastructure (Curiosities / Schematic Tech) - Days 3 & 6
"""
from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class DayPillar:
    """Represents the thematic pillar, game pool, and categories for a specific weekday."""
    weekday: int  # 0=Monday .. 5=Saturday
    day_name: str
    pillar_title: str
    theme_a: str
    theme_b: str
    games: List[str]
    pillar_type: str = "technical"  # "technical", "gamer", or "curiosities"
    theme_a_category: str = ""
    theme_b_category: str = ""
    preset: str = "liquid_glass"   # "liquid_glass" or "schematic_tech"


WEEKLY_PILLARS: Dict[int, DayPillar] = {
    0: DayPillar(
        weekday=0,
        day_name="Monday",
        pillar_title="Hardware Benchmarks & Silicon",
        pillar_type="technical",
        preset="liquid_glass",
        theme_a_category="gpu_architecture",
        theme_a="GPU vs GPU architectural rendering pipelines and rasterization efficiency",
        theme_b_category="silicon_deep_dive",
        theme_b="Silicon lithography, transistor density, and W/mm2 thermal dissipation",
        games=[
            "Cyberpunk 2077",
            "Alan Wake 2",
            "The Last of Us Part I",
            "Hogwarts Legacy",
            "Avatar: Frontiers of Pandora",
            "Forza Horizon 5",
        ],
    ),
    1: DayPillar(
        weekday=1,
        day_name="Tuesday",
        pillar_title="Gaming & Optimization",
        pillar_type="gamer",
        preset="liquid_glass",
        theme_a_category="gaming_benchmarks",
        theme_a="Popular GPU performance (RTX 4060, RX 6600) in current AAA titles",
        theme_b_category="fps_optimization",
        theme_b="Graphics settings that crush 1% lows and how to recover 20-35 FPS",
        games=[
            "Black Myth: Wukong",
            "Counter-Strike 2",
            "Helldivers 2",
            "S.T.A.L.K.E.R. 2",
            "Cyberpunk 2077",
            "Call of Duty: Warzone",
        ],
    ),
    2: DayPillar(
        weekday=2,
        day_name="Wednesday",
        pillar_title="Tech Curiosities & Infrastructure",
        pillar_type="curiosities",
        preset="schematic_tech",
        theme_a_category="tech_curiosities",
        theme_a="Speed of light in AI datacenters: why physics is the ultimate network bottleneck",
        theme_b_category="tech_curiosities",
        theme_b="Subsea transoceanic fiber cables: the optical backbone powering the globe",
        games=[
            "Microsoft Project Natick",
            "Subsea Fiber Infrastructure",
            "Hyperscale Cloud Datacenters",
            "Hollow Core Optical Fiber",
            "Global Network Topology",
            "ASML EUV Photolithography",
        ],
    ),
    3: DayPillar(
        weekday=3,
        day_name="Thursday",
        pillar_title="Hardware Benchmarks & Silicon",
        pillar_type="technical",
        preset="liquid_glass",
        theme_a_category="memory_buses",
        theme_a="Bus widths (128-bit vs 256-bit), DDR4 vs DDR5 nanosecond true latency",
        theme_b_category="storage_pcie",
        theme_b="PCIe x8 vs x16 lanes, Gen4/Gen5 bus saturation, and DirectStorage streaming",
        games=[
            "Spider-Man Remastered",
            "Ratchet & Clank: Rift Apart",
            "Returnal",
            "Forza Horizon 5",
            "Horizon Forbidden West",
            "Star Wars Jedi: Survivor",
        ],
    ),
    4: DayPillar(
        weekday=4,
        day_name="Friday",
        pillar_title="Gaming & Optimization",
        pillar_type="gamer",
        preset="liquid_glass",
        theme_a_category="hardware_news",
        theme_a="Hardware alerts and urgent driver updates: performance regressions and fixes",
        theme_b_category="vram_and_buying_dilemmas",
        theme_b="VRAM buying dilemmas: why 8GB frame buffers choke modern 1440p gaming",
        games=[
            "Baldur's Gate 3",
            "Microsoft Flight Simulator",
            "Dragon's Dogma 2",
            "Starfield",
            "Red Dead Redemption 2",
            "The Witcher 3: Wild Hunt",
        ],
    ),
    5: DayPillar(
        weekday=5,
        day_name="Saturday",
        pillar_title="Tech Curiosities & Infrastructure",
        pillar_type="curiosities",
        preset="schematic_tech",
        theme_a_category="tech_curiosities",
        theme_a="ASML EUV lithography: picometer mirror precision shaping modern microchips",
        theme_b_category="tech_curiosities",
        theme_b="Submerged two-phase immersion cooling and silicon physical clock barriers",
        games=[
            "ASML High-NA EUV",
            "Immersion Cooling Datacenters",
            "TSMC N2 GAA Transistors",
            "NVIDIA DGX SuperPOD",
            "Silicon Photonics Interconnects",
            "Silicon Thermal Limits",
        ],
    ),
}


def get_pillar_for_weekday(weekday: int) -> DayPillar:
    """Returns the DayPillar for a weekday index (0=Monday .. 5=Saturday).

    If Sunday (6) or out of range, maps cleanly via modulo 6.
    """
    normalized = int(weekday) % 6
    return WEEKLY_PILLARS[normalized]


def get_theme_description(weekday: int, theme_key: str) -> str:
    """Returns the textual theme description for a given weekday and theme key."""
    pillar = get_pillar_for_weekday(weekday)
    if theme_key == "theme_b":
        return pillar.theme_b
    return pillar.theme_a


def get_category_for_theme(weekday: int, theme_key: str) -> str:
    """Returns the category key (e.g. 'gaming_benchmarks', 'tech_curiosities') for a given weekday and theme key."""
    pillar = get_pillar_for_weekday(weekday)
    if theme_key == "theme_b":
        return pillar.theme_b_category
    return pillar.theme_a_category


def get_tone_for_weekday(weekday: int) -> str:
    """Returns 'technical', 'gamer', or 'curiosities' tone according to the pillar type for the weekday."""
    pillar = get_pillar_for_weekday(weekday)
    return pillar.pillar_type


def get_preset_for_weekday(weekday: int) -> str:
    """Returns 'liquid_glass' or 'schematic_tech' according to the visual preset configured for the day."""
    pillar = get_pillar_for_weekday(weekday)
    return pillar.preset
