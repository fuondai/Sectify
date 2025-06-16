"""Middleware to append security-related HTTP headers.

These headers help mitigate risks of XSS, click-jacking, and cache-leaking attacks.
"""
from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Append security headers to every response."""

    async def dispatch(self, request, call_next):  # type: ignore[override]
        response = await call_next(request)

        headers = MutableHeaders(response.headers)
        # Do not cache on client / proxy
        headers["Cache-Control"] = "no-store, private"
        # Prevent sending referrer
        headers["Referrer-Policy"] = "no-referrer"
        # Prevent MIME sniffing
        headers["X-Content-Type-Options"] = "nosniff"
        # Basic blocking of XSS, dangerous plugins
        headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "font-src 'self' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "media-src 'self' blob:; object-src 'none';"
        )
        return response
