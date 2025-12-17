"""Forced alignment service using Aeneas."""

import json
import logging
import re
import tempfile
import uuid
from pathlib import Path
from typing import List

from app.config import get_settings
from app.models.schemas import Segment

settings = get_settings()
logger = logging.getLogger(__name__)

# Language code mapping for Aeneas
LANGUAGE_MAP = {
    "vie": "vie",  # Vietnamese
    "deu": "deu",  # German
    "eng": "eng",  # English
    "fra": "fra",  # French
    "spa": "spa",  # Spanish
    "ita": "ita",  # Italian
    "por": "por",  # Portuguese
    "rus": "rus",  # Russian
    "zho": "zho",  # Chinese
    "jpn": "jpn",  # Japanese
    "kor": "kor",  # Korean
}


class AlignmentError(Exception):
    """Custom exception for alignment errors."""
    pass


def _split_into_sentences(text: str, max_words: int = 5) -> List[str]:
    """
    Split text into segments for alignment.

    Args:
        text: Input text
        max_words: Maximum words per segment (default: 5)

    Returns:
        List of text segments
    """
    # Get all words from the text
    words = text.strip().split()

    if not words:
        return []

    segments = []

    for i in range(0, len(words), max_words):
        segment = " ".join(words[i:i + max_words])
        segments.append(segment)

    return segments


def _normalize_segments(
    segments: List[Segment],
    max_chars: int = 80,
    max_lines: int = 2
) -> List[Segment]:
    """
    Normalize segments for subtitle display.

    Args:
        segments: Raw aligned segments
        max_chars: Maximum characters per segment
        max_lines: Maximum lines per segment

    Returns:
        Normalized segments
    """
    normalized = []

    for segment in segments:
        text = segment.text.strip()

        # If text is too long, it will be displayed on multiple lines
        # We don't split segments here, just ensure formatting
        if len(text) > max_chars:
            # Find a good break point
            words = text.split()
            lines = []
            current_line = []

            for word in words:
                test_line = " ".join(current_line + [word])
                if len(test_line) <= max_chars // max_lines:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [word]

            if current_line:
                lines.append(" ".join(current_line))

            # Limit to max_lines
            text = "\n".join(lines[:max_lines])

        normalized.append(Segment(
            start=segment.start,
            end=segment.end,
            text=text
        ))

    return normalized


async def forced_align(
    audio_path: Path,
    script_text: str,
    language: str = "vie"
) -> List[Segment]:
    """
    Perform forced alignment of script to audio using Aeneas.

    Args:
        audio_path: Path to the audio file (WAV 16kHz)
        script_text: The script text to align
        language: Language code (vie, deu, eng, etc.)

    Returns:
        List of aligned segments with timing

    Raises:
        AlignmentError: If alignment fails
    """
    # Validate language
    if language not in LANGUAGE_MAP:
        logger.warning(f"Unknown language '{language}', defaulting to 'eng'")
        language = "eng"

    aeneas_lang = LANGUAGE_MAP[language]

    # Split text into sentences
    sentences = _split_into_sentences(script_text)
    if not sentences:
        raise AlignmentError("No sentences found in script text")

    logger.info(f"Aligning {len(sentences)} sentences in {language}")

    # Create temp files for Aeneas
    temp_dir = Path(settings.temp_dir)
    job_id = str(uuid.uuid4())[:8]

    text_file = temp_dir / f"{job_id}_text.txt"
    output_file = temp_dir / f"{job_id}_output.json"

    try:
        # Write sentences to text file (one per line)
        with open(text_file, "w", encoding="utf-8") as f:
            for sentence in sentences:
                f.write(sentence + "\n")

        # Try Aeneas alignment
        try:
            segments = await _run_aeneas(
                audio_path,
                text_file,
                output_file,
                aeneas_lang
            )
        except Exception as e:
            logger.warning(f"Aeneas failed: {e}, using fallback alignment")
            segments = _fallback_alignment(sentences, audio_path)

        # Normalize segments
        segments = _normalize_segments(segments)

        logger.info(f"Alignment complete: {len(segments)} segments")
        return segments

    finally:
        # Cleanup temp files
        for f in [text_file, output_file]:
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass


async def _run_aeneas(
    audio_path: Path,
    text_file: Path,
    output_file: Path,
    language: str
) -> List[Segment]:
    """
    Run Aeneas forced alignment.

    Args:
        audio_path: Path to audio file
        text_file: Path to text file with sentences
        output_file: Path for JSON output
        language: Aeneas language code

    Returns:
        List of aligned segments

    Raises:
        AlignmentError: If Aeneas fails
    """
    import asyncio

    # Aeneas command
    cmd = [
        "python3", "-m", "aeneas.tools.execute_task",
        str(audio_path),
        str(text_file),
        f"task_language={language}|is_text_type=plain|os_task_file_format=json",
        str(output_file)
    ]

    logger.info(f"Running Aeneas: {' '.join(cmd)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise AlignmentError(f"Aeneas failed: {error_msg}")

        # Parse output
        with open(output_file, "r", encoding="utf-8") as f:
            result = json.load(f)

        segments = []
        for fragment in result.get("fragments", []):
            # Skip empty fragments
            text = fragment.get("lines", [""])[0].strip()
            if not text:
                continue

            segments.append(Segment(
                start=float(fragment.get("begin", 0)),
                end=float(fragment.get("end", 0)),
                text=text
            ))

        return segments

    except FileNotFoundError:
        raise AlignmentError("Aeneas not installed. Run: pip install aeneas")
    except json.JSONDecodeError:
        raise AlignmentError("Failed to parse Aeneas output")


def _fallback_alignment(
    sentences: List[str],
    audio_path: Path
) -> List[Segment]:
    """
    Fallback alignment when Aeneas is not available.
    Distributes sentences evenly across audio duration.

    Args:
        sentences: List of sentences to align
        audio_path: Path to audio file

    Returns:
        List of segments with estimated timing
    """
    from app.services.video import get_video_duration

    # Get audio duration
    try:
        # Use ffprobe on audio file
        import subprocess
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
    except Exception:
        # Default fallback
        duration = len(sentences) * 3.0  # ~3 seconds per sentence

    logger.warning(f"Using fallback alignment for {len(sentences)} sentences over {duration}s")

    # Calculate timing based on text length
    total_chars = sum(len(s) for s in sentences)
    if total_chars == 0:
        total_chars = 1

    segments = []
    current_time = 0.0

    for sentence in sentences:
        # Duration proportional to text length
        sentence_duration = (len(sentence) / total_chars) * duration

        # Minimum duration
        sentence_duration = max(sentence_duration, 0.5)

        segments.append(Segment(
            start=round(current_time, 3),
            end=round(current_time + sentence_duration, 3),
            text=sentence
        ))

        current_time += sentence_duration

    return segments
