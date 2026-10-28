"""Record tab — one form, one action.

Law #4 in action: this screen has ONE thing to do — record a session.
The list of past sessions lives on the Home tab; editing/deleting lives
in a separate dialog reachable from Home's session rows.

The FAB also opens the same form as a quick-record dialog. The form
itself is the screen's primary content; the FAB is just a shortcut from
other tabs.
"""
from __future__ import annotations

from datetime import date
from services import time_sync

import flet as ft

from core import models
from ui.theme import Colors, Typography, Spacing, Radius, Motion, Layout
from ui import (
    ACCENT, ACCENT_SOFT, ON_SURFACE, ON_SURFACE_VAR, ON_SURFACE_MUT,
    OUTLINE, SURFACE, SURFACE_HIGH, WARN,
    CENTER, CENTER_LEFT, BOTTOM_CENTER,
    body_text, caption, card, divider, label, pad_only, pad_sym, margin_only,
    primary_button, screen_scroll, screen_title, section_title, to_fa,
)


def build(ctx) -> ft.Control:
    today = time_sync.today()
    activities = models.list_activities(active_only=True)

    if not activities:
        return screen_scroll([
            screen_title("ثبت"),
            ft.Container(height=Spacing.lg),
            card(
                ft.Text(value="اول از تنظیمات یک درس اضافه کن.",
                        size=Typography.body, color=ON_SURFACE_VAR, rtl=True),
                padding=Layout.card_padding,
            ),
        ])

    form = _form_card(ctx, today, activities)
    return screen_scroll([
        screen_title("ثبت جلسه"),
        ft.Container(height=Spacing.sm),
        caption("یک جلسه را همینجا ثبت کن. تمام فیلدها در دستگاهت ذخیره می‌شوند."),
        ft.Container(height=Spacing.lg),
        form,
    ])


def on_show(ctx) -> None:
    return None


# --------------------------------------------------------------------------- #
# Form
# --------------------------------------------------------------------------- #


def _form_card(ctx, today: date, activities: list) -> ft.Control:
    subject = ft.Dropdown(
        label="درس",
        rtl=True, text_size=Typography.body,
        dense=True,
        options=[ft.DropdownOption(key=str(a.id), text=a.name) for a in activities],
        value=str(activities[0].id),
        expand=True,
        border_radius=Radius.sm,
    )
    minutes = _minute_stepper(default=25)
    tests = _tests_field(default=0)
    note = ft.TextField(
        label="یادداشت (اختیاری)",
        rtl=True, text_size=Typography.body,
        dense=True,
        max_length=140,
        expand=True,
        border_radius=Radius.sm,
    )

    def _save(_e=None):
        try:
            act_id = int(subject.value) if subject.value else 0
            mins = minutes.value_int()
            tcount = tests.value_int()
        except (TypeError, ValueError):
            ctx.snack("عدد معتبر وارد کن.")
            return
        if not act_id or mins <= 0:
            ctx.snack("درس و دقیقه را پر کن.")
            return
        models.create_session(
            date_str=today.isoformat(),
            activity_id=act_id,
            minutes=mins,
            tests_count=tcount,
            note=(note.value or "").strip() or None,
        )
        # Reset for next entry — keep the same subject (faster for repeat sessions).
        minutes.set_value(25)
        tests.set_value(0)
        note.value = ""
        ctx.snack("ثبت شد.")
        ctx.refresh()

    save_btn = primary_button("ثبت جلسه", on_click=_save,
                              icon=ft.Icons.SAVE_OUTLINED)

    return card(
        ft.Column(
            [
                _field_label("درس"),
                subject,
                ft.Container(height=Spacing.md),
                _field_label("مدت (دقیقه)"),
                minutes.control,
                ft.Container(height=Spacing.md),
                _field_label("آزمون (تعداد)"),
                tests.control,
                ft.Container(height=Spacing.md),
                _field_label("یادداشت"),
                note,
                ft.Container(height=Spacing.lg),
                save_btn,
            ],
            spacing=Spacing.sm,
        ),
        padding=Layout.card_padding,
    )


