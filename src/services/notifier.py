"""Notification service — periodic "درس می‌خوانی؟" reminder with quiet hours.

Behavior:
    - Every `interval` minutes (default 30), check if it's time to notify.
    - If notifications are disabled → skip.
    - If inside quiet hours → skip.
    - If a study session is currently active → skip (user is already studying).
    - If the user said "آره" recently (within 1 hour) → skip.
    - If the user said "نه" recently (within 10 minutes) → skip.
    - Otherwise → play the chime + show a modal asking "درس می‌خوانی؟".

The modal has two buttons:
    - "آره" → silenced for 1 hour.
    - "نه"  → next check in 10 minutes.

All settings are persisted in the `settings` table so they survive
app restarts.

Platform note:
    In v0.1 this shows an in-app modal dialog (works on web/desktop/Android
    while the app is open). True system notifications (visible from the
    notification bar when the app is in the background) require a native
    Android plugin — deferred to v0.2. The logic (timing, quiet hours,
    yes/no behavior) is identical either way.
"""
from __future__ import annotations

import asyncio
import datetime as dt
from typing import Optional

import flet as ft

from core import models, study_session
from services import time_sync

# --------------------------------------------------------------------------- #
# Settings keys (stored in the `settings` table)
# --------------------------------------------------------------------------- #

KEY_ENABLED = "notif_enabled"
KEY_QUIET_START = "notif_quiet_start"  # "HH:MM"
KEY_QUIET_END = "notif_quiet_end"      # "HH:MM"
KEY_INTERVAL = "notif_interval_minutes"  # "30"
KEY_SILENCED_UNTIL = "notif_silenced_until"  # ISO datetime or ""
KEY_NEXT_CHECK_AT = "notif_next_check_at"    # ISO datetime or ""

DEFAULTS = {
    KEY_ENABLED: "0",          # disabled by default — user opts in
    KEY_QUIET_START: "23:00",
    KEY_QUIET_END: "07:00",
    KEY_INTERVAL: "30",
    KEY_SILENCED_UNTIL: "",
    KEY_NEXT_CHECK_AT: "",
}


# --------------------------------------------------------------------------- #
# Settings helpers
# --------------------------------------------------------------------------- #


def _get(key: str) -> str:
    val = models.get_setting(key)
    return val if val is not None else DEFAULTS.get(key, "")


def _set(key: str, value: str) -> None:
    models.set_setting(key, value)


def is_enabled() -> bool:
    return _get(KEY_ENABLED) == "1"


def set_enabled(enabled: bool) -> None:
    _set(KEY_ENABLED, "1" if enabled else "0")


def get_quiet_start() -> str:
    return _get(KEY_QUIET_START)


def get_quiet_end() -> str:
    return _get(KEY_QUIET_END)


def set_quiet_start(hhmm: str) -> None:
    _set(KEY_QUIET_START, hhmm)


def set_quiet_end(hhmm: str) -> None:
    _set(KEY_QUIET_END, hhmm)


def get_interval() -> int:
    try:
        return max(1, int(_get(KEY_INTERVAL)))
    except (TypeError, ValueError):
        return 30


def set_interval(minutes: int) -> None:
    _set(KEY_INTERVAL, str(max(1, int(minutes))))


def _get_silenced_until() -> Optional[dt.datetime]:
    s = _get(KEY_SILENCED_UNTIL)
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def _set_silenced_until(when: Optional[dt.datetime]) -> None:
    _set(KEY_SILENCED_UNTIL, when.isoformat() if when else "")


def _get_next_check_at() -> Optional[dt.datetime]:
    s = _get(KEY_NEXT_CHECK_AT)
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def _set_next_check_at(when: Optional[dt.datetime]) -> None:
    _set(KEY_NEXT_CHECK_AT, when.isoformat() if when else "")


# --------------------------------------------------------------------------- #
# Quiet-hours logic
# --------------------------------------------------------------------------- #


def _parse_hhmm(s: str) -> tuple[int, int]:
    """Parse 'HH:MM' → (hours, minutes). Returns (0, 0) on error."""
    try:
        h, m = s.split(":")
        return int(h), int(m)
    except Exception:
        return 0, 0


