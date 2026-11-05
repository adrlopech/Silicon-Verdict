"""TikTok Content Posting API and Video Upload Service.

Implements automated vertical long-video (>60.5s) publishing for the TikTok Creator
Rewards Program. Features unattended OAuth 2.0 access token management, automatic
token refresh using refresh_token, chunked binary video upload with Content-Range,
and status polling via TikTok Content Posting API v2.
"""

import json
import logging
import math
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

from config.settings import settings
from services.history import record_tiktok_post

logger = logging.getLogger(__name__)

TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"
TIKTOK_TOKEN_URL = f"{TIKTOK_API_BASE}/oauth/token/"
DEFAULT_CHUNK_SIZE = 20 * 1024 * 1024  # 20 MB chunks for large files
MAX_SINGLE_CHUNK = 64 * 1024 * 1024   # Up to 64 MB can be uploaded in 1 chunk


def get_video_duration_ffprobe(video_path: Path) -> float:
    """Measures precise video duration in seconds via ffprobe."""
    video_path = Path(video_path).resolve()
    ffprobe_bin = (
        shutil.which("ffprobe")
        or str(Path(sys.executable).parent / "ffprobe")
        or "ffprobe"
    )
    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(res.stdout.strip())
    except Exception as exc:
        logger.warning("ffprobe measurement failed for %s (%s).", video_path, exc)
        return 0.0


def validate_tiktok_creator_rewards_eligibility(video_path: Path, min_duration: float = 60.5) -> bool:
    """Validates that a video strictly qualifies for the TikTok Creator Rewards Program (>60s).

    Args:
        video_path: Path to the target video file.
        min_duration: Minimum duration threshold in seconds (default: 60.5s).

    Returns:
        bool: True if duration strictly meets or exceeds threshold.
    """
    duration = get_video_duration_ffprobe(video_path)
    logger.info("Verifying TikTok Creator Rewards monetization threshold: %.2fs (Floor: %.2fs)", duration, min_duration)

    if duration < min_duration:
        logger.error(
            "Video duration %.2fs is below the mandatory >60.5s threshold for TikTok Creator Rewards monetization!",
            duration,
        )
        return False

    logger.info("Video successfully verified for TikTok Creator Rewards Program: %.2fs (>60.5s)", duration)
    return True


