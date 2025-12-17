"""Render endpoint router."""

import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.auth import verify_api_key
from app.config import get_settings
from app.models.schemas import RenderRequest
from app.services.video import (
    download_video,
    get_video_duration,
    get_video_resolution,
    cleanup_files,
    VideoError
)
from app.services.ass_generator import save_ass_file
from app.services.ffmpeg import render_subtitles, RenderError
from app.templates.styles import AVAILABLE_PRESETS

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter()


def cleanup_task(paths: List[Path]):
    """Background task to cleanup temporary files."""
    cleanup_files(*paths)


@router.post(
    "/render",
    response_class=FileResponse,
    summary="Render video with subtitles",
    description="Burns subtitle segments into a video using ASS styling.",
    responses={
        401: {"description": "Invalid or missing API key"},
        400: {"description": "Invalid request or processing error"},
        413: {"description": "Video too long"}
    }
)
async def render_endpoint(
    request: RenderRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """
    Render video with hardcoded subtitles.

    This endpoint:
    1. Downloads the video from the provided URL
    2. Generates ASS subtitle file from segments
    3. Burns subtitles into video using FFmpeg
    4. Returns the rendered video file

    Use the output from /align as the segments input.
    """
    video_path = None
    ass_path = None
    output_path = None

    try:
        # Validate style preset
        if request.style_preset not in AVAILABLE_PRESETS:
            logger.warning(
                f"Unknown preset '{request.style_preset}', using 'tiktok_clean'"
            )

        # Download video
        logger.info(f"Processing render request for {request.video_url}")
        video_path = await download_video(str(request.video_url))

        # Check video duration
        duration = get_video_duration(video_path)
        if duration > settings.max_video_duration:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Video too long ({duration:.1f}s). Maximum is {settings.max_video_duration}s."
            )

        # Get video resolution for style scaling
        resolution = get_video_resolution(video_path)

        # Generate ASS file
        ass_path = video_path.with_suffix(".ass")
        save_ass_file(
            segments=request.segments,
            style_preset=request.style_preset,
            resolution=resolution,
            output_path=ass_path
        )

        # Render video with subtitles
        output_path = await render_subtitles(video_path, ass_path)

        logger.info(f"Render complete: {output_path}")

        # Schedule cleanup after response is sent
        paths_to_cleanup = [p for p in [video_path, ass_path, output_path] if p]
        background_tasks.add_task(cleanup_task, paths_to_cleanup)

        # Return video file
        return FileResponse(
            path=str(output_path),
            media_type="video/mp4",
            filename="subtitled_video.mp4"
        )

    except VideoError as e:
        logger.error(f"Video processing error: {e}")
        cleanup_files(video_path, ass_path, output_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RenderError as e:
        logger.error(f"Render error: {e}")
        cleanup_files(video_path, ass_path, output_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        cleanup_files(video_path, ass_path, output_path)
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in render endpoint: {e}")
        cleanup_files(video_path, ass_path, output_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during rendering"
        )


@router.get(
    "/styles",
    summary="List available style presets",
    description="Returns a list of available subtitle style presets."
)
async def list_styles(api_key: str = Depends(verify_api_key)):
    """Get list of available subtitle style presets."""
    return {
        "presets": AVAILABLE_PRESETS,
        "default": "tiktok_clean"
    }
