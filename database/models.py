from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


# =========================
# 🎥 Video Table
# =========================
class Video(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True)  # YouTube video ID

    title = Column(Text, nullable=False)
    channel_name = Column(Text)
    published_at = Column(DateTime)

    duration_sec = Column(Integer)

    views = Column(BigInteger, default=0)
    likes = Column(BigInteger, default=0)
    comments = Column(BigInteger, default=0)

    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # relationship
    playlists = relationship(
        "PlaylistVideo",
        back_populates="video",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_video_channel", "channel_name"),
        Index("idx_video_views", "views"),
    )


# =========================
# 📋 Playlist Table
# =========================
class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(String, primary_key=True)  # Playlist ID

    title = Column(Text, nullable=False)
    channel_name = Column(Text)

    total_videos = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # relationship
    videos = relationship(
        "PlaylistVideo",
        back_populates="playlist",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_playlist_channel", "channel_name"),
    )


# =========================
# 🔗 Playlist ↔ Video Mapping
# =========================
class PlaylistVideo(Base):
    __tablename__ = "playlist_videos"

    id = Column(Integer, primary_key=True, autoincrement=True)

    playlist_id = Column(
        String,
        ForeignKey("playlists.id", ondelete="CASCADE"),
        nullable=False
    )

    video_id = Column(
        String,
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False
    )

    position = Column(Integer, nullable=False)  # order in playlist

    # relationships
    playlist = relationship("Playlist", back_populates="videos")
    video = relationship("Video", back_populates="playlists")

    __table_args__ = (
        UniqueConstraint("playlist_id", "video_id", name="unique_playlist_video"),
        Index("idx_playlist_position", "playlist_id", "position"),
    )