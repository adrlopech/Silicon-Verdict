"""Services module encapsulating third-party APIs and platform integrations."""
from .tts import synthesize_all_scenes, SceneAudio
from .media import fetch_all_scene_media, SceneMedia
from .youtube import YouTubeService, youtube_service, upload_video_resumable
from .tiktok import upload_video_to_tiktok, validate_tiktok_creator_rewards_eligibility
from .notifier import notify_pipeline_success

__all__ = [
    "synthesize_all_scenes",
    "SceneAudio",
    "fetch_all_scene_media",
    "SceneMedia",
    "YouTubeService",
    "youtube_service",
    "upload_video_resumable",
    "upload_video_to_tiktok",
    "validate_tiktok_creator_rewards_eligibility",
    "notify_pipeline_success",
]
