"""
Web UI CSP Compliance & Static Assets Unit Test Suite
======================================================
Verifies that the web dashboard HTML has zero inline scripts/styles/handlers,
serves static asset files properly, and sets strict CSP security headers.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_application


@pytest.mark.asyncio
async def test_web_ui_endpoint_returns_clean_html_and_csp_headers() -> None:
    """Verify Web UI endpoint serves clean HTML with strict CSP headers."""
    app = create_application()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

        # Verify CSP header is present and does not contain unsafe-inline
        csp = response.headers.get("Content-Security-Policy", "")
        assert csp != "", "Content-Security-Policy header must be present"
        assert "unsafe-inline" not in csp, "Content-Security-Policy must not allow unsafe-inline"
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "style-src 'self'" in csp

        html = response.text

        # Verify zero inline scripts and zero inline styles
        assert "<script>" not in html, "HTML must not contain inline <script> tags"
        assert "<style>" not in html, "HTML must not contain inline <style> tags"
        assert "onclick=" not in html, "HTML must not contain inline event handlers (onclick)"
        assert "style=" not in html, "HTML must not contain inline style attributes"

        # Verify static asset link and script module references
        assert '<link rel="stylesheet" href="/static/css/styles.css">' in html
        assert '<script type="module" src="/static/js/main.js"></script>' in html


@pytest.mark.asyncio
async def test_static_assets_are_served() -> None:
    """Verify that all static JS modules and CSS stylesheet files are served via FastAPI StaticFiles."""
    app = create_application()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        expected_assets = [
            "/static/css/styles.css",
            "/static/js/main.js",
            "/static/js/api.js",
            "/static/js/utils.js",
            "/static/js/tabs.js",
            "/static/js/health.js",
            "/static/js/ocr.js",
            "/static/js/search.js",
            "/static/js/rag.js",
            "/static/js/workflow.js",
        ]

        for asset_path in expected_assets:
            res = await client.get(asset_path)
            assert res.status_code == 200, f"Asset '{asset_path}' failed to load with status {res.status_code}"
            assert len(res.content) > 0, f"Asset '{asset_path}' is empty"
