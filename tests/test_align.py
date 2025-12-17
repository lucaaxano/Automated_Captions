"""Tests for the align endpoint and alignment service."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings
from app.models.schemas import Segment
from app.services.alignment import _split_into_sentences, _normalize_segments


# Test settings override
settings = get_settings()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def api_key():
    """Get API key for tests."""
    return settings.api_key


class TestSentenceSplitting:
    """Tests for sentence splitting utility."""

    def test_split_simple_sentences(self):
        """Test splitting simple sentences."""
        text = "Hello world. This is a test. Another sentence!"
        sentences = _split_into_sentences(text)
        assert len(sentences) == 3
        assert sentences[0] == "Hello world."
        assert sentences[1] == "This is a test."
        assert sentences[2] == "Another sentence!"

    def test_split_vietnamese_text(self):
        """Test splitting Vietnamese text."""
        text = "Xin chào. Đây là một ví dụ. Cảm ơn bạn!"
        sentences = _split_into_sentences(text)
        assert len(sentences) == 3

    def test_split_empty_text(self):
        """Test splitting empty text."""
        sentences = _split_into_sentences("")
        assert len(sentences) == 0

    def test_split_single_sentence(self):
        """Test splitting single sentence."""
        text = "Just one sentence."
        sentences = _split_into_sentences(text)
        assert len(sentences) == 1
        assert sentences[0] == "Just one sentence."


class TestSegmentNormalization:
    """Tests for segment normalization."""

    def test_normalize_short_segments(self):
        """Test that short segments are not modified."""
        segments = [
            Segment(start=0.0, end=2.0, text="Short text"),
            Segment(start=2.0, end=4.0, text="Another short")
        ]
        normalized = _normalize_segments(segments)
        assert len(normalized) == 2
        assert normalized[0].text == "Short text"

    def test_normalize_long_segment(self):
        """Test that long segments are split into lines."""
        long_text = "This is a very long segment that should be split into multiple lines for better readability on screen"
        segments = [Segment(start=0.0, end=5.0, text=long_text)]
        normalized = _normalize_segments(segments, max_chars=80, max_lines=2)
        assert len(normalized) == 1
        # Should contain line break
        assert "\n" in normalized[0].text or len(normalized[0].text) <= 80


class TestAlignEndpoint:
    """Tests for the /align endpoint."""

    def test_align_missing_api_key(self, client):
        """Test that missing API key returns 401."""
        response = client.post(
            "/align",
            json={
                "video_url": "https://example.com/video.mp4",
                "script_text": "Hello world"
            }
        )
        assert response.status_code == 401

    def test_align_invalid_api_key(self, client):
        """Test that invalid API key returns 401."""
        response = client.post(
            "/align",
            headers={"X-API-Key": "wrong-key"},
            json={
                "video_url": "https://example.com/video.mp4",
                "script_text": "Hello world"
            }
        )
        assert response.status_code == 401

    def test_align_invalid_url(self, client, api_key):
        """Test that invalid URL returns 422."""
        response = client.post(
            "/align",
            headers={"X-API-Key": api_key},
            json={
                "video_url": "not-a-url",
                "script_text": "Hello world"
            }
        )
        assert response.status_code == 422

    def test_align_missing_script(self, client, api_key):
        """Test that missing script returns 422."""
        response = client.post(
            "/align",
            headers={"X-API-Key": api_key},
            json={
                "video_url": "https://example.com/video.mp4"
            }
        )
        assert response.status_code == 422


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_check(self, client):
        """Test health check returns ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_returns_info(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "endpoints" in data
