"""
Tests for the health endpoint and CORS configuration.
"""
from __future__ import annotations


class TestHealthEndpoint:
    """Tests for GET /api/health."""

    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "model" in data
        assert "root_directory" in data

    def test_health_includes_model_name(self, client):
        resp = client.get("/api/health")
        data = resp.json()
        assert data["model"] == "qwen3:4b"

    def test_health_includes_root_directory(self, client, test_settings):
        resp = client.get("/api/health")
        data = resp.json()
        assert data["root_directory"] == test_settings.slothdesk_root


class TestRootEndpoint:
    """Tests for GET /."""

    def test_root_returns_welcome(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data


class TestCORS:
    """Verify CORS is configured for the local frontend only."""

    def test_cors_allows_localhost_5173(self, client):
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_cors_allows_127_5173(self, client):
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"

    def test_cors_blocks_unknown_origin(self, client):
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Should not include the evil origin
        allow_origin = resp.headers.get("access-control-allow-origin")
        assert allow_origin != "https://evil.example.com"
