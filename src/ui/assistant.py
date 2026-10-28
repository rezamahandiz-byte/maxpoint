"""Assistant modal — 3-step progressive disclosure.

Law #4 in action: even inside the modal, only ONE action at a time is
available. The 3 steps:

    1. PREVIEW — show the local summary that WILL be sent. The user can
       review it before any network call. Two buttons: "بستن" / "ادامه".
    2. CALL    — disable the action button, show a calm progress indicator,
       call `core.ai.request_report` (stub in 0.1). No "loading…" copy.
    3. RESULT  — show the AI response (or the stub message). If the call
       failed, show the Persian error string. One button: "بستن".

In v0.1 step 2 returns immediately with the stub message; the structure
is in place for v0.2 to swap in the real OpenAI call.
"""
from __future__ import annotations

from datetime import date, timedelta
from services import time_sync
from typing import Any

import flet as ft

from core import analytics
from ui.theme import Colors, Typography, Spacing, Radius, Motion, Layout
from ui import (
    ACCENT, ACCENT_SOFT, ON_SURFACE, ON_SURFACE_VAR, ON_SURFACE_MUT,
    OUTLINE, SURFACE, SURFACE_HIGH, WARN,
    CENTER, CENTER_LEFT,
    body_text, caption, card, divider, label, pad_only, pad_sym, margin_only,
    primary_button, secondary_button, text_button, to_fa,
)


def open_assistant(ctx) -> None:
    """Open the 3-step assistant modal."""
    today = time_sync.today()
    summary = _build_summary(today)

    # Step views are stacked in a single Container; we swap its `content`.
    content_host = ft.Container(padding=Spacing.md)
    state = {"step": "preview"}

    def _render_step():
        if state["step"] == "preview":
            content_host.content = _preview_step(ctx, summary, _go_to_call)
        elif state["step"] == "call":
            content_host.content = _call_step()
        elif state["step"] == "result":
            content_host.content = _result_step(
                state.get("result", ""),
                state.get("is_error", False),
                lambda: ctx.close_dialog(dlg),
            )
        try:
            content_host.update()
            dlg.update()
            ctx.page.update()
        except Exception:
            pass

    def _go_to_call():
        state["step"] = "call"
        _render_step()

        async def _do_call():
            api_key = await ctx.secure.get_async() or ""
            try:
                content = await analytics_request_or_fallback(ctx, summary, api_key)
                state["result"] = content
                state["is_error"] = False
            except Exception as exc:
                state["result"] = f"خطا در تهیه گزارش: {exc}"
                state["is_error"] = True
            state["step"] = "result"
            _render_step()

        ctx.page.run_task(_do_call)

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(value="دستیار تحلیل", rtl=True, size=Typography.h2,
                      weight=ft.FontWeight.W_600),
        content=ft.Container(
            width=340,
            content=ft.Column(
                [
                    content_host,
                    ft.Container(height=Spacing.sm),
                    _stepper_indicator(state),
                ],
                spacing=Spacing.xs, tight=True,
            ),
        ),
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # We don't pass `actions` — each step renders its own buttons inside
    # content_host. Cleaner UI, single source of truth per step.
    ctx.open_dialog(dlg)
    _render_step()


# --------------------------------------------------------------------------- #
# Steps
# --------------------------------------------------------------------------- #


def _preview_step(ctx, summary: dict, on_continue) -> ft.Control:
    """Step 1: show the local summary that will be sent."""
    return ft.Column(
        [
            ft.Text(
                value="این خلاصه به هوش مصنوعی ارسال می‌شود:",
                size=Typography.small, color=ON_SURFACE_VAR, rtl=True,
            ),
            ft.Container(height=Spacing.sm),
            ft.Container(
                padding=Spacing.md,
                bgcolor=SURFACE_HIGH,
                border_radius=Radius.sm,
                content=_summary_block(summary),
            ),
            ft.Container(height=Spacing.sm),
            ft.Text(
                value="هیچ یادداشت شخصی یا ردیف خامی ارسال نمی‌شود.",
                size=Typography.tiny, color=ON_SURFACE_MUT, rtl=True,
            ),
            ft.Container(height=Spacing.md),
            ft.Row(
                [
                    text_button("بستن",
                                on_click=lambda _: ctx.close_dialog(_current_dlg(ctx))),
                    primary_button("ادامه", on_click=lambda _: on_continue(),
                                   icon=ft.Icons.ARROW_FORWARD),
                ],
                alignment=ft.MainAxisAlignment.END,
                spacing=Spacing.sm,
            ),
        ],
        spacing=0,
    )


