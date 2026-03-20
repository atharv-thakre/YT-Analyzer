from typing import Literal

from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class AnalyzePlaylistResponse(BaseModel):
    playlist_id: str
    total_videos: int
    updated_or_created: int
    cached: int


class AnalyzeVideoResponse(BaseModel):
    status: Literal["updated", "cached"]
    video_id: str


class ErrorResponse(BaseModel):
    detail: str
