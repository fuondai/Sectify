"""HLS segment cleanup utility.

This background task automatically deletes old `.ts` files to save storage space.
Designed to be safe:
- Only deletes segments older than `age_seconds` (default: 10 mins).
- Preserves playlists (.m3u8), keys (.key), and other metadata files.
- Removes empty directories after deleting segments.
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
from typing import Final

logger = logging.getLogger(__name__)

# Root directory for HLS content
HLS_DIRECTORY: Final[str] = "hls"

# Segment file extension
_SEGMENT_EXT: Final[str] = ".ts"

async def cleanup_loop(interval_seconds: int = 120, age_seconds: int = 600) -> None:
    """Asynchronous loop that deletes old segments.

    Args:
        interval_seconds: How often to check, default 2 minutes.
        age_seconds: Files older than this will be deleted, default 10 minutes.
    """
    logger.info("Starting HLS cleanup task: every %ss, delete segments older than %ss", interval_seconds, age_seconds)
    try:
        while True:
            # Run _cleanup_once in a thread to avoid blocking the event loop
            await asyncio.to_thread(_cleanup_once, age_seconds)
            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        logger.info("HLS cleanup task cancelled")
        raise


def _cleanup_once(age_seconds: int) -> None:
    """Performs a single pass to delete expired segments."""
    now = time.time()
    for root, dirs, files in os.walk(HLS_DIRECTORY, topdown=False):
        # Delete old .ts files
        for file in files:
            if not file.endswith(_SEGMENT_EXT):
                continue
            path = os.path.join(root, file)
            try:
                if now - os.path.getmtime(path) > age_seconds:
                    os.remove(path)
                    logger.debug("Removed old segment %s", path)
            except FileNotFoundError:
                # File might have been deleted by another process
                continue
            except Exception as exc:
                logger.error("Failed to remove segment %s: %s", path, exc)

        # After processing files, remove empty directories (except HLS root)
        if root == HLS_DIRECTORY:
            continue
        try:
            if not os.listdir(root):
                shutil.rmtree(root, ignore_errors=True)
                logger.debug("Removed empty HLS directory %s", root)
        except FileNotFoundError:
            continue
        except Exception as exc:
            logger.error("Failed to remove directory %s: %s", root, exc)
