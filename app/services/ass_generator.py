"""ASS subtitle file generator."""

import logging
from pathlib import Path
from typing import List, Tuple

from app.models.schemas import Segment
from app.templates.styles import get_style_for_resolution, AVAILABLE_PRESETS

logger = logging.getLogger(__name__)


def _seconds_to_ass_time(seconds: float) -> str:
    """
    Convert seconds to ASS timestamp format (H:MM:SS.cc).

    Args:
        seconds: Time in seconds

    Returns:
        ASS formatted timestamp
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int((seconds % 1) * 100)

    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def _escape_ass_text(text: str) -> str:
    """
    Escape special characters for ASS format.

    Args:
        text: Raw text

    Returns:
        Escaped text safe for ASS
    """
    # Replace newlines with ASS line break
    text = text.replace("\n", "\\N")

    # Escape special ASS characters
    # Note: { } are used for override tags, but we don't escape them
    # as they might be intentionally used

    return text


def generate_ass(
    segments: List[Segment],
    style_preset: str,
    resolution: Tuple[int, int]
) -> str:
    """
    Generate ASS subtitle file content.

    Args:
        segments: List of subtitle segments with timing
        style_preset: Name of the style preset to use
        resolution: Video resolution as (width, height)

    Returns:
        Complete ASS file content as string
    """
    width, height = resolution

    # Validate preset
    if style_preset not in AVAILABLE_PRESETS:
        logger.warning(f"Unknown preset '{style_preset}', using 'tiktok_clean'")
        style_preset = "tiktok_clean"

    # Get style adjusted for resolution
    style = get_style_for_resolution(style_preset, width, height)

    logger.info(f"Generating ASS with style '{style_preset}' for {width}x{height}")

    # Build ASS file
    ass_content = []

    # Script Info section
    ass_content.append("[Script Info]")
    ass_content.append("Title: Generated Subtitles")
    ass_content.append("ScriptType: v4.00+")
    ass_content.append(f"PlayResX: {width}")
    ass_content.append(f"PlayResY: {height}")
    ass_content.append("ScaledBorderAndShadow: yes")
    ass_content.append("YCbCr Matrix: TV.709")
    ass_content.append("")

    # Styles section
    ass_content.append("[V4+ Styles]")
    ass_content.append(
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding"
    )
    ass_content.append(style.to_ass_line())
    ass_content.append("")

    # Events section
    ass_content.append("[Events]")
    ass_content.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

    for segment in segments:
        start_time = _seconds_to_ass_time(segment.start)
        end_time = _seconds_to_ass_time(segment.end)
        text = _escape_ass_text(segment.text)

        # Dialogue line format
        dialogue = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}"
        ass_content.append(dialogue)

    return "\n".join(ass_content)


def save_ass_file(
    segments: List[Segment],
    style_preset: str,
    resolution: Tuple[int, int],
    output_path: Path
) -> Path:
    """
    Generate and save ASS subtitle file.

    Args:
        segments: List of subtitle segments
        style_preset: Style preset name
        resolution: Video resolution
        output_path: Path to save the ASS file

    Returns:
        Path to the saved file
    """
    content = generate_ass(segments, style_preset, resolution)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"ASS file saved to {output_path}")
    return output_path
