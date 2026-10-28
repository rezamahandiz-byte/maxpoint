"""MAXPOINT domain models — frozen dataclasses mirroring SQLite rows.

These are pure value objects. They never touch the database themselves;
that's the job of `core.db` and the small per-table repository helpers in
this module. UI code receives these dataclasses and never sees sqlite3.Row.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import db


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ActivityGroup:
    id: int
    name: str
    color: Optional[str] = None
    priority: str = "flexible"  # 'mandatory' | 'priority' | 'flexible'


@dataclass(frozen=True)
class Activity:
    id: int
    name: str
    group_id: Optional[int] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_custom: int = 0
    is_active: int = 1

    @property
    def active(self) -> bool:
        return bool(self.is_active)


@dataclass(frozen=True)
class Session:
    id: int
    date: str  # YYYY-MM-DD
    activity_id: int
    minutes: int = 0
    tests_count: int = 0
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    note: Optional[str] = None
    created_at: str = ""


@dataclass(frozen=True)
class Goal:
    id: int
    activity_id: int
    period: str  # 'daily' | 'weekly'
    target_minutes: int = 0
    target_tests: int = 0


@dataclass(frozen=True)
class Exam:
    id: int
    date: str
    exam_number: int
    taraz: int
    notes: Optional[str] = None


@dataclass(frozen=True)
class ExamSubject:
    id: int
    exam_id: int
    subject: str
    percent: Optional[float] = None
    correct: Optional[int] = None
    wrong: Optional[int] = None
    blank: Optional[int] = None


@dataclass(frozen=True)
class Report:
    id: int
    type: str  # 'daily' | 'weekly' | 'monthly'
    period_start: str
    period_end: str
    content: str
    generated_at: str


@dataclass(frozen=True)
class Setting:
    key: str
    value: str


# --------------------------------------------------------------------------- #
# Repositories — thin CRUD wrappers around db.fetch_*/execute.
# Each function returns a dataclass instance (or None / list).
# --------------------------------------------------------------------------- #


def _row_to(cls, row):
    if row is None:
        return None
    # sqlite3.Row is mapping-like; pick only the columns that match a dataclass
    # field so we don't choke on extra columns or renamed ones.
    import dataclasses as _dc
    valid = {f.name for f in _dc.fields(cls)}
    kwargs = {k: row[k] for k in row.keys() if k in valid}
    return cls(**kwargs)


# ---- ActivityGroup -------------------------------------------------------- #


def list_groups() -> list[ActivityGroup]:
    rows = db.fetch_all("SELECT * FROM activity_groups ORDER BY id;")
    return [_row_to(ActivityGroup, r) for r in rows]


def get_group(group_id: int) -> Optional[ActivityGroup]:
    return _row_to(ActivityGroup, db.fetch_one(
        "SELECT * FROM activity_groups WHERE id=?;", (group_id,)))


# ---- Activity ------------------------------------------------------------- #


def list_activities(active_only: bool = True) -> list[Activity]:
    sql = "SELECT * FROM activities"
    sql += " WHERE is_active=1" if active_only else ""
    sql += " ORDER BY name;"
    return [_row_to(Activity, r) for r in db.fetch_all(sql)]


def get_activity(activity_id: int) -> Optional[Activity]:
    return _row_to(Activity, db.fetch_one(
        "SELECT * FROM activities WHERE id=?;", (activity_id,)))


def find_activity_by_name(name: str) -> Optional[Activity]:
    return _row_to(Activity, db.fetch_one(
        "SELECT * FROM activities WHERE name=? COLLATE NOCASE;", (name,)))


def create_activity(name: str, group_id: Optional[int],
                    color: Optional[str] = None,
                    icon: Optional[str] = None) -> int:
    return db.execute(
        "INSERT INTO activities (name, group_id, color, icon, is_custom, is_active) "
        "VALUES (?,?,?,?,1,1);",
        (name, group_id, color, icon),
    )


def rename_activity(activity_id: int, new_name: str) -> None:
    db.execute("UPDATE activities SET name=? WHERE id=?;", (new_name, activity_id))


def set_activity_active(activity_id: int, is_active: bool) -> None:
    db.execute("UPDATE activities SET is_active=? WHERE id=?;",
               (1 if is_active else 0, activity_id))


# ---- Session -------------------------------------------------------------- #


def list_sessions_for_date(date_str: str) -> list[Session]:
    rows = db.fetch_all(
        "SELECT * FROM sessions WHERE date=? ORDER BY id DESC;", (date_str,))
    return [_row_to(Session, r) for r in rows]


def list_sessions_in_range(start: str, end: str) -> list[Session]:
    rows = db.fetch_all(
        "SELECT * FROM sessions WHERE date BETWEEN ? AND ? ORDER BY date, id;",
        (start, end))
    return [_row_to(Session, r) for r in rows]


def create_session(date_str: str, activity_id: int, minutes: int,
                   tests_count: int = 0, note: Optional[str] = None,
                   start_time: Optional[str] = None,
                   end_time: Optional[str] = None) -> int:
    return db.execute(
        "INSERT INTO sessions (date, start_time, end_time, activity_id, minutes, "
        "tests_count, note, created_at) VALUES (?,?,?,?,?,?,?,?);",
        (date_str, start_time, end_time, activity_id, minutes,
         tests_count, note, db.now_iso()),
    )


def update_session(session_id: int, *, activity_id: Optional[int] = None,
                   minutes: Optional[int] = None,
                   tests_count: Optional[int] = None,
                   note: Optional[str] = None) -> None:
    sets: list[str] = []
    params: list = []
    if activity_id is not None:
        sets.append("activity_id=?"); params.append(activity_id)
    if minutes is not None:
        sets.append("minutes=?"); params.append(int(minutes))
    if tests_count is not None:
        sets.append("tests_count=?"); params.append(int(tests_count))
    if note is not None:
        sets.append("note=?"); params.append(note)
    if not sets:
        return
    params.append(session_id)
    db.execute(f"UPDATE sessions SET {', '.join(sets)} WHERE id=?;", params)


def delete_session(session_id: int) -> None:
    db.execute("DELETE FROM sessions WHERE id=?;", (session_id,))


def get_session(session_id: int) -> Optional[Session]:
    return _row_to(Session, db.fetch_one(
        "SELECT * FROM sessions WHERE id=?;", (session_id,)))


# ---- Goal ----------------------------------------------------------------- #


def list_goals() -> list[Goal]:
    rows = db.fetch_all("SELECT * FROM goals ORDER BY id;")
    return [_row_to(Goal, r) for r in rows]


def get_goal(activity_id: int, period: str) -> Optional[Goal]:
    return _row_to(Goal, db.fetch_one(
        "SELECT * FROM goals WHERE activity_id=? AND period=?;",
        (activity_id, period)))


def upsert_goal(activity_id: int, period: str,
                target_minutes: int, target_tests: int = 0) -> None:
    existing = get_goal(activity_id, period)
    if existing is None:
        db.execute(
            "INSERT INTO goals (activity_id, period, target_minutes, target_tests) "
            "VALUES (?,?,?,?);",
            (activity_id, period, int(target_minutes), int(target_tests)),
        )
    else:
        db.execute(
            "UPDATE goals SET target_minutes=?, target_tests=? WHERE id=?;",
            (int(target_minutes), int(target_tests), existing.id),
        )


def delete_goal(activity_id: int, period: str) -> None:
    db.execute("DELETE FROM goals WHERE activity_id=? AND period=?;",
               (activity_id, period))


# ---- Exam ----------------------------------------------------------------- #


def list_exams() -> list[Exam]:
    rows = db.fetch_all("SELECT * FROM exams ORDER BY exam_number;")
    return [_row_to(Exam, r) for r in rows]


def create_exam(date_str: str, exam_number: int, taraz: int,
                notes: Optional[str] = None) -> int:
    return db.execute(
        "INSERT INTO exams (date, exam_number, taraz, notes) VALUES (?,?,?,?);",
        (date_str, exam_number, taraz, notes))


def list_exam_subjects(exam_id: int) -> list[ExamSubject]:
    rows = db.fetch_all("SELECT * FROM exam_subjects WHERE exam_id=?;", (exam_id,))
    return [_row_to(ExamSubject, r) for r in rows]


# ---- Report --------------------------------------------------------------- #


def save_report(report_type: str, period_start: str, period_end: str,
                content: str) -> int:
    return db.execute(
        "INSERT INTO reports (type, period_start, period_end, content, generated_at) "
        "VALUES (?,?,?,?,?);",
        (report_type, period_start, period_end, content, db.now_iso()))


def list_reports(limit: int = 20) -> list[Report]:
    rows = db.fetch_all(
        "SELECT * FROM reports ORDER BY generated_at DESC LIMIT ?;", (limit,))
    return [_row_to(Report, r) for r in rows]


# ---- Settings ------------------------------------------------------------- #


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    row = db.fetch_one("SELECT value FROM settings WHERE key=?;", (key,))
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?);",
               (key, value))


def delete_setting(key: str) -> None:
    db.execute("DELETE FROM settings WHERE key=?;", (key,))


def all_settings() -> list[Setting]:
    rows = db.fetch_all("SELECT * FROM settings ORDER BY key;")
    return [_row_to(Setting, r) for r in rows]