def _call_step() -> ft.Control:
    """Step 2: calm progress. No 'loading…' copy — just a spinner + fact."""
    return ft.Column(
        [
            ft.Container(height=Spacing.lg),
            ft.Row(
                [
                    ft.ProgressRing(color=ACCENT, width=32, height=32,
                                    stroke_width=2.5),
                    ft.Container(width=Spacing.md),
                    ft.Column(
                        [
                            ft.Text(value="در حال تهیه تحلیل…",
                                    size=Typography.body,
                                    color=ON_SURFACE, rtl=True,
                                    weight=ft.FontWeight.W_600),
                            ft.Text(value="این عملیات چند ثانیه طول می‌کشد.",
                                    size=Typography.tiny,
                                    color=ON_SURFACE_VAR, rtl=True),
                        ],
                        spacing=2,
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(height=Spacing.lg),
        ],
        spacing=0,
    )


def _result_step(content: str, is_error: bool,
                 on_close) -> ft.Control:
    """Step 3: show the result (or the error)."""
    color = WARN if is_error else ON_SURFACE
    return ft.Column(
        [
            ft.Text(
                value="تحلیل" if not is_error else "خطا",
                size=Typography.small, color=ON_SURFACE_VAR, rtl=True,
            ),
            ft.Container(height=Spacing.xs),
            ft.Container(
                padding=Spacing.md,
                bgcolor=SURFACE_HIGH,
                border_radius=Radius.sm,
                content=ft.Text(
                    value=content,
                    size=Typography.body, color=color, rtl=True,
                    selectable=True,
                ),
            ),
            ft.Container(height=Spacing.md),
            ft.Row(
                [
                    primary_button("بستن", on_click=lambda _: on_close()),
                ],
                alignment=ft.MainAxisAlignment.END,
            ),
        ],
        spacing=0,
    )


# --------------------------------------------------------------------------- #
# Stepper indicator
# --------------------------------------------------------------------------- #


def _stepper_indicator(state: dict) -> ft.Control:
    """A row of 3 dots — the current step's dot is filled accent."""
    step_idx = {"preview": 0, "call": 1, "result": 2}.get(state["step"], 0)
    dots: list[ft.Control] = []
    for i in range(3):
        is_current = (i == step_idx)
        dots.append(
            ft.Container(
                width=8, height=8,
                bgcolor=ACCENT if is_current else OUTLINE,
                border_radius=Radius.full,
            )
        )
        if i < 2:
            dots.append(ft.Container(width=Spacing.sm))
    return ft.Row(
        dots,
        alignment=ft.MainAxisAlignment.CENTER,
    )


# --------------------------------------------------------------------------- #
# Summary builder
# --------------------------------------------------------------------------- #


def _build_summary(today: date) -> dict[str, Any]:
    """Aggregate-only summary. No raw rows, no notes."""
    last7 = analytics.last_7_days_minutes(today)
    total_7d = sum(m for _, m in last7)
    nonzero_days = sum(1 for _, m in last7 if m > 0)
    tests_7d = sum(t for _, t in analytics.last_7_days_tests(today))
    dq = analytics.data_quality((today - timedelta(days=6), today))

    weekly = analytics.weekly_trend(4)
    weekly_totals = [w["minutes"] for w in weekly]

    series = analytics.exam_taraz_series()

    return {
        "report_type": "weekly",
        "period_start": (today - timedelta(days=6)).isoformat(),
        "period_end": today.isoformat(),
        "minutes_7d": total_7d,
        "active_days_7d": nonzero_days,
        "tests_7d": tests_7d,
        "data_quality_percent": dq,
        "weekly_trend": weekly_totals,
        "exam_count": len(series),
        "exam_taraz_first": series[0][1] if series else None,
        "exam_taraz_last": series[-1][1] if series else None,
    }


def _summary_block(summary: dict[str, Any]) -> ft.Control:
    rows = [
        ("مجموع مطالعه ۷ روز", to_fa(summary["minutes_7d"]) + " دقیقه"),
        ("روزهای فعال", to_fa(summary["active_days_7d"])),
        ("آزمون‌ها", to_fa(summary["tests_7d"])),
        ("کیفیت ثبت", to_fa(summary["data_quality_percent"]) + "٪"),
        ("آزمون‌های ثبت‌شده", to_fa(summary["exam_count"])),
    ]
    return ft.Column(
        [
            ft.Row(
                [
                    ft.Text(value=label, size=Typography.small,
                            color=ON_SURFACE_VAR, rtl=True, expand=True),
                    ft.Text(value=value, size=Typography.small,
                            color=ON_SURFACE, rtl=True,
                            text_align=ft.TextAlign.LEFT,
                            weight=ft.FontWeight.W_600),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
            for label, value in rows
        ],
        spacing=Spacing.xs,
    )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _current_dlg(ctx):
    """Best-effort: return the topmost dialog. Used by the 'بستن' button."""
    try:
        return ctx.page._dialogs.controls[-1] if ctx.page._dialogs.controls else None
    except Exception:
        return None


async def analytics_request_or_fallback(ctx, summary: dict, api_key: str) -> str:
    """Call `core.ai.request_report` (stub in 0.1)."""
    from core import ai
    return await ai.request_report(summary["report_type"], summary, api_key)
