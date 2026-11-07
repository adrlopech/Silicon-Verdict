import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Find project root and explicitly load .env
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.is_file():
    load_dotenv(dotenv_path=ENV_FILE, override=True)
else:
    logger.warning("No .env file found at %s. Relying on system environment variables.", ENV_FILE)


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Base Paths
    BASE_DIR: Path = BASE_DIR
    TMP_DIR: str = "/tmp/yt_automation"

    # Hard ceiling for the length of ANY video (every series): 3 minutes
    MAX_VIDEO_SECONDS: float = 180.0

    # Gemini AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"

    # Fallback LLM providers, tried in order when every Gemini model is unavailable (leave a key empty to disable it)
    GROQ_API_KEY: str = ""
    CLOUDFLARE_ACCOUNT_ID: str = ""
    CLOUDFLARE_API_TOKEN: str = ""  # token with the "Workers AI" permission
    CLOUDFLARE_VISION_MODELS: str = "@cf/meta/llama-3.2-11b-vision-instruct"  # used when a request carries images
    CLOUDFLARE_MODELS: str = "@cf/openai/gpt-oss-120b,@cf/meta/llama-3.3-70b-instruct-fp8-fast"  # comma-separated
    GROQ_MODELS: str = "openai/gpt-oss-120b,openai/gpt-oss-20b,qwen/qwen3.8-27b"  # comma-separated, preference order

    # ElevenLabs TTS & Voice Rotation Pool (Verified Active Voices)
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "onwK4e9ZLuTAKqWW03F9"  # Daniel - Steady Broadcaster
    ELEVENLABS_VOICE_1: str = "onwK4e9ZLuTAKqWW03F9"   # Voice 1: Daniel (Steady Broadcaster)
    ELEVENLABS_VOICE_2: str = "pNInz6obpgDQGcFmaJgB"   # Voice 2: Adam (Dominant, Firm)
    ELEVENLABS_VOICE_3: str = "TX3LPaxmHKxFdv7VOQHJ"   # Voice 3: Liam (Energetic, Social Media Creator)
    ELEVENLABS_MODEL_ID: str = "eleven_turbo_v2_5"

    # Narration backend: "elevenlabs" (default; paid credits) with the free local voice as backup, or "local" (local only)
    TTS_BACKEND: str = "elevenlabs"
    LOCAL_TTS_FALLBACK: bool = True  # when ElevenLabs fails (no credits, network), narrate with the cloned local voice
    LOCAL_TTS_URL: str = "http://127.0.0.1:3900"  # VoiceStudio backend (ASR for word timestamps)
    MLX_TTS_URL: str = "http://127.0.0.1:3901"

    # Minecraft series: on-screen language (en default / es)
    MC_LANGUAGE: str = "en"

    # Media APIs (Pixabay preferred, Pexels optional fallback)
    PIXABAY_API_KEY: str = ""
    PEXELS_API_KEY: Optional[str] = ""

    # YouTube OAuth & Upload
    YOUTUBE_TOKEN_PATH: str = "token.json"
    YOUTUBE_CLIENT_SECRETS_PATH: str = "client_secrets.json"
    YOUTUBE_PRIVACY_STATUS: str = "public"  # "public", "private", "unlisted"
    YOUTUBE_CATEGORY_ID: str = "28"  # 28: Science & Technology

    # TikTok Content Posting API Settings
    TIKTOK_ACCESS_TOKEN: str = ""
    TIKTOK_CLIENT_KEY: str = ""
    TIKTOK_CLIENT_SECRET: str = ""
    TIKTOK_TOKEN_PATH: str = "data/tiktok_token.json"
    TIKTOK_PRIVACY_LEVEL: str = "PUBLIC_TO_EVERYONE"  # "SELF_ONLY" (Draft), "PUBLIC_TO_EVERYONE"

    # Notifications (Discord or Telegram)
    DISCORD_WEBHOOK_URL: Optional[str] = None
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # Scheduling & Execution
    PUBLISH_TIME: str = "14:00"  # Target UTC or local execution time (HH:MM)

    # Video Rendering Settings
    VIDEO_FPS: int = 30
    VIDEO_WIDTH: int = 1920
    VIDEO_HEIGHT: int = 1080
    SHORT_WIDTH: int = 1080
    SHORT_HEIGHT: int = 1920
    FONT_PATH: str = "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"

    def resolve_token_path(self) -> Path:
        """Resolves token.json location checking data/ first, then root and tokens/."""
        p = Path(self.YOUTUBE_TOKEN_PATH)
        if not p.is_absolute():
            p = self.BASE_DIR / p
        if not p.is_file():
            fallbacks = [
                self.BASE_DIR / "data" / "token.json",
                self.BASE_DIR / "token.json",
                self.BASE_DIR / "tokens" / "token.json",
            ]
            for fb in fallbacks:
                if fb.is_file():
                    return fb
        return p

    def resolve_client_secrets_path(self) -> Path:
        """Resolves client_secrets.json location checking data/ first, then root and fallbacks."""
        p = Path(self.YOUTUBE_CLIENT_SECRETS_PATH)
        if not p.is_absolute():
            p = self.BASE_DIR / p
        if not p.is_file():
            fallbacks = [
                self.BASE_DIR / "data" / "client_secrets.json",
                self.BASE_DIR / "client_secrets.json",
                self.BASE_DIR / "tokens" / "client_secret.json",
            ]
            for fb in fallbacks:
                if fb.is_file():
                    return fb
        return p

    def resolve_tiktok_token_path(self) -> Path:
        """Resolves tiktok_token.json location checking data/ first, then root and tokens/."""
        p = Path(self.TIKTOK_TOKEN_PATH)
        if not p.is_absolute():
            p = self.BASE_DIR / p
        if not p.is_file():
            alt1 = self.BASE_DIR / "data" / "tiktok_token.json"
            if alt1.is_file():
                return alt1
            alt2 = self.BASE_DIR / "tiktok_token.json"
            if alt2.is_file():
                return alt2
            alt3 = self.BASE_DIR / "tokens" / "tiktok_token.json"
            if alt3.is_file():
                return alt3
        return p

    def validate_required_keys(self) -> dict:
        """Validates critical API keys and logs warnings for any missing credentials."""
        status = {}
        if not self.GEMINI_API_KEY or self.GEMINI_API_KEY.startswith("your_"):
            logger.warning("GEMINI_API_KEY is not properly configured.")
            status["GEMINI_API_KEY"] = False
        else:
            status["GEMINI_API_KEY"] = True

        if not self.ELEVENLABS_API_KEY or self.ELEVENLABS_API_KEY.startswith("your_"):
            logger.warning("ELEVENLABS_API_KEY is not properly configured.")
            status["ELEVENLABS_API_KEY"] = False
        else:
            status["ELEVENLABS_API_KEY"] = True

        if not self.PIXABAY_API_KEY and not self.PEXELS_API_KEY:
            logger.warning("Neither PIXABAY_API_KEY nor PEXELS_API_KEY is configured. Stock B-roll acquisition may fail.")
            status["MEDIA_API_KEY"] = False
        else:
            status["MEDIA_API_KEY"] = True

        return status


settings = Settings()
