import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import requests

from config.settings import settings
from core.schemas import Scene

logger = logging.getLogger(__name__)


@dataclass
class SceneMedia:
    """Metadata container for acquired visual media."""
    scene_id: int
    media_path: str
    media_type: str  # 'video' or 'image'
    duration: float  # Video duration or requested duration for image


BROLL_BLACKLIST = [
    "motherboard",
    "pcb",
    "circuit board",
    "circuit",
    "synthetic",
    "3d render",
    "render",
    "abstract board",
    "generic electronics",
    "electronic component",
    "mother board",
]

APPROVED_BROLL_REPLACEMENTS = [
    "gaming pc benchmark gameplay",
    "semiconductor silicon wafer macro",
    "cyberpunk 2077 gameplay 4k",
    "microchip processor die macro",
    "cinematic cpu die silicon",
    "pc gaming graphics 4k",
]


def sanitize_broll_query(query: str) -> str:
    """Replaces blacklisted queries with high-res gameplay or cinematic silicon macro footage."""
    q_lower = query.lower()
    for bad in BROLL_BLACKLIST:
        if bad in q_lower:
            logger.info("Blacklisted term '%s' detected in query '%s'. Substituting with approved cinematic asset.", bad, query)
            if any(term in q_lower for term in ["chip", "silicon", "die", "wafer", "cpu", "gpu", "hardware"]):
                return "semiconductor silicon wafer macro"
            return "gaming pc benchmark gameplay"
    return query


def is_blacklisted_hit(hit: dict) -> bool:
    """Checks if a stock video hit contains blacklisted tags or keywords."""
    tags = hit.get("tags", "").lower()
    for bad in BROLL_BLACKLIST:
        if bad in tags:
            return True
    return False


def get_video_duration(file_path: str) -> float:
    """Extracts duration of a video file using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return 10.0


def download_file(url: str, dest_path: Path) -> None:
    """Streams a file from a URL to local disk."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def search_and_download_pixabay_video(query: str, target_file: Path) -> Optional[float]:
    """Queries Pixabay Video API for an HD clip and downloads it, enforcing strict blacklist filtering."""
    if not settings.PIXABAY_API_KEY:
        return None

    clean_query = sanitize_broll_query(query)
    queries_to_try = [clean_query]
    if clean_query != "gaming pc benchmark gameplay":
        queries_to_try.append("gaming pc benchmark gameplay")
    queries_to_try.append("semiconductor silicon wafer macro")

    url = "https://pixabay.com/api/videos/"

    for cur_query in queries_to_try:
        params = {
            "key": settings.PIXABAY_API_KEY,
            "q": cur_query,
            "video_type": "all",
            "per_page": 15,
        }

        try:
            response = requests.get(url, params=params, timeout=20)
            if response.status_code != 200:
                logger.warning("Pixabay video API error (%d): %s", response.status_code, response.text)
                continue

            data = response.json()
            hits = data.get("hits", [])
            if not hits:
                continue

            for hit in hits:
                if is_blacklisted_hit(hit):
                    logger.info("Skipping Pixabay video hit %d due to blacklisted tags: '%s'", hit.get("id"), hit.get("tags"))
                    continue

                videos = hit.get("videos", {})
                # Prefer large (1080p) or medium (720p)
                for quality in ["large", "medium", "small"]:
                    v_data = videos.get(quality, {})
                    video_url = v_data.get("url")
                    if video_url:
                        logger.info("Downloading clean Pixabay %s video for '%s' (tags: '%s')", quality, cur_query, hit.get("tags", ""))
                        download_file(video_url, target_file)
                        duration = get_video_duration(str(target_file))
                        return duration

        except Exception as exc:
            logger.warning("Failed querying Pixabay video API for '%s': %s", cur_query, exc)

    return None


