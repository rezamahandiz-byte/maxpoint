"""Settings tab — 4 expandable groups.

Law #4 in action: ONE action per screen would be impossible here (settings
is intrinsically multi-purpose), so we honour the spirit of the law by
COLLAPSING every group by default. The screen shows 4 section headers;
only the one the user taps expands. This keeps the screen scannable in
under 5 seconds.

Groups:
    1. مدیریت دروس        — rename + activate/deactivate each subject
    2. اهداف روزانه       — per-subject daily minute target
    3. کلید API و Keystore — OpenAI key, keystore status, delete key
    4. پشتیبان و پاک‌سازی  — JSON export, JSON import, double-confirm wipe

The "danger zone" (clear all data) lives inside group 4 and requires
two-step confirmation (type PAKE → final confirm).
"""
from __future__ import annotations

import flet as ft

from core import models
from services import backup as backup_service
from services import notifier as _notifier
from ui.theme import Colors, Typography, Spacing, Radius, Motion, Layout
from ui import (
    ACCENT, ACCENT_SOFT, ON_SURFACE, ON_SURFACE_VAR, ON_SURFACE_MUT,
    OUTLINE, SURFACE, SURFACE_HIGH, WARN,
    CENTER, CENTER_LEFT, BOTTOM_CENTER,
    body_text, caption, card, divider, label, pad_only, pad_sym, margin_only,
    primary_button, secondary_button, tertiary_button, text_button,
    screen_scroll, screen_title, section_title, to_fa, border_all,
)


def build(ctx) -> ft.Control:
    return screen_scroll([
        screen_title("تنظیمات"),
        ft.Container(height=Spacing.sm),
        caption("گروه مورد نظر را باز کن. تغییرات در دستگاهت ذخیره می‌شوند."),
        ft.Container(height=Spacing.lg),
        _subjects_group(ctx),
        ft.Container(height=Spacing.md),
        _goals_group(ctx),
        ft.Container(height=Spacing.md),
        _notifications_group(ctx),
        ft.Container(height=Spacing.md),
        _api_key_group(ctx),
        ft.Container(height=Spacing.md),
        _backup_and_danger_group(ctx),
    ])


def on_show(ctx) -> None:
    return None


# --------------------------------------------------------------------------- #
# Group 1 — Subjects
# --------------------------------------------------------------------------- #


def _subjects_group(ctx) -> ft.Control:
    activities = models.list_activities(active_only=False)
    rows: list[ft.Control] = [_subject_row(ctx, a) for a in activities]

    add_btn = secondary_button("افزودن درس جدید",
                               on_click=lambda _: _open_add_dialog(ctx),
                               icon=ft.Icons.ADD)

    return _group_card(
        title="مدیریت دروس",
        subtitle=f"{to_fa(len(activities))} درس",
        icon=ft.Icons.MENU_BOOK_OUTLINED,
        content=ft.Column(
            rows + [
                ft.Container(height=Spacing.sm),
                add_btn,
            ],
            spacing=Spacing.xs,
        ),
    )


