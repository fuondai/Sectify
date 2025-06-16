"""Utility functions for generating and verifying short-lived signed URLs (JWT) for HLS resources.

Goal: allow public access for "listening" but prevent casual downloading and link sharing.
Tokens are short-lived (5 mins), bound to the track_id (and optionally IP).
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from jose import jwt

from app.core.config import SECRET_KEY, ALGORITHM

TOKEN_EXPIRE_MINUTES_DEFAULT = 2  # reduced TTL to strengthen anti-scraping


def create_track_token(
    track_id: str,
    ip: Optional[str] = None,
    *,
    range_header: Optional[str] = None,
    expires_minutes: int = TOKEN_EXPIRE_MINUTES_DEFAULT,
) -> str:
    """Create a JWT for an HLS track.

    Args:
        track_id: Track ID.
        ip: Client IP address (optional binding).
        expires_minutes: TTL.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "track_id": track_id,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    if ip:
        payload["ip"] = ip
    if range_header:
        payload["rng"] = range_header
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_track_token(
    token: str,
    track_id: str,
    *,
    ip: Optional[str] = None,
    range_header: Optional[str] = None,
) -> None:
    """Verify a JWT, raising HTTPException 403/401 on failure."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from None

    if payload.get("track_id") != track_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token track mismatch")

    if ip and payload.get("ip") and payload["ip"] != ip:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="IP mismatch")

    if payload.get("rng") and (range_header or "") != payload["rng"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Range header mismatch")

    # Expiration is checked automatically by jose.
