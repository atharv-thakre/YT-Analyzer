from pathlib import Path
import time

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import FileResponse , HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from app.config import get_settings, validate_settings
from app.schemas import (
    AnalyzePlaylistResponse,
    ErrorResponse,
    MessageResponse,
)
from app.services.extractor import extract_playlist_info
from database.db_pipeline import process_playlist, get_stale_video_ids , get_playlist_videos, get_playlist_stats, get_all_playlists
from app.services.yt_api import get_video_details, YouTubeAPIError
from app.services.deps import get_db
from database.excel import export_playlist_report

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="YouTube Analysis API")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.on_event("startup")
def startup_validation():
    errors = validate_settings()
    if errors:
        raise RuntimeError("Invalid startup configuration: " + " | ".join(errors))

@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/compare")
def compare_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "compare.html")


@app.get("/health")
def health(db: Session = Depends(get_db)) -> MessageResponse:
    return {"message": "YT Analyzer Running 🚀"}


@app.get("/playlists", response_class=HTMLResponse)
def list_playlists(db: Session = Depends(get_db)):
    playlists = get_all_playlists(db)

    rows = ""
    for p in playlists:
        created_at = p["created_at"].strftime("%Y-%m-%d %H:%M:%S") if p["created_at"] else ""
        rows += f"""
        <tr>
            <td>{p['playlist_id']}</td>
            <td>{p['playlist_title']}</td>
            <td>{p['playlist_channel']}</td>
            <td>{p['declared_total_videos']}</td>
            <td>{p['mapped_videos']}</td>
            <td>{created_at}</td>
            <td><a href="/playlist/{p['playlist_id']}/view" target="_blank">View</a></td>
            <td><a href="/playlist/{p['playlist_id']}/export" target="_blank">Export</a></td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="8" style="text-align:center;">No playlists found.</td>
        </tr>
        """

    return f"""
    <html>
    <head>
        <title>All Playlists</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 20px;
                background: #f5f7fa;
            }}
            h1 {{ margin-bottom: 14px; }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 10px;
                overflow: hidden;
            }}
            th, td {{
                padding: 10px;
                text-align: left;
                border-bottom: 1px solid #ddd;
                vertical-align: top;
            }}
            th {{
                background: #1f4e78;
                color: white;
                position: sticky;
                top: 0;
            }}
            tr:hover {{ background: #f1f1f1; }}
            a {{ color: #1f4e78; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .nav {{
                margin-bottom: 14px;
                display: flex;
                gap: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="nav">
            <a href="/">Analyze</a>
            <a href="/compare">Compare</a>
            <a href="/playlists">Playlists</a>
        </div>
        <h1>All Playlists</h1>
        <table>
            <thead>
                <tr>
                    <th>Playlist ID</th>
                    <th>Title</th>
                    <th>Channel</th>
                    <th>Declared Total Videos</th>
                    <th>Mapped Videos</th>
                    <th>Created At (UTC)</th>
                    <th>View</th>
                    <th>Export</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </body>
    </html>
    """