def _field_label(text: str) -> ft.Text:
    return ft.Text(value=text, size=Typography.small,
                   color=ON_SURFACE_VAR, rtl=True)


# --------------------------------------------------------------------------- #
# Stepper widgets — large tap targets, no keyboard friction
# --------------------------------------------------------------------------- #


class _MinuteStepper:
    """A +/- stepper for minute entry. Default 25 (Pomodoro-ish).

    Why a stepper and not a TextField? On a phone, typing a number is
    three taps (open keyboard, type, dismiss). A stepper is one tap to
    add or subtract 5 minutes. Reduces friction → reduces procrastination.
    """

    def __init__(self, default: int = 25, step: int = 5,
                 min_v: int = 5, max_v: int = 240):
        self._value = default
        self._step = step
        self._min = min_v
        self._max = max_v
        self._label = ft.Text(value=to_fa(default), size=Typography.h2,
                              weight=ft.FontWeight.W_600,
                              color=ON_SURFACE, rtl=True,
                              text_align=ft.TextAlign.CENTER)
        self._caption = ft.Text(value="دقیقه", size=Typography.tiny,
                                color=ON_SURFACE_VAR, rtl=True,
                                text_align=ft.TextAlign.CENTER)
        self.control = ft.Container(
            content=ft.Row(
                [
                    self._minus_btn(),
                    ft.Container(
                        content=ft.Column(
                            [self._label, self._caption],
                            spacing=2,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        alignment=CENTER,
                        expand=True,
                    ),
                    self._plus_btn(),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=pad_sym(horizontal=Spacing.sm, vertical=Spacing.sm),
            bgcolor=SURFACE_HIGH,
            border_radius=Radius.sm,
        )

    def _minus_btn(self) -> ft.Control:
        return ft.IconButton(
            icon=ft.Icons.REMOVE_OUTLINED,
            icon_size=24,
            icon_color=ON_SURFACE,
            tooltip="کمتر",
            on_click=lambda _: self._add(-self._step),
            style=ft.ButtonStyle(shape=ft.CircleBorder()),
        )

    def _plus_btn(self) -> ft.Control:
        return ft.IconButton(
            icon=ft.Icons.ADD_OUTLINED,
            icon_size=24,
            icon_color=ON_SURFACE,
            tooltip="بیشتر",
            on_click=lambda _: self._add(self._step),
            style=ft.ButtonStyle(shape=ft.CircleBorder()),
        )

    def _add(self, delta: int) -> None:
        new_v = max(self._min, min(self._max, self._value + delta))
        if new_v == self._value:
            return
        self._value = new_v
        self._label.value = to_fa(new_v)
        self._label.update()

    def set_value(self, v: int) -> None:
        self._value = max(self._min, min(self._max, int(v)))
        self._label.value = to_fa(self._value)
        try:
            self._label.update()
        except Exception:
            pass

    def value_int(self) -> int:
        return self._value


class _TestsField:
    """Tests count — also a stepper. Most days it's 0; sometimes 1-3."""

    def __init__(self, default: int = 0, step: int = 1,
                 min_v: int = 0, max_v: int = 20):
        self._value = default
        self._step = step
        self._min = min_v
        self._max = max_v
        self._label = ft.Text(value=to_fa(default), size=Typography.h2,
                              weight=ft.FontWeight.W_600,
                              color=ON_SURFACE, rtl=True,
                              text_align=ft.TextAlign.CENTER)
        self._caption = ft.Text(value="آزمون", size=Typography.tiny,
                                color=ON_SURFACE_VAR, rtl=True,
                                text_align=ft.TextAlign.CENTER)
        self.control = ft.Container(
            content=ft.Row(
                [
                    ft.IconButton(
                        icon=ft.Icons.REMOVE_OUTLINED, icon_size=24,
                        icon_color=ON_SURFACE, tooltip="کمتر",
                        on_click=lambda _: self._add(-self._step),
                        style=ft.ButtonStyle(shape=ft.CircleBorder()),
                    ),
                    ft.Container(
                        content=ft.Column(
                            [self._label, self._caption],
                            spacing=2,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        alignment=CENTER,
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.ADD_OUTLINED, icon_size=24,
                        icon_color=ON_SURFACE, tooltip="بیشتر",
                        on_click=lambda _: self._add(self._step),
                        style=ft.ButtonStyle(shape=ft.CircleBorder()),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=pad_sym(horizontal=Spacing.sm, vertical=Spacing.sm),
            bgcolor=SURFACE_HIGH,
            border_radius=Radius.sm,
        )

    def _add(self, delta: int) -> None:
        new_v = max(self._min, min(self._max, self._value + delta))
        if new_v == self._value:
            return
        self._value = new_v
        self._label.value = to_fa(new_v)
        self._label.update()

    def set_value(self, v: int) -> None:
        self._value = max(self._min, min(self._max, int(v)))
        self._label.value = to_fa(self._value)
        try:
            self._label.update()
        except Exception:
            pass

    def value_int(self) -> int:
        return self._value


def _minute_stepper(default: int = 25) -> _MinuteStepper:
    return _MinuteStepper(default=default)


def _tests_field(default: int = 0) -> _TestsField:
    return _TestsField(default=default)


# --------------------------------------------------------------------------- #
# Quick-record dialog (opened from FAB on Home/Record)
# --------------------------------------------------------------------------- #


def open_quick_record(ctx) -> None:
    """Open a compact record dialog from the FAB."""
    today = time_sync.today()
    activities = models.list_activities(active_only=True)
    if not activities:
        ctx.snack("اول یک درس در تنظیمات اضافه کن.")
        return

    subject = ft.Dropdown(
        label="درس", rtl=True, text_size=Typography.body, dense=True,
        options=[ft.DropdownOption(key=str(a.id), text=a.name) for a in activities],
        value=str(activities[0].id), expand=True,
    )
    minutes = _MinuteStepper(default=25)
    tests = _TestsField(default=0)
    note = ft.TextField(
        label="یادداشت (اختیاری)", rtl=True, text_size=Typography.body,
        dense=True, max_length=140, expand=True,
    )

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(value="ثبت سریع", rtl=True, size=Typography.h2,
                      weight=ft.FontWeight.W_600),
        content=ft.Container(
            width=320,
            content=ft.Column(
                [
                    _field_label("درس"),
                    subject,
                    ft.Container(height=Spacing.sm),
                    _field_label("مدت (دقیقه)"),
                    minutes.control,
                    ft.Container(height=Spacing.sm),
                    _field_label("آزمون"),
                    tests.control,
                    ft.Container(height=Spacing.sm),
                    _field_label("یادداشت"),
                    note,
                ],
                spacing=Spacing.xs, tight=True,
            ),
        ),
        actions=[
            ft.TextButton(content="انصراف",
                          on_click=lambda _: ctx.close_dialog(dlg)),
            primary_button("ثبت", on_click=lambda _: _save_quick(
                ctx, dlg, today, subject, minutes, tests, note),
                icon=ft.Icons.SAVE_OUTLINED),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    ctx.open_dialog(dlg)


def _save_quick(ctx, dlg, today, subject, minutes, tests, note) -> None:
    try:
        act_id = int(subject.value) if subject.value else 0
        mins = minutes.value_int()
        tcount = tests.value_int()
    except (TypeError, ValueError):
        ctx.snack("عدد معتبر وارد کن.")
        return
    if not act_id or mins <= 0:
        ctx.snack("درس و دقیقه را پر کن.")
        return
    models.create_session(
        date_str=today.isoformat(),
        activity_id=act_id,
        minutes=mins,
        tests_count=tcount,
        note=(note.value or "").strip() or None,
    )
    ctx.close_dialog(dlg)
    ctx.snack("ثبت شد.")
    ctx.refresh()
