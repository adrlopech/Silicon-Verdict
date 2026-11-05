import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List


from core.schemas import MarketTopic

logger = logging.getLogger(__name__)


def load_history(history_path: Path) -> List[dict]:
    """Loads previously covered topics from history.json."""
    if not history_path.is_file():
        return []
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as exc:
        logger.warning("Could not read history file %s: %s. Starting fresh history.", history_path, exc)
        return []


def save_history(history_path: Path, history_data: List[dict]) -> None:
    """Saves updated history to history.json atomically."""
    history_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = history_path.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)
    temp_file.replace(history_path)


def record_topic_in_history(topic_data: MarketTopic, history_path: Path) -> None:
    """Appends a completed topic to the history tracking file."""
    history = load_history(history_path)
    entry = {
        "topic": topic_data.topic,
        "hook_angle": topic_data.hook_angle,
        "target_audience": topic_data.target_audience,
        "suggested_benchmarks": topic_data.suggested_benchmarks,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    history.append(entry)
    save_history(history_path, history)
    logger.info("Recorded topic '%s' to history (%s)", topic_data.topic, history_path.name)


def generate_market_topic(history_path: Path) -> MarketTopic:
    """Autonomously discovers an unexploited, high-CTR PC hardware topic for Silicon Verdict.

    Args:
        history_path: Path to history.json.

    Returns:
        MarketTopic: Validated Pydantic schema with topic title, hook, and suggested benchmark angles.
    """
    logger.info("Silicon Verdict Topic Engine: Generating autonomous PC Hardware topic via Gemini...")
    history = load_history(history_path)
    past_topics = [item.get("topic", "") for item in history if isinstance(item, dict)]

    system_instruction = (
        "You are the Editorial Director for 'Silicon Verdict', an elite tech channel specializing in "
        "PC Hardware, Semiconductor Architectures, and empirical price-to-performance analysis.\n\n"
        "Your mission is to generate the NEXT single viral, high-CTR video topic in technical English. "
        "Focus on architectural controversies, empirical benchmark reveals, and urgent buying dilemmas.\n\n"
        "Key Pillars:\n"
        "1. Architectural Shootouts: AMD 3D V-Cache vs Intel Hybrid P/E core topologies, memory sub-timings, IPC scaling.\n"
        "2. Price-to-Performance ($/FPS): True cost of platform upgrades (AM5 vs LGA1700/LGA1851), GPU VRAM bottlenecks.\n"
        "3. Bottleneck Investigations: PCIe 4.0 vs PCIe 5.0 SSDs/GPUs in real gaming, CPU overhead with high-tier GPUs.\n"
        "4. Thermal & Efficiency Telemetry: Undervolting gains, VRM thermal throttling under heavy multi-threaded loads.\n\n"
        "Strict Requirement: The topic and benchmarks must be in technical English and must NOT duplicate previously covered topics."
    )

    history_context = ""
    if past_topics:
        recent_topics = past_topics[-30:]
        history_context = "\nPreviously produced topics (DO NOT REPEAT OR CLOSELY CLONE THESE):\n" + "\n".join(
            f"- {t}" for t in recent_topics
        )

    prompt = (
        f"Generate a fresh, highly compelling Silicon Verdict PC hardware video topic.{history_context}\n\n"
        "Identify an urgent buying dilemma or technical benchmark comparison that PC gamers and tech enthusiasts "
        "are actively debating right now. Provide topic, hook_angle, target_audience, and suggested_benchmarks."
    )

    try:
        from services.gemini_client import generate_structured
        market_topic, _tok, _model = generate_structured(prompt=prompt, system_instruction=system_instruction, schema=MarketTopic, temperature=0.85)
        logger.info("Selected autonomous Silicon Verdict topic: '%s'", market_topic.topic)
        logger.info("Hook: %s | Target: %s", market_topic.hook_angle, market_topic.target_audience)
        return market_topic

    except Exception as exc:
        logger.error("Failed to generate autonomous topic: %s", exc, exc_info=True)
        raise RuntimeError(f"Silicon Verdict Topic Engine failed: {exc}") from exc