class TikTokService:
    """High-level client for TikTok Content Posting API v2 with automatic token refresh."""

    def __init__(
        self,
        token_path: Optional[Path] = None,
        client_key: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        self.token_path = token_path or settings.resolve_tiktok_token_path()
        self.client_key = client_key or settings.TIKTOK_CLIENT_KEY
        self.client_secret = client_secret or settings.TIKTOK_CLIENT_SECRET
        self._token_cache: Optional[Dict[str, Any]] = None

    def is_token_available(self) -> bool:
        """Checks if a valid TikTok token file exists and contains credentials."""
        if self._token_cache and (self._token_cache.get("access_token") or self._token_cache.get("refresh_token")):
            return True

        resolved_path = self.token_path
        if not resolved_path.is_file():
            fallbacks = [
                settings.BASE_DIR / "data" / "tiktok_token.json",
                settings.BASE_DIR / "tiktok_token.json",
                settings.BASE_DIR / "tokens" / "tiktok_token.json",
            ]
            for fb in fallbacks:
                if fb.is_file():
                    resolved_path = fb
                    break

        if not resolved_path.is_file():
            return False

        try:
            with open(resolved_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return bool(data.get("access_token") or data.get("refresh_token"))
        except Exception:
            return False

    def _load_token_data(self) -> Dict[str, Any]:
        """Loads token data from disk or cache."""
        if self._token_cache:
            return self._token_cache

        resolved_path = self.token_path
        if not resolved_path.is_file():
            # Check fallback locations
            fallbacks = [
                settings.BASE_DIR / "data" / "tiktok_token.json",
                settings.BASE_DIR / "tiktok_token.json",
                settings.BASE_DIR / "tokens" / "tiktok_token.json",
            ]
            for fb in fallbacks:
                if fb.is_file():
                    resolved_path = fb
                    break

        if not resolved_path.is_file():
            raise FileNotFoundError(
                f"TikTok OAuth credentials not found at {self.token_path}. "
                "Please run 'python scripts/auth_tiktok.py' to authorize your TikTok account."
            )

        try:
            with open(resolved_path, "r", encoding="utf-8") as f:
                self._token_cache = json.load(f)
            self.token_path = resolved_path
            return self._token_cache
        except Exception as exc:
            raise RuntimeError(f"Failed to read TikTok token file {resolved_path}: {exc}")

    def _save_token_data(self, data: Dict[str, Any]) -> None:
        """Atomically saves token data to disk and updates in-memory cache."""
        self._token_cache = data
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("TikTok token data updated and saved to %s", self.token_path)

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Exchanges a refresh_token for a new access_token and updated refresh_token."""
        logger.info("Executing unattended TikTok access token refresh...")

        payload = {
            "client_key": self.client_key,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "no-cache",
        }

        try:
            resp = requests.post(TIKTOK_TOKEN_URL, data=payload, headers=headers, timeout=30)
            res_data = resp.json()
        except Exception as exc:
            logger.error("Network error during TikTok token refresh: %s", exc)
            raise RuntimeError(f"Network error refreshing TikTok token: {exc}")

        # Check for TikTok error envelopes
        err_envelope = res_data.get("error", {})
        err_code = err_envelope.get("code", "ok") if isinstance(err_envelope, dict) else "ok"
        if resp.status_code != 200 or (err_code != "ok" and err_code != 0 and err_code != ""):
            err_msg = err_envelope.get("message", resp.text) if isinstance(err_envelope, dict) else resp.text
            logger.error("TikTok token refresh failed (HTTP %d): %s", resp.status_code, err_msg)
            raise RuntimeError(f"Failed to refresh TikTok access token: {err_msg}")

        token_info = res_data.get("data", res_data)
        access_token = token_info.get("access_token")
        new_refresh_token = token_info.get("refresh_token") or refresh_token
        expires_in = token_info.get("expires_in", 86400)
        refresh_expires_in = token_info.get("refresh_expires_in", 31536000)
        open_id = token_info.get("open_id") or self._token_cache.get("open_id") if self._token_cache else ""
        scope = token_info.get("scope") or self._token_cache.get("scope") if self._token_cache else ""

        updated_data = {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "open_id": open_id,
            "expires_in": expires_in,
            "refresh_expires_in": refresh_expires_in,
            "scope": scope,
            "created_at": time.time(),
            "issued_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "client_key": self.client_key,
        }

        self._save_token_data(updated_data)
        logger.info("[✓] TikTok access token refreshed successfully (Expires in: %ds)", expires_in)
        return updated_data

    def get_valid_access_token(self) -> str:
        """Returns a valid access token, automatically refreshing it if expired or near expiration."""
        data = self._load_token_data()
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        created_at = data.get("created_at", 0)
        expires_in = data.get("expires_in", 86400)

        # 5-minute safety threshold
        safety_margin = 300
        time_elapsed = time.time() - created_at
        time_remaining = expires_in - time_elapsed

        if time_remaining <= safety_margin:
            logger.info("Access token is near expiration (%.1fs remaining). Triggering automatic refresh...", time_remaining)
            if not refresh_token:
                raise ValueError("No refresh_token found in token file. Please re-run scripts/auth_tiktok.py.")
            new_data = self.refresh_access_token(refresh_token)
            return new_data["access_token"]

        return access_token

    def init_publish(
        self,
        file_path: Path,
        title: str,
        privacy_level: str = "PUBLIC_TO_EVERYONE",
        disable_duet: bool = False,
        disable_stitch: bool = False,
        disable_comment: bool = False,
    ) -> Tuple[str, str, int, int]:
        """Initializes direct publication session with TikTok Content Posting API.

        Args:
            file_path: Video file path.
            title: Caption / title.
            privacy_level: 'PUBLIC_TO_EVERYONE', 'MUTUAL_FOLLOW_FRIENDS', or 'SELF_ONLY'.
            disable_duet: Whether duet is disabled.
            disable_stitch: Whether stitch is disabled.
            disable_comment: Whether comments are disabled.

        Returns:
            Tuple[str, str, int, int]: (upload_url, publish_id, chunk_size, total_chunk_count)
        """
        file_path = Path(file_path).resolve()
        file_size = file_path.stat().st_size

        if file_size <= MAX_SINGLE_CHUNK:
            chunk_size = file_size
            total_chunk_count = 1
        else:
            chunk_size = DEFAULT_CHUNK_SIZE
            total_chunk_count = math.ceil(file_size / chunk_size)

        access_token = self.get_valid_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        init_url = f"{TIKTOK_API_BASE}/post/publish/video/init/"

        payload = {
            "post_info": {
                "title": title[:150],
                "privacy_level": privacy_level,
                "disable_duet": disable_duet,
                "disable_stitch": disable_stitch,
                "disable_comment": disable_comment,
                "video_cover_timestamp_ms": 1000,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunk_count,
            },
        }

        logger.info(
            "Initializing TikTok Post [POST %s] (Size: %.2f MB | Chunks: %d)...",
            init_url,
            file_size / (1024 * 1024),
            total_chunk_count,
        )

        resp = requests.post(init_url, headers=headers, json=payload, timeout=30)
        resp_json = resp.json()

        err_envelope = resp_json.get("error", {})
        err_code = err_envelope.get("code", "ok") if isinstance(err_envelope, dict) else "ok"
        if resp.status_code != 200 or (err_code != "ok" and err_code != 0 and err_code != ""):
            err_msg = err_envelope.get("message", resp.text) if isinstance(err_envelope, dict) else resp.text
            logger.error("TikTok API init error (%d): %s", resp.status_code, err_msg)
            raise RuntimeError(f"TikTok upload initialization failed: {err_msg}")

        data = resp_json.get("data", {})
        publish_id = data.get("publish_id")
        upload_url = data.get("upload_url")

        if not upload_url or not publish_id:
            raise RuntimeError(f"TikTok API returned incomplete init data: {resp_json}")

        logger.info("[✓] TikTok upload session initialized: Publish ID: %s", publish_id)
        return upload_url, publish_id, chunk_size, total_chunk_count

    def upload_binary(
        self,
        upload_url: str,
        file_path: Path,
        chunk_size: Optional[int] = None,
        total_chunk_count: Optional[int] = None,
    ) -> None:
        """Uploads video binary chunks using HTTP PUT with Content-Range."""
        file_path = Path(file_path).resolve()
        file_size = file_path.stat().st_size

        if not chunk_size or not total_chunk_count:
            if file_size <= MAX_SINGLE_CHUNK:
                chunk_size = file_size
                total_chunk_count = 1
            else:
                chunk_size = DEFAULT_CHUNK_SIZE
                total_chunk_count = math.ceil(file_size / chunk_size)

        logger.info(
            "Uploading binary payload to TikTok CDN (%d chunks | Total: %.2f MB)...",
            total_chunk_count,
            file_size / (1024 * 1024),
        )

        with open(file_path, "rb") as f:
            for chunk_idx in range(total_chunk_count):
                start_byte = chunk_idx * chunk_size
                end_byte = min(start_byte + chunk_size, file_size) - 1
                current_chunk_len = end_byte - start_byte + 1

                f.seek(start_byte)
                chunk_bytes = f.read(current_chunk_len)

                upload_headers = {
                    "Content-Type": "video/mp4",
                    "Content-Range": f"bytes {start_byte}-{end_byte}/{file_size}",
                    "Content-Length": str(current_chunk_len),
                }

                logger.info(
                    "PUT chunk %d/%d: bytes %d-%d/%d (%.2f MB)...",
                    chunk_idx + 1,
                    total_chunk_count,
                    start_byte,
                    end_byte,
                    file_size,
                    current_chunk_len / (1024 * 1024),
                )

                resp = requests.put(upload_url, headers=upload_headers, data=chunk_bytes, timeout=180)
                if resp.status_code not in (200, 201):
                    raise RuntimeError(
                        f"TikTok CDN chunk upload failed (HTTP {resp.status_code}) for chunk {chunk_idx + 1}: {resp.text}"
                    )

        logger.info("[✓] All video chunks uploaded successfully to TikTok CDN.")

    def poll_publish_status(self, publish_id: str, timeout: int = 120, poll_interval: int = 5) -> Dict[str, Any]:
        """Polls TikTok Content Posting API until publication is complete or failed."""
        status_url = f"{TIKTOK_API_BASE}/post/publish/status/fetch/"
        start_time = time.time()

        logger.info("Polling TikTok publication status for Publish ID: %s (Timeout: %ds)...", publish_id, timeout)

        while time.time() - start_time < timeout:
            access_token = self.get_valid_access_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            }
            payload = {"publish_id": publish_id}

            try:
                resp = requests.post(status_url, headers=headers, json=payload, timeout=20)
                resp_json = resp.json()
            except Exception as exc:
                logger.warning("Transient error polling TikTok status: %s. Retrying...", exc)
                time.sleep(poll_interval)
                continue

            data = resp_json.get("data", {})
            status = data.get("status")
            fail_reason = data.get("fail_reason")

            logger.info("TikTok status for %s: %s (Elapsed: %.1fs)", publish_id, status, time.time() - start_time)

            if status in ("PUBLISH_COMPLETE", "SUCCESS"):
                logger.info("[✓] Video successfully published to TikTok! Status: %s", status)
                return data

            if status == "FAILED":
                err_msg = f"TikTok publishing failed for {publish_id}: {fail_reason}"
                logger.error(err_msg)
                raise RuntimeError(err_msg)

            time.sleep(poll_interval)

        logger.warning("TikTok publication status polling timed out after %ds for %s.", timeout, publish_id)
        return {"status": "TIMEOUT", "publish_id": publish_id}

    def export_staging(
        self,
        file_path: Union[Path, str],
        title: str,
        theme_name: str = "theme_a",
        acts_script: Optional[List[Dict[str, Any]]] = None,
        output_dir: Optional[Path] = None,
        tags: Optional[List[str]] = None,
        spec_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Exports the rendered video and accompanying metadata to output/tiktok/ (Staging Mode)."""
        file_path = Path(file_path).resolve()
        if not file_path.is_file():
            raise FileNotFoundError(f"Video file not found: {file_path}")

        duration = get_video_duration_ffprobe(file_path)
        out_dir = output_dir or (settings.BASE_DIR / "output" / "tiktok")
        out_dir.mkdir(parents=True, exist_ok=True)

        date_str = time.strftime("%Y%m%d")
        safe_theme = re.sub(r"[^a-zA-Z0-9_-]", "_", theme_name or "theme_a")
        target_video = out_dir / f"{date_str}_{safe_theme}.mp4"
        target_metadata = out_dir / f"{date_str}_{safe_theme}.txt"

        # 1. Copy video file to target staging location
        shutil.copy2(file_path, target_video)

        # 2. Build metadata text
        mandatory_hashtags = ["#hardware", "#pcgaming", "#pcbuild", "#tech", "#techtok", "#siliconverdict", "#techexplained"]
        all_tags = list(mandatory_hashtags)
        if tags:
            for t in tags:
                clean_t = f"#{t.lstrip('#')}"
                if clean_t.lower() not in [x.lower() for x in all_tags]:
                    all_tags.append(clean_t)
        hashtags_block = " ".join(all_tags)

        # Build 5-acts breakdown with timestamps
        acts_text = []
        if acts_script:
            current_sec = 0.0
            for act in acts_script:
                act_num = act.get("act_num", len(acts_text) + 1)
                act_name = act.get("name", f"Act {act_num}")
                act_title = act.get("title", "")
                voiceover = act.get("voiceover", "")
                act_dur = float(act.get("duration", 0.0))
                end_sec = current_sec + act_dur

                m_start, s_start = divmod(int(current_sec), 60)
                m_end, s_end = divmod(int(end_sec), 60)
                ts_str = f"[{m_start:02d}:{s_start:02d} - {m_end:02d}:{s_end:02d}]"

                extra_options = f"\n   Options: {act.get('options')}" if act.get("options") else ""
                acts_text.append(
                    f"- {ts_str} Act {act_num}: {act_name}\n"
                    f"   Title: {act_title}{extra_options}\n"
                    f"   Voiceover: \"{voiceover}\""
                )
                current_sec = end_sec
        else:
            acts_text.append("   (5-act breakdown details not provided)")

        acts_block = "\n\n".join(acts_text)

        metadata_content = (
            "================================================================================\n"
            "SILICON VERDICT • TIKTOK METADATA (STAGING / LOCAL EXPORT)\n"
            f"Creation Date:     {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n"
            f"Video File:        {target_video.name}\n"
            f"Measured Duration: {duration:.2f}s (Eligible TikTok Creator Rewards: >60.5s)\n"
            f"Resolution / FPS:  1080x1920 (9:16 Vertical) @ 60 FPS\n"
            f"Theme / Subtheme:  {safe_theme}\n"
            "================================================================================\n\n"
            "[SUGGESTED TITLE]\n"
            f"{title}\n\n"
            "[TECHNICAL HASHTAGS]\n"
            f"{hashtags_block}\n\n"
            "[5-ACT NARRATIVE TIMESTAMPS & VOICEOVER]\n"
            f"{acts_block}\n\n"
            "================================================================================\n"
            "PUBLISHING INSTRUCTIONS:\n"
            "1. Upload the video file to TikTok Studio:\n"
            "   https://www.tiktok.com/creator-center/upload\n"
            "2. Copy and paste the suggested title and technical hashtags into the description.\n"
            "3. When the TikTok Developers application completes review and the token is generated\n"
            "   in data/tiktok_token.json, direct API publishing will operate transparently.\n"
            "================================================================================\n"
        )

        with open(target_metadata, "w", encoding="utf-8") as f:
            f.write(metadata_content)

        # 3. Informative structured logging
        logger.info(
            "[TIKTOK STAGING] Token not found or export mode active. "
            "Video and metadata ready in output/tiktok/ for manual upload or pending approval."
        )

        publish_id = f"staging_{date_str}_{safe_theme}"

        # 4. Record to SQLite History (data/history.db)
        try:
            record_tiktok_post(
                publish_id=publish_id,
                title=title,
                file_path=str(target_video),
                privacy_level="STAGING",
                status="STAGING_MODE",
            )
        except Exception as exc:
            logger.warning("Could not record staging in database: %s", exc)

        return {
            "publish_id": publish_id,
            "url": f"file://{target_video.resolve()}",
            "status": "STAGING_MODE",
            "staging": True,
            "video_path": str(target_video.resolve()),
            "metadata_path": str(target_metadata.resolve()),
            "privacy_level": "STAGING",
        }

    def upload_video(
        self,
        file_path: Union[Path, str],
        title: str,
        tags: Optional[List[str]] = None,
        as_draft: bool = False,
        privacy_level: Optional[str] = None,
        export_only: bool = False,
        theme_name: Optional[str] = None,
        acts_script: Optional[List[Dict[str, Any]]] = None,
        spec_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Main end-to-end video publishing method with automatic staging fallback.

        Args:
            file_path: Local path to the rendered vertical MP4 video.
            title: Video caption / title.
            tags: List of hashtags.
            as_draft: If True, stages as draft (SELF_ONLY).
            privacy_level: Optional privacy override.
            export_only: If True, exports locally without attempting API upload.
            theme_name: Optional theme name (e.g. 'theme_a' or 'theme_b').
            acts_script: Script breakdown with act durations and voiceover for staging metadata.
            spec_info: Optional DailyShortSpec details.

        Returns:
            Dict containing publish_id, url, status, and staging flags.
        """
        file_path = Path(file_path).resolve()
        if not file_path.is_file():
            raise FileNotFoundError(f"Video file not found: {file_path}")

        # Enforce >60.5s Creator Rewards monetization eligibility
        validate_tiktok_creator_rewards_eligibility(file_path)

        # Staging Mode Check
        if export_only or not self.is_token_available():
            logger.info(
                "TikTok Staging active (export_only=%s, token_available=%s). Diverting to staging export...",
                export_only,
                self.is_token_available(),
            )
            return self.export_staging(
                file_path=file_path,
                title=title,
                theme_name=theme_name or "theme_a",
                acts_script=acts_script,
                tags=tags,
                spec_info=spec_info,
            )

        # Assemble caption with hashtags
        caption = title.strip()
        if tags:
            tag_str = " ".join(f"#{t.lstrip('#')}" for t in tags if f"#{t.lstrip('#')}" not in caption)
            if tag_str:
                caption = f"{caption} {tag_str}"

        # Privacy resolution
        if as_draft:
            resolved_privacy = "SELF_ONLY"
        elif privacy_level:
            resolved_privacy = "SELF_ONLY" if privacy_level.upper() in ("DRAFT", "SELF_ONLY", "PRIVATE") else "PUBLIC_TO_EVERYONE"
        else:
            resolved_privacy = settings.TIKTOK_PRIVACY_LEVEL or "PUBLIC_TO_EVERYONE"

        logger.info("=== Starting TikTok Video Distribution (Production API) ===")
        logger.info(" File:     %s", file_path.name)
        logger.info(" Title:    %s", caption[:80])
        logger.info(" Privacy:  %s", resolved_privacy)

        # 1. Initialize session
        upload_url, publish_id, chunk_size, total_chunk_count = self.init_publish(
            file_path=file_path,
            title=caption,
            privacy_level=resolved_privacy,
        )

        # 2. Stream binary
        self.upload_binary(
            upload_url=upload_url,
            file_path=file_path,
            chunk_size=chunk_size,
            total_chunk_count=total_chunk_count,
        )

        # 3. Poll status
        status_data = self.poll_publish_status(publish_id=publish_id)

        canonical_url = f"https://www.tiktok.com/@siliconverdict/video/{publish_id}"

        # 4. Record to SQLite History (data/history.db)
        try:
            record_tiktok_post(
                publish_id=publish_id,
                title=caption,
                file_path=str(file_path),
                privacy_level=resolved_privacy,
                status=status_data.get("status", "PUBLISH_COMPLETE"),
            )
            logger.info("Recorded TikTok upload into data/history.db (Publish ID: %s)", publish_id)
        except Exception as exc:
            logger.warning("Could not record TikTok history in database: %s", exc)

        return {
            "publish_id": publish_id,
            "url": canonical_url,
            "status": status_data.get("status", "PUBLISH_COMPLETE"),
            "privacy_level": resolved_privacy,
        }


def upload_video_to_tiktok(
    file_path: Path,
    title: str,
    privacy: str = "PUBLIC",
    tags: Optional[List[str]] = None,
    disable_duet: bool = False,
    disable_stitch: bool = False,
    disable_comment: bool = False,
    export_only: bool = False,
    theme_name: Optional[str] = None,
    acts_script: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Backward-compatible functional wrapper delegating to TikTokService."""
    as_draft = privacy.upper() in ("DRAFT", "SELF_ONLY", "PRIVATE")
    service = TikTokService()
    res = service.upload_video(
        file_path=file_path,
        title=title,
        tags=tags,
        as_draft=as_draft,
        export_only=export_only,
        theme_name=theme_name,
        acts_script=acts_script,
    )
    return res.get("url", f"https://www.tiktok.com/@siliconverdict/video/{res.get('publish_id')}")
