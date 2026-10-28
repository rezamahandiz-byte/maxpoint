"""Local-only analytics. No network, no async, no heavy deps.

Public functions (per spec):
    today_summary(date)         -> dict(minutes, tests, goal_percent, next_step_text)
    weekly_trend(weeks=4)       -> list[dict] (one entry per week, oldest → newest)
    goal_gap(activity_id, period) -> dict(target, actual, gap)  [re-exported from goals]
    data_quality(date_range)    -> float (percent of days recorded, 0..100)
    exam_taraz_series()         -> list[(exam_number, taraz)]
    last_7_days_minutes()       -> list[(date_str, minutes)]  (used by Analysis tab)

Every function returns zeros / empty on missing data. Never raises.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from . import db, models
from . import goals as _goals


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def to_fa(value) -> str:
    """Render an int/float/str with Persian digits. Used for display only."""
    return str(value).translate(_FA_DIGITS)


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b else default


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def today_summary(today: Optional[date] = None) -> dict:
    """Single-shot summary used by the Home tab.

    Returns:
        {
          'minutes':     int,        # total study minutes today
          'tests':       int,        # total tests done today
          'goal_percent': float,     # 0..100 (averaged across all daily goals)
          'goal_gap_text': str,      # short Persian phrase for the next-step card
          'next_step_text': str,     # one concrete suggestion (local logic only)
          'sessions_count': int,
        }
    """
    today = today or date.today()
    today_str = today.isoformat()
    sessions = models.list_sessions_for_date(today_str)

    study_group_ids = _study_group_ids()
    study_minutes = sum(s.minutes for s in sessions
                        if _activity_in_groups(s.activity_id, study_group_ids))
    total_tests = sum(s.tests_count for s in sessions)

    # Goal progress: average across all daily goals defined.
    gaps = _goals.daily_gaps(today)
    if gaps:
        goal_percent = round(sum(g.percent for g in gaps) / len(gaps), 1)
    else:
        goal_percent = 0.0

    next_step_text = _next_step(today, gaps, study_minutes, total_tests)
    goal_gap_text = _gap_phrase(gaps)

    return {
        "minutes": study_minutes,
        "tests": total_tests,
        "goal_percent": goal_percent,
        "goal_gap_text": goal_gap_text,
        "next_step_text": next_step_text,
        "sessions_count": len(sessions),
    }


def weekly_trend(weeks: int = 4) -> list[dict]:
    """One entry per ISO week for the last `weeks` weeks (oldest → newest).

    Each entry: {'week_start': 'YYYY-MM-DD', 'minutes': int, 'tests': int}
    Empty weeks are returned with zeros — the chart should still render.
    """
    weeks = max(1, min(weeks, 12))
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    out: list[dict] = []
    for i in range(weeks - 1, -1, -1):
        ws = monday - timedelta(weeks=i)
        we = ws + timedelta(days=6)
        rows = models.list_sessions_in_range(ws.isoformat(), we.isoformat())
        out.append({
            "week_start": ws.isoformat(),
            "minutes": sum(r.minutes for r in rows),
            "tests": sum(r.tests_count for r in rows),
        })
    return out


def data_quality(date_range: tuple[date, date]) -> float:
    """Percent of days in the range with at least one recorded session.

    Returns 0.0 for an empty range. Capped at 100.0.
    """
    start, end = date_range
    if end < start:
        start, end = end, start
    days = (end - start).days + 1
    if days <= 0:
        return 0.0

    rows = db.fetch_all(
        "SELECT DISTINCT date FROM sessions WHERE date BETWEEN ? AND ?;",
        (start.isoformat(), end.isoformat()),
    )
    recorded = len(rows)
    return round(100.0 * recorded / days, 1)


def exam_taraz_series() -> list[tuple[int, int]]:
    """List of (exam_number, taraz) sorted by exam_number. Empty if no exams."""
    exams = models.list_exams()
    return [(e.exam_number, e.taraz) for e in exams]


def last_7_days_minutes(today: Optional[date] = None) -> list[tuple[str, int]]:
    """[(date_str, minutes), ...] for the last 7 days, oldest → newest."""
    today = today or date.today()
    out: list[tuple[str, int]] = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        rows = models.list_sessions_for_date(d.isoformat())
        out.append((d.isoformat(), sum(r.minutes for r in rows)))
    return out


def last_7_days_tests(today: Optional[date] = None) -> list[tuple[str, int]]:
    today = today or date.today()
    out: list[tuple[str, int]] = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        rows = models.list_sessions_for_date(d.isoformat())
        out.append((d.isoformat(), sum(r.tests_count for r in rows)))
    return out


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #


def _study_group_ids() -> set[int]:
    """Group ids considered 'study' (مطالعه + آزمون). Tests count as study time too."""
    out: set[int] = set()
    for g in models.list_groups():
        if g.name in ("مطالعه", "آزمون"):
            out.add(g.id)
    return out


def _activity_in_groups(activity_id: int, group_ids: set[int]) -> bool:
    if not group_ids:
        return True  # if no groups configured, count everything
    act = models.get_activity(activity_id)
    return bool(act and act.group_id in group_ids)


def _gap_phrase(gaps: list) -> str:
    """A neutral Persian phrase summarising the largest gap. No 'failure'."""
    if not gaps:
        return "هنوز هدفی تعریف نکرده‌ای."
    biggest = gaps[0]
    if biggest.gap_minutes <= 0:
        return "امروز روی برنامه بودی."
    return (f"فاصله از برنامه در {biggest.activity_name}: "
            f"{to_fa(biggest.gap_minutes)} دقیقه.")


def _next_step(today: date, gaps: list, study_minutes: int,
               total_tests: int) -> str:
    """One concrete suggestion. Local logic only. No motivational clichés.

    Priority:
        1. If a daily goal exists with a positive gap and the day isn't over →
           suggest closing the gap on that activity, capped at 25-min chunks.
        2. If no goals defined → suggest recording the first session.
        3. If all goals are met → suggest a short break or a test.
    """
    midday = today  # we don't track time-of-day here; the suggestion stays mild.

    if not gaps:
        return "یک جلسه ۲۵ دقیقه‌ای ثبت کن تا نمودار امروزمت پر شود."

    # Find the activity with the largest remaining gap.
    for g in gaps:
        if g.gap_minutes > 0:
            chunk = min(25, g.gap_minutes)
            return (f"{chunk} دقیقه دیگر برای «{g.activity_name}» ثبت کن "
                    f"تا فاصله از برنامه کمتر شود.")
        if g.gap_tests > 0:
            return (f"{to_fa(g.gap_tests)} آزمون برای «{g.activity_name}» "
                    f"ثبت کن.")

    # All goals met.
    if total_tests == 0:
        return "اهداف امروز محقق شد؛ یک آزمون کوتاه ثبت کن تا روند سنجیده شود."
    return "اهداف امروز محقق شد. ۱۵ دقیقه استراحت فعال پیشنهاد می‌شود."