def search_and_download_pixabay_image(query: str, target_file: Path) -> bool:
    """Fallback: Queries Pixabay Photo API for a high-res image and downloads it."""
    if not settings.PIXABAY_API_KEY:
        return False

    url = "https://pixabay.com/api/"
    params = {
        "key": settings.PIXABAY_API_KEY,
        "q": query,
        "image_type": "photo",
        "orientation": "horizontal",
        "per_page": 5,
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        if response.status_code != 200:
            logger.warning("Pixabay image API error (%d): %s", response.status_code, response.text)
            return False

        data = response.json()
        hits = data.get("hits", [])
        if hits:
            photo = hits[0]
            image_url = photo.get("largeImageURL") or photo.get("webformatURL")
            if image_url:
                logger.info("Downloading fallback Pixabay image for '%s'", query)
                download_file(image_url, target_file)
                return True
    except Exception as exc:
        logger.warning("Failed querying Pixabay image API for '%s': %s", query, exc)

    return False


def search_and_download_pexels_video(query: str, target_file: Path) -> Optional[float]:
    """Queries Pexels Video API as secondary provider if key configured."""
    if not settings.PEXELS_API_KEY:
        return None

    headers = {"Authorization": settings.PEXELS_API_KEY}
    url = "https://api.pexels.com/videos/search"
    params = {
        "query": query,
        "orientation": "landscape",
        "per_page": 10,
        "size": "medium",
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        if response.status_code != 200:
            return None

        data = response.json()
        videos = data.get("videos", [])
        for video in videos:
            video_files = video.get("video_files", [])
            hd_files = [f for f in video_files if (f.get("width") or 0) >= 1280] or video_files
            if hd_files:
                best_file = max(hd_files, key=lambda f: f.get("width", 0))
                download_url = best_file.get("link")
                if download_url:
                    logger.info("Downloading Pexels video for '%s'", query)
                    download_file(download_url, target_file)
                    return get_video_duration(str(target_file))
    except Exception:
        pass

    return None


def create_fallback_solid_color_image(target_file: Path) -> None:
    """Generates an elegant dark gradient placeholder using FFmpeg if no stock media found."""
    target_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "color=c=0x0a0d12:s=1920x1080:d=1",
        "-vframes", "1",
        str(target_file),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def fetch_media_for_scene(scene: Scene, output_dir: Path, target_duration: float) -> SceneMedia:
    """Finds and downloads the best visual asset for a single scene with multiple fallbacks.

    Priority:
    1. Pixabay Video
    2. Pexels Video (if key configured)
    3. Pixabay Image
    4. Elegant dark placeholder
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    video_dest = output_dir / f"scene_{scene.scene_id:03d}_media.mp4"
    image_dest = output_dir / f"scene_{scene.scene_id:03d}_media.jpg"

    # 1. Search Pixabay Video
    for term in scene.visual_search_terms:
        duration = search_and_download_pixabay_video(term, video_dest)
        if duration and duration > 0:
            return SceneMedia(
                scene_id=scene.scene_id,
                media_path=str(video_dest),
                media_type="video",
                duration=duration,
            )

    # 2. Search Pexels Video fallback
    for term in scene.visual_search_terms:
        duration = search_and_download_pexels_video(term, video_dest)
        if duration and duration > 0:
            return SceneMedia(
                scene_id=scene.scene_id,
                media_path=str(video_dest),
                media_type="video",
                duration=duration,
            )

    # 3. Search Pixabay Image fallback
    for term in scene.visual_search_terms:
        if search_and_download_pixabay_image(term, image_dest):
            return SceneMedia(
                scene_id=scene.scene_id,
                media_path=str(image_dest),
                media_type="image",
                duration=target_duration,
            )

    # 4. Emergency fallback to solid stylish placeholder
    logger.warning("No media found on stock APIs for scene %d; using dark tech placeholder", scene.scene_id)
    create_fallback_solid_color_image(image_dest)
    return SceneMedia(
        scene_id=scene.scene_id,
        media_path=str(image_dest),
        media_type="image",
        duration=target_duration,
    )


def fetch_all_scene_media(scenes: List[Scene], audio_durations: dict[int, float], output_dir: Path) -> List[SceneMedia]:
    """Fetches visual assets for all scenes sequentially."""
    media_list: List[SceneMedia] = []
    for scene in scenes:
        target_duration = audio_durations.get(scene.scene_id, 8.0)
        scene_media = fetch_media_for_scene(scene, output_dir, target_duration)
        media_list.append(scene_media)
    return media_list
