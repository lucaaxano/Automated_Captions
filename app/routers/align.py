"""Alignment endpoint router."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import verify_api_key
from app.config import get_settings
from app.models.schemas import AlignRequest, AlignResponse
from app.services.video import (
    download_video,
    extract_audio,
    get_video_duration,
    cleanup_files,
    VideoError
)
from app.services.alignment import forced_align, AlignmentError

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/align",
    response_model=AlignResponse,
    summary="Forced alignment of script to audio",
    description="Aligns a script text to the audio track of a video, returning timed subtitle segments.",
    responses={
        401: {"description": "Invalid or missing API key"},
        400: {"description": "Invalid request or processing error"},
        413: {"description": "Video too long"}
    }
)
async def align_endpoint(
    request: AlignRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Perform forced alignment of script text to video audio.

    This endpoint:
    1. Downloads the video from the provided URL
    2. Extracts the audio track
    3. Performs forced alignment using Aeneas
    4. Returns timed subtitle segments

    The script text should be the exact text spoken in the video.
    """
    video_path = None
    audio_path = None

    try:
        # Download video
        logger.info(f"Processing align request for {request.video_url}")
        video_path = await download_video(str(request.video_url))

        # Check video duration
        duration = get_video_duration(video_path)
        if duration > settings.max_video_duration:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Video too long ({duration:.1f}s). Maximum is {settings.max_video_duration}s."
            )

        # Extract audio
        audio_path = await extract_audio(video_path)

        # Perform alignment
        segments = await forced_align(
            audio_path,
            request.script_text,
            request.language
        )

        if not segments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No segments could be aligned. Check your script text."
            )

        logger.info(f"Alignment complete: {len(segments)} segments")

        return AlignResponse(
            segments=segments,
            duration=duration,
            language=request.language
        )

    except VideoError as e:
        logger.error(f"Video processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AlignmentError as e:
        logger.error(f"Alignment error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in align endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during alignment"
        )
    finally:
        # Cleanup temporary files
        cleanup_files(video_path, audio_path)
