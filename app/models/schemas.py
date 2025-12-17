"""Pydantic models for request/response schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class Segment(BaseModel):
    """A single subtitle segment with timing."""

    start: float = Field(..., ge=0, description="Start time in seconds")
    end: float = Field(..., ge=0, description="End time in seconds")
    text: str = Field(..., min_length=1, description="Subtitle text")


class AlignRequest(BaseModel):
    """Request body for /align endpoint."""

    video_url: HttpUrl = Field(..., description="URL to the video file")
    script_text: str = Field(
        ...,
        min_length=1,
        description="The script text to align (UTF-8)"
    )
    language: str = Field(
        default="vie",
        description="Language code (vie, deu, eng)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "video_url": "https://example.com/video.mp4",
                "script_text": "Xin chào. Đây là một ví dụ.",
                "language": "vie"
            }
        }


class AlignResponse(BaseModel):
    """Response body for /align endpoint."""

    segments: List[Segment] = Field(..., description="Aligned subtitle segments")
    duration: float = Field(..., ge=0, description="Total video duration in seconds")
    language: str = Field(..., description="Language used for alignment")


class RenderRequest(BaseModel):
    """Request body for /render endpoint."""

    video_url: HttpUrl = Field(..., description="URL to the video file")
    segments: List[Segment] = Field(
        ...,
        min_length=1,
        description="Subtitle segments from /align"
    )
    style_preset: str = Field(
        default="tiktok_clean",
        description="Style preset name"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "video_url": "https://example.com/video.mp4",
                "segments": [
                    {"start": 0.0, "end": 2.5, "text": "Hello world"},
                    {"start": 2.5, "end": 5.0, "text": "This is an example"}
                ],
                "style_preset": "tiktok_clean"
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str = Field(..., description="Error message")
