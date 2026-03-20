import yt_dlp

def extract_playlist_info(playlist_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        data = ydl.extract_info(playlist_url, download=False)

    if not data:
        return None

    return {
        "id": data.get("id"),
        "title": data.get("title"),
        "channel": data.get("uploader"),
        "video_ids": [v['id'] for v in data['entries'] if v]
    }