"""Home tab — the calm report at the top of the day.

Top of screen: start/end study widget.
    - When idle: a "شروع مطالعه" button → opens dialog to pick subject
      and type (study/test), then starts a live session.
    - When active: shows subject + type + live elapsed timer, with
      "پایان" (save) and "انصراف" (discard) buttons.

Below that:
    - Greeting + date header
    - One hero number (today's study minutes)
    - One "next step" card
    - 7-day sparkline (read-only context)
    - Today's sessions list

Law #4: one action per screen. The start/end widget IS the primary
action on Home. Everything else is read-only context.
"""
from __future__ import annotations

import asyncio
import datetime as dt
from typing import Optional

import flet as ft

from core import analytics, models, study_session
from services import time_sync
from ui.theme import Colors, Typography, Spacing, Radius, Motion, Layout
from ui import (
    ACCENT, ACCENT_SOFT, BG_DARK, ON_SURFACE, ON_SURFACE_VAR, ON_SURFACE_MUT,
    OUTLINE, SURFACE, SURFACE_HIGH, SUCCESS, WARN,
    CENTER, CENTER_LEFT, CENTER_RIGHT, TOP_CENTER, BOTTOM_CENTER,
    body_text, caption, card, divider, label, pad_only, pad_sym, margin_only,
    primary_button, secondary_button, screen_scroll, screen_title,
    section_title, to_fa,
)


def build(ctx) -> ft.Control:
    today = time_sync.today()
    s = analytics.today_summary(today)

    # The start/end widget goes at the very top — it's the primary action.
    session_widget = _session_widget(ctx)

    hero = _hero_card(s)
    next_step = _next_step_card(s)
    sparkline = _sparkline_card(today)
    today_list = _today_sessions_card(today)

    return screen_scroll([
        _greeting_header(today),
        ft.Container(height=Spacing.md),
        session_widget,
        ft.Container(height=Spacing.md),
        hero,
        ft.Container(height=Spacing.md),
        next_step,
        ft.Container(height=Spacing.md),
        sparkline,
        ft.Container(height=Spacing.md),
        today_list,
    ])


def on_show(ctx) -> None:
    # If a session is active, start/refresh the timer loop.
    _ensure_timer_loop(ctx)


# --------------------------------------------------------------------------- #
# Start / End study widget
# --------------------------------------------------------------------------- #


def _session_widget(ctx) -> ft.Control:
    """Top-of-screen widget: start a session or show the active one."""
    active = study_session.get()
    if active is not None:
        return _active_session_card(ctx, active)
    return _idle_session_card(ctx)


