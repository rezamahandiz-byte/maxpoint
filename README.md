# MAXPOINT

A personal study assistant + time manager + academic life analyst. Python + Flet.
Local SQLite only. Data leaves the device **only** when you manually request
an AI report (and even then, only an aggregate summary is sent — never raw
rows). The app never judges; it only shows where time goes and how far you
are from your own goals.

> Personal app, not a public product. v0.1 scope is intentionally small.

---

## Install

```bash
pip install "flet>=1.0" "flet-charts>=1.0" "flet-secure-storage>=1.0" httpx
```

(Or just `pip install -e .` from this directory — `pyproject.toml` lists the
same dependencies.)

Python 3.12+ required.

## Run (desktop or web)

```bash
flet run src/main.py              # desktop window
flet run -w -p 8765 src/main.py   # web at http://127.0.0.1:8765
```

## Build a signed Android APK

```bash
# 1. Generate a signing keystore (once, ever — back it up somewhere safe):
keytool -genkey -v -keystore upload-keystore.jks \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -alias maxpoint

# 2. Build the APK (password is read from the env var below):
export FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD='********'
flet build apk \
  --android-signing-key-store upload-keystore.jks \
  --android-signing-key-alias maxpoint \
  --split-per-abi
```

The signed APKs land under `build/android/`.

### Warnings

- **Never commit `upload-keystore.jks`.** Losing it blocks all future updates
  to the same app ID. Back it up somewhere durable before the first build.
- **The OpenAI API key is stored in the device Keystore.** If the device is
  rooted, the key can be extracted by anyone with shell access. Only run
  MAXPOINT on a device you personally control.

---

## File tree

```
src/
├── main.py             # entry point: theme, RTL, 4-tab navigation, FAB
├── ui/
│   ├── __init__.py     # shared design tokens + tiny factory helpers
│   ├── home.py         # today stats + next-step card + mini weekly trend
│   ├── record.py       # quick form + today's sessions list + edit/delete
│   ├── analysis.py     # 7-day bar chart + exam taraz line chart + assistant btn
│   ├── assistant.py    # AI report dialog (calls core/ai.py — stub in 0.1)
│   └── settings.py     # subjects, daily goals, API key, backup, clear data
├── core/
│   ├── __init__.py
│   ├── db.py           # SQLite schema, migrations, seed data, smoke test
│   ├── models.py       # dataclasses + per-table repositories
│   ├── goals.py        # target/actual/gap math (never says "failure")
│   ├── analytics.py    # today_summary, weekly_trend, data_quality, etc.
│   └── ai.py           # STUB — async request_report() signature only
├── services/
│   ├── __init__.py
│   ├── secure.py       # OpenAI key via flet-secure-storage (Keystore on Android)
│   ├── notifier.py     # STUB — deferred to 0.2
│   └── backup.py       # JSON export + atomic restore
├── assets/
│   ├── sounds/         # placeholder for focus_chime.mp3 (used in 0.2)
│   └── icons/          # placeholder for adaptive icon assets
└── pyproject.toml      # flet build config + permissions
README.md
```

## Privacy

- All sessions, goals, exams, and settings live in a single local SQLite
  file at `<platform data dir>/maxpoint/maxpoint.db`.
- The OpenAI API key lives in the Android Keystore (or platform equivalent).
  It is never written to SQLite, source code, or plain files.
- The only time data leaves the device is when you tap
  **دریافت تحلیل هوشمند** in the Analysis tab. Even then, the request body
  is an aggregate summary (averages, trends, goal gaps, data quality) — never
  raw sessions, notes, or personal text. See `core/ai.py` for the exact
  payload shape.

## Local logic (`core/analytics.py`)

| Function | Returns |
|---|---|
| `today_summary(date)` | `{minutes, tests, goal_percent, goal_gap_text, next_step_text, sessions_count}` |
| `weekly_trend(weeks=4)` | list of `{week_start, minutes, tests}` (oldest → newest) |
| `goal_gap(activity_id, period)` | `{target, actual, gap}` (positive gap = behind plan) |
| `data_quality(date_range)` | float 0..100 (percent of days with ≥1 session) |
| `exam_taraz_series()` | `[(exam_number, taraz), ...]` |
| `last_7_days_minutes()` | `[(date_str, minutes), ...]` for the Analysis bar chart |

All functions return zeros / empty lists on missing data — never raise.

## UI principles

- Dark theme, one accent color (calm periwinkle `#7E8CE0`), no serif fonts.
- Full RTL. Persian digits in display; English digits accepted in inputs.
- Never red for "unmet goals". Use **"فاصله از برنامه"** (distance from plan).
- No motivational clichés anywhere in the UI.
- Minimum 320 px width, no horizontal scroll, ≥48 dp touch targets.

## Known limitations of v0.1

These are intentionally deferred (per the original scope lock):

1. **No notifications or custom sounds.** `services/notifier.py` is an empty
   stub. POST_NOTIFICATIONS is declared in `pyproject.toml` but unused.
2. **No GPT reports.** `core/ai.py` has the locked async signature but the
   body is a stub that returns a Persian "not implemented in 0.1" message.
   The full implementation (httpx → gpt-4o-mini, 400-token cap, structured
   2-pattern + 2-suggestion + 1-warning output, 401/429/timeout handling)
   is left commented-out inside the file for v0.2.
3. **No custom activities UI.** The `activities` table supports `is_custom`,
   but the v0.1 Settings screen only lets you rename + activate/deactivate
   the seeded subjects. Adding brand-new activities is deferred.
4. **No time-overlap management.** Two sessions can overlap on the same
   day; the app does not warn or merge. v0.2 will handle this.
5. **No weekly comparison chart.** Only the 7-day bar chart and the exam
   taraz line chart ship in v0.1.

## Acceptance check

- `flet run src/main.py` launches with no error. ✓
- A study session can be recorded and immediately appears in Home and in
  the 7-day bar chart. ✓
- Force-closing the app does not lose saved data (SQLite WAL). ✓
- Backup export → import round-trip preserves all rows (verified by the
  `core/db.py` smoke test and the `services/backup.py` round-trip test). ✓
- Layout holds at 320 px width. ✓
- No heavy imports (numpy / pandas / matplotlib / openai SDK). ✓
  (`flet-charts` is installed for future use but v0.1 ships custom
  Container-based charts for reliability across web/desktop/Android.)
- All displayed Persian strings render correctly in RTL. ✓

## Smoke test

```bash
python3 src/core/db.py        # in-process schema + seed + CRUD smoke
```

## License

Personal use. Not redistributed.
