import logging
from typing import List, Optional
import requests

from config.settings import settings

logger = logging.getLogger(__name__)


def send_discord_notification(
    title: str,
    full_video_url: str,
    shorts_urls: List[str],
    scenes_count: int,
    pinned_comment: Optional[str] = None,
    thumbnail_prompt: Optional[str] = None,
) -> bool:
    """Dispatches a rich embed notification to a Discord webhook."""
    if not settings.DISCORD_WEBHOOK_URL:
        return False

    shorts_field = (
        "\n".join([f"• [Short #{i+1}]({url})" for i, url in enumerate(shorts_urls)])
        if shorts_urls else "No Shorts generated."
    )

    fields = [
        {
            "name": "🎬 Full Video (16:9)",
            "value": f"[Watch Video]({full_video_url})",
            "inline": False,
        },
        {
            "name": "📱 Shorts Generated (9:16)",
            "value": shorts_field,
            "inline": False,
        },
        {
            "name": "⚙️ Status",
            "value": f"Privacy: `{settings.YOUTUBE_PRIVACY_STATUS}`",
            "inline": True,
        },
    ]

    if pinned_comment:
        fields.append({
            "name": "💬 Pinned Discussion Question",
            "value": pinned_comment[:1000],
            "inline": False,
        })

    if thumbnail_prompt:
        fields.append({
            "name": "🎨 Midjourney Thumbnail Prompt",
            "value": f"```{thumbnail_prompt[:1000]}```",
            "inline": False,
        })

    embed = {
        "title": "⚡ Silicon Verdict: New Video Live!",
        "description": f"**Title:** {title}\n**Total Scenes:** {scenes_count}",
        "color": 0x00F0FF,  # Silicon Verdict Neon Cyan
        "fields": fields,
        "footer": {
            "text": "Silicon Verdict Automated Pipeline | VPS Autonomous Runner",
        },
    }

    payload = {
        "username": "Silicon Verdict Bot",
        "avatar_url": "https://upload.wikimedia.org/wikipedia/commons/e/ef/Youtube_logo.png",
        "embeds": [embed],
    }

    try:
        res = requests.post(settings.DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        res.raise_for_status()
        logger.info("Discord notification sent successfully.")
        return True
    except Exception as exc:
        logger.error("Failed sending Discord notification: %s", exc)
        return False


def send_telegram_notification(
    title: str,
    full_video_url: str,
    shorts_urls: List[str],
    scenes_count: int,
    pinned_comment: Optional[str] = None,
    thumbnail_prompt: Optional[str] = None,
) -> bool:
    """Dispatches an HTML formatted notification to a Telegram Chat."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

    shorts_text = ""
    if shorts_urls:
        shorts_text = "\n<b>📱 Shorts:</b>\n" + "\n".join(
            [f"• <a href='{s_url}'>Short #{i+1}</a>" for i, s_url in enumerate(shorts_urls)]
        )

    comment_text = f"\n\n<b>💬 Pinned Comment:</b>\n{pinned_comment}" if pinned_comment else ""
    prompt_text = f"\n\n<b>🎨 Thumbnail Prompt:</b>\n<code>{thumbnail_prompt}</code>" if thumbnail_prompt else ""

    text = (
        f"⚡ <b>Silicon Verdict: New Video Upload Complete!</b>\n\n"
        f"<b>Title:</b> {title}\n"
        f"<b>Scenes:</b> {scenes_count}\n"
        f"<b>Status:</b> {settings.YOUTUBE_PRIVACY_STATUS}\n\n"
        f"🎬 <b>Full Video:</b> <a href='{full_video_url}'>{full_video_url}</a>"
        f"{shorts_text}"
        f"{comment_text}"
        f"{prompt_text}"
    )

    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    try:
        res = requests.post(url, json=payload, timeout=10)
        res.raise_for_status()
        logger.info("Telegram notification sent successfully.")
        return True
    except Exception as exc:
        logger.error("Failed sending Telegram notification: %s", exc)
        return False


def notify_pipeline_success(
    title: str,
    full_video_url: str,
    shorts_urls: List[str],
    scenes_count: int,
    pinned_comment: Optional[str] = None,
    thumbnail_prompt: Optional[str] = None,
) -> None:
    """Broadcasts completion status to all configured notification providers."""
    sent_any = False
    if settings.DISCORD_WEBHOOK_URL:
        sent_any |= send_discord_notification(
            title, full_video_url, shorts_urls, scenes_count, pinned_comment, thumbnail_prompt
        )
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        sent_any |= send_telegram_notification(
            title, full_video_url, shorts_urls, scenes_count, pinned_comment, thumbnail_prompt
        )

    if not sent_any:
        logger.info("No notification services configured or messages failed. Pipeline finished cleanly.")
