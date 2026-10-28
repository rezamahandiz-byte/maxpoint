"""MAXPOINT SQLite layer.

A single local database (no server, no cloud). All schema changes are
recorded via PRAGMA user_version, so future versions can migrate forward
without losing user data.

Tables (exactly per spec):
    sessions, activities, activity_groups, goals, exams, exam_subjects,
    reports, settings

The DB path resolves to:
    1. env MAXPOINT_DB_PATH (full file path)              — explicit override
    2. env MAXPOINT_DB_DIR (directory) + "maxpoint.db"    — directory override
    3. platform data dir + "maxpoint" / "maxpoint.db"     — default

This module is safe to import from any thread; every public helper opens
its own short-lived connection (SQLite handles file locking for us). No
long-lived connections are kept, which avoids threading surprises inside
Flet's event loop.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

# --------------------------------------------------------------------------- #
# Schema definition (single source of truth)
# --------------------------------------------------------------------------- #

SCHEMA_VERSION = 1

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS activity_groups (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    color     TEXT,
    priority  TEXT NOT NULL CHECK (priority IN ('mandatory','priority','flexible'))
);

CREATE TABLE IF NOT EXISTS activities (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    group_id   INTEGER,
    color      TEXT,
    icon       TEXT,
    is_custom  INTEGER NOT NULL DEFAULT 0,
    is_active  INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (group_id) REFERENCES activity_groups(id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id           INTEGER PRIMARY KEY,
    date         TEXT NOT NULL,                 -- YYYY-MM-DD
    start_time   TEXT,
    end_time     TEXT,
    activity_id  INTEGER NOT NULL,
    minutes      INTEGER NOT NULL DEFAULT 0,
    tests_count  INTEGER NOT NULL DEFAULT 0,
    note         TEXT,
    created_at   TEXT NOT NULL,
    FOREIGN KEY (activity_id) REFERENCES activities(id)
);

CREATE TABLE IF NOT EXISTS goals (
    id              INTEGER PRIMARY KEY,
    activity_id     INTEGER NOT NULL,
    period          TEXT NOT NULL CHECK (period IN ('daily','weekly')),
    target_minutes  INTEGER NOT NULL DEFAULT 0,
    target_tests    INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (activity_id) REFERENCES activities(id)
);

CREATE TABLE IF NOT EXISTS exams (
    id          INTEGER PRIMARY KEY,
    date        TEXT NOT NULL,
    exam_number INTEGER NOT NULL,
    taraz       INTEGER NOT NULL,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS exam_subjects (
    id       INTEGER PRIMARY KEY,
    exam_id  INTEGER NOT NULL,
    subject  TEXT NOT NULL,
    percent  REAL,
    correct  INTEGER,
    wrong    INTEGER,
    blank    INTEGER,
    FOREIGN KEY (exam_id) REFERENCES exams(id)
);

CREATE TABLE IF NOT EXISTS reports (
    id            INTEGER PRIMARY KEY,
    type          TEXT NOT NULL CHECK (type IN ('daily','weekly','monthly')),
    period_start  TEXT NOT NULL,
    period_end    TEXT NOT NULL,
    content       TEXT NOT NULL,
    generated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_date        ON sessions(date);
CREATE INDEX IF NOT EXISTS idx_sessions_activity    ON sessions(activity_id);
CREATE INDEX IF NOT EXISTS idx_goals_activity       ON goals(activity_id);
CREATE INDEX IF NOT EXISTS idx_exam_subjects_exam   ON exam_subjects(exam_id);
"""

# --------------------------------------------------------------------------- #
# Seed data — first run only
# --------------------------------------------------------------------------- #

# (name, color, priority)
_SEED_GROUPS: list[tuple[str, str, str]] = [
    ("مطالعه",      "#7E8CE0", "mandatory"),  # Study
    ("آزمون",       "#E08A5A", "mandatory"),  # Test
    ("کار",         "#5AB0E0", "priority"),   # Work
    ("اوقات فراغت", "#6FBF73", "flexible"),   # Leisure
    ("مسئولیت‌ها",  "#C98AE0", "priority"),   # Responsibility
    ("سلامتی",      "#E0B85A", "priority"),   # Health
    ("استراحت",     "#7C8C9A", "flexible"),   # Rest
]

# (name, group_name, color) — all default subjects belong to "مطالعه"
_SEED_ACTIVITIES: list[tuple[str, str, str]] = [
    ("ریاضی",   "مطالعه", "#7E8CE0"),
    ("فیزیک",   "مطالعه", "#5A8CE0"),
    ("شیمی",    "مطالعه", "#5AB0E0"),
    ("زیست",    "مطالعه", "#6FBF73"),
    ("ادبیات",  "مطالعه", "#E0B85A"),
    ("عربی",    "مطالعه", "#C98AE0"),
    ("دینی",    "مطالعه", "#8FB07A"),
    ("زبان",    "مطالعه", "#5AC8C8"),
]

# --------------------------------------------------------------------------- #
# DB path resolution
# --------------------------------------------------------------------------- #

_LOCK = threading.Lock()


