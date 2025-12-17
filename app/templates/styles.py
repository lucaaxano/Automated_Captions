"""ASS subtitle style presets."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ASSStyle:
    """ASS subtitle style definition."""

    name: str
    fontname: str
    fontsize: int
    primary_color: str  # &HBBGGRR (ASS format, BGR)
    secondary_color: str
    outline_color: str
    back_color: str
    bold: int  # -1 for true, 0 for false
    italic: int
    underline: int
    strikeout: int
    scale_x: int
    scale_y: int
    spacing: int
    angle: float
    border_style: int  # 1 = outline + shadow, 3 = opaque box
    outline: float
    shadow: float
    alignment: int  # 2 = bottom center (numpad style)
    margin_l: int
    margin_r: int
    margin_v: int
    encoding: int

    def to_ass_line(self) -> str:
        """Convert to ASS Style line format."""
        return (
            f"Style: {self.name},{self.fontname},{self.fontsize},"
            f"{self.primary_color},{self.secondary_color},"
            f"{self.outline_color},{self.back_color},"
            f"{self.bold},{self.italic},{self.underline},{self.strikeout},"
            f"{self.scale_x},{self.scale_y},{self.spacing},{self.angle},"
            f"{self.border_style},{self.outline},{self.shadow},"
            f"{self.alignment},{self.margin_l},{self.margin_r},{self.margin_v},"
            f"{self.encoding}"
        )


def get_style_for_resolution(preset_name: str, width: int, height: int) -> ASSStyle:
    """
    Get style adjusted for video resolution.

    Args:
        preset_name: Name of the style preset
        width: Video width
        height: Video height

    Returns:
        ASSStyle adjusted for resolution
    """
    # Base font size scaling
    # Reference: 1080p (1920x1080) = base size
    scale_factor = height / 1080.0

    presets = get_style_presets()

    if preset_name not in presets:
        preset_name = "tiktok_clean"

    style = presets[preset_name]

    # Scale font size and margins
    style.fontsize = int(style.fontsize * scale_factor)
    style.margin_v = int(style.margin_v * scale_factor)
    style.outline = round(style.outline * scale_factor, 1)
    style.shadow = round(style.shadow * scale_factor, 1)

    return style


def get_style_presets() -> Dict[str, ASSStyle]:
    """
    Get all available style presets.

    Returns:
        Dictionary of preset name to ASSStyle
    """
    return {
        "tiktok_clean": ASSStyle(
            name="Default",
            fontname="Inter",
            fontsize=48,  # Will be scaled
            # White color in ASS BGR format: &H00FFFFFF (with alpha)
            primary_color="&H00FFFFFF",
            secondary_color="&H000000FF",
            # Black outline
            outline_color="&H00000000",
            # Semi-transparent black shadow
            back_color="&H80000000",
            bold=-1,  # Bold enabled
            italic=0,
            underline=0,
            strikeout=0,
            scale_x=100,
            scale_y=100,
            spacing=0,
            angle=0.0,
            border_style=1,  # Outline + shadow
            outline=2.5,
            shadow=1.5,
            alignment=2,  # Bottom center
            margin_l=40,
            margin_r=40,
            margin_v=80,  # Will be scaled
            encoding=1
        ),

        "tiktok_bold": ASSStyle(
            name="Default",
            fontname="Inter",
            fontsize=56,
            primary_color="&H00FFFFFF",
            secondary_color="&H000000FF",
            outline_color="&H00000000",
            back_color="&H80000000",
            bold=-1,
            italic=0,
            underline=0,
            strikeout=0,
            scale_x=100,
            scale_y=100,
            spacing=1,
            angle=0.0,
            border_style=1,
            outline=3.0,
            shadow=2.0,
            alignment=2,
            margin_l=40,
            margin_r=40,
            margin_v=100,
            encoding=1
        ),

        "minimal": ASSStyle(
            name="Default",
            fontname="Arial",
            fontsize=40,
            primary_color="&H00FFFFFF",
            secondary_color="&H000000FF",
            outline_color="&H00000000",
            back_color="&H00000000",
            bold=0,
            italic=0,
            underline=0,
            strikeout=0,
            scale_x=100,
            scale_y=100,
            spacing=0,
            angle=0.0,
            border_style=1,
            outline=1.5,
            shadow=0,
            alignment=2,
            margin_l=20,
            margin_r=20,
            margin_v=60,
            encoding=1
        ),
    }


# List of available presets for validation
AVAILABLE_PRESETS = list(get_style_presets().keys())