def _subject_row(ctx, a) -> ft.Control:
    status_text = "فعال" if a.is_active else "غیرفعال"
    status_color = ACCENT if a.is_active else ON_SURFACE_MUT

    def _rename(_e):
        _open_rename_dialog(ctx, a)

    def _toggle(_e):
        models.set_activity_active(a.id, not a.is_active)
        ctx.snack("وضعیت درس به‌روز شد.")
        ctx.refresh()

    return ft.Container(
        padding=pad_sym(horizontal=Spacing.md, vertical=Spacing.sm),
        bgcolor=SURFACE_HIGH,
        border_radius=Radius.sm,
        content=ft.Row(
            [
                ft.Container(width=3, height=24, bgcolor=a.color or ACCENT,
                             border_radius=Radius.full),
                ft.Container(width=Spacing.sm),
                ft.Column(
                    [
                        ft.Text(value=a.name, size=Typography.body,
                                color=ON_SURFACE,
                                weight=ft.FontWeight.W_600, rtl=True),
                        ft.Text(value=status_text, size=Typography.tiny,
                                color=status_color, rtl=True),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.EDIT_OUTLINED, icon_size=18,
                            tooltip="ویرایش نام", on_click=_rename,
                            style=ft.ButtonStyle(color=ON_SURFACE_VAR),
                        ),
                        ft.Switch(value=bool(a.is_active), on_change=_toggle),
                    ],
                    spacing=0,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _open_rename_dialog(ctx, a) -> None:
    field = ft.TextField(
        label="نام درس", rtl=True, text_size=Typography.body, dense=True,
        value=a.name, autofocus=True, expand=True, max_length=40,
        border_radius=Radius.sm,
    )

    def _save(_e):
        name = (field.value or "").strip()
        if not name:
            ctx.snack("نام خالی مجاز نیست.")
            return
        models.rename_activity(a.id, name)
        ctx.close_dialog(dlg)
        ctx.snack("نام درس به‌روز شد.")
        ctx.refresh()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(value="ویرایش نام درس", rtl=True, size=Typography.h2,
                      weight=ft.FontWeight.W_600),
        content=ft.Container(width=320, content=field),
        actions=[
            text_button("انصراف", on_click=lambda _: ctx.close_dialog(dlg)),
            primary_button("ذخیره", on_click=_save),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    ctx.open_dialog(dlg)


def _open_add_dialog(ctx) -> None:
    name_field = ft.TextField(
        label="نام درس", rtl=True, text_size=Typography.body, dense=True,
        autofocus=True, expand=True, max_length=40,
        border_radius=Radius.sm,
    )
    groups = models.list_groups()
    group_dd = ft.Dropdown(
        label="گروه", rtl=True, text_size=Typography.body, dense=True,
        options=[ft.DropdownOption(key=str(g.id), text=g.name) for g in groups],
        value=str(groups[0].id) if groups else None,
        expand=True, border_radius=Radius.sm,
    )

    def _save(_e):
        name = (name_field.value or "").strip()
        if not name:
            ctx.snack("نام خالی مجاز نیست.")
            return
        try:
            gid = int(group_dd.value) if group_dd.value else None
        except (TypeError, ValueError):
            gid = None
        models.create_activity(name, gid, color=ACCENT)
        ctx.close_dialog(dlg)
        ctx.snack("درس افزوده شد.")
        ctx.refresh()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(value="افزودن درس", rtl=True, size=Typography.h2,
                      weight=ft.FontWeight.W_600),
        content=ft.Container(
            width=320,
            content=ft.Column([name_field, group_dd],
                              spacing=Spacing.sm, tight=True),
        ),
        actions=[
            text_button("انصراف", on_click=lambda _: ctx.close_dialog(dlg)),
            primary_button("افزودن", on_click=_save, icon=ft.Icons.ADD),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    ctx.open_dialog(dlg)


# --------------------------------------------------------------------------- #
# Group 2 — Daily goals
# --------------------------------------------------------------------------- #


def _goals_group(ctx) -> ft.Control:
    activities = models.list_activities(active_only=True)
    if not activities:
        return _group_card(
            title="اهداف روزانه",
            subtitle="—",
            icon=ft.Icons.FLAG_OUTLINED,
            content=ft.Text(
                value="اول یک درس اضافه کن تا هدف تعریف کنی.",
                size=Typography.small, color=ON_SURFACE_VAR, rtl=True,
            ),
        )

    rows: list[ft.Control] = [_goal_row(ctx, a) for a in activities]
    return _group_card(
        title="اهداف روزانه",
        subtitle="دقیقه در روز برای هر درس",
        icon=ft.Icons.FLAG_OUTLINED,
        content=ft.Column(
            rows + [
                ft.Container(height=Spacing.xs),
                ft.Text(
                    value="۰ یعنی بدون هدف. اهداف فقط برای راهنمایی‌اند، نه قضاوت.",
                    size=Typography.tiny, color=ON_SURFACE_MUT, rtl=True,
                ),
            ],
            spacing=Spacing.xs,
        ),
    )


def _goal_row(ctx, a) -> ft.Control:
    goal = models.get_goal(a.id, "daily")
    field = ft.TextField(
        label="دقیقه/روز",
        rtl=True, text_size=Typography.small, dense=True,
        keyboard_type=ft.KeyboardType.NUMBER,
        input_filter=ft.NumbersOnlyInputFilter(),
        value=str(goal.target_minutes) if goal else "0",
        width=80,
        border_radius=Radius.sm,
        text_align=ft.TextAlign.CENTER,
    )

    def _on_change(_e):
        try:
            v = int(field.value or 0)
        except ValueError:
            v = 0
        if v <= 0:
            from core import goals as _g
            _g.remove_goal(a.id, "daily")
            ctx.snack(f"هدف «{a.name}» حذف شد.")
        else:
            from core import goals as _g
            _g.set_goal(a.id, "daily", v, 0)

    return ft.Container(
        padding=pad_sym(horizontal=Spacing.md, vertical=Spacing.sm),
        bgcolor=SURFACE_HIGH,
        border_radius=Radius.sm,
        content=ft.Row(
            [
                ft.Container(width=3, height=24, bgcolor=a.color or ACCENT,
                             border_radius=Radius.full),
                ft.Container(width=Spacing.sm),
                ft.Text(value=a.name, size=Typography.body,
                        color=ON_SURFACE, rtl=True, expand=True),
                field,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


# --------------------------------------------------------------------------- #
# Group 3 — Notifications
# --------------------------------------------------------------------------- #


def _hhmm_options() -> list[ft.DropdownOption]:
    """30-minute increments: 00:00, 00:30, ..., 23:30."""
    opts = []
    for h in range(24):
        for m in (0, 30):
            label = f"{to_fa(str(h).zfill(2))}:{to_fa(str(m).zfill(2))}"
            value = f"{h:02d}:{m:02d}"
            opts.append(ft.DropdownOption(key=value, text=label))
    return opts


def _notifications_group(ctx) -> ft.Control:
    enabled = _notifier.is_enabled()
    quiet_start = _notifier.get_quiet_start()
    quiet_end = _notifier.get_quiet_end()
    interval = _notifier.get_interval()

    enable_switch = ft.Switch(
        value=enabled,
        label="فعال‌سازی یادآوری",
        label_position=ft.LabelPosition.LEFT,
        on_change=lambda e: _on_enable_toggle(ctx, e.control.value),
    )

    start_dd = ft.Dropdown(
        label="شروع سکوت", rtl=True, text_size=Typography.small, dense=True,
        options=_hhmm_options(), value=quiet_start,
        expand=True, border_radius=Radius.sm,
        on_select=lambda e: _notifier.set_quiet_start(start_dd.value or "23:00"),
    )
    end_dd = ft.Dropdown(
        label="پایان سکوت", rtl=True, text_size=Typography.small, dense=True,
        options=_hhmm_options(), value=quiet_end,
        expand=True, border_radius=Radius.sm,
        on_select=lambda e: _notifier.set_quiet_end(end_dd.value or "07:00"),
    )

    interval_dd = ft.Dropdown(
        label="فاصله یادآوری", rtl=True, text_size=Typography.small, dense=True,
        options=[
            ft.DropdownOption(key="15", text=f"هر {to_fa(15)} دقیقه"),
            ft.DropdownOption(key="30", text=f"هر {to_fa(30)} دقیقه"),
            ft.DropdownOption(key="60", text=f"هر {to_fa(60)} دقیقه"),
            ft.DropdownOption(key="120", text=f"هر {to_fa(2)} ساعت"),
        ],
        value=str(interval),
        expand=True, border_radius=Radius.sm,
        on_select=lambda e: _notifier.set_interval(int(interval_dd.value or 30)),
    )

    test_btn = tertiary_button(
        "تست یادآوری",
        on_click=lambda _: _notifier.test_now(ctx),
        icon=ft.Icons.NOTIFICATIONS_OUTLINED,
    )

    return _group_card(
        title="یادآوری مطالعه",
        subtitle="یادآوری دوره‌ای با ساعت سکوت",
        icon=ft.Icons.NOTIFICATIONS_OUTLINED,
        content=ft.Column(
            [
                enable_switch,
                ft.Container(height=Spacing.sm),
                ft.Text(
                    value="ساعت سکوت (مثلاً زمان خواب):",
                    size=Typography.small, color=ON_SURFACE_VAR, rtl=True,
                ),
                ft.Row([start_dd, end_dd], spacing=Spacing.sm),
                ft.Container(height=Spacing.sm),
                interval_dd,
                ft.Container(height=Spacing.md),
                ft.Text(
                    value="با زدن «آره» یک ساعت سکوت می‌شود. با زدن «نه» تا ده دقیقه دیگر تکرار می‌شود.",
                    size=Typography.tiny, color=ON_SURFACE_MUT, rtl=True,
                ),
                ft.Container(height=Spacing.sm),
                test_btn,
            ],
            spacing=0,
        ),
    )


def _on_enable_toggle(ctx, value: bool) -> None:
    _notifier.set_enabled(bool(value))
    if value:
        ctx.snack("یادآوری فعال شد.")
    else:
        ctx.snack("یادآوری خاموش شد.")


# --------------------------------------------------------------------------- #
# Group 4 — API key + Keystore
# --------------------------------------------------------------------------- #
# (Previously Group 3; renumbered after adding the Notifications group.)


def _api_key_group(ctx) -> ft.Control:
    status = ctx.secure.status_message()
    available = ctx.secure.available()
    status_color = ACCENT if available else WARN

    status_text = ft.Text(value=status, size=Typography.small,
                          color=status_color, rtl=True)

    key_field = ft.TextField(
        label="کلید OpenAI",
        rtl=True, text_size=Typography.small, dense=True,
        password=True, can_reveal_password=True,
        expand=True, hint_text="sk-...",
        border_radius=Radius.sm,
    )

    def _save(_e):
        val = (key_field.value or "").strip()
        if not val:
            ctx.snack("کلید را وارد کن.")
            return

        async def _go():
            ok = await ctx.secure.set_async(val)
            if ok:
                key_field.value = ""
                ctx.snack("کلید در Keystore ذخیره شد.")
            else:
                ctx.snack("ذخیره کلید ممکن نشد.")
            try:
                ctx.refresh()
            except Exception:
                pass

        ctx.page.run_task(_go)

    def _delete(_e):
        async def _go():
            ok = await ctx.secure.delete_async()
            if ok:
                ctx.snack("کلید حذف شد.")
            else:
                ctx.snack("حذف کلید ممکن نشد.")
            try:
                ctx.refresh()
            except Exception:
                pass

        ctx.page.run_task(_go)

    save_btn = secondary_button("ذخیره کلید", on_click=_save,
                                icon=ft.Icons.LOCK_OUTLINE)
    delete_btn = tertiary_button("حذف کلید", on_click=_delete,
                                 icon=ft.Icons.DELETE_OUTLINE)

    return _group_card(
        title="کلید OpenAI",
        subtitle="ذخیره در Keystore دستگاه",
        icon=ft.Icons.LOCK_OUTLINE,
        content=ft.Column(
            [
                status_text,
                ft.Container(height=Spacing.sm),
                key_field,
                ft.Container(height=Spacing.sm),
                ft.Row([save_btn, delete_btn],
                       alignment=ft.MainAxisAlignment.END, spacing=Spacing.sm),
            ],
            spacing=0,
        ),
    )


# --------------------------------------------------------------------------- #
# Group 5 — Backup + Danger zone
# --------------------------------------------------------------------------- #


def _backup_and_danger_group(ctx) -> ft.Control:
    file_picker = ctx.get_file_picker()
    state = {"mode": "export"}

    def _on_pick_result(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        if state["mode"] == "import":
            path = e.files[0].path
            _open_import_confirm(ctx, path)
        elif state["mode"] == "export" and e.path:
            _do_export(ctx, e.path)

    if file_picker is not None:
        file_picker.on_result = _on_pick_result

    def _export(_e):
        if file_picker is None:
            ctx.snack("انتخاب فایل در این پلتفرم پشتیبانی نمی‌شود.")
            return
        state["mode"] = "export"
        try:
            file_picker.save_file(
                file_name="maxpoint-backup.json",
                allowed_extensions=["json"],
            )
        except Exception as exc:
            ctx.snack(f"خطا در باز کردن ذخیره‌سازی: {exc}")

    def _import(_e):
        if file_picker is None:
            ctx.snack("انتخاب فایل در این پلتفرم پشتیبانی نمی‌شود.")
            return
        state["mode"] = "import"
        try:
            file_picker.pick_files(
                allow_multiple=False, allowed_extensions=["json"],
            )
        except Exception as exc:
            ctx.snack(f"خطا در باز کردن انتخاب فایل: {exc}")

    export_btn = secondary_button("خروجی JSON", on_click=_export,
                                  icon=ft.Icons.FILE_DOWNLOAD_OUTLINED)
    import_btn = tertiary_button("بازیابی از JSON", on_click=_import,
                                 icon=ft.Icons.FILE_UPLOAD_OUTLINED)

    clear_btn = tertiary_button("پاک‌سازی همه داده‌ها",
                                on_click=lambda _: _open_clear_confirm_1(ctx),
                                icon=ft.Icons.DELETE_FOREVER)

    return _group_card(
        title="پشتیبان و پاک‌سازی",
        subtitle="خروجی، بازیابی، پاک‌سازی نهایی",
        icon=ft.Icons.BACKUP_OUTLINED,
        content=ft.Column(
            [
                ft.Text(
                    value="خروجی شامل همه دروس، اهداف، جلسات و تنظیمات است.",
                    size=Typography.tiny, color=ON_SURFACE_MUT, rtl=True,
                ),
                ft.Container(height=Spacing.sm),
                ft.Row([export_btn, import_btn],
                       alignment=ft.MainAxisAlignment.END, spacing=Spacing.sm),
                ft.Container(height=Spacing.lg),
                divider(),
                ft.Container(height=Spacing.sm),
                ft.Text(
                    value="پاک‌سازی بازگشت‌ناپذیر است. ابتدا یک خروجی بگیر.",
                    size=Typography.tiny, color=WARN, rtl=True,
                ),
                ft.Container(height=Spacing.sm),
                ft.Row([clear_btn], alignment=ft.MainAxisAlignment.END),
            ],
            spacing=0,
        ),
    )


def _do_export(ctx, path: str) -> None:
    try:
        backup_service.export_to_file(path)
        ctx.snack("پشتیبان ذخیره شد.")
    except Exception as exc:
        ctx.snack(f"خطا در ذخیره: {exc}")


def _open_import_confirm(ctx, path: str) -> None:
    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(value="بازیابی پشتیبان؟", rtl=True, size=Typography.h2,
                      weight=ft.FontWeight.W_600),
        content=ft.Text(
            value="تمام داده‌های فعلی با فایل پشتیبان جایگزین می‌شود. ادامه می‌دهی؟",
            rtl=True, size=Typography.body, color=ON_SURFACE_VAR),
        actions=[
            text_button("انصراف", on_click=lambda _: ctx.close_dialog(dlg)),
            primary_button("بازیابی کن",
                           on_click=lambda _: _do_import(ctx, dlg, path),
                           icon=ft.Icons.RESTORE_OUTLINED),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    ctx.open_dialog(dlg)


def _do_import(ctx, dlg, path: str) -> None:
    try:
        counts = backup_service.restore_from_file(path)
        ctx.close_dialog(dlg)
        ctx.snack(f"بازیابی شد: {to_fa(sum(counts.values()))} ردیف.")
        ctx.refresh()
    except Exception as exc:
        ctx.close_dialog(dlg)
        ctx.snack(f"خطا در بازیابی: {exc}")


def _open_clear_confirm_1(ctx) -> None:
    field = ft.TextField(
        label="برای تایید، عبارت PAKE را بنویس",
        rtl=True, text_size=Typography.small, dense=True,
        autofocus=True, expand=True, border_radius=Radius.sm,
    )

    def _next(_e):
        if (field.value or "").strip() == "PAKE":
            ctx.close_dialog(dlg1)
            _open_clear_confirm_2(ctx)
        else:
            ctx.snack("عبارت درست نیست.")

    dlg1 = ft.AlertDialog(
        modal=True,
        title=ft.Text(value="تایید اول", rtl=True, size=Typography.h2,
                      weight=ft.FontWeight.W_600),
        content=ft.Container(
            width=320,
            content=ft.Column(
                [
                    ft.Text(
                        value="برای ادامه، عبارت PAKE را وارد کن.",
                        rtl=True, size=Typography.body, color=ON_SURFACE_VAR),
                    field,
                ],
                spacing=Spacing.sm, tight=True,
            ),
        ),
        actions=[
            text_button("انصراف", on_click=lambda _: ctx.close_dialog(dlg1)),
            primary_button("ادامه", on_click=_next),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    ctx.open_dialog(dlg1)


def _open_clear_confirm_2(ctx) -> None:
    dlg2 = ft.AlertDialog(
        modal=True,
        title=ft.Text(value="تایید نهایی", rtl=True, size=Typography.h2,
                      weight=ft.FontWeight.W_600),
        content=ft.Text(
            value="همه داده‌ها حذف شود؟ این کار بازگشت‌ناپذیر است.",
            rtl=True, size=Typography.body, color=ON_SURFACE_VAR),
        actions=[
            text_button("انصراف", on_click=lambda _: ctx.close_dialog(dlg2)),
            primary_button("بله، حذف کن",
                           on_click=lambda _: _do_clear(ctx, dlg2),
                           icon=ft.Icons.DELETE_FOREVER),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    ctx.open_dialog(dlg2)


def _do_clear(ctx, dlg) -> None:
    """Drop every row, then re-seed defaults."""
    from core import db as _db
    with _db.connect() as c:
        for t in ["sessions", "goals", "exam_subjects", "exams",
                  "reports", "settings", "activities", "activity_groups"]:
            c.execute(f"DELETE FROM {t};")
        _db._seed(c)
    ctx.close_dialog(dlg)
    ctx.snack("همه داده‌ها پاک شد.")
    ctx.refresh()


# --------------------------------------------------------------------------- #
# Expandable group card
# --------------------------------------------------------------------------- #


def _group_card(title: str, subtitle: str, icon: str,
                content: ft.Control) -> ft.Control:
    """A collapsed-by-default group. Tap to expand."""
    return ft.Container(
        bgcolor=SURFACE,
        border_radius=Radius.md,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.ExpansionTile(
            title=ft.Column(
                [
                    ft.Text(value=title, size=Typography.body,
                            weight=ft.FontWeight.W_600,
                            color=ON_SURFACE, rtl=True),
                    ft.Text(value=subtitle, size=Typography.tiny,
                            color=ON_SURFACE_MUT, rtl=True),
                ],
                spacing=2,
            ),
            leading=ft.Icon(icon, color=ACCENT, size=20),
            controls=[content],
            controls_padding=pad_sym(horizontal=Spacing.md, vertical=Spacing.sm),
            tile_padding=pad_sym(horizontal=Spacing.md, vertical=Spacing.sm),
            bgcolor=SURFACE,
            collapsed_bgcolor=SURFACE,
            shape=ft.RoundedRectangleBorder(radius=Radius.md),
            collapsed_shape=ft.RoundedRectangleBorder(radius=Radius.md),
            expanded_cross_axis_alignment=ft.CrossAxisAlignment.STRETCH,
            affinity=ft.TileAffinity.LEADING,
        ),
    )
