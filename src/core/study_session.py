"""Active study session — in-memory state for the start/end study widget.

This is NOT persisted. If the app closes, the active session is lost.
That's acceptable for now — the user can always re-start. A future
version could persist `started_at` to the `settings` table and resume
on next launch.

The session is started from the Home tab (start/end study widget) and
ended from the same place. When ended, the elapsed minutes are saved
as a normal session row via `core.models.create_session`.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

from services import time_sync


STUDY_TYPE_STUDY = "study"
STUDY_TYPE_TEST = "test"


@dataclass
class ActiveSession:
    activity_id: int
    activity_name: str
    study_type: str  # 'study' | 'test'
    started_at: dt.datetime

    def elapsed_seconds(self) -> int:
        return max(0, int((time_sync.now() - self.started_at).total_seconds()))

    def elapsed_minutes(self) -> int:
        # Round up to at least 1 minute so very short sessions still record.
        return max(1, (self.elapsed_seconds() + 59) // 60)


# --------------------------------------------------------------------------- #
# Module-level singleton state
# --------------------------------------------------------------------------- #

_current: Optional[ActiveSession] = None


def get() -> Optional[ActiveSession]:
    """Return the active session, or None."""
    return _current


def is_active() -> bool:
    return _current is not None


def start(activity_id: int, activity_name: str, study_type: str) -> ActiveSession:
    """Start a new session. If one is already active, it's replaced
    (the previous one is discarded — call `end()` first if you want to
    save it)."""
    global _current
    _current = ActiveSession(
        activity_id=activity_id,
        activity_name=activity_name,
        study_type=study_type,
        started_at=time_sync.now(),
    )
    return _current


def end() -> Optional[ActiveSession]:
    """End the current session. Returns the ended session (or None if
    no session was active). The caller is responsible for saving it to
    the database."""
    global _current
    s = _current
    _current = None
    return s


def cancel() -> None:
    """Discard the current session without saving."""
    global _current
    _current = None
