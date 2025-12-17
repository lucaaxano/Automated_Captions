"""Video download and processing service."""

import asyncio
import logging
import subprocess
import uuid
from pathlib import Path
from typing import Tuple

import httpx

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class VideoError(Exception):
    """Custom exception for video processing errors."""
    pass


async def download_video(url: str) -> Path:
    """
    Download video from URL to temp directory.

    Args:
        url: URL of the video to download

    Returns:
        Path to the downloaded video file

    Raises:
        VideoError: If download fails
    """
    temp_dir = Path(settings.temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    video_id = str(uuid.uuid4())[:8]
    video_path = temp_dir / f"{video_id}_input.mp4"

    logger.info(f"Downloading video from {url}")

    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(str(url))
            response.raise_for_status()

            with open(video_path, "wb") as f:
                f.write(response.content)

        logger.info(f"Video downloaded to {video_path}")
        return video_path

    except httpx.HTTPError as e:
        raise VideoError(f"Failed to download video: {e}")
    except Exception as e:
        raise VideoError(f"Unexpected error downloading video: {e}")


async def extract_audio(video_path: Path) -> Path:
    """
    Extract audio from video as WAV 16kHz mono.

    Args:
        video_path: Path to the input video

    Returns:
        Path to the extracted audio file

    Raises:
        VideoError: If extraction fails
    """
    audio_path = video_path.with_suffix(".wav")

    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-i", str(video_path),
        "-vn",  # No video
        "-acodec", "pcm_s16le",  # PCM 16-bit
        "-ar", "16000",  # 16kHz sample rate
        "-ac", "1",  # Mono
        str(audio_path)
    ]

    logger.info(f"Extracting audio: {' '.join(cmd)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise VideoError(f"FFmpeg audio extraction failed: {error_msg}")

        logger.info(f"Audio extracted to {audio_path}")
        return audio_path

    except FileNotFoundError:
        raise VideoError("FFmpeg not found. Please install FFmpeg.")
    except Exception as e:
        if isinstance(e, VideoError):
            raise
        raise VideoError(f"Audio extraction failed: {e}")


def get_video_duration(video_path: Path) -> float:
    """
    Get video duration in seconds using ffprobe.

    Args:
        video_path: Path to the video file

    Returns:
        Duration in seconds

    Raises:
        VideoError: If duration cannot be determined
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        duration = float(result.stdout.strip())
        logger.info(f"Video duration: {duration}s")
        return duration

    except FileNotFoundError:
        raise VideoError("FFprobe not found. Please install FFmpeg.")
    except (subprocess.CalledProcessError, ValueError) as e:
        raise VideoError(f"Could not determine video duration: {e}")


def get_video_resolution(video_path: Path) -> Tuple[int, int]:
    """
    Get video resolution (width, height) using ffprobe.

    Args:
        video_path: Path to the video file

    Returns:
        Tuple of (width, height)

    Raises:
        VideoError: If resolution cannot be determined
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0",
        str(video_path)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        width, height = map(int, result.stdout.strip().split("x"))
        logger.info(f"Video resolution: {width}x{height}")
        return width, height

    except FileNotFoundError:
        raise VideoError("FFprobe not found. Please install FFmpeg.")
    except (subprocess.CalledProcessError, ValueError) as e:
        raise VideoError(f"Could not determine video resolution: {e}")


def cleanup_files(*paths: Path) -> None:
    """
    Remove temporary files.

    Args:
        paths: File paths to remove
    """
    for path in paths:
        try:
            if path and path.exists():
                path.unlink()
                logger.debug(f"Cleaned up: {path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {path}: {e}")
