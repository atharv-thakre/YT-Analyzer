from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from sqlalchemy import select , func
from typing import List, Dict
import isodate

from database.models import Video, Playlist, PlaylistVideo


def parse_published_at(value: str | None):
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


def safe_int(value, default: int = 0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_stale_video_ids(db: Session, video_ids: list, threshold_hours: int = 24):
    """
    Returns a list of video IDs that are either missing from the DB
    or were fetched more than threshold_hours ago.
    """
    threshold_time = datetime.utcnow() - timedelta(hours=threshold_hours)
    
    # Query for existing videos within the threshold
    fresh_videos = db.query(Video.id).filter(
        Video.id.in_(video_ids),
        Video.fetched_at >= threshold_time
    ).all()
    
    fresh_ids = {v[0] for v in fresh_videos}
    stale_ids = [vid for vid in video_ids if vid not in fresh_ids]
    
    return stale_ids


def upsert_playlist(db: Session, playlist_id: str, title: str, channel_name: str, total_videos: int):
    playlist = db.query(Playlist).filter_by(id=playlist_id).first()

    if not playlist:
        playlist = Playlist(
            id=playlist_id,
            title=title,
            channel_name=channel_name,
            total_videos=total_videos
        )
        db.add(playlist)
    else:
        playlist.title = title
        playlist.channel_name = channel_name
        playlist.total_videos = total_videos

    return playlist


def upsert_video(db: Session, v: dict):
    video_id = v.get("id")
    if not video_id:
        return None

    snippet = v.get("snippet", {})
    statistics = v.get("statistics", {})
    content_details = v.get("contentDetails", {})

    video = db.query(Video).filter_by(id=video_id).first()

    if not video:
        video = Video(
            id=video_id,
            title=snippet.get("title", "Unknown Title"),
            channel_name=snippet.get("channelTitle", "Unknown Channel"),
            published_at=parse_published_at(snippet.get("publishedAt")),

            duration_sec=parse_duration(content_details.get("duration", "PT0S")),

            views=safe_int(statistics.get("viewCount", 0)),
            likes=safe_int(statistics.get("likeCount", 0)),
            comments=safe_int(statistics.get("commentCount", 0)),

            fetched_at=datetime.utcnow()
        )
        db.add(video)
    else:
        video.title = snippet.get("title", video.title)
        video.channel_name = snippet.get("channelTitle", video.channel_name)
        published_at = parse_published_at(snippet.get("publishedAt"))
        if published_at is not None:
            video.published_at = published_at
        video.duration_sec = parse_duration(content_details.get("duration", "PT0S"))

        # update stats
        video.views = safe_int(statistics.get("viewCount", 0))
        video.likes = safe_int(statistics.get("likeCount", 0))
        video.comments = safe_int(statistics.get("commentCount", 0))
        video.fetched_at = datetime.utcnow()

    return video


def insert_playlist_videos(db: Session, playlist_id: str, video_ids: list):
    for position, vid in enumerate(video_ids):
        exists = db.query(PlaylistVideo).filter_by(
            playlist_id=playlist_id,
            video_id=vid
        ).first()

        if not exists:
            db.add(PlaylistVideo(
                playlist_id=playlist_id,
                video_id=vid,
                position=position
            ))
        else:
            # Update position if it changed
            if exists.position != position:
                exists.position = position


def ensure_videos_exist(db: Session, video_ids: list):
    if not video_ids:
        return

    db.flush()

    unique_video_ids = list(dict.fromkeys(video_ids))

    existing_ids = {
        row[0]
        for row in db.query(Video.id).filter(Video.id.in_(unique_video_ids)).all()
    }

    missing_ids = [vid for vid in unique_video_ids if vid not in existing_ids]

    for vid in missing_ids:
        db.add(
            Video(
                id=vid,
                title="Unavailable Video",
                channel_name="Unknown Channel",
                published_at=None,
                duration_sec=0,
                views=0,
                likes=0,
                comments=0,
                fetched_at=datetime.utcnow(),
            )
        )


# 🔥 MAIN PIPELINE
def process_playlist(
    db: Session,
    playlist_id: str,
    playlist_title: str,
    channel_name: str,
    video_ids: list,
    video_data: list
):
    if not playlist_id:
        raise ValueError("Playlist ID is required.")

    try:
        # 1. Upsert playlist
        upsert_playlist(
            db,
            playlist_id,
            playlist_title,
            channel_name,
            total_videos=len(video_ids)
        )

        # 2. Map API data by ID
        video_map = {v["id"]: v for v in video_data if v.get("id")}

        # 3. Process videos (only those provided in video_data)
        for v_info in video_map.values():
            upsert_video(db, v_info)

        # 4. Ensure every playlist video ID has a parent row in videos
        ensure_videos_exist(db, video_ids)
        db.flush()

        # 5. Insert playlist-video mapping
        insert_playlist_videos(db, playlist_id, video_ids)

        # 6. Commit everything
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "playlist_id": playlist_id,
        "total_videos": len(video_ids),
        "updated_or_created": len(video_data),
        "cached": len(video_ids) - len(video_data)
    }


