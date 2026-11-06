"""Database storage and query service for Silicon Verdict short production history.

Stores historical production telemetry in SQLite (data/history.db) tracking:
- weekday_index (INTEGER: 0=Lunes to 4=Viernes)
- theme_key (TEXT: 'theme_a' or 'theme_b')
- game_title (TEXT: benchmark title)
- voice_id_used (TEXT: ElevenLabs voice ID)
- topic, title, video_id, created_at
"""
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = settings.BASE_DIR / "data" / "history.db"


class _ClosingConnection(sqlite3.Connection):
    """sqlite3 only commits/rolls back at the end of a `with` block and leaves the connection open; this one also closes it."""

    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Returns a connection to the SQLite history database, creating directories if needed.
    Use it as `with get_db_connection() as conn:` - the transaction is committed and the connection closed on exit."""
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30, factory=_ClosingConnection)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> Path:
    """Initializes the database schema if it doesn't already exist."""
    path = db_path or DEFAULT_DB_PATH
    with get_db_connection(path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shorts_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                weekday_index INTEGER NOT NULL,
                theme_key TEXT NOT NULL,
                game_title TEXT NOT NULL,
                voice_id_used TEXT NOT NULL,
                topic TEXT,
                title TEXT,
                video_id TEXT,
                created_at TEXT NOT NULL,
                category TEXT DEFAULT '',
                tone TEXT DEFAULT 'technical'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tiktok_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                publish_id TEXT NOT NULL,
                title TEXT,
                file_path TEXT,
                privacy_level TEXT,
                status TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS content_catalog (
                category_key TEXT PRIMARY KEY,
                category_name TEXT NOT NULL,
                category_type TEXT NOT NULL,
                premise TEXT NOT NULL,
                focus TEXT NOT NULL,
                mandatory_terms TEXT,
                sample_hardware TEXT,
                sample_topics TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rotation_matrix (
                day_number INTEGER PRIMARY KEY,
                day_name TEXT NOT NULL,
                pillar_title TEXT NOT NULL,
                pillar_type TEXT NOT NULL,
                theme_a_category TEXT NOT NULL,
                theme_a_desc TEXT NOT NULL,
                theme_b_category TEXT NOT NULL,
                theme_b_desc TEXT NOT NULL,
                games_pool TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS topics_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_key TEXT UNIQUE NOT NULL,
                block TEXT NOT NULL,
                title TEXT NOT NULL,
                hook TEXT NOT NULL,
                principle TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'tech_curiosities',
                order_index INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                produced_at TEXT,
                video_id TEXT,
                created_at TEXT NOT NULL
            )
        """)
        # Ensure schema migrations for existing topics_queue table
        cursor_tq = conn.execute("PRAGMA table_info(topics_queue)")
        existing_tq_cols = [r[1] for r in cursor_tq.fetchall()]
        if "order_index" not in existing_tq_cols:
            conn.execute("ALTER TABLE topics_queue ADD COLUMN order_index INTEGER DEFAULT 0")
        if "block" not in existing_tq_cols:
            conn.execute("ALTER TABLE topics_queue ADD COLUMN block TEXT DEFAULT ''")
        if "produced_at" not in existing_tq_cols:
            conn.execute("ALTER TABLE topics_queue ADD COLUMN produced_at TEXT")
        if "video_id" not in existing_tq_cols:
            conn.execute("ALTER TABLE topics_queue ADD COLUMN video_id TEXT")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_topics_queue_status ON topics_queue(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_topics_queue_key ON topics_queue(topic_key)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_topics_queue_order ON topics_queue(order_index)")
        # Ensure backwards-compatible columns on existing shorts_history table
        cursor = conn.execute("PRAGMA table_info(shorts_history)")
        existing_cols = [r[1] for r in cursor.fetchall()]
        if "category" not in existing_cols:
            conn.execute("ALTER TABLE shorts_history ADD COLUMN category TEXT DEFAULT ''")
        if "tone" not in existing_cols:
            conn.execute("ALTER TABLE shorts_history ADD COLUMN tone TEXT DEFAULT 'technical'")
        if "preset" not in existing_cols:
            conn.execute("ALTER TABLE shorts_history ADD COLUMN preset TEXT DEFAULT 'liquid_glass'")

        # Ensure preset column on rotation_matrix
        cursor_m = conn.execute("PRAGMA table_info(rotation_matrix)")
        existing_m_cols = [r[1] for r in cursor_m.fetchall()]
        if "preset" not in existing_m_cols:
            conn.execute("ALTER TABLE rotation_matrix ADD COLUMN preset TEXT DEFAULT 'liquid_glass'")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_shorts_history_weekday ON shorts_history(weekday_index)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shorts_history_created_at ON shorts_history(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_posts_publish_id ON tiktok_posts(publish_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_posts_created_at ON tiktok_posts(created_at)")

        # Generation telemetry & token / cost guardrails table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS generation_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                run_id TEXT,
                topic_id TEXT,
                category TEXT,
                gemini_input_tokens INTEGER DEFAULT 0,
                gemini_output_tokens INTEGER DEFAULT 0,
                elevenlabs_characters INTEGER DEFAULT 0,
                estimated_cost_usd REAL DEFAULT 0.0,
                duration_seconds REAL DEFAULT 0.0,
                word_count INTEGER DEFAULT 0
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_gen_metrics_time ON generation_metrics(timestamp)")

        # YouTube Analytics & retention feedback table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analytics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT UNIQUE,
                title TEXT,
                category TEXT,
                theme_key TEXT,
                views INTEGER DEFAULT 0,
                viewer_percentage REAL DEFAULT 0.0,
                avg_view_percentage REAL DEFAULT 0.0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                performance_score REAL DEFAULT 0.0,
                swiped_away_percentage REAL DEFAULT 0.0,
                synced_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_analytics_score ON analytics_history(performance_score)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_analytics_cat ON analytics_history(category)")

        # Seed content catalog and rotation matrix if empty
        _seed_catalog_and_rotation(conn)
        _seed_topics_queue(conn)

        conn.commit()
    logger.debug("History database initialized at: %s", path)
    return path


def _seed_catalog_and_rotation(conn: sqlite3.Connection) -> None:
    """Populates content_catalog and rotation_matrix tables with the 10 categories and 6-day matrix."""
    import json
    now_iso = datetime.now(timezone.utc).isoformat()

    categories_seed = [
        # 5 Low-Level Technical Categories (Silicio, Memoria, Kernel, Redes, Almacenamiento, GPU vs GPU)
        (
            "gpu_architecture",
            "Arquitectura GPU y Render",
            "technical",
            "GPU vs GPU, microarquitectura de render, pipelines de rasterización, transistores, computación shaders.",
            "Telemetría de GPU, microarquitectura, latencia en nanosegundos (ns), rendimiento térmico.",
            json.dumps(["IPC", "nanosegundos", "shader execution", "rasterization pipeline", "silicon telemetry"]),
            json.dumps(["RTX 4090", "RTX 4080 Super", "RX 7900 XTX", "RTX 5080", "RDNA 3 vs Ada Lovelace"]),
            json.dumps(["Ada Lovelace vs RDNA 3 Shader Pipeline Efficiency", "SM Sub-Core Scheduler Saturation at 4K", "Rasterization Bottlenecks in Modern Compute Shaders"]),
            now_iso,
        ),
        (
            "silicon_deep_dive",
            "Silicio, Litografía y Caché",
            "technical",
            "Silicio, litografía (TSMC N4/N3, Intel 20A/18A), packaging 3D, V-Cache, distribución térmica en la pastilla.",
            "Fórmulas de disipación W/mm², densidades de transistores, telemetría de silicio puro y empaquetado térmico.",
            json.dumps(["litografía", "densidad térmica W/mm2", "3D V-Cache", "TjMax", "telemetría de silicio", "nanosegundos"]),
            json.dumps(["Ryzen 7 9800X3D", "Ryzen 7 7800X3D", "Core Ultra 9 285K", "i9-14900KS"]),
            json.dumps(["3D V-Cache vs GHz brutos y consistencia en 1% Lows", "TSMC N4 vs N3 Transistor Density & Voltage Scaling", "Package Junction Hotspots: Heat Dissipation per mm2"]),
            now_iso,
        ),
        (
            "memory_buses",
            "Memorias y Anchos de Bus",
            "technical",
            "Memoria DDR4 optimizada vs DDR5, anchos de bus (128-bit vs 256-bit), GDDR6/6X, subtimings y paginación PCIe.",
            "MT/s vs latencia real en nanosegundos (ns), ancho de banda en GB/s y saturación del bus de memoria.",
            json.dumps(["MT/s vs nanosegundos", "ancho de bus", "subtimings", "latencia CAS", "ancho de banda GDDR6X"]),
            json.dumps(["DDR5-6000 CL30", "DDR4-3600 CL14", "128-bit vs 256-bit GDDR6", "LPDDR5X"]),
            json.dumps(["DDR4 optimizada vs DDR5: Latencia real en nanosegundos", "128-bit vs 256-bit Bus Width Choking 1440p Textures", "GDDR6X Thermal Throttling on Memory Controllers"]),
            now_iso,
        ),
        (
            "kernel_latency",
            "Kernel y Planificación de Hilos",
            "technical",
            "Planificación del kernel de SO, DPC latency, interrupciones hardware, gestión de hilos en arquitecturas híbridas (P/E-Cores).",
            "Microsegundos y nanosegundos de latencia de sistema, context switching, interrupciones IRQ y consistencia de frametimes.",
            json.dumps(["DPC latency", "kernel thread scheduler", "nanosegundos", "context switching", "P/E-Core affinity"]),
            json.dumps(["Intel Thread Director", "Windows Scheduler vs Linux Zen Kernel", "AMD Dual-CCD Core Parking"]),
            json.dumps(["Escalado multihilo y asignación en núcleos híbridos P/E-Cores", "DPC Latency Spikes: How Audio Drivers Destroy 1% Lows", "Timer Resolution & Kernel Thread Interrupts in Competitive Gaming"]),
            now_iso,
        ),
        (
            "storage_pcie",
            "Almacenamiento PCIe y Enlaces",
            "technical",
            "Almacenamiento NVMe PCIe Gen 4 vs Gen 5, líneas PCIe (x8 vs x16), DirectStorage y descompresión por GPU.",
            "Rendimiento de líneas PCIe, IOPS, saturación de carril y descompresión por hardware.",
            json.dumps(["líneas PCIe x8 vs x16", "DirectStorage", "IOPS", "latencia DMA", "saturación de bus"]),
            json.dumps(["PCIe 4.0 x8 on PCIe 3.0 Slot", "PCIe 5.0 NVMe", "DirectStorage GPU Decompression Engine"]),
            json.dumps(["Líneas PCIe x8 vs x16 y transferencias DirectStorage", "PCIe 4.0 x8 GPU in PCIe 3.0 Motherboard Penalty", "NVMe Thermal Throttling during Asset Streaming"]),
            now_iso,
        ),
        (
            "networking_bufferbloat",
            "Redes y Bufferbloat",
            "technical",
            "Redes para gaming competitivo, bufferbloat en routers, colas AQM (CoDel/Cake), jitter de paquetes.",
            "Telemetría de red, latencia RTT bajo carga en ms/ns, micro-congestión de paquetes y tick rates.",
            json.dumps(["bufferbloat", "AQM / CoDel", "latencia RTT", "jitter de paquetes", "tick rate"]),
            json.dumps(["OpenWrt SQM", "Gaming Routers", "2.5GbE Intel I225-V vs Realtek"]),
            json.dumps(["Bufferbloat: Why 1Gbps Fiber Stutters in Ranked Games", "AQM FQ-CoDel vs Default Router Queue Telemetry", "Ethernet Driver Interrupt Moderation & Latency"]),
            now_iso,
        ),

        # 5 New Gamer / News Categories
        (
            "gaming_benchmarks",
            "Gaming Benchmarks (Rendimiento en Juegos del Momento)",
            "gamer",
            "Cómo rinde una tarjeta popular (RTX 4060, RTX 3060, RX 6600, etc.) en los títulos más exigentes o recientes.",
            "FPS promedio, percentiles 1% Low (los tirones molestos), resolución recomendada (1080p/1440p) y veredicto rotundo ('¿Se puede jugar bien o necesitas bajar calidad?').",
            json.dumps(["FPS promedio", "1% Lows (micro-stuttering)", "resolución (1080p/1440p)", "texturas", "fluidez", "Cómprala / Evítala"]),
            json.dumps(["RTX 4060 8GB", "RTX 3060 12GB", "RX 6600 8GB", "RX 7600 XT 16GB", "RTX 4070 Super"]),
            json.dumps(["RTX 4060 en Black Myth Wukong: ¿Aguanta en 1080p?", "RX 6600 en 2026: Rendimiento real en juegos pesados", "RTX 3060 12GB vs RTX 4060 8GB: ¿Cuál rinde mejor hoy?"]),
            now_iso,
        ),
        (
            "hardware_news",
            "Noticias y Alertas Express de Hardware",
            "gamer",
            "Novedades del sector explicadas al grano (nuevas actualizaciones de drivers que mejoran o rompen juegos, requisitos mínimos desorbitados de lanzamientos próximos, polémicas de precios o filtraciones de nueva generación).",
            "Noticia rápida + impacto real para el usuario que va a jugar o actualizar su PC.",
            json.dumps(["FPS promedio", "1% Lows (micro-stuttering)", "resolución (1080p/1440p)", "texturas", "fluidez", "alerta gamer"]),
            json.dumps(["Últimos drivers NVIDIA/AMD", "Nuevos lanzamientos AAA", "Próxima generación de GPUs"]),
            json.dumps(["Alerta Drivers: Esta actualización rompe el rendimiento en tus juegos", "Requisitos insensatos: Este juego exige 16GB de VRAM en mínimo", "Filtración nueva generación: Precios y rendimiento que debes saber"]),
            now_iso,
        ),
        (
            "fps_optimization",
            "Ajustes Gráficos que Roban FPS",
            "gamer",
            "Los 3 ajustes concretos en un juego popular (sombras volumétricas, oclusión ambiental, trazado de rayos puntual) que hunden el rendimiento sin apenas mejora visual.",
            "Guía práctica para aplicar en el menú del juego y ganar entre 20 y 35 FPS gratis.",
            json.dumps(["FPS promedio", "1% Lows (micro-stuttering)", "resolución (1080p/1440p)", "texturas", "fluidez", "Desactiva esto"]),
            json.dumps(["Menús gráficos de juegos AAA", "Sombras volumétricas", "Oclusión ambiental"]),
            json.dumps(["Los 3 ajustes que te están robando 30 FPS en Cyberpunk", "Niebla volumétrica: Apaga esto para ganar 25 FPS gratis", "Ajustes trampa en juegos modernos: Cómo optimizar sin perder calidad"]),
            now_iso,
        ),
        (
            "vram_and_buying_dilemmas",
            "Dilemas de Compra y VRAM",
            "gamer",
            "¿Siguen siendo suficientes 8 GB de VRAM hoy? ¿Vale la pena comprar una GPU de gama media de la generación anterior de segunda mano?",
            "Demostración de tirones cuando se satura la memoria gráfica y recomendación clara de compra.",
            json.dumps(["FPS promedio", "1% Lows (micro-stuttering)", "resolución (1080p/1440p)", "texturas", "fluidez", "Cómprala / Evítala"]),
            json.dumps(["RTX 3070 8GB de segunda mano", "RTX 4060 8GB nueva", "RX 6700 XT 12GB"]),
            json.dumps(["¿Alcanzan 8GB de VRAM en 2026? La prueba definitiva con tirones", "GPU usada de gama anterior vs nueva de entrada: Dónde poner tu dinero", "El engaño de los 8GB: Por qué 12GB es el nuevo mínimo"]),
            now_iso,
        ),
        (
            "upscaling_tech",
            "Tecnologías de Reescalado (DLSS vs FSR vs Nativo)",
            "gamer",
            "Cuándo activar reescalado en modo Calidad te da fluidez sin perder nitidez y en qué casos el reescalado genera artefactos visuales borrosos.",
            "DLSS vs FSR vs Nativo, fluidez sin perder nitidez vs artefactos visuales borrosos.",
            json.dumps(["FPS promedio", "1% Lows (micro-stuttering)", "resolución (1080p/1440p)", "texturas", "fluidez", "modo Calidad"]),
            json.dumps(["NVIDIA DLSS 3.7", "AMD FSR 3.1", "Intel XeSS", "Native TAA"]),
            json.dumps(["DLSS Calidad vs Nativo: Cuándo ganas FPS sin perder nitidez", "FSR en 1080p: El problema de los artefactos borrosos", "Frame Generation: ¿Vale la pena la latencia extra en shooters?"]),
            now_iso,
        ),
        (
            "tech_curiosities",
            "Tech Curiosities & Infraestructura",
            "curiosities",
            "Infraestructura, física de semiconductores, telecomunicaciones y curiosidades de ingeniería a gran escala (estilo 'Tecnología Desmontada').",
            "Premisa paradójica (0-8s), concepto físico/logístico (8-20s), aterrizaje cotidiano y analogía (20-40s), resolución de ingeniería real (40-55s), y punchline rotundo (55-65s).",
            json.dumps(["velocidad de la luz", "nanosegundos", "fibra óptica", "infraestructura", "datacenters", "latencia", "ingeniería", "paradoja"]),
            json.dumps(["Datacenters submarinos (Project Natick)", "Litografía EUV ASML", "Cables submarinos transoceánicos (Marea)", "Supercomputadores DGX SuperPOD"]),
            json.dumps(["Por qué para Microsoft la velocidad de la luz ya es un atasco insoportable", "Cómo cruzan Internet los océanos: Los cables submarinos que sostienen el planeta", "La máquina más compleja de la humanidad: Los espejos imposibles de ASML"]),
            now_iso,
        ),
    ]

    for cat in categories_seed:
        conn.execute("""
            INSERT INTO content_catalog (
                category_key, category_name, category_type, premise, focus,
                mandatory_terms, sample_hardware, sample_topics, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(category_key) DO UPDATE SET
                category_name=excluded.category_name,
                category_type=excluded.category_type,
                premise=excluded.premise,
                focus=excluded.focus,
                mandatory_terms=excluded.mandatory_terms,
                sample_hardware=excluded.sample_hardware,
                sample_topics=excluded.sample_topics
        """, cat)

    # 6-Day Balanced Rotation Matrix across 3 Pillars:
    # 1. Hardware Benchmarks & Silicio (Technical)
    # 2. Gaming & Optimización (Gamer)
    # 3. Tech Curiosities & Infraestructura (Curiosities / Schematic Tech)
    matrix_seed = [
        (
            1, "Lunes", "Hardware Benchmarks & Silicio", "technical", "liquid_glass",
            "gpu_architecture", "GPU vs GPU, microarquitectura de render y pipelines de rasterización",
            "silicon_deep_dive", "Silicio, litografía y empaquetado térmico W/mm2",
            json.dumps(["Cyberpunk 2077", "Alan Wake 2", "The Last of Us Part I", "Hogwarts Legacy", "Avatar", "Forza Horizon 5"]),
        ),
        (
            2, "Martes", "Gaming & Optimización", "gamer", "liquid_glass",
            "gaming_benchmarks", "Rendimiento de GPUs populares (RTX 4060, RX 6600) en juegos del momento",
            "fps_optimization", "Ajustes gráficos que roban FPS (sombras volumétricas, oclusión) para ganar 20-35 FPS",
            json.dumps(["Black Myth: Wukong", "Counter-Strike 2", "Helldivers 2", "S.T.A.L.K.E.R. 2", "Cyberpunk 2077", "Warzone"]),
        ),
        (
            3, "Miércoles", "Tech Curiosities & Infraestructura", "curiosities", "schematic_tech",
            "tech_curiosities", "Velocidad de la luz en datacenters: por qué para Microsoft ya es un atasco insoportable",
            "tech_curiosities", "Cables submarinos y latencia global: la autopista de fibra óptica bajo los océanos",
            json.dumps(["Microsoft Project Natick", "Cables Submarinos Transoceánicos", "Datacenters AWS Azure", "Fibras de Núcleo Hueco", "Topología de Red Global", "ASML EUV Lithography"]),
        ),
        (
            4, "Jueves", "Hardware Benchmarks & Silicio", "technical", "liquid_glass",
            "memory_buses", "Anchos de bus (128 vs 256 bits), DDR4 vs DDR5 y latencia en nanosegundos",
            "storage_pcie", "Líneas PCIe x8 vs x16, saturación Gen4/Gen5 y transferencias DirectStorage",
            json.dumps(["Spider-Man Remastered", "Ratchet & Clank", "Returnal", "Horizon Forbidden West", "Star Wars Jedi", "Forza Horizon 5"]),
        ),
        (
            5, "Viernes", "Gaming & Optimización", "gamer", "liquid_glass",
            "hardware_news", "Noticias y alertas express de hardware (drivers rotos, requisitos desorbitados)",
            "vram_and_buying_dilemmas", "Dilemas de compra y VRAM: ¿Siguen siendo suficientes 8 GB en 2026?",
            json.dumps(["Baldur's Gate 3", "MS Flight Simulator", "Dragon's Dogma 2", "Starfield", "RDR2", "The Witcher 3"]),
        ),
        (
            6, "Sábado", "Tech Curiosities & Infraestructura", "curiosities", "schematic_tech",
            "tech_curiosities", "Litografía EUV de ASML: los espejos imposibles con precisión de un picómetro",
            "tech_curiosities", "Refrigeración por inmersión y límites físicos del silicio a más de 6 GHz",
            json.dumps(["ASML High-NA EUV", "Refrigeración Sumergida", "TSMC N2 Transistores GAA", "Supercomputador DGX", "Fotónica de Silicio", "Límites Térmicos de Silicio"]),
        ),
    ]

    for row in matrix_seed:
        conn.execute("""
            INSERT INTO rotation_matrix (
                day_number, day_name, pillar_title, pillar_type, preset,
                theme_a_category, theme_a_desc, theme_b_category, theme_b_desc, games_pool
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(day_number) DO UPDATE SET
                day_name=excluded.day_name,
                pillar_title=excluded.pillar_title,
                pillar_type=excluded.pillar_type,
                preset=excluded.preset,
                theme_a_category=excluded.theme_a_category,
                theme_a_desc=excluded.theme_a_desc,
                theme_b_category=excluded.theme_b_category,
                theme_b_desc=excluded.theme_b_desc,
                games_pool=excluded.games_pool
        """, row)


def record_short_history(
    weekday_index: int,
    theme_key: str,
    game_title: str,
    voice_id_used: str,
    topic: str = "",
    title: str = "",
    video_id: str = "",
    created_at: Optional[str] = None,
    category: str = "",
    tone: str = "",
    preset: str = "liquid_glass",
    db_path: Optional[Path] = None,
) -> int:
    """Inserts a completed short execution into the history database."""
    init_db(db_path)
    now_iso = created_at or datetime.now(timezone.utc).isoformat()
    with get_db_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO shorts_history (
                weekday_index, theme_key, game_title, voice_id_used, topic, title, video_id, created_at, category, tone, preset
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(weekday_index),
                str(theme_key),
                str(game_title),
                str(voice_id_used),
                str(topic),
                str(title),
                str(video_id),
                str(now_iso),
                str(category),
                str(tone),
                str(preset),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def record_tiktok_post(
    publish_id: str,
    title: str = "",
    file_path: str = "",
    privacy_level: str = "PUBLIC_TO_EVERYONE",
    status: str = "PUBLISH_COMPLETE",
    created_at: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> int:
    """Inserts a completed TikTok upload into the tiktok_posts history table."""
    init_db(db_path)
    now_iso = created_at or datetime.now(timezone.utc).isoformat()
    with get_db_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO tiktok_posts (
                publish_id, title, file_path, privacy_level, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(publish_id),
                str(title),
                str(file_path),
                str(privacy_level),
                str(status),
                str(now_iso),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_last_used_voice(db_path: Optional[Path] = None) -> Optional[str]:
    """Queries the most recently used ElevenLabs voice ID from history."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT voice_id_used FROM shorts_history ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row:
            return str(row["voice_id_used"])
    return None


def get_last_theme_for_weekday(weekday_index: int, db_path: Optional[Path] = None) -> Optional[str]:
    """Queries the last theme_key ('theme_a' or 'theme_b') used for a specific weekday."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT theme_key FROM shorts_history
            WHERE weekday_index = ?
            ORDER BY id DESC LIMIT 1
            """,
            (int(weekday_index),),
        ).fetchone()
        if row:
            return str(row["theme_key"])
    return None


def get_recently_used_games(
    days: int = 14,
    db_path: Optional[Path] = None,
    ref_date: Optional[datetime] = None,
) -> List[str]:
    """Retrieves all distinct game titles used within the specified time window (default: 14 days).

    Args:
        days: Window in days to look back.
        db_path: Optional custom path to SQLite database.
        ref_date: Optional reference datetime for calculation (defaults to current UTC time).
    """
    init_db(db_path)
    base_dt = ref_date or datetime.now(timezone.utc)
    cutoff = (base_dt - timedelta(days=days)).isoformat()

    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT game_title FROM shorts_history
            WHERE created_at >= ?
            ORDER BY created_at DESC
            """,
            (cutoff,),
        ).fetchall()
        return [str(r["game_title"]) for r in rows]


def get_all_history(limit: int = 50, db_path: Optional[Path] = None) -> List[dict]:
    """Fetches the latest recorded short entries."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM shorts_history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_content_catalog(db_path: Optional[Path] = None) -> List[dict]:
    """Retrieves all 10 content categories from content_catalog table in SQLite."""
    import json
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM content_catalog ORDER BY category_type, category_key").fetchall()
        results = []
        for r in rows:
            d = dict(r)
            if d.get("mandatory_terms"):
                try:
                    d["mandatory_terms"] = json.loads(d["mandatory_terms"])
                except Exception:
                    pass
            if d.get("sample_hardware"):
                try:
                    d["sample_hardware"] = json.loads(d["sample_hardware"])
                except Exception:
                    pass
            if d.get("sample_topics"):
                try:
                    d["sample_topics"] = json.loads(d["sample_topics"])
                except Exception:
                    pass
            results.append(d)
        return results


def get_rotation_matrix(db_path: Optional[Path] = None) -> List[dict]:
    """Retrieves the 6-day rotation matrix from rotation_matrix table in SQLite."""
    import json
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM rotation_matrix ORDER BY day_number").fetchall()
        results = []
        for r in rows:
            d = dict(r)
            if d.get("games_pool"):
                try:
                    d["games_pool"] = json.loads(d["games_pool"])
                except Exception:
                    pass
            results.append(d)
        return results


def get_category_info(category_key: str, db_path: Optional[Path] = None) -> Optional[dict]:
    """Fetches details for a single category from the content catalog."""
    import json
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM content_catalog WHERE category_key = ?", (category_key,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        for key in ["mandatory_terms", "sample_hardware", "sample_topics"]:
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except Exception:
                    pass
        return d


# ==============================================================================
# 30 TOPICS QUEUE FOR 'TECH CURIOSITIES' (HIGH-RETENTION TECH STORYTELLING)
# ==============================================================================
TOPICS_QUEUE_SEED = [
    # Block A: Sensors, Security & Everyday Devices
    (1, "gps_relatividad", "Block A: Sensors, Security & Everyday Devices",
     "No Satellite Can See You",
     "Your phone never asks permission from orbit to know where you are standing.",
     "Passive reception of atomic clock timestamps and local triangulation delta computation."),
    (2, "faceid_proyeccion", "Block A: Sensors, Security & Everyday Devices",
     "The 30,000 Invisible Dots of Face ID",
     "Every time you glance at your screen, invisible laser light blankets your face.",
     "Infrared structured relief projection that flat 2D photographs can never spoof."),
    (3, "acelerometro_caida", "Block A: Sensors, Security & Everyday Devices",
     "The Sensor That Reads Zero When You Fall",
     "Your phone detects free fall because its internal sensors suddenly weigh nothing.",
     "Capacitively suspended microstructures (MEMS) entering weightlessness during free fall."),
    (4, "nfc_tokens", "Block A: Sensors, Security & Everyday Devices",
     "Why Merchants Never See Your Card Number at Checkout",
     "You could pay on an infected checkout terminal and your account cannot be cloned.",
     "Single-use cryptographic tokens encrypted locally by the silicon Secure Element."),
    (5, "wifi_microondas", "Block A: Sensors, Security & Everyday Devices",
     "Why Heating Milk Kills Your Wi-Fi Signal",
     "Your wireless router and microwave oven broadcast across the exact same electromagnetic spectrum.",
     "Shared 2.4 GHz unlicensed ISM frequency band and RF wave scattering."),
    (6, "camara_zafiro", "Block A: Sensors, Security & Everyday Devices",
     "The Camera Glass Your Keys Cannot Scratch",
     "Your screen picks up micro-scratches in your pocket, but the camera lens remains immaculate.",
     "Mohs hardness scale: crystalline aluminum oxide sapphire vs ion-strengthened glass."),
    (7, "sensor_proximidad", "Block A: Sensors, Security & Everyday Devices",
     "How Screens Detect When Held to Your Ear",
     "There is no visible cutout on modern displays, yet the screen turns off immediately.",
     "Infrared optical sensors placed beneath active OLED pixels measuring photon bounce."),
    (8, "bateria_apagado_1", "Block A: Sensors, Security & Everyday Devices",
     "Why Phones Shut Down Before Reaching True Zero",
     "Your smartphone is lying when it claims battery capacity has dropped to one percent.",
     "Safe low-voltage cutoff threshold designed to prevent irreversible lithium crystallization."),

    # Block B: Semiconductors, Silicon & Chip Architecture
    (9, "velocidad_luz_datacenter", "Block B: Semiconductors, Silicon & Chip Architecture",
     "Why the Speed of Light is a Bottleneck for AI",
     "Light speed is the fastest barrier in the universe, yet for Microsoft it is too slow.",
     "Tens of thousands of GPUs synchronizing distributed workloads across 5 ms fiber hops."),
    (10, "trampa_nanometros", "Block B: Semiconductors, Silicon & Chip Architecture",
     "The 3-Nanometer Marketing Trap",
     "No physical component inside a 3nm processor actually measures 3 nanometers.",
     "Commercial density naming equivalence versus the actual physical gate length of transistors."),
    (11, "tsmc_amortiguadores", "Block B: Semiconductors, Silicon & Chip Architecture",
     "Chip Fabs Floating on Giant Seismic Dampers",
     "A truck braking 500 meters away can ruin millions of dollars in silicon wafers.",
     "Extreme ultraviolet (EUV) lithography sensitivity to nanometer floor vibrations."),
    (12, "dram_refresco", "Block B: Semiconductors, Silicon & Chip Architecture",
     "Why RAM Constantly Leaks Its Own Memory",
     "Your system memory forgets everything it knows thousands of times every single second.",
     "Sub-microscopic capacitor charge leakage and mandatory periodic refresh cycles (tRFC)."),
    (13, "silicon_lottery", "Block B: Semiconductors, Silicon & Chip Architecture",
     "Why Two Identical Chips Never Perform Alike",
     "You buy the exact same graphics card as your friend, yet theirs clocks higher and consumes less power.",
     "Atomic variance during chemical silicon wafer deposition known as the Silicon Lottery."),
    (14, "branch_prediction", "Block B: Semiconductors, Silicon & Chip Architecture",
     "The Transistor That Predicts the Future",
     "Your CPU executes instructions before you even decide to click and open an app.",
     "Speculative execution and algorithmic branch prediction preventing execution pipeline stalls."),
    (15, "cables_submarinos", "Block B: Semiconductors, Silicon & Chip Architecture",
     "99% of the Internet Fits in a Garden Hose",
     "The cloud does not live in the sky: it is buried beneath the seabed across ocean floors.",
     "Hair-thin optical fiber strands protected by tons of steel armor and tar jackets."),
    (16, "oro_procesadores", "Block B: Semiconductors, Silicon & Chip Architecture",
     "Why Processors Use Gold Over Silver",
     "Processors use gold contact pins even though silver conducts electricity faster.",
     "Immunity to galvanic surface oxidation on critical high-frequency contacts exposed to ambient air."),

    # Block C: Networks, Protocols & Telecommunications
    (17, "curva_fibra_optica", "Block C: Networks, Protocols & Telecommunications",
     "Light Doesn't Turn Corners (Until Inside Fiber)",
     "Light rays travel in straight lines, yet your fiber optic patch cable wraps around corners.",
     "Total internal reflection between the silica core and lower refractive index cladding."),
    (18, "bufferbloat", "Block C: Networks, Protocols & Telecommunications",
     "Why 1 Gbps Fiber Still Suffers From Lag",
     "You pay for gigabit fiber and your online competitive matches still stutter and spike.",
     "Oversized buffer queues inside home routers delaying time-critical gaming packets."),
    (19, "ntp_segundo_intercalar", "Block C: Networks, Protocols & Telecommunications",
     "The Atomic Clock Synchronizing the Internet",
     "If global servers drifted by just one single second, global financial networks would collapse.",
     "Network Time Protocol (NTP) and Stratum 1 atomic clocks coordinating transactional ledger state."),
    (20, "modo_avion_real", "Block C: Networks, Protocols & Telecommunications",
     "The Real Reason You Are Forced Into Airplane Mode",
     "Airliners won't crash from checking social feeds, but cellular ground towers will panic.",
     "Massive high-speed handovers from hundreds of phones at 500 mph overwhelming ground cell towers."),
    (21, "ipv4_nat", "Block C: Networks, Protocols & Telecommunications",
     "How Your Entire Home Browses with One Address",
     "Internet address space ran out years ago, yet you keep connecting new smart devices daily.",
     "Network Address Translation (NAT) mapping dozens of private local addresses to a single public IP."),
    (22, "datacenter_nuclear", "Block C: Networks, Protocols & Telecommunications",
     "Why AI Datacenters Require Nuclear Reactors",
     "Next-generation artificial intelligence campuses are being constructed directly beside nuclear plants.",
     "Continuous multi-gigawatt baseload energy requirements without wind or solar intermittency."),

    # Block D: Displays, Storage & Computing Physics
    (23, "oled_negro_real", "Block D: Displays, Storage & Computing Physics",
     "The Black Color That Physically Turns Displays Off",
     "On an OLED panel, displaying pure black doesn't dim light: it cuts pixel power completely.",
     "Self-emissive organic diodes versus always-on global LED backlights found in IPS/LCD panels."),
    (24, "ssd_trim_borrado", "Block D: Displays, Storage & Computing Physics",
     "Why an SSD Never Deletes Your Files",
     "When you empty your trash bin, your solid-state drive touches zero stored data blocks.",
     "Flash memory mapping lookup tables and asynchronous block garbage collection via TRIM."),
    (25, "pulldown_24fps", "Block D: Displays, Storage & Computing Physics",
     "The Ghost Framerate Artifact in Cinema",
     "Playing 24 FPS movies on a 60 Hz monitor produces mathematical motion judder.",
     "3:2 pulldown cadence when distributing 24 frames across a non-divisible 60 Hz refresh cycle."),
    (26, "bluetooth_cuerpo", "Block D: Displays, Storage & Computing Physics",
     "Why Earbuds Stutter Behind Your Back",
     "A radio signal penetrates apartment walls, yet fails to pass through your own torso.",
     "Absorption of 2.4 GHz microwave radio frequencies by water molecules inside human body tissue."),
    (27, "proyector_dlp", "Block D: Displays, Storage & Computing Physics",
     "The Projector Housing Millions of Moving Mirrors",
     "Cinemas don't rely on magic lenses: they project light with millions of pivoting mirrors.",
     "Digital Micromirror Devices (DMD) tilting thousands of times per second to modulate pixel luminance."),
    (28, "landauer_calor", "Block D: Displays, Storage & Computing Physics",
     "Why Deleting Data Generates Physical Heat",
     "Your processor heats up not from computing, but whenever it permanently erases a logical bit.",
     "Landauer's Principle: thermodynamic minimum energy dissipation upon destroying informational entropy."),
    (29, "induccion_fria", "Block D: Displays, Storage & Computing Physics",
     "Why Induction Cooktops Don't Burn Your Hand",
     "You can lay your bare hand flat on an active induction stovetop and feel zero heat.",
     "High-frequency electromagnetic fields generating eddy currents exclusively in ferromagnetic cookware."),
    (30, "disco_duro_grito", "Block D: Displays, Storage & Computing Physics",
     "The Engineer Who Froze a Datacenter by Screaming",
     "A single human scream can paralyze server hard drive data transfer in real time.",
     "Acoustic resonance vibrations misaligning read-write mechanical heads floating nanometers above platters."),
]


def _seed_topics_queue(conn: sqlite3.Connection) -> None:
    """Populates the topics_queue table with the 30 verified high-retention engineering topics."""
    now_iso = datetime.now(timezone.utc).isoformat()
    # Check if block_name column exists
    cursor_tq = conn.execute("PRAGMA table_info(topics_queue)")
    cols = [r[1] for r in cursor_tq.fetchall()]
    has_block_name = "block_name" in cols

    for row in TOPICS_QUEUE_SEED:
        order_idx, key, block, title, hook, principle = row
        if has_block_name:
            conn.execute(
                """
                INSERT INTO topics_queue (
                    order_index, topic_key, block, block_name, title, hook, principle, category, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'tech_curiosities', 'pending', ?)
                ON CONFLICT(topic_key) DO UPDATE SET
                    order_index=excluded.order_index,
                    block=excluded.block,
                    block_name=excluded.block_name,
                    title=excluded.title,
                    hook=excluded.hook,
                    principle=excluded.principle
                """,
                (order_idx, key, block, block, title, hook, principle, now_iso),
            )
        else:
            conn.execute(
                """
                INSERT INTO topics_queue (
                    order_index, topic_key, block, title, hook, principle, category, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'tech_curiosities', 'pending', ?)
                ON CONFLICT(topic_key) DO UPDATE SET
                    order_index=excluded.order_index,
                    block=excluded.block,
                    title=excluded.title,
                    hook=excluded.hook,
                    principle=excluded.principle
                """,
                (order_idx, key, block, title, hook, principle, now_iso),
            )


def get_next_queue_topic(
    category: str = "tech_curiosities",
    db_path: Optional[Path] = None,
) -> Optional[dict]:
    """Retrieves the next pending topic in topics_queue ordered by order_index ASC."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT * FROM topics_queue
            WHERE category = ? AND status = 'pending'
            ORDER BY order_index ASC, id ASC
            LIMIT 1
            """,
            (category,),
        ).fetchone()
        return dict(row) if row else None


def get_topic_by_key(topic_key: str, db_path: Optional[Path] = None) -> Optional[dict]:
    """Retrieves a topic from topics_queue by its unique topic_key."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM topics_queue WHERE topic_key = ?", (topic_key,)
        ).fetchone()
        return dict(row) if row else None


def mark_queue_topic_completed(
    topic_key: str,
    video_id: str = "",
    db_path: Optional[Path] = None,
) -> None:
    """Marks a topic in topics_queue as completed with timestamp and video_id."""
    init_db(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE topics_queue
            SET status = 'completed', produced_at = ?, video_id = ?
            WHERE topic_key = ?
            """,
            (now_iso, video_id, topic_key),
        )
        conn.commit()


def list_topics_queue(
    status: Optional[str] = None,
    block: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> List[dict]:
    """Lists topics from topics_queue, optionally filtered by status ('pending', 'completed') or block."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        query = "SELECT * FROM topics_queue WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if block:
            query += " AND block LIKE ?"
            params.append(f"%{block}%")
        query += " ORDER BY order_index ASC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# ==============================================================================
# GENERATION METRICS & TELEMETRY COST TRACKING
# ==============================================================================
def record_generation_metric(
    run_id: str,
    topic_id: str,
    category: str,
    gemini_input_tokens: int = 0,
    gemini_output_tokens: int = 0,
    elevenlabs_characters: int = 0,
    duration_seconds: float = 0.0,
    word_count: int = 0,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Records consumption, tokens, and estimated USD cost in generation_metrics table."""
    init_db(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    # Cost = (Chars_ElevenLabs * 0.00030) + (Tokens_Gemini * 0.000002)
    total_tokens = gemini_input_tokens + gemini_output_tokens
    estimated_cost = (elevenlabs_characters * 0.00030) + (total_tokens * 0.000002)

    with get_db_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO generation_metrics (
                timestamp, run_id, topic_id, category,
                gemini_input_tokens, gemini_output_tokens,
                elevenlabs_characters, estimated_cost_usd,
                duration_seconds, word_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now_iso, run_id, topic_id, category,
                gemini_input_tokens, gemini_output_tokens,
                elevenlabs_characters, round(estimated_cost, 5),
                round(duration_seconds, 2), word_count,
            ),
        )
        conn.commit()
        metric_id = cursor.lastrowid

    return {
        "id": metric_id,
        "timestamp": now_iso,
        "run_id": run_id,
        "topic_id": topic_id,
        "category": category,
        "total_tokens": total_tokens,
        "elevenlabs_characters": elevenlabs_characters,
        "estimated_cost_usd": round(estimated_cost, 5),
        "duration_seconds": round(duration_seconds, 2),
        "word_count": word_count,
    }


def get_recent_generation_metrics(limit: int = 10, db_path: Optional[Path] = None) -> List[dict]:
    """Retrieves the most recent generation telemetry records."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM generation_metrics ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


# ==============================================================================
# ALGORITHMIC FEEDBACK LOOP (ANALYTICS HISTORY & RETENTION CALIBRATION)
# ==============================================================================
def record_analytics_metric(
    video_id: str,
    title: str,
    category: str,
    theme_key: str,
    views: int,
    viewer_percentage: float,
    avg_view_percentage: float,
    likes: int = 0,
    comments: int = 0,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Inserts or updates video performance score in analytics_history."""
    init_db(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    # Performance score = (viewerPercentage * 0.4) + (averageViewPercentage * 0.6)
    score = (viewer_percentage * 0.4) + (avg_view_percentage * 0.6)
    swiped_away = max(0.0, 100.0 - viewer_percentage)

    with get_db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO analytics_history (
                video_id, title, category, theme_key, views,
                viewer_percentage, avg_view_percentage,
                likes, comments, performance_score,
                swiped_away_percentage, synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                views=excluded.views,
                viewer_percentage=excluded.viewer_percentage,
                avg_view_percentage=excluded.avg_view_percentage,
                likes=excluded.likes,
                comments=excluded.comments,
                performance_score=excluded.performance_score,
                swiped_away_percentage=excluded.swiped_away_percentage,
                synced_at=excluded.synced_at
            """,
            (
                video_id, title, category, theme_key, views,
                round(viewer_percentage, 2), round(avg_view_percentage, 2),
                likes, comments, round(score, 2),
                round(swiped_away, 2), now_iso,
            ),
        )
        conn.commit()

    return {
        "video_id": video_id,
        "performance_score": round(score, 2),
        "swiped_away_percentage": round(swiped_away, 2),
    }


def get_category_performance_averages(db_path: Optional[Path] = None) -> Dict[str, float]:
    """Calculates average performance score per category from analytics_history."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT category, AVG(performance_score) as avg_score, COUNT(*) as count
            FROM analytics_history
            WHERE category != ''
            GROUP BY category
            """
        ).fetchall()
        return {r["category"]: round(r["avg_score"], 2) for r in rows}


def get_next_rotated_category(db_path: Optional[Path] = None) -> str:
    """Selects the optimal category with the highest rotation rest and retention weighting.

    Consults recent production history in data/history.db (generation_metrics & shorts_history)
    and algorithmic retention weights from data/category_weights.json.
    """
    import json
    init_db(db_path)
    candidates = ["hardware_benchmarks", "gaming_benchmarks", "tech_curiosities"]

    # Check recent productions in generation_metrics
    last_produced_rank = {}
    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT category, MAX(id) as max_id
            FROM generation_metrics
            WHERE category IN ('hardware_benchmarks', 'gaming_benchmarks', 'tech_curiosities')
            GROUP BY category
            """
        ).fetchall()
        for r in rows:
            last_produced_rank[r["category"]] = r["max_id"]

        # Also check shorts_history
        sh_rows = conn.execute(
            """
            SELECT category, MAX(id) as max_id
            FROM shorts_history
            WHERE category IN ('hardware_benchmarks', 'gaming_benchmarks', 'tech_curiosities')
            GROUP BY category
            """
        ).fetchall()
        for r in sh_rows:
            if r["category"] not in last_produced_rank:
                last_produced_rank[r["category"]] = r["max_id"]

    # Load weights from category_weights.json if available
    weights_path = Path(settings.BASE_DIR) / "data" / "category_weights.json"
    weights = {"tech_curiosities": 0.50, "gaming_benchmarks": 0.25, "hardware_benchmarks": 0.25}
    if weights_path.is_file():
        try:
            with open(weights_path, "r", encoding="utf-8") as f:
                w_data = json.load(f)
                weights.update(w_data.get("weights", {}))
        except Exception as err:
            logger.debug("Could not read category_weights.json: %s", err)

    # Categories never produced have highest rest
    unproduced = [c for c in candidates if c not in last_produced_rank]
    if unproduced:
        unproduced.sort(key=lambda c: weights.get(c, 0.0), reverse=True)
        return unproduced[0]

    # Otherwise sort by smallest max_id (longest rest), secondary by highest weight
    sorted_candidates = sorted(
        candidates,
        key=lambda c: (last_produced_rank.get(c, 0), -weights.get(c, 0.0))
    )
    return sorted_candidates[0]






def get_recently_used_topics_safe(limit: int = 25) -> list:
    """Titles of recently produced videos (best effort; empty list on any error)."""
    try:
        init_db()
        with get_db_connection() as conn:
            rows = conn.execute("SELECT topic FROM shorts_history WHERE topic IS NOT NULL ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        seen = []
        for r in rows:
            if r["topic"] and r["topic"] not in seen:
                seen.append(r["topic"])
        return seen
    except Exception:
        return []
