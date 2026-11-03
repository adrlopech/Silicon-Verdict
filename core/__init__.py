"""Core module for Silicon Verdict schema definitions, AI generation, and topic discovery."""
from .schemas import ChartData, MarketTopic, Scene, ShortMetadata, VideoProject
from .generator import format_final_description, generate_video_plan
from .topic_engine import generate_market_topic, record_topic_in_history

__all__ = [
    "ChartData",
    "MarketTopic",
    "Scene",
    "ShortMetadata",
    "VideoProject",
    "format_final_description",
    "generate_video_plan",
    "generate_market_topic",
    "record_topic_in_history",
]
