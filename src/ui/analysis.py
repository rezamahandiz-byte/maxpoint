"""Analysis tab — two charts, two sentences, one assistant button.

Law #5 in action: every chart has one sentence below it. A chart without
interpretation is noise; the sentence turns the chart into insight.

The tab is intentionally NOT a dashboard. There are no KPI tiles, no
comparison cards, no time-range pickers. Just:
    - 7-day bar chart (study minutes) + one sentence
    - Exam taraz line chart (only if data exists) + one sentence
    - One assistant button at the bottom

The assistant button opens the AI modal (ui/assistant.py). It is the
only state-changing tap target on this screen.
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from services import time_sync

import flet as ft

from core import analytics, models
from ui.theme import Colors, Typography, Spacing, Radius, Motion, Layout
from ui import (
    ACCENT, ACCENT_SOFT, ON_SURFACE, ON_SURFACE_VAR, ON_SURFACE_MUT,
    OUTLINE, SURFACE, SURFACE_HIGH, WARN, INFO,
    CENTER, CENTER_LEFT, BOTTOM_CENTER,
    body_text, caption, card, divider, label, pad_only, pad_sym, margin_only,
    primary_button, screen_scroll, screen_title, section_title, to_fa,
)
from ui import assistant as _assistant


def build(ctx) -> ft.Control:
    today = time_sync.today()
    last7 = analytics.last_7_days_minutes(today)
    series = analytics.exam_taraz_series()

    bar_card = _bar_chart_card(last7)
    line_card = _line_chart_card(series)
    assistant_btn = primary_button(
        "دریافت تحلیل هوشمند",
        on_click=lambda _: _assistant.open_assistant(ctx),
        icon=ft.Icons.AUTO_AWESOME,
    )

    return screen_scroll([
        screen_title("تحلیل"),
        ft.Container(height=Spacing.sm),
        caption("نمودارها توصیفی‌اند، نه قضاوت. فقط نشان می‌دهند زمان کجا رفته."),
        ft.Container(height=Spacing.lg),
        bar_card,
        ft.Container(height=Spacing.md),
        line_card,
        ft.Container(height=Spacing.lg),
        assistant_btn,
    ])


def on_show(ctx) -> None:
    return None


# --------------------------------------------------------------------------- #
# Bar chart card — 7-day study minutes
# --------------------------------------------------------------------------- #


def _bar_chart_card(last7: list[tuple[str, int]]) -> ft.Control:
    chart = _bar_chart(last7)
    sentence = _bar_sentence(last7)
    return card(
        ft.Column(
            [
                section_title("۷ روز اخیر"),
                ft.Container(height=Spacing.md),
                chart,
                ft.Container(height=Spacing.sm),
                ft.Text(value=sentence, size=Typography.small,
                        color=ON_SURFACE_VAR, rtl=True),
            ],
            spacing=0,
        ),
        padding=Layout.card_padding,
    )


def _bar_chart(last7: list[tuple[str, int]]) -> ft.Control:
    """Custom 7-day bar chart built from Containers.

    Law #1: missing data is rendered in muted surface (OUTLINE), never red.
    Law #5: the chart is paired with a sentence below it.
    """
    fa_weekdays_sat = ["ش", "ی", "د", "س", "چ", "پ", "ج"]
    max_m = max((m for _, m in last7), default=60) or 60
    tick = _nice_interval(max_m)
    y_top = max(tick * 3, max_m, 30)

    PLOT_H = 120

    bar_cols: list[ft.Control] = []
    label_cols: list[ft.Control] = []
    for date_str, mins in last7:
        d = date.fromisoformat(date_str)
        sat_idx = (d.weekday() + 2) % 7
        wd_label = fa_weekdays_sat[sat_idx]

        # Today gets a slightly stronger color so the user can find themselves.
        is_today = (date_str == time_sync.today().isoformat())
        bar_color = ACCENT if mins > 0 else OUTLINE
        bar_h = max(2, int(PLOT_H * mins / y_top)) if mins > 0 else 2

        bar_cols.append(ft.Container(
            expand=True,
            alignment=ft.Alignment(0, 1),  # bottom-center
            content=ft.Column(
                [
                    ft.Container(
                        width=22, height=bar_h,
                        bgcolor=bar_color,
                        border_radius=Radius.sm,
                    ),
                ],
                alignment=ft.MainAxisAlignment.END,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            ),
        ))
        label_cols.append(ft.Container(
            expand=True,
            alignment=CENTER,
            content=ft.Text(
                value=wd_label,
                size=Typography.tiny,
                color=ACCENT if is_today else ON_SURFACE_MUT,
                rtl=True, text_align=ft.TextAlign.CENTER,
                weight=ft.FontWeight.W_600 if is_today else ft.FontWeight.W_400,
            ),
        ))

    plot = ft.Container(
        height=PLOT_H,
        bgcolor=SURFACE_HIGH,
        border_radius=Radius.sm,
        padding=pad_sym(horizontal=Spacing.sm, vertical=Spacing.sm),
        content=ft.Row(bar_cols, spacing=Spacing.xs, expand=True),
    )

    # Y-axis ticks: 0, mid, max — small, on the right.
    y_labels = ft.Row(
        [
            ft.Text(value=to_fa(0), size=Typography.tiny, color=ON_SURFACE_MUT),
            ft.Container(expand=True),
            ft.Text(value=to_fa(int(y_top / 2)), size=Typography.tiny,
                    color=ON_SURFACE_MUT),
            ft.Container(expand=True),
            ft.Text(value=to_fa(int(y_top)), size=Typography.tiny,
                    color=ON_SURFACE_MUT),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    return ft.Column(
        [
            y_labels,
            ft.Container(height=Spacing.xs),
            plot,
            ft.Container(height=Spacing.xs),
            ft.Row(label_cols, spacing=Spacing.xs),
        ],
        spacing=0,
    )


def _bar_sentence(last7: list[tuple[str, int]]) -> str:
    total = sum(m for _, m in last7)
    if total == 0:
        return "هیچ فعالیتی در ۷ روز اخیر ثبت نشده."
    nonzero = [m for _, m in last7 if m > 0]
    avg = sum(nonzero) // len(nonzero) if nonzero else 0
    peak_date_str, peak_m = max(last7, key=lambda x: x[1])
    peak_d = date.fromisoformat(peak_date_str)
    fa_weekdays_sat = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه",
                       "چهارشنبه", "پنجشنبه", "جمعه"]
    peak_wd = fa_weekdays_sat[(peak_d.weekday() + 2) % 7]
    return (f"میانگین روزهای ثبت‌شده: {to_fa(avg)} دقیقه. "
            f"بیشترین مطالعه در {peak_wd} با {to_fa(peak_m)} دقیقه.")


# --------------------------------------------------------------------------- #
# Line chart card — exam taraz over time
# --------------------------------------------------------------------------- #


def _line_chart_card(series: list[tuple[int, int]]) -> ft.Control:
    if not series:
        return card(
            ft.Column(
                [
                    section_title("روند تراز آزمون‌ها"),
                    ft.Container(height=Spacing.md),
                    ft.Container(
                        padding=Spacing.md,
                        bgcolor=SURFACE_HIGH,
                        border_radius=Radius.sm,
                        alignment=CENTER,
                        content=ft.Text(
                            value="هنوز آزمونی ثبت نشده. در تنظیمات → آزمون‌ها اضافه کن.",
                            size=Typography.small, color=ON_SURFACE_MUT, rtl=True,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ),
                ],
                spacing=0,
            ),
            padding=Layout.card_padding,
        )

    chart = _line_chart(series)
    sentence = _line_sentence(series)
    return card(
        ft.Column(
            [
                section_title("روند تراز آزمون‌ها"),
                ft.Container(height=Spacing.md),
                chart,
                ft.Container(height=Spacing.sm),
                ft.Text(value=sentence, size=Typography.small,
                        color=ON_SURFACE_VAR, rtl=True),
            ],
            spacing=0,
        ),
        padding=Layout.card_padding,
    )


def _line_chart(series: list[tuple[int, int]]) -> ft.Control:
    """Custom line chart for exam taraz — dots + line segments."""
    n = len(series)
    ys = [t for _, t in series]
    y_min = min(ys)
    y_max = max(ys)
    if y_max == y_min:
        y_max = y_min + 1
    y_pad = (y_max - y_min) * 0.15
    y_lo = y_min - y_pad
    y_hi = y_max + y_pad

    PLOT_W = 280
    PLOT_H = 120
    DOT = 8
    LINE_W = 2

    def to_xy(i: int, t: int) -> tuple[float, float]:
        x = (i / max(1, n - 1)) * (PLOT_W - DOT) + DOT / 2
        y = PLOT_H - DOT/2 - ((t - y_lo) / (y_hi - y_lo)) * (PLOT_H - DOT)
        return x, y

    points_xy = [to_xy(i, t) for i, (_, t) in enumerate(series)]

    stack_items: list[ft.Control] = [
        ft.Container(width=PLOT_W, height=PLOT_H, bgcolor=SURFACE_HIGH,
                     border_radius=Radius.sm),
    ]

    # Line segments between consecutive points.
    for i in range(len(points_xy) - 1):
        x1, y1 = points_xy[i]
        x2, y2 = points_xy[i + 1]
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length < 1:
            continue
        angle_rad = math.atan2(dy, dx)
        stack_items.append(
            ft.Container(
                left=x1,
                top=y1 - LINE_W / 2,
                width=length,
                height=LINE_W,
                bgcolor=ACCENT,
                border_radius=LINE_W / 2,
                rotate=ft.Rotate(angle=angle_rad,
                                 alignment=ft.Alignment(-1, 0)),
            )
        )

    # Dots on top — last dot is filled accent, others are muted surface ring.
    for i, (x, y) in enumerate(points_xy):
        is_last = (i == len(points_xy) - 1)
        stack_items.append(
            ft.Container(
                left=x - DOT / 2,
                top=y - DOT / 2,
                width=DOT, height=DOT,
                bgcolor=ACCENT if is_last else ON_SURFACE,
                shape=ft.BoxShape.CIRCLE,
            )
        )

    plot = ft.Stack(
        stack_items, width=PLOT_W, height=PLOT_H, expand=True,
    )

    y_labels = ft.Row(
        [
            ft.Text(value=to_fa(int(y_lo)), size=Typography.tiny,
                    color=ON_SURFACE_MUT),
            ft.Container(expand=True),
            ft.Text(value=to_fa(int(y_hi)), size=Typography.tiny,
                    color=ON_SURFACE_MUT),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    x_labels = ft.Row(
        [
            ft.Container(
                expand=True, alignment=CENTER,
                content=ft.Text(value=to_fa(n), size=Typography.tiny,
                                color=ON_SURFACE_MUT, rtl=True,
                                text_align=ft.TextAlign.CENTER),
            )
            for n, _ in series
        ],
        spacing=0,
    )

    return ft.Column(
        [
            y_labels,
            ft.Container(height=Spacing.xs),
            ft.Container(
                content=ft.Row([plot], alignment=ft.MainAxisAlignment.CENTER),
                alignment=CENTER,
            ),
            ft.Container(height=Spacing.xs),
            x_labels,
        ],
        spacing=0,
    )


def _line_sentence(series: list[tuple[int, int]]) -> str:
    if len(series) < 2:
        return "برای دیدن روند، حداقل دو آزمون لازم است."
    first_n, first_t = series[0]
    last_n, last_t = series[-1]
    diff = last_t - first_t
    if diff == 0:
        return f"تراز از آزمون {to_fa(first_n)} تا {to_fa(last_n)} ثابت بوده."
    direction = "افزایش" if diff > 0 else "کاهش"
    return (f"تراز از آزمون {to_fa(first_n)} تا {to_fa(last_n)} "
            f"{to_fa(abs(diff))} واحد {direction} داشته.")


def _nice_interval(max_value: int) -> float:
    """Pick a readable y-axis interval for the bar chart."""
    if max_value <= 0:
        return 30.0
    raw = max_value / 4
    for step in (15, 30, 60, 90, 120, 180, 240, 360, 480, 600):
        if raw <= step:
            return float(step)
    return float(int(raw))
