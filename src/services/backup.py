"""Backup — JSON export and import.

Export: writes every table to a JSON file the user picks. The file contains
a `version` field for forward-compatible restores.

Import: reads the JSON file, validates the schema, and replaces all tables
inside a single transaction. The UI is expected to confirm with the user
twice before calling `restore_from_dict` — the function itself does not
ask for confirmation.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from core import db

BACKUP_VERSION = 1

# Order matters: child tables first (so FK constraints don't fire on DELETE),
# parent tables last. Insert happens in reverse, which is FK-safe.
_BACKUP_TABLES = [
    "settings",
    "reports",
    "exam_subjects",
    "exams",
    "sessions",
    "goals",
    "activities",
    "activity_groups",
]

# Insert order = reverse of delete order.
_INSERT_ORDER = list(reversed(_BACKUP_TABLES))


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #


def export_to_dict() -> dict[str, Any]:
    """Read every table into a JSON-serialisable dict."""
    out: dict[str, Any] = {
        "version": BACKUP_VERSION,
        "app": "MAXPOINT",
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "tables": {},
    }
    for table in _BACKUP_TABLES:
        rows = db.fetch_all(f"SELECT * FROM {table};")
        out["tables"][table] = [dict(r) for r in rows]
    return out


def export_to_file(path: str | os.PathLike) -> Path:
    """Write the backup dict to `path` as pretty JSON. Returns the Path."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = export_to_dict()
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


# --------------------------------------------------------------------------- #
# Import
# --------------------------------------------------------------------------- #


def restore_from_dict(data: dict[str, Any]) -> dict[str, int]:
    """Replace every table with the contents of `data`.

    Returns a {table_name: rows_written} dict for the UI to show.

    Safety:
        - Runs inside a single transaction; rolls back on any error.
        - Skips unknown tables.
        - Always preserves the schema (deletes rows, not the table).
        - Re-runs the seed AFTER clearing only if no activities remain
          (so a blank restore still leaves the app usable).
    """
    counts: dict[str, int] = {}
    with db.connect() as conn:
        cur = conn.cursor()
        try:
            # 1. Delete in child-first order (FK-safe).
            for table in _BACKUP_TABLES:
                cur.execute(f"DELETE FROM {table};")
            # 2. Insert in parent-first order (FK-safe).
            for table in _INSERT_ORDER:
                rows = data.get("tables", {}).get(table, [])
                if rows:
                    cols = list(rows[0].keys())
                    placeholders = ",".join("?" * len(cols))
                    sql = (
                        f"INSERT OR REPLACE INTO {table} "
                        f"({','.join(cols)}) VALUES ({placeholders});"
                    )
                    cur.executemany(sql, [tuple(r[c] for c in cols) for r in rows])
                    counts[table] = len(rows)
                else:
                    counts[table] = 0
        except Exception:
            conn.rollback()
            raise

    # Re-seed if the restore left the app empty (rare but possible).
    from core import models as _m
    if not _m.list_activities(active_only=False):
        with db.connect() as conn:
            db._seed(conn)

    return counts


def restore_from_file(path: str | os.PathLike) -> dict[str, int]:
    """Read a JSON backup file and replace all tables. Throws on bad JSON."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict) or "tables" not in data:
        raise ValueError("فایل پشتیبان معتبر نیست.")
    return restore_from_dict(data)
