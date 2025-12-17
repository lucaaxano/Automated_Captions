"""Tests for the render endpoint and related services."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings
from app.models.schemas import Segment
from app.services.ass_generator import (
    generate_ass,
    _seconds_to_ass_time,
    _escape_ass_text
)
from app.templates.styles import (
    get_style_presets,
    get_style_for_resolution,
    AVAILABLE_PRESETS
)


settings = get_settings()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def api_key():
    """Get API key for tests."""
    return settings.api_key


@pytest.fixture
def sample_segments():
    """Create sample segments for testing."""
    return [
        Segment(start=0.0, end=2.5, text="Hello world"),
        Segment(start=2.5, end=5.0, text="This is a test"),
        Segment(start=5.0, end=7.5, text="Goodbye")
    ]


class TestTimeConversion:
    """Tests for ASS time format conversion."""

    def test_zero_seconds(self):
        """Test converting 0 seconds."""
        assert _seconds_to_ass_time(0.0) == "0:00:00.00"

    def test_simple_seconds(self):
        """Test converting simple seconds."""
        assert _seconds_to_ass_time(5.5) == "0:00:05.50"

    def test_minutes(self):
        """Test converting minutes."""
        assert _seconds_to_ass_time(65.25) == "0:01:05.25"

    def test_hours(self):
        """Test converting hours."""
        assert _seconds_to_ass_time(3665.0) == "1:01:05.00"

    def test_centiseconds(self):
        """Test centisecond precision."""
        assert _seconds_to_ass_time(1.99) == "0:00:01.99"


class TestTextEscaping:
    """Tests for ASS text escaping."""

    def test_simple_text(self):
        """Test simple text without escaping."""
        assert _escape_ass_text("Hello world") == "Hello world"

    def test_newline_conversion(self):
        """Test newline to ASS line break."""
        assert _escape_ass_text("Line 1\nLine 2") == "Line 1\\NLine 2"

    def test_multiple_newlines(self):
        """Test multiple newlines."""
        text = "Line 1\nLine 2\nLine 3"
        result = _escape_ass_text(text)
        assert result == "Line 1\\NLine 2\\NLine 3"


class TestStylePresets:
    """Tests for style presets."""

    def test_available_presets(self):
        """Test that presets are available."""
        presets = get_style_presets()
        assert "tiktok_clean" in presets
        assert len(AVAILABLE_PRESETS) > 0

    def test_style_has_required_fields(self):
        """Test that styles have required fields."""
        presets = get_style_presets()
        style = presets["tiktok_clean"]
        assert style.fontname
        assert style.fontsize > 0
        assert style.alignment > 0

    def test_resolution_scaling(self):
        """Test that styles scale with resolution."""
        style_1080p = get_style_for_resolution("tiktok_clean", 1920, 1080)
        style_720p = get_style_for_resolution("tiktok_clean", 1280, 720)

        # 720p should have smaller font
        assert style_720p.fontsize < style_1080p.fontsize

    def test_unknown_preset_fallback(self):
        """Test that unknown preset falls back to tiktok_clean."""
        style = get_style_for_resolution("nonexistent", 1920, 1080)
        assert style is not None
        assert style.fontsize > 0


class TestASSGeneration:
    """Tests for ASS file generation."""

    def test_generate_ass_structure(self, sample_segments):
        """Test that generated ASS has correct structure."""
        ass_content = generate_ass(
            segments=sample_segments,
            style_preset="tiktok_clean",
            resolution=(1920, 1080)
        )

        # Check sections exist
        assert "[Script Info]" in ass_content
        assert "[V4+ Styles]" in ass_content
        assert "[Events]" in ass_content

    def test_generate_ass_contains_segments(self, sample_segments):
        """Test that ASS contains all segments."""
        ass_content = generate_ass(
            segments=sample_segments,
            style_preset="tiktok_clean",
            resolution=(1920, 1080)
        )

        # Check all segment texts are present
        for segment in sample_segments:
            assert segment.text in ass_content

    def test_generate_ass_dialogue_format(self, sample_segments):
        """Test that dialogues have correct format."""
        ass_content = generate_ass(
            segments=sample_segments,
            style_preset="tiktok_clean",
            resolution=(1920, 1080)
        )

        # Check dialogue lines exist
        dialogue_count = ass_content.count("Dialogue:")
        assert dialogue_count == len(sample_segments)


class TestRenderEndpoint:
    """Tests for the /render endpoint."""

    def test_render_missing_api_key(self, client, sample_segments):
        """Test that missing API key returns 401."""
        response = client.post(
            "/render",
            json={
                "video_url": "https://example.com/video.mp4",
                "segments": [s.model_dump() for s in sample_segments]
            }
        )
        assert response.status_code == 401

    def test_render_invalid_api_key(self, client, sample_segments):
        """Test that invalid API key returns 401."""
        response = client.post(
            "/render",
            headers={"X-API-Key": "wrong-key"},
            json={
                "video_url": "https://example.com/video.mp4",
                "segments": [s.model_dump() for s in sample_segments]
            }
        )
        assert response.status_code == 401

    def test_render_missing_segments(self, client, api_key):
        """Test that missing segments returns 422."""
        response = client.post(
            "/render",
            headers={"X-API-Key": api_key},
            json={
                "video_url": "https://example.com/video.mp4"
            }
        )
        assert response.status_code == 422

    def test_render_empty_segments(self, client, api_key):
        """Test that empty segments list returns 422."""
        response = client.post(
            "/render",
            headers={"X-API-Key": api_key},
            json={
                "video_url": "https://example.com/video.mp4",
                "segments": []
            }
        )
        assert response.status_code == 422


class TestStylesEndpoint:
    """Tests for the /styles endpoint."""

    def test_list_styles_requires_auth(self, client):
        """Test that /styles requires authentication."""
        response = client.get("/styles")
        assert response.status_code == 401

    def test_list_styles_success(self, client, api_key):
        """Test successful styles listing."""
        response = client.get(
            "/styles",
            headers={"X-API-Key": api_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert "default" in data
        assert data["default"] == "tiktok_clean"