def _default_db_dir() -> Path:
    """A writable per-user data directory for MAXPOINT."""
    if override := os.environ.get("MAXPOINT_DB_DIR"):
        p = Path(override).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p
    if full := os.environ.get("MAXPOINT_DB_PATH"):
        p = Path(full).expanduser().parent
        p.mkdir(parents=True, exist_ok=True)
        return p

    # Platform-default
    if os.name == "nt":  # Windows
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:  # Linux / macOS / Android (via Termux-style $HOME)
        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    p = base / "maxpoint"
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_path() -> Path:
    """Resolve the absolute SQLite file path used by the app."""
    if full := os.environ.get("MAXPOINT_DB_PATH"):
        return Path(full).expanduser()
    return _default_db_dir() / "maxpoint.db"


# --------------------------------------------------------------------------- #
# Connection helpers
# --------------------------------------------------------------------------- #


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Yield a short-lived connection with sensible pragmas.

    `check_same_thread=False` is unnecessary here because each call opens its
    own connection; Flet's UI thread and the analytics helpers will not share
    one.
    """
    conn = sqlite3.connect(db_path(), detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Migrations
# --------------------------------------------------------------------------- #


def _run_migrations(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("PRAGMA user_version;")
    current = cur.fetchone()[0] or 0

    if current == 0:
        conn.executescript(_SCHEMA_SQL)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION};")
        _seed(conn)
        return

    # Forward-only migrations live here as `elif current == N:` blocks.
    # v0.1 ships with version 1 only.
    if current < SCHEMA_VERSION:
        # Example placeholder for the next version:
        #   conn.executescript("ALTER TABLE ... ;")
        #   conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION};")
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION};")


def _seed(conn: sqlite3.Connection) -> None:
    """Insert default groups + activities on first run only."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM activity_groups;")
    if cur.fetchone()[0] > 0:
        return  # already seeded

    for name, color, priority in _SEED_GROUPS:
        cur.execute(
            "INSERT INTO activity_groups (name, color, priority) VALUES (?,?,?);",
            (name, color, priority),
        )

    # name → group_id lookup
    cur.execute("SELECT id, name FROM activity_groups;")
    group_by_name: dict[str, int] = {row["name"]: row["id"] for row in cur.fetchall()}

    for name, group_name, color in _SEED_ACTIVITIES:
        gid = group_by_name.get(group_name)
        cur.execute(
            "INSERT INTO activities (name, group_id, color, icon, is_custom, is_active) "
            "VALUES (?,?,?,?,0,1);",
            (name, gid, color, None),
        )


def init_db() -> None:
    """Create/migrate the database. Idempotent — safe to call at app start."""
    with _LOCK:
        with connect() as conn:
            _run_migrations(conn)


# --------------------------------------------------------------------------- #
# Generic CRUD-ish helpers (used by models / analytics / UI)
# --------------------------------------------------------------------------- #


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def fetch_one(sql: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
    with connect() as conn:
        cur = conn.execute(sql, tuple(params))
        return cur.fetchone()


def fetch_all(sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    with connect() as conn:
        cur = conn.execute(sql, tuple(params))
        return list(cur.fetchall())


def execute(sql: str, params: Iterable[Any] = ()) -> int:
    """Execute a write statement. Returns lastrowid."""
    with connect() as conn:
        cur = conn.execute(sql, tuple(params))
        return cur.lastrowid or 0


def executemany(sql: str, seq: Iterable[Iterable[Any]]) -> int:
    with connect() as conn:
        cur = conn.executemany(sql, [tuple(p) for p in seq])
        return cur.rowcount or 0


# --------------------------------------------------------------------------- #
# Smoke test
# --------------------------------------------------------------------------- #


def _smoke_test() -> None:
    """Tiny self-test: create DB, seed, count rows, drop, recreate. No pytest."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MAXPOINT_DB_PATH"] = str(Path(tmp) / "smoke.db")
        try:
            init_db()
            g = fetch_one("SELECT COUNT(*) AS c FROM activity_groups;")
            a = fetch_one("SELECT COUNT(*) AS c FROM activities;")
            assert g and g["c"] == len(_SEED_GROUPS), f"groups seed mismatch: {g}"
            assert a and a["c"] == len(_SEED_ACTIVITIES), f"activities seed mismatch: {a}"

            # Re-init must be idempotent (no duplicate seeds)
            init_db()
            g2 = fetch_one("SELECT COUNT(*) AS c FROM activity_groups;")
            assert g2 and g2["c"] == len(_SEED_GROUPS), "re-init duplicated seeds"

            # A session can be inserted and read back
            act = fetch_one("SELECT id FROM activities WHERE name='ریاضی';")
            assert act is not None
            sid = execute(
                "INSERT INTO sessions (date, activity_id, minutes, tests_count, "
                "note, created_at) VALUES (?,?,?,?,?,?);",
                ("2026-01-01", act["id"], 60, 0, "smoke", now_iso()),
            )
            row = fetch_one("SELECT minutes FROM sessions WHERE id=?;", (sid,))
            assert row and row["minutes"] == 60

            # settings round-trips
            execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?);",
                    ("smoke", "1"))
            s = fetch_one("SELECT value FROM settings WHERE key='smoke';")
            assert s and s["value"] == "1"
        finally:
            os.environ.pop("MAXPOINT_DB_PATH", None)

    print("db smoke OK")


if __name__ == "__main__":
    _smoke_test()