@app.post(
    "/analyze",
    response_model=AnalyzePlaylistResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def analyze_playlist(
    url: str,
    freshness_hours: int = Query(
        default=settings.freshness_default_hours,
        ge=settings.freshness_min_hours,
        le=settings.freshness_max_hours,
    ),
    db: Session = Depends(get_db),
) -> AnalyzePlaylistResponse:
    
    # 1. Extract playlist metadata & video IDs
    try:
        playlist_info = extract_playlist_info(url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Playlist extraction failed: {exc}") from exc

    if not playlist_info:
        raise HTTPException(status_code=400, detail="Could not extract playlist information.")
    

    video_ids = playlist_info.get("video_ids") or []
    playlist_id = playlist_info.get("id")
    if not playlist_id:
        raise HTTPException(status_code=400, detail="Playlist ID could not be extracted.")
    
    # 2. Identify missing or stale videos
    stale_ids = get_stale_video_ids(db, video_ids, threshold_hours=freshness_hours)
    
    # 3. Fetch missing/stale video details in batches of 50
    all_video_data = []
    if stale_ids:
        try:
            for i in range(0, len(stale_ids), 50):
                batch = stale_ids[i:i + 50]
                batch_data = get_video_details(batch)
                all_video_data.extend(batch_data)
        except YouTubeAPIError as exc:
            raise HTTPException(status_code=502, detail=f"YouTube API error: {exc}") from exc

    # 4. Process & Save to DB
    try:
        result = process_playlist(
            db=db,
            playlist_id=playlist_id,
            playlist_title=playlist_info.get("title") or "Unknown Playlist",
            channel_name=playlist_info.get("channel") or "Unknown Channel",
            video_ids=video_ids,
            video_data=all_video_data
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database processing failed: {exc}") from exc
    

    return result


@app.get("/playlist/{playlist_id}/export")
def export_playlist(
    playlist_id: str,
    db: Session = Depends(get_db)
):
    file_path = f"sheets/{playlist_id}.xlsx"

    file_path = export_playlist_report(db, playlist_id)

    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=file_path
    )


@app.get("/playlist/{playlist_id}/view", response_class=HTMLResponse)
def view_playlist(
    playlist_id: str,
    db: Session = Depends(get_db)
):
    videos = get_playlist_videos(db, playlist_id)
    stats = get_playlist_stats(db, playlist_id)
    if not stats:
        raise HTTPException(status_code=404, detail=f"Playlist not found or has no videos: {playlist_id}")

    # ✅ define BEFORE HTML
    download_url = f"/playlist/{playlist_id}/export"

    rows = ""
    for v in videos:
        rows += f"""
        <tr>
            <td>{v['position']}</td>
            <td>{v['title']}</td>
            <td>{v['channel_name']}</td>
            <td>{v['duration_sec']}</td>
            <td>{v['published_at'].strftime('%Y-%m-%d') if v['published_at'] else ''}</td>
            <td>{v['views']:,}</td>
            <td>{v['likes']:,}</td>
            <td>{v['comments']:,}</td>
        </tr>
        """

    return f"""
    <html>
    <head>
        <title>Playlist Report</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 20px;
                background: #f5f7fa;
            }}

            h1 {{
                margin-bottom: 5px;
            }}

            .top-bar {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }}

            .meta {{
                color: #555;
            }}

            .stats {{
                display: flex;
                gap: 20px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }}

            .card {{
                background: white;
                padding: 15px;
                border-radius: 10px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);
                min-width: 150px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 10px;
                overflow: hidden;
            }}

            th, td {{
                padding: 10px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}

            th {{
                background: #1f4e78;
                color: white;
                position: sticky;
                top: 0;
            }}

            tr:hover {{
                background: #f1f1f1;
            }}

            .download-btn {{
                background: #28a745;
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-weight: bold;
            }}

            .nav {{
                margin-bottom: 14px;
                display: flex;
                gap: 12px;
            }}

            .nav a {{
                color: #1f4e78;
                text-decoration: none;
            }}

            .nav a:hover {{
                text-decoration: underline;
            }}
        </style>
    </head>

    <body>

        <div class="nav">
            <a href="/">Analyze</a>
            <a href="/compare">Compare</a>
            <a href="/playlists">Playlists</a>
        </div>

        <h1>{stats['playlist_title']}</h1>

        <div class="top-bar">
            <div class="meta">
                Channel: {stats['playlist_channel']} <br>
                Playlist ID: {stats['playlist_id']}
            </div>

            <a href="{download_url}" target="_blank">
                <button class="download-btn">
                    ⬇ Download Excel
                </button>
            </a>
        </div>

        <div class="stats">
            <div class="card"><b>Total Videos</b><br>{stats['total_videos']}</div>
            <div class="card"><b>Avg Duration</b><br>{round(stats['avg_duration_sec'],2)}</div>
            <div class="card"><b>Avg Views</b><br>{round(stats['avg_views'],2)}</div>
            <div class="card"><b>Avg Likes</b><br>{round(stats['avg_likes'],2)}</div>
            <div class="card"><b>Avg Comments</b><br>{round(stats['avg_comments'],2)}</div>
            <div class="card"><b>Engagement</b><br>{round(stats['engagement_avg'],4)}</div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Pos</th>
                    <th>Title</th>
                    <th>Channel</th>
                    <th>Duration</th>
                    <th>Published</th>
                    <th>Views</th>
                    <th>Likes</th>
                    <th>Comments</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>

    </body>
    </html>
    """

def compare_stats(s1: dict, s2: dict):
    def compare(val1, val2):
        if val1 is None: val1 = 0
        if val2 is None: val2 = 0

        if val1 > val2:
            return {
                "winner": "p1",
                "diff": val1 - val2
            }
        elif val2 > val1:
            return {
                "winner": "p2",
                "diff": val2 - val1
            }
        else:
            return {
                "winner": "tie",
                "diff": 0
            }

    result = {
        "views": compare(s1["avg_views"], s2["avg_views"]),
        "likes": compare(s1["avg_likes"], s2["avg_likes"]),
        "comments": compare(s1["avg_comments"], s2["avg_comments"]),
        "engagement": compare(s1["engagement_avg"], s2["engagement_avg"]),
        "duration": compare(s1["avg_duration_sec"], s2["avg_duration_sec"]),
    }

    # 🏆 Overall winner
    score = {"p1": 0, "p2": 0}

    for metric in result.values():
        if metric["winner"] == "p1":
            score["p1"] += 1
        elif metric["winner"] == "p2":
            score["p2"] += 1

    if score["p1"] > score["p2"]:
        overall = "p1"
    elif score["p2"] > score["p1"]:
        overall = "p2"
    else:
        overall = "tie"

    return {
        "metrics": result,
        "score": score,
        "overall_winner": overall
    }

@app.get("/compare-playlists")
def compare_playlists_api(
    p1: str = Query(...),
    p2: str = Query(...),
    db: Session = Depends(get_db)
):
    s1 = get_playlist_stats(db, p1)
    s2 = get_playlist_stats(db, p2)

    if not s1:
        raise HTTPException(status_code=404, detail=f"Playlist not found or has no videos: {p1}")
    if not s2:
        raise HTTPException(status_code=404, detail=f"Playlist not found or has no videos: {p2}")

    comparison = compare_stats(s1, s2)

    return {
        "playlist_1": s1,
        "playlist_2": s2,
        "comparison": comparison
    }
