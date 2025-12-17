"""FFmpeg video rendering service."""

import asyncio
import logging
import uuid
from pathlib import Path

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class RenderError(Exception):
    """Custom exception for rendering errors."""
    pass


async def render_subtitles(
    video_path: Path,
    ass_path: Path,
    output_path: Path = None
) -> Path:
    """
    Render video with hardcoded ASS subtitles.

    Args:
        video_path: Path to input video
        ass_path: Path to ASS subtitle file
        output_path: Optional output path. Generated if not provided.

    Returns:
        Path to rendered video

    Raises:
        RenderError: If rendering fails
    """
    if output_path is None:
        temp_dir = Path(settings.temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_id = str(uuid.uuid4())[:8]
        output_path = temp_dir / f"{output_id}_output.mp4"

    # FFmpeg command for burning subtitles
    # Using ass filter for proper ASS rendering
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-i", str(video_path),
        "-vf", f"ass={str(ass_path)}",
        "-c:v", "libx264",  # H.264 video codec
        "-preset", "fast",  # Encoding speed preset
        "-crf", "23",  # Quality (lower = better, 18-28 is good range)
        "-c:a", "aac",  # AAC audio codec
        "-b:a", "128k",  # Audio bitrate
        "-movflags", "+faststart",  # Web optimization
        str(output_path)
    ]

    logger.info(f"Rendering video: {' '.join(cmd)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"FFmpeg render failed: {error_msg}")
            raise RenderError(f"FFmpeg render failed: {error_msg}")

        if not output_path.exists():
            raise RenderError("Output file was not created")

        logger.info(f"Video rendered to {output_path}")
        return output_path

    except FileNotFoundError:
        raise RenderError("FFmpeg not found. Please install FFmpeg.")
    except Exception as e:
        if isinstance(e, RenderError):
            raise
        raise RenderError(f"Rendering failed: {e}")


async def render_subtitles_with_copy(
    video_path: Path,
    ass_path: Path,
    output_path: Path = None
) -> Path:
    """
    Render video with subtitles, trying to copy streams when possible.
    Falls back to re-encoding if copy fails.

    This is faster but may not work with all input formats.

    Args:
        video_path: Path to input video
        ass_path: Path to ASS subtitle file
        output_path: Optional output path

    Returns:
        Path to rendered video
    """
    # Subtitles require video re-encoding (can't use -c:v copy with filters)
    # But we can try to copy audio
    if output_path is None:
        temp_dir = Path(settings.temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_id = str(uuid.uuid4())[:8]
        output_path = temp_dir / f"{output_id}_output.mp4"

    # Try with audio copy first
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vf", f"ass={str(ass_path)}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "copy",  # Try to copy audio
        "-movflags", "+faststart",
        str(output_path)
    ]

    logger.info(f"Rendering video (audio copy): {' '.join(cmd)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0 and output_path.exists():
            logger.info(f"Video rendered with audio copy to {output_path}")
            return output_path

        # Fall back to full re-encode
        logger.warning("Audio copy failed, falling back to full re-encode")
        return await render_subtitles(video_path, ass_path, output_path)

    except Exception:
        return await render_subtitles(video_path, ass_path, output_path)


def check_ffmpeg_available() -> bool:
    """
    Check if FFmpeg is available on the system.

    Returns:
        True if FFmpeg is available
    """
    import subprocess

    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False
