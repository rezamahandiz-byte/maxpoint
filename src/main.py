"""MAXPOINT entry point.

Run:  flet run src/main.py
Web:  flet run --web src/main.py

Architecture:
    main(page) constructs an `AppContext` (page + shared services + helpers),
    sets up the dark RTL theme, mounts the bottom navigation bar, and swaps
    the active tab's view in a single content container.

Each tab module (ui/home.py, ui/record.py, ui/analysis.py, ui/settings.py)
exposes:
    build(ctx) -> ft.Control          builds the tab's root control
    on_show(ctx) -> None              (optional) called every time tab is shown

The Assistant is reachable from inside the Analysis tab (button), not a tab.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import flet as ft

# Make `core`, `ui`, `services` importable when launched via `flet run src/main.py`.
_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from core import db
from services import secure as secure_service
from services import time_sync, notifier as _notifier
from ui.theme import Colors, Typography, Spacing, Radius, Motion, Layout
from ui import home as ui_home
from ui import record as ui_record
from ui import analysis as ui_analysis
from ui import settings as ui_settings


# --------------------------------------------------------------------------- #
# Theme — every value comes from ui.theme; nothing is hardcoded here.
# --------------------------------------------------------------------------- #


def _build_theme() -> ft.Theme:
    cs = ft.ColorScheme(
        primary=Colors.accent,
        on_primary=Colors.accent_text,
        primary_container=Colors.accent_muted,
        on_primary_container=Colors.text_primary,
        secondary=Colors.accent,
        on_secondary=Colors.accent_text,
        secondary_container=Colors.surface_2,
        on_secondary_container=Colors.text_primary,
        tertiary=Colors.info,
        surface=Colors.bg,
        surface_container=Colors.surface_1,
        surface_container_high=Colors.surface_2,
        surface_container_highest=Colors.surface_3,
        on_surface=Colors.text_primary,
        on_surface_variant=Colors.text_secondary,
        outline=Colors.surface_3,
        outline_variant=Colors.surface_3,
        # "Behind plan" is amber, never red. Flutter's `error` slot is used
        # by form fields to show validation errors, so we keep it amber too.
        error=Colors.warning,
        error_container=Colors.surface_2,
        on_error=Colors.bg,
    )
    return ft.Theme(
        color_scheme=cs,
        color_scheme_seed=Colors.accent,
        font_family="Noto Sans",  # system fallback handles Persian; no serif
        use_material3=True,
        scaffold_bgcolor=Colors.bg,
        canvas_color=Colors.bg,
        divider_color=Colors.surface_3,
        navigation_bar_theme=ft.NavigationBarTheme(
            bgcolor=Colors.surface_1,
            indicator_color=Colors.accent_muted,
            label_text_style=ft.TextStyle(
                size=Typography.tiny, weight=ft.FontWeight.W_600),
        ),
        card_theme=ft.CardTheme(
            color=Colors.surface_1,
            elevation=0,
            shape=ft.RoundedRectangleBorder(radius=Radius.md),
        ),
        dialog_theme=ft.DialogTheme(
            bgcolor=Colors.surface_2,
            shape=ft.RoundedRectangleBorder(radius=Radius.lg),
        ),
        snackbar_theme=ft.SnackBarTheme(
            bgcolor=Colors.surface_2,
            content_text_style=ft.TextStyle(
                color=Colors.text_primary, size=Typography.small),
        ),
        floating_action_button_theme=ft.FloatingActionButtonTheme(
            bgcolor=Colors.accent,
            foreground_color=Colors.accent_text,
        ),
        appbar_theme=ft.AppBarTheme(
            bgcolor=Colors.bg,
            color=Colors.text_primary,
            center_title=False,
            elevation=0,
        ),
    )


# --------------------------------------------------------------------------- #
# App context
# --------------------------------------------------------------------------- #


@dataclass
class AppContext:
    """Shared state handed to every tab module."""
    page: ft.Page
    secure: "secure_service.SecureKeyStore"
    current_tab: int = 0
    file_picker: Optional[ft.FilePicker] = None
    audio: Optional[ft.Audio] = None
    _content: Optional[ft.Control] = field(default=None, repr=False)
    _handlers: dict = field(default_factory=dict, repr=False)
    # Timer-loop state for the active study session (Home tab).
    _active_timer_text: Optional[ft.Text] = field(default=None, repr=False)
    _active_session: object = field(default=None, repr=False)
    _timer_loop_running: bool = False

    def get_file_picker(self) -> ft.FilePicker:
        """Lazily create one FilePicker service per app session.

        FilePicker is a Service (auto-registers with the page); creating it
        multiple times would leak. We keep a single instance on the context.
        """
        if self.file_picker is None:
            try:
                self.file_picker = ft.FilePicker()
            except Exception:
                # Web/desktop without picker support — return a stub that
                # the caller can detect via `on_result is None`.
                self.file_picker = None
        return self.file_picker

    # ---- navigation ----
    def set_tab(self, index: int) -> None:
        self.current_tab = index
        self.page.navigation_bar.selected_index = index
        self._render()
        self._update_fab()
        self.page.update()

    # ---- content rendering ----
    def _render(self) -> None:
        view = self._build_current_view()
        if self._content is None:
            self._content = ft.Container(
                content=view,
                expand=True,
                padding=ft.Padding(
                    left=0, top=Spacing.sm, right=0, bottom=Spacing.sm,
                ),
            )
            # remove old controls except navigation_bar/fab (managed separately)
            self.page.controls.clear()
            self.page.add(self._content)
        else:
            self._content.content = view
        # post-render hook
        mod = self._tab_module(self.current_tab)
        on_show = getattr(mod, "on_show", None)
        if on_show:
            on_show(self)

    def _build_current_view(self) -> ft.Control:
        mod = self._tab_module(self.current_tab)
        return mod.build(self)

    def _tab_module(self, index: int):
        return {
            0: ui_home,
            1: ui_record,
            2: ui_analysis,
            3: ui_settings,
        }[index]

    def refresh(self) -> None:
        """Rebuild the current tab (e.g. after recording a session)."""
        self._render()
        self.page.update()

    # ---- FAB ----
    def _update_fab(self) -> None:
        # FAB only on Home (tab 0) and Record (tab 1) — both benefit from quick add.
        if self.current_tab in (0, 1):
            self.page.floating_action_button = ft.FloatingActionButton(
                icon=ft.Icons.ADD,
                tooltip="ثبت سریع",
                on_click=lambda _: ui_record.open_quick_record(self),
            )
        else:
            self.page.floating_action_button = None

    # ---- helpers ----
    def snack(self, msg: str) -> None:
        """Show a short SnackBar message.

        Flet 1.0.x has no `page.open()` — SnackBars go into `page.overlay`
        with `open=True` and are removed by their own dismiss timer.
        """
        snackbar = ft.SnackBar(
            content=ft.Text(value=msg, rtl=True, color=Colors.text_primary,
                            size=Typography.small),
            duration=Motion.standard * 10,  # ~2.5s
            bgcolor=Colors.surface_2,
            open=True,
        )
        try:
            self.page.overlay.append(snackbar)
            self.page.update()
        except Exception:
            # Last-resort: ignore — UI is non-blocking
            pass

    def open_dialog(self, dlg: ft.AlertDialog) -> None:
        """Open a modal dialog using the Flet 1.0.x API (`show_dialog`)."""
        try:
            self.page.show_dialog(dlg)
        except Exception:
            # Fallback for older/newer Flet variants that use page.open()
            try:
                self.page.open(dlg)
            except Exception:
                dlg.open = True
                self.page.dialog = dlg
                self.page.update()

    def close_dialog(self, dlg: ft.AlertDialog) -> None:
        """Close the topmost open dialog.

        Flet 1.0.x uses `page.pop_dialog()` which closes the most recently
        opened dialog. We assume dialogs are opened/closed in LIFO order
        (which is true for every flow in this app).
        """
        try:
            self.page.pop_dialog()
        except Exception:
            try:
                self.page.close(dlg)
            except Exception:
                dlg.open = False
                self.page.update()


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def main(page: ft.Page) -> None:
    # 1. Database first — every screen depends on it.
    db.init_db()

    # 2. Page config.
    page.title = "MAXPOINT"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = _build_theme()
    page.dark_theme = page.theme
    page.rtl = True
    page.bgcolor = Colors.bg
    page.padding = 0
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    page.vertical_alignment = ft.CrossAxisAlignment.START
    page.scroll = ft.ScrollMode.AUTO

    # 3. Secure storage service (auto-registers with the page on Android;
    #    on desktop the wrapper reports "unavailable" and the UI degrades).
    secure = secure_service.SecureKeyStore(page)

    ctx = AppContext(page=page, secure=secure)

    # 3b. Audio — for the notification chime. Registered once on the page
    #     overlay. The notifier calls `ctx.audio.play()` when it fires.
    try:
        ctx.audio = ft.Audio(src="sounds/focus_chime.wav", autoplay=False)
        page.overlay.append(ctx.audio)
    except Exception:
        ctx.audio = None  # audio unavailable — notifier silently skips it

    # 4. Bottom navigation — 4 tabs.
    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME,
                label="خانه"),
            ft.NavigationBarDestination(
                icon=ft.Icons.EDIT_NOTE_OUTLINED, selected_icon=ft.Icons.EDIT_NOTE,
                label="ثبت"),
            ft.NavigationBarDestination(
                icon=ft.Icons.INSIGHTS_OUTLINED, selected_icon=ft.Icons.INSIGHTS,
                label="تحلیل"),
            ft.NavigationBarDestination(
                icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS,
                label="تنظیمات"),
        ],
        selected_index=0,
        on_change=lambda e: ctx.set_tab(e.control.selected_index),
    )

    # 5. Initial render.
    ctx._render()
    ctx._update_fab()
    page.update()

    # 6. Start background services:
    #    - time_sync: verifies local clock against online time every 30 min.
    #      Silent on offline — never errors.
    #    - notifier: periodic "درس می‌خوانی؟" reminder with quiet hours.
    #      Only fires if the user enabled it in settings.
    try:
        page.run_task(time_sync.sync_loop)
        page.run_task(_notifier.loop, ctx)
    except Exception:
        # If background tasks can't start (e.g., no event loop), the app
        # still works — just without time-sync and notifications.
        pass


if __name__ == "__main__":
    ft.run(main)
