"""Online time verification — silent on offline, re-check on online.

Behavior:
    - On app start, try to fetch the current UTC time from an HTTPS
      response's `Date` header. Compute the offset between real UTC
      and local UTC. Store it.
    - Every 30 minutes, re-sync.
    - If offline (network error), silently fall back to local clock.
      No exceptions, no UI errors.
    - All calls to `now()` / `today()` return the time-corrected values.
    - If the drift exceeds 5 minutes, `status()` reports it so the UI
      can show a small indicator (optional — the app works fine either way).

We use the HTTP `Date` header from any HTTPS site (google.com) because:
    1. It's free and requires no API key.
    2. It works through any proxy that lets HTTPS through.
    3. It's RFC 7231 formatted UTC — trivial to parse.

The offset is stored as a module-level float. This is fine for a
single-user, single-process app. If the app restarts, the offset resets
to zero and re-syncs within a few seconds.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import email.utils
from typing import Optional

import httpx

# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #

_offset_seconds: float = 0.0
_last_sync: Optional[dt.datetime] = None
_last_error: Optional[str] = None
_syncing: bool = False

# Re-sync every 30 minutes.
_RESYNC_INTERVAL = 30 * 60  # seconds
# Timeout for the HTTP HEAD request.
_TIMEOUT = 5.0  # seconds
# Drift threshold for "significant" offset.
_DRIFT_THRESHOLD = 300  # 5 minutes


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


async def sync() -> bool:
    """Fetch online time and store the offset. Returns True on success.

    Never raises — on any error, returns False and keeps the previous
    offset (or zero if never synced).
    """
    global _offset_seconds, _last_sync, _last_error, _syncing
    if _syncing:
        return False  # another sync is in progress
    _syncing = True
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # HEAD request to any HTTPS site — we only need the Date header.
            resp = await client.head("https://www.google.com")
            date_header = resp.headers.get("date")
            if not date_header:
                _last_error = "no Date header in response"
                return False
            api_utc = email.utils.parsedate_to_datetime(date_header)
            if api_utc is None:
                _last_error = "could not parse Date header"
                return False
            # Ensure timezone-aware UTC.
            if api_utc.tzinfo is None:
                api_utc = api_utc.replace(tzinfo=dt.timezone.utc)
            else:
                api_utc = api_utc.astimezone(dt.timezone.utc)

            local_utc = dt.datetime.now(dt.timezone.utc)
            _offset_seconds = (api_utc - local_utc).total_seconds()
            _last_sync = dt.datetime.now(dt.timezone.utc)
            _last_error = None
            return True
    except Exception as exc:
        _last_error = str(exc)[:200]
        return False
    finally:
        _syncing = False


async def sync_loop() -> None:
    """Background loop: sync on start, then every 30 minutes.

    Never raises. Silently retries on failure.
    """
    # Initial sync — don't wait the full interval.
    await sync()
    while True:
        await asyncio.sleep(_RESYNC_INTERVAL)
        await sync()


def now() -> dt.datetime:
    """Time-corrected current datetime (naive, local timezone)."""
    return dt.datetime.now() + dt.timedelta(seconds=_offset_seconds)


def today() -> dt.date:
    """Time-corrected today."""
    return now().date()


def status() -> dict:
    """Return sync status for the UI (optional display)."""
    return {
        "offset_seconds": _offset_seconds,
        "offset_minutes": round(_offset_seconds / 60, 1),
        "last_sync": _last_sync.isoformat() if _last_sync else None,
        "last_error": _last_error,
        "synced": _last_sync is not None,
        "drift_significant": abs(_offset_seconds) > _DRIFT_THRESHOLD,
    }