def parse_duration(duration):
    try:
        return int(isodate.parse_duration(duration).total_seconds())
    except (TypeError, ValueError, OverflowError):
        return 0
    


def get_playlist_videos(session: Session, playlist_id: str) -> List[Dict]:
    stmt = (
        select(
            PlaylistVideo.position,
            Video.title,
            Video.channel_name,
            Video.duration_sec,
            Video.published_at,
            Video.views,
            Video.likes,
            Video.comments,
        )
        .join(Video, PlaylistVideo.video_id == Video.id)
        .where(PlaylistVideo.playlist_id == playlist_id)
        .order_by(PlaylistVideo.position)
    )

    results = session.execute(stmt).all()

    return [
        {
            "position": row.position,
            "title": row.title,
            "channel_name": row.channel_name,
            "duration_sec": row.duration_sec,
            "published_at": row.published_at,
            "views": row.views,
            "likes": row.likes,
            "comments": row.comments,
        }
        for row in results
    ]


def get_playlist_stats(session: Session, playlist_id: str):
    stmt = (
        select(
            Playlist.id.label("playlist_id"),
            Playlist.title.label("playlist_title"),
            Playlist.channel_name.label("playlist_channel"),

            func.count(Video.id).label("total_videos"),

            func.avg(Video.views).label("avg_views"),
            func.avg(Video.likes).label("avg_likes"),
            func.avg(Video.comments).label("avg_comments"),
            func.avg(Video.duration_sec).label("avg_duration_sec"),

            func.sum(Video.duration_sec).label("total_duration"),

            func.avg(
                ((Video.likes + Video.comments) * 1000 ) / func.nullif(Video.views, 0)
            ).label("engagement_avg"),
        )
        .join(PlaylistVideo, PlaylistVideo.playlist_id == Playlist.id)
        .join(Video, PlaylistVideo.video_id == Video.id)
        .where(Playlist.id == playlist_id)
        .group_by(Playlist.id)  # important
    )

    result = session.execute(stmt).one_or_none()

    if not result:
        return None

    return {
        "playlist_id": result.playlist_id,
        "playlist_title": result.playlist_title,
        "playlist_channel": result.playlist_channel,

        "total_videos": result.total_videos or 0,

        "avg_views": float(result.avg_views or 0),
        "avg_likes": float(result.avg_likes or 0),
        "avg_comments": float(result.avg_comments or 0),
        "avg_duration_sec": float(result.avg_duration_sec or 0),

        "total_duration_sec": int(result.total_duration or 0),

        "engagement_avg": float(result.engagement_avg or 0),
    }


def get_all_playlists(session: Session) -> List[Dict]:
    stmt = (
        select(
            Playlist.id.label("playlist_id"),
            Playlist.title.label("playlist_title"),
            Playlist.channel_name.label("playlist_channel"),
            Playlist.total_videos.label("declared_total_videos"),
            Playlist.created_at.label("created_at"),
            func.count(PlaylistVideo.video_id).label("mapped_videos"),
        )
        .outerjoin(PlaylistVideo, PlaylistVideo.playlist_id == Playlist.id)
        .group_by(
            Playlist.id,
            Playlist.title,
            Playlist.channel_name,
            Playlist.total_videos,
            Playlist.created_at,
        )
        .order_by(Playlist.created_at.desc())
    )

    results = session.execute(stmt).all()

    return [
        {
            "playlist_id": row.playlist_id,
            "playlist_title": row.playlist_title,
            "playlist_channel": row.playlist_channel,
            "declared_total_videos": row.declared_total_videos or 0,
            "mapped_videos": row.mapped_videos or 0,
            "created_at": row.created_at,
        }
        for row in results
    ]
