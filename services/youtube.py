import http.client
import logging
import random
import time
from pathlib import Path
from typing import List, Optional

import httplib2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from config.settings import settings

logger = logging.getLogger(__name__)

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
RETRIABLE_EXCEPTIONS = (
    httplib2.HttpLib2Error,
    IOError,
    http.client.NotConnected,
    http.client.IncompleteRead,
    http.client.ImproperConnectionState,
    http.client.CannotSendRequest,
    http.client.CannotSendHeader,
    http.client.ResponseNotReady,
    http.client.BadStatusLine,
)
MAX_RETRIES = 10
DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024  # 5MB chunks for resumable upload


class YouTubeService:
    """Manages YouTube Data API v3 authentication, automatic token refresh, and resumable video uploads."""

    def __init__(self, token_path: Optional[str] = None):
        if token_path:
            self.token_file = Path(token_path)
        else:
            self.token_file = settings.resolve_token_path()

        self._client: Optional[Resource] = None

    def get_authenticated_client(self) -> Resource:
        """Loads credentials from token.json, auto-refreshes expired tokens, and builds the YouTube client."""
        if self._client is not None:
            return self._client

        if not self.token_file.is_file():
            raise FileNotFoundError(
                f"YouTube token file not found at: {self.token_file.resolve()}.\n"
                "Execute 'python scripts/authenticate_yt.py' on your local workstation to generate token.json."
            )

        logger.info("Loading YouTube OAuth credentials from: %s", self.token_file)
        credentials = Credentials.from_authorized_user_file(str(self.token_file), YOUTUBE_SCOPES)

        # Refresh token automatically if expired
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                logger.info("Access token has expired. Initiating automatic refresh with Google OAuth server...")
                try:
                    credentials.refresh(Request())
                    # Persist refreshed token back to disk
                    with open(self.token_file, "w", encoding="utf-8") as f:
                        f.write(credentials.to_json())
                    logger.info("YouTube OAuth token successfully refreshed and saved to disk.")
                except Exception as exc:
                    logger.error("Failed to automatically refresh OAuth token: %s", exc)
                    raise PermissionError(f"OAuth token refresh failed: {exc}") from exc
            else:
                raise PermissionError(
                    "YouTube credentials are invalid or lack a refresh token. "
                    "Re-run 'python scripts/authenticate_yt.py' with prompt='consent'."
                )

        self._client = build("youtube", "v3", credentials=credentials)
        return self._client

    def upload_video(
        self,
        file_path: str,
        title: str,
        description: str,
        tags: List[str],
        privacy_status: str = "private",
        is_short: bool = False,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> str:
        """Uploads a video to YouTube using chunked resumable upload with exponential backoff.

        Args:
            file_path: Local path to the .mp4 video file.
            title: Video title (max 100 characters).
            description: Video description (max 5000 characters).
            tags: SEO keyword tags.
            privacy_status: 'private', 'unlisted', or 'public'.
            is_short: If True, validates/appends #Shorts tag in title/description.
            chunk_size: Byte size per upload chunk (default 5MB).

        Returns:
            str: Direct YouTube video URL (https://youtu.be/{video_id}).
        """
        video_path = Path(file_path)
        if not video_path.is_file():
            raise FileNotFoundError(f"Video file to upload does not exist: {file_path}")

        youtube = self.get_authenticated_client()

        # Format title & description for Shorts compliance
        final_title = title.strip()
        final_description = description.strip()

        if is_short:
            if "#Shorts" not in final_title and "#shorts" not in final_title:
                if len(final_title) <= 92:
                    final_title = f"{final_title} #Shorts"
            if "#Shorts" not in final_description and "#shorts" not in final_description:
                final_description = f"{final_description}\n\n#Shorts #SiliconVerdict #Tech"

        # Apply YouTube character limits
        safe_title = final_title[:100]
        safe_description = final_description[:5000]
        safe_tags = tags[:50]

        body = {
            "snippet": {
                "title": safe_title,
                "description": safe_description,
                "tags": safe_tags,
                "categoryId": settings.YOUTUBE_CATEGORY_ID,  # Category 28: Science & Technology
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            str(video_path),
            mimetype="video/*",
            chunksize=chunk_size,
            resumable=True,
        )

        insert_request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media,
        )

        logger.info(
            "Starting resumable upload: '%s' | Size: %.2f MB | Privacy: %s",
            safe_title,
            video_path.stat().st_size / (1024 * 1024),
            privacy_status,
        )

        response = None
        retry_count = 0

        while response is None:
            try:
                status, response = insert_request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info("Upload progress for '%s': %d%%", safe_title, progress)
            except HttpError as exc:
                status_code = exc.resp.status
                error_details = exc._get_reason()
                if status_code in RETRIABLE_STATUS_CODES:
                    retry_count += 1
                    if retry_count > MAX_RETRIES:
                        logger.error("Max HTTP retries exceeded uploading video. Status: %d", status_code)
                        raise RuntimeError(f"Max retries reached: {status_code} - {error_details}") from exc
                    sleep_seconds = (2 ** retry_count) + random.uniform(0.5, 1.5)
                    logger.warning(
                        "Retriable HTTP error %d: '%s'. Retrying in %.1fs (attempt %d/%d)...",
                        status_code, error_details, sleep_seconds, retry_count, MAX_RETRIES
                    )
                    time.sleep(sleep_seconds)
                else:
                    logger.error("Fatal non-retriable YouTube API error (status %d): %s", status_code, error_details)
                    raise
            except RETRIABLE_EXCEPTIONS as exc:
                retry_count += 1
                if retry_count > MAX_RETRIES:
                    logger.error("Max network retries exceeded uploading video.")
                    raise RuntimeError(f"Max network retries reached: {exc}") from exc
                sleep_seconds = (2 ** retry_count) + random.uniform(0.5, 1.5)
                logger.warning(
                    "Network connection issue: '%s'. Retrying in %.1fs (attempt %d/%d)...",
                    exc, sleep_seconds, retry_count, MAX_RETRIES
                )
                time.sleep(sleep_seconds)

        video_id = response.get("id")
        video_url = f"https://youtu.be/{video_id}"
        logger.info("SUCCESS: Video uploaded to YouTube! Video ID: %s | URL: %s", video_id, video_url)
        return video_url


# Global service instance and backward-compatibility wrapper
youtube_service = YouTubeService()


def upload_video_resumable(
    file_path: str,
    title: str,
    description: str,
    tags: List[str],
    privacy_status: Optional[str] = None,
    is_short: bool = False,
) -> str:
    """Convenience functional wrapper around YouTubeService.upload_video."""
    privacy = privacy_status or settings.YOUTUBE_PRIVACY_STATUS
    return youtube_service.upload_video(
        file_path=file_path,
        title=title,
        description=description,
        tags=tags,
        privacy_status=privacy,
        is_short=is_short,
    )
