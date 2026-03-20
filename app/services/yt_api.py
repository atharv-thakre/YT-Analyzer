import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from app.config import get_settings

settings = get_settings()


session = requests.Session()
retry = Retry(
    total=settings.yt_api_retries,
    connect=settings.yt_api_retries,
    read=settings.yt_api_retries,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)
session.mount("http://", adapter)


class YouTubeAPIError(Exception):
    pass

def get_video_details(video_ids):
    if not video_ids:
        return []

    if not settings.youtube_api_key:
        raise YouTubeAPIError("YOUTUBE_API_KEY is missing.")

    url = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "part": "snippet,statistics,contentDetails",
        "id": ",".join(video_ids),
        "key": settings.youtube_api_key
    }

    try:
        res = session.get(url, params=params, timeout=settings.yt_api_timeout)
        res.raise_for_status()
    except requests.RequestException as exc:
        raise YouTubeAPIError(f"Failed to fetch video details: {exc}") from exc

    payload = res.json()
    if "error" in payload:
        message = payload.get("error", {}).get("message", "Unknown YouTube API error")
        raise YouTubeAPIError(message)

    return payload.get("items", [])