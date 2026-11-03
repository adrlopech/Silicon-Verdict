"""Weekly thematic pillars and game pools for Silicon Verdict.

Defines the Monday-to-Friday matrix (0=Lunes to 4=Viernes) with 2 alternating
subthemes (theme_a, theme_b) and a curated pool of 6 benchmark titles per day.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class DayPillar:
    """Represents the technical pillar and game pool for a specific weekday."""
    weekday: int  # 0=Lunes .. 4=Viernes
    day_name: str
    pillar_title: str
    theme_a: str
    theme_b: str
    games: List[str]


WEEKLY_PILLARS: Dict[int, DayPillar] = {
    0: DayPillar(
        weekday=0,
        day_name="Lunes",
        pillar_title="GPU & Render",
        theme_a="VRAM, ancho de bus (128 vs 256 bits) y paginación PCIe",
        theme_b="Reconstrucción (DLSS/FSR) y penalización de latencia en Frame Gen",
        games=[
            "The Last of Us Part I",
            "Hogwarts Legacy",
            "Cyberpunk 2077",
            "Alan Wake 2",
            "Avatar",
            "Forza Horizon 5",
        ],
    ),
    1: DayPillar(
        weekday=1,
        day_name="Martes",
        pillar_title="CPU & Silicio",
        theme_a="3D V-Cache vs GHz brutos y consistencia en 1% Lows",
        theme_b="Escalado multihilo y asignación en núcleos híbridos (P/E-Cores)",
        games=[
            "Baldur's Gate 3",
            "MS Flight Simulator",
            "Counter-Strike 2",
            "Starfield",
            "Dragon's Dogma 2",
            "Total War",
        ],
    ),
    2: DayPillar(
        weekday=2,
        day_name="Miércoles",
        pillar_title="Memorias & Buses",
        theme_a="DDR4 optimizada vs DDR5 (MT/s vs latencia real en nanosegundos)",
        theme_b="Líneas PCIe x8 vs x16 y transferencias DirectStorage",
        games=[
            "Spider-Man Remastered",
            "Ratchet & Clank",
            "Returnal",
            "Forza Horizon 5",
            "Horizon Forbidden West",
            "Star Wars Jedi",
        ],
    ),
    3: DayPillar(
        weekday=3,
        day_name="Jueves",
        pillar_title="Eficiencia & Bottlenecks",
        theme_a="Thermal Throttling, curvas de undervolt y consumo real en W vs TDP",
        theme_b="Diagnóstico empírico de cuello de botella (prueba a 720p)",
        games=[
            "Black Myth: Wukong",
            "S.T.A.L.K.E.R. 2",
            "Cyberpunk 2077",
            "The Witcher 3",
            "Helldivers 2",
            "RDR2",
        ],
    ),
    4: DayPillar(
        weekday=4,
        day_name="Viernes",
        pillar_title="Generaciones & Mercado",
        theme_a="Comparativas generacionales (GPU legendaria vs moderna de entrada)",
        theme_b="Ratio FPS por euro y mercado de ocasión",
        games=[
            "Doom Eternal",
            "Warzone",
            "Apex Legends",
            "Fortnite",
            "Rainbow Six Siege",
            "Tomb Raider",
        ],
    ),
}


def get_pillar_for_weekday(weekday: int) -> DayPillar:
    """Returns the DayPillar for a weekday index (0=Lunes .. 4=Viernes).

    If weekend (5, 6), defaults to Monday (0) or clamps to Friday (4).
    """
    normalized = max(0, min(weekday, 4))
    return WEEKLY_PILLARS[normalized]


def get_theme_description(weekday: int, theme_key: str) -> str:
    """Returns the textual theme description for a given weekday and theme key."""
    pillar = get_pillar_for_weekday(weekday)
    if theme_key == "theme_b":
        return pillar.theme_b
    return pillar.theme_a