def _in_quiet_hours(now: dt.datetime) -> bool:
    """True if `now` falls inside quiet hours.

    Quiet hours can wrap around midnight (e.g., 23:00 → 07:00).
    """
    start_s = get_quiet_start()
    end_s = get_quiet_end()
    if not start_s or not end_s or start_s == end_s:
        return False

    sh, sm = _parse_hhmm(start_s)
    eh, em = _parse_hhmm(end_s)
    start_min = sh * 60 + sm
    end_min = eh * 60 + em
    now_min = now.hour * 60 + now.minute

    if start_min < end_min:
        # Same-day window, e.g. 09:00 → 12:00
        return start_min <= now_min < end_min
    else:
        # Wraps midnight, e.g. 23:00 → 07:00
        return now_min >= start_min or now_min < end_min


# --------------------------------------------------------------------------- #
# Notification decision
# --------------------------------------------------------------------------- #


def should_notify(now: dt.datetime) -> bool:
    """True if a notification should fire right now."""
    if not is_enabled():
        return False
    if _in_quiet_hours(now):
        return False
    if study_session.is_active():
        return False
    silenced = _get_silenced_until()
    if silenced and now < silenced:
        return False
    next_check = _get_next_check_at()
    if next_check and now < next_check:
        return False
    return True


# --------------------------------------------------------------------------- #
# Show notification
# --------------------------------------------------------------------------- #


def _play_chime(ctx) -> None:
    """Play the focus chime. Silently fails if audio is unavailable."""
    try:
        audio = getattr(ctx, "audio", None)
        if audio is not None:
            audio.play()
    except Exception:
        pass


def _show_notification(ctx) -> None:
    """Show the 'درس می‌خوانی؟' modal dialog."""
    from ui.theme import Colors, Typography, Spacing, Radius
    from ui import (
        ACCENT, ON_SURFACE, ON_SURFACE_VAR, SURFACE_HIGH,
        primary_button, text_button, to_fa,
    )

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(value="درس می‌خوانی؟", rtl=True,
                      size=20, weight=ft.FontWeight.W_600,
                      color=ON_SURFACE),
        content=ft.Text(
            value="اگر در حال مطالعه‌ای، ثبتش کن تا نمودارت پر شود.",
            rtl=True, size=14, color=ON_SURFACE_VAR),
        actions=[
            text_button("نه", on_click=lambda _: _on_no(ctx, dlg)),
            primary_button("آره", on_click=lambda _: _on_yes(ctx, dlg)),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    _play_chime(ctx)
    ctx.open_dialog(dlg)


def _on_yes(ctx, dlg) -> None:
    """User said 'yes' — silence for 1 hour."""
    _set_silenced_until(time_sync.now() + dt.timedelta(hours=1))
    _set_next_check_at(None)  # clear the 10-min retry
    ctx.close_dialog(dlg)
    ctx.snack("یک ساعت دیگر یادآوری می‌شود.")


def _on_no(ctx, dlg) -> None:
    """User said 'no' — check again in 10 minutes."""
    _set_next_check_at(time_sync.now() + dt.timedelta(minutes=10))
    _set_silenced_until(None)  # clear the 1-hour silence
    ctx.close_dialog(dlg)


# --------------------------------------------------------------------------- #
# Background loop
# --------------------------------------------------------------------------- #


async def loop(ctx) -> None:
    """Background loop: check every 60 seconds if it's time to notify.

    Never raises. Silently continues on any error.
    """
    # Wait a bit after app start so the first check doesn't fire immediately.
    await asyncio.sleep(10)
    while True:
        try:
            now = time_sync.now()
            if should_notify(now):
                _show_notification(ctx)
                # After showing, wait a bit before checking again so we
                # don't spam if the dialog stays open.
                await asyncio.sleep(60)
            else:
                await asyncio.sleep(60)
        except Exception:
            # Never let the loop die — just wait and retry.
            await asyncio.sleep(60)


# --------------------------------------------------------------------------- #
# Manual trigger (for the "test notification" button in settings)
# --------------------------------------------------------------------------- #


def test_now(ctx) -> None:
    """Show the notification immediately, bypassing all checks. Used by
    the 'تست نوتیفیکیشن' button in settings so the user can preview it."""
    _show_notification(ctx)
