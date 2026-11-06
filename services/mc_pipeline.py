"""End-to-end pipeline for the Minecraft series: script -> render -> output folders (+ TikTok metadata) -> optional YouTube upload."""
import logging
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import settings

logger = logging.getLogger(__name__)


def run_minecraft_pipeline(
    topic: Optional[str] = None,
    export_only: bool = False,
    dry_run: bool = False,
    privacy: str = "public",
    prefer_bank: bool = True,
    story: Optional[Any] = None,
) -> Dict[str, Any]:
    """Produces one Minecraft explainer. `story` may be passed in (e.g. a hand-written McStory)."""
    from services.history import record_short_history
    from services.mc_renderer import render_mc_video
    from services.mc_story_generator import generate_story
    from services.output_layout import timestamp_stem, video_dir
    from services.voice import get_ffmpeg_bin  # noqa: F401  (fails early if ffmpeg is missing)

    t0 = time.time()
    run_id = uuid.uuid4().hex[:8]
    from services.gemini_client import GeminiUnavailable
    from services.mc_review import qa_video, review_and_fix
    from services.mc_story_generator import McScriptUnavailable
    review_ok = True
    for attempt in range(1, 4):  # fact-check gate: a script that fails review is discarded and replaced by another new one
        story = story or generate_story(topic, prefer_bank=prefer_bank)  # always a new Gemini script (bank or live); raises if none
        try:
            if review_and_fix(story):
                break
        except GeminiUnavailable as exc:
            logger.warning("Script review unavailable (%s): the video will be rendered but NOT uploaded.", str(exc)[:120])
            review_ok = False
            break
        logger.warning("Script '%s' failed the review (attempt %d/3); taking another one.", story.title, attempt)
        story = None
    else:
        raise McScriptUnavailable("Three consecutive scripts failed the technical review; nothing was produced.")
    logger.info("Minecraft story: '%s' (%d beats)", story.title, len(story.beats))

    work = Path(settings.TMP_DIR) / f"run_mc_{run_id}"
    work.mkdir(parents=True, exist_ok=True)
    from services.mc_voice import narrate_beats
    try:
        clips = narrate_beats(story, work / "voice")  # ElevenLabs narration; also stretches each beat to fit its line
        video, cover, timing = render_mc_video(story, work / "mc_master.mp4", work / "cover.jpg", voice_clips=clips)
    except BaseException:
        from services.story_bank import release_story  # a banked script is only spent by a video that was actually produced
        release_story(story)
        shutil.rmtree(work, ignore_errors=True)
        raise

    qa_fails = qa_video(video, story)
    if qa_fails:
        logger.error("Video QA FAILED, it will not be uploaded: %s", "; ".join(qa_fails))
    if not review_ok or qa_fails:
        export_only = True
    else:
        logger.info("Video QA passed.")

    stem = timestamp_stem()
    out = {}
    for platform in ("youtube", "tiktok"):
        d = video_dir(platform, story.title)
        shutil.copyfile(video, d / f"{stem}.mp4")
        if cover.is_file():
            shutil.copyfile(cover, d / f"{stem}_cover.jpg")
        out[platform] = d / f"{stem}.mp4"

    tags = [t if t.startswith("#") else f"#{t}" for t in story.tags]
    meta = out["tiktok"].with_suffix(".txt")
    meta.write_text(
        "=" * 80 + "\nSILICON VERDICT • MINECRAFT EXPLAINER • TIKTOK & SHORTS METADATA\n"
        f"Creation Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\nVideo File: {out['tiktok'].name}\nTopic: {story.topic}\n" + "=" * 80
        + f"\n\n[TITLE]\n{story.title}\n\n[DESCRIPTION]\n{story.description}\n\n[HASHTAGS]\n{' '.join(tags)}\n\n[PINNED COMMENT]\n{story.pinned_comment}\n\n[SUBTITLES]\n"
        + "\n".join(f"- {b.text}" for b in story.beats) + "\n",
        encoding="utf-8",
    )

    youtube_url, yt_id = f"file://{out['youtube'].resolve()}", f"local_export_{run_id}"
    if not export_only and not dry_run:
        try:
            from services.youtube import upload_video_resumable
            youtube_url = upload_video_resumable(file_path=str(out["youtube"]), title=story.title, description=story.description, tags=story.tags, privacy_status=privacy, is_short=True)
            yt_id = youtube_url.split("/")[-1]
        except Exception as exc:
            logger.error("YouTube upload failed (%s). Video kept locally.", exc)
            yt_id = f"local_{run_id}"

    try:
        record_short_history(weekday_index=datetime.now().weekday(), theme_key="minecraft", game_title=story.header_banner or story.topic,
                             voice_id_used="none", topic=story.topic, title=story.title, video_id=yt_id, category=story.category_name,
                             tone="minecraft_explainer", preset="remotion_minecraft")
    except Exception as exc:
        logger.warning("History not recorded: %s", exc)

    if prefer_bank and not topic:
        from services.bank_manager import replenish_after_use
        replenish_after_use("minecraft")

    shutil.rmtree(work, ignore_errors=True)  # the master was copied to the output folders
    elapsed = time.time() - t0
    logger.info("Minecraft video ready in %.0fs: %s", elapsed, out["tiktok"])
    return {"youtube_video": str(out["youtube"]), "youtube_url": youtube_url, "tiktok_video": str(out["tiktok"]), "tiktok_metadata": str(meta),
            "title": story.title, "topic": story.topic, "render_seconds": timing["headless_render"], "qa_failures": qa_fails, "uploaded": not export_only and not dry_run}