def _idle_session_card(ctx) -> ft.Control:
    """When no session is active: show a 'شروع مطالعه' button."""

    def _start(_e=None):
        _open_start_dialog(ctx)

    return card(
        ft.Row(
            [
                ft.Container(
                    width=40, height=40,
                    alignment=CENTER,
                    bgcolor=ACCENT_SOFT,
                    border_radius=Radius.full,
                    content=ft.Icon(ft.Icons.PLAY_ARROW, color=ACCENT, size=22),
                ),
                ft.Container(width=Spacing.md),
                ft.Column(
                    [
                        ft.Text(value="شروع مطالعه", size=Typography.body,
                                color=ON_SURFACE, rtl=True,
                                weight=ft.FontWeight.W_600),
                        ft.Text(value="درس و نوع مطالعه را انتخاب کن",
                                size=Typography.tiny,
                                color=ON_SURFACE_VAR, rtl=True),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.IconButton(
                    icon=ft.Icons.ARROW_FORWARD_IOS,
                    icon_size=18,
                    icon_color=ON_SURFACE_VAR,
                    on_click=_start,
                    style=ft.ButtonStyle(shape=ft.CircleBorder()),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=Layout.card_padding,
    )


def _active_session_card(ctx, session: study_session.ActiveSession) -> ft.Control:
    """When a session is active: show live timer + end/cancel buttons."""
    type_label = "مطالعه" if session.study_type == study_session.STUDY_TYPE_STUDY else "آزمون"

    # The timer text — updated every second by a background task.
    timer_text = ft.Text(
        value=_format_elapsed(session.elapsed_seconds()),
        size=Typography.h1,
        weight=ft.FontWeight.W_600,
        color=ACCENT, rtl=True,
    )

    # Pulse dot to show the session is live.
    pulse = ft.Container(
        width=8, height=8,
        bgcolor=SUCCESS,
        border_radius=Radius.full,
    )

    def _end(_e=None):
        ended = study_session.end()
        if ended is None:
            return
        # Save to database.
        minutes = ended.elapsed_minutes()
        note = f"[{type_label}]"
        models.create_session(
            date_str=time_sync.today().isoformat(),
            activity_id=ended.activity_id,
            minutes=minutes,
            tests_count=1 if ended.study_type == study_session.STUDY_TYPE_TEST else 0,
            note=note,
        )
        _stop_timer_loop(ctx)
        ctx.snack(f"{to_fa(minutes)} دقیقه ثبت شد.")
        ctx.refresh()

    def _cancel(_e=None):
        study_session.cancel()
        _stop_timer_loop(ctx)
        ctx.snack("جلسه بدون ثبت پایان یافت.")
        ctx.refresh()

    # Store timer_text on ctx so the timer loop can find it.
    ctx._active_timer_text = timer_text
    ctx._active_session = session
    _ensure_timer_loop(ctx)

    return card(
        ft.Column(
            [
                ft.Row(
                    [
                        pulse,
                        ft.Container(width=Spacing.sm),
                        ft.Text(value="در حال مطالعه", size=Typography.small,
                                color=SUCCESS, rtl=True,
                                weight=ft.FontWeight.W_600),
                        ft.Container(expand=True),
                        ft.Text(value=f"{session.activity_name} • {type_label}",
                                size=Typography.small, color=ON_SURFACE_VAR,
                                rtl=True),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=Spacing.sm),
                ft.Row(
                    [timer_text],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=Spacing.sm),
                ft.Row(
                    [
                        ft.TextButton(
                            content="انصراف",
                            icon=ft.Icons.CLOSE,
                            on_click=_cancel,
                            style=ft.ButtonStyle(color=ON_SURFACE_VAR),
                        ),
                        ft.Container(expand=True),
                        primary_button("پایان و ثبت", on_click=_end,
                                       icon=ft.Icons.STOP_CIRCLE_OUTLINED),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=0,
        ),
        padding=Layout.card_padding,
    )


def _open_start_dialog(ctx) -> None:
    """Dialog to pick subject + type, then start the session."""
    activities = models.list_activities(active_only=True)
    if not activities:
        ctx.snack("اول از تنظیمات یک درس اضافه کن.")
        return

    subject = ft.Dropdown(
        label="درس", rtl=True, text_size=Typography.body, dense=True,
        options=[ft.DropdownOption(key=str(a.id), text=a.name) for a in activities],
        value=str(activities[0].id),
        expand=True, border_radius=Radius.sm,
    )

    # Type selector: two buttons that toggle.
    type_state = {"value": study_session.STUDY_TYPE_STUDY}

    study_btn = ft.FilledButton(
        content="مطالعه",
        icon=ft.Icons.MENU_BOOK_OUTLINED,
        height=Layout.button_height,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=Radius.sm)),
    )
    test_btn = ft.OutlinedButton(
        content="آزمون",
        icon=ft.Icons.EDIT_NOTE_OUTLINED,
        height=Layout.button_height,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=Radius.sm)),
    )

    def _update_type_buttons():
        if type_state["value"] == study_session.STUDY_TYPE_STUDY:
            study_btn.style = ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=Radius.sm),
                bgcolor=ACCENT, color=Colors.accent_text,
            )
            test_btn.style = ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=Radius.sm),
            )
        else:
            study_btn.style = ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=Radius.sm),
            )
            test_btn.style = ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=Radius.sm),
                bgcolor=ACCENT, color=Colors.accent_text,
            )
        try:
            study_btn.update()
            test_btn.update()
        except Exception:
            pass

    def _pick_study(_e):
        type_state["value"] = study_session.STUDY_TYPE_STUDY
        _update_type_buttons()

    def _pick_test(_e):
        type_state["value"] = study_session.STUDY_TYPE_TEST
        _update_type_buttons()

    study_btn.on_click = _pick_study
    test_btn.on_click = _pick_test
    _update_type_buttons()

    def _start_session(_e=None):
        try:
            act_id = int(subject.value) if subject.value else 0
        except (TypeError, ValueError):
            act_id = 0
        if not act_id:
            ctx.snack("یک درس انتخاب کن.")
            return
        act = models.get_activity(act_id)
        if act is None:
            ctx.snack("درس یافت نشد.")
            return
        study_session.start(act_id, act.name, type_state["value"])
        ctx.close_dialog(dlg)
        ctx.refresh()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(value="شروع مطالعه", rtl=True, size=Typography.h2,
                      weight=ft.FontWeight.W_600),
        content=ft.Container(
            width=320,
            content=ft.Column(
                [
                    ft.Text(value="درس", size=Typography.small,
                            color=ON_SURFACE_VAR, rtl=True),
                    subject,
                    ft.Container(height=Spacing.sm),
                    ft.Text(value="نوع", size=Typography.small,
                            color=ON_SURFACE_VAR, rtl=True),
                    ft.Row([study_btn, test_btn], spacing=Spacing.sm),
                ],
                spacing=Spacing.xs, tight=True,
            ),
        ),
        actions=[
            ft.TextButton(content="انصراف",
                          on_click=lambda _: ctx.close_dialog(dlg)),
            primary_button("شروع", on_click=_start_session,
                           icon=ft.Icons.PLAY_ARROW),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    ctx.open_dialog(dlg)


# --------------------------------------------------------------------------- #
# Timer loop — updates the elapsed timer every second
# --------------------------------------------------------------------------- #


def _ensure_timer_loop(ctx) -> None:
    """Start a background loop that updates the active session timer.

    Only one loop runs at a time. The loop exits when no session is active.
    """
    if getattr(ctx, "_timer_loop_running", False):
        return
    if study_session.get() is None:
        return
    ctx._timer_loop_running = True

    async def _loop():
        try:
            while True:
                session = study_session.get()
                if session is None:
                    break
                timer_text = getattr(ctx, "_active_timer_text", None)
                if timer_text is None:
                    break
                timer_text.value = _format_elapsed(session.elapsed_seconds())
                try:
                    timer_text.update()
                except Exception:
                    break
                await asyncio.sleep(1)
        finally:
            ctx._timer_loop_running = False

    try:
        ctx.page.run_task(_loop)
    except Exception:
        ctx._timer_loop_running = False


def _stop_timer_loop(ctx) -> None:
    """Signal the timer loop to stop. It will exit on its next iteration."""
    # The loop checks `study_session.get() is None` — once we end/cancel
    # the session, the loop will exit naturally. Nothing else to do.
    ctx._active_timer_text = None
    ctx._active_session = None


def _format_elapsed(seconds: int) -> str:
    """Format seconds as MM:SS with Persian digits."""
    mm, ss = divmod(seconds, 60)
    hh, mm = divmod(mm, 60)
    if hh > 0:
        return f"{to_fa(str(hh))}:{to_fa(str(mm).zfill(2))}:{to_fa(str(ss).zfill(2))}"
    return f"{to_fa(str(mm))}:{to_fa(str(ss).zfill(2))}"


# --------------------------------------------------------------------------- #
# Hero, next-step, sparkline, today-list (unchanged from previous redesign)
# --------------------------------------------------------------------------- #


def _greeting_header(today) -> ft.Control:
    greeting = _greeting()
    date_fa = _persian_date(today)
    return ft.Row(
        [
            ft.Column(
                [
                    ft.Text(value=greeting, size=Typography.h2,
                            weight=ft.FontWeight.W_600,
                            color=ON_SURFACE, rtl=True),
                    ft.Text(value=date_fa, size=Typography.small,
                            color=ON_SURFACE_VAR, rtl=True),
                ],
                spacing=Spacing.xs,
                expand=True,
            ),
            ft.Container(
                content=ft.Text(value="M", size=Typography.h2,
                                weight=ft.FontWeight.W_600,
                                color=ACCENT),
                width=40, height=40,
                alignment=CENTER,
                bgcolor=ACCENT_SOFT,
                border_radius=Radius.full,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )


def _hero_card(s: dict) -> ft.Control:
    minutes_fa = to_fa(s["minutes"])
    if s["goal_percent"] >= 100:
        support = f"هدف امروز محقق شد — {to_fa(int(s['goal_percent']))}٪"
        support_color = SUCCESS
    elif s["goal_percent"] > 0:
        support = (f"فاصله از برنامه: "
                   f"{to_fa(int(100 - s['goal_percent']))}٪")
        support_color = WARN
    else:
        support = "هنوز هدفی برای امروز تعریف نشده."
        support_color = ON_SURFACE_MUT

    tests_line = (f"{to_fa(s['tests'])} آزمون ثبت شده"
                  if s["tests"] else "بدون آزمون امروز")

    return card(
        ft.Column(
            [
                ft.Text(value="دقیقه مطالعه امروز",
                        size=Typography.small,
                        color=ON_SURFACE_VAR, rtl=True),
                ft.Container(height=Spacing.xs),
                ft.Text(value=minutes_fa, size=Typography.h1 + 12,
                        weight=ft.FontWeight.W_600,
                        color=ON_SURFACE, rtl=True),
                ft.Container(height=Spacing.xs),
                ft.Text(value=support, size=Typography.small,
                        color=support_color, rtl=True,
                        weight=ft.FontWeight.W_600),
                ft.Container(height=Spacing.xs),
                ft.Text(value=tests_line, size=Typography.tiny,
                        color=ON_SURFACE_MUT, rtl=True),
            ],
            spacing=0,
        ),
        padding=Layout.card_padding + Spacing.sm,
    )


def _next_step_card(s: dict) -> ft.Control:
    return card(
        ft.Row(
            [
                ft.Container(
                    width=32, height=32,
                    alignment=CENTER,
                    bgcolor=ACCENT_SOFT,
                    border_radius=Radius.full,
                    content=ft.Icon(ft.Icons.LIGHTBULB_OUTLINE,
                                    color=ACCENT, size=18),
                ),
                ft.Container(width=Spacing.md),
                ft.Column(
                    [
                        ft.Text(value="قدم بعدی", size=Typography.small,
                                color=ON_SURFACE_VAR, rtl=True),
                        ft.Container(height=2),
                        ft.Text(value=s["next_step_text"],
                                size=Typography.body,
                                color=ON_SURFACE, rtl=True,
                                weight=ft.FontWeight.W_600),
                    ],
                    spacing=0,
                    expand=True,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=Layout.card_padding,
    )


def _sparkline_card(today) -> ft.Control:
    last7 = analytics.last_7_days_minutes(today)
    spark = _sparkline(last7)
    sentence = _sparkline_sentence(last7)
    return card(
        ft.Column(
            [
                section_title("هفته اخیر"),
                ft.Container(height=Spacing.md),
                spark,
                ft.Container(height=Spacing.sm),
                ft.Text(value=sentence, size=Typography.tiny,
                        color=ON_SURFACE_VAR, rtl=True),
            ],
            spacing=0,
        ),
        padding=Layout.card_padding,
    )


def _today_sessions_card(today) -> ft.Control:
    sessions = models.list_sessions_for_date(today.isoformat())
    activities = {a.id: a for a in models.list_activities(active_only=False)}

    if not sessions:
        return card(
            ft.Column(
                [
                    section_title("جلسات امروز"),
                    ft.Container(height=Spacing.sm),
                    ft.Text(value="هنوز چیزی ثبت نشده.",
                            size=Typography.small,
                            color=ON_SURFACE_MUT, rtl=True),
                ],
                spacing=0,
            ),
            padding=Layout.card_padding,
        )

    rows: list[ft.Control] = []
    for sess in sessions:
        rows.append(_session_row(sess, activities.get(sess.activity_id)))
    return card(
        ft.Column(
            [
                section_title(f"جلسات امروز ({to_fa(len(sessions))})"),
                ft.Container(height=Spacing.sm),
                ft.Column(rows, spacing=Spacing.xs),
            ],
            spacing=0,
        ),
        padding=Layout.card_padding,
    )


def _session_row(sess, act) -> ft.Control:
    name = act.name if act else "—"
    color = act.color if act and act.color else ACCENT
    sub = f"{to_fa(sess.minutes)} دقیقه"
    if sess.tests_count:
        sub += f" • {to_fa(sess.tests_count)} آزمون"
    if sess.note:
        # Strip the [مطالعه]/[آزمون] prefix for display — it's metadata.
        note_clean = sess.note
        if note_clean.startswith("[") and "]" in note_clean:
            note_clean = note_clean.split("]", 1)[1].strip()
        if note_clean:
            sub += f" • {note_clean}"

    return ft.Container(
        padding=pad_sym(horizontal=Spacing.md, vertical=Spacing.sm),
        bgcolor=SURFACE_HIGH,
        border_radius=Radius.sm,
        content=ft.Row(
            [
                ft.Container(width=3, height=28, bgcolor=color,
                             border_radius=Radius.full),
                ft.Container(width=Spacing.sm),
                ft.Column(
                    [
                        ft.Text(value=name, size=Typography.small,
                                color=ON_SURFACE,
                                weight=ft.FontWeight.W_600, rtl=True),
                        ft.Text(value=sub, size=Typography.tiny,
                                color=ON_SURFACE_VAR, rtl=True),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _sparkline(last7: list[tuple[str, int]]) -> ft.Control:
    max_m = max((m for _, m in last7), default=60) or 60
    H = 36
    fa_weekdays_sat = ["ش", "ی", "د", "س", "چ", "پ", "ج"]

    cols: list[ft.Control] = []
    for date_str, mins in last7:
        d = time_sync.now().date()  # just for weekday calc — we use the date_str
        from datetime import date as _date
        d = _date.fromisoformat(date_str)
        sat_idx = (d.weekday() + 2) % 7
        wd = fa_weekdays_sat[sat_idx]
        h = max(3, int(H * mins / max_m)) if mins > 0 else 3
        color = ACCENT if mins > 0 else OUTLINE
        cols.append(ft.Column(
            [
                ft.Container(
                    width=4, height=h, bgcolor=color,
                    border_radius=Radius.full,
                ),
                ft.Container(height=Spacing.xs),
                ft.Text(value=wd, size=Typography.tiny,
                        color=ON_SURFACE_MUT, rtl=True,
                        text_align=ft.TextAlign.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.END,
            expand=True,
        ))

    return ft.Row(cols, spacing=Spacing.sm, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)


def _sparkline_sentence(last7: list[tuple[str, int]]) -> str:
    total = sum(m for _, m in last7)
    if total == 0:
        return "هفته‌ای بدون ثبت. می‌توانی از امروز شروع کنی."
    days_active = sum(1 for _, m in last7 if m > 0)
    avg = total // max(1, days_active)
    return (f"۷ روز اخیر: {to_fa(total)} دقیقه در {to_fa(days_active)} روز "
            f"(میانگین {to_fa(avg)} دقیقه در روزهای فعال).")


def _greeting() -> str:
    h = time_sync.now().hour
    if 5 <= h < 12:  return "صبحت بخیر"
    if 12 <= h < 18: return "ظهرت بخیر"
    if 18 <= h < 22: return "عصرت بخیر"
    return "شبت بخیر"


def _persian_date(d) -> str:
    months = ["ژانویه", "فوریه", "مارس", "آوریل", "مه", "ژوئن",
              "ژوئیه", "اوت", "سپتامبر", "اکتبر", "نوامبر", "دسامبر"]
    return f"{to_fa(d.day)} {months[d.month - 1]} {to_fa(d.year)}"
