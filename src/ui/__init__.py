"""MAXPOINT UI package — bottom-tab screens + shared helpers.

Tabs (v0.1): home, record, analysis, settings.
`assistant` is reachable from inside the Analysis tab, not a separate tab.

Every visual constant (color, size, radius, duration, layout) is imported
from `ui.theme` — never hardcoded here or in any tab module.
"""
from __future__ import annotations

from typing import Iterable, Optional

import flet as ft

from core import analytics as _analytics
from ui.theme import Colors, Typography, Spacing, Radius, Motion, Layout


# ---- Convenience aliases (the rest of the package imports these) -----------
ACCENT         = Colors.accent
ACCENT_SOFT    = Colors.accent_muted
BG_DARK        = Colors.bg
SURFACE        = Colors.surface_1
SURFACE_HIGH   = Colors.surface_2
OUTLINE        = Colors.surface_3
ON_SURFACE     = Colors.text_primary
ON_SURFACE_VAR = Colors.text_secondary
ON_SURFACE_MUT = Colors.text_muted
SUCCESS        = Colors.success
WARN           = Colors.warning
INFO           = Colors.info


# ---- Persian digit helper -------------------------------------------------- #


def to_fa(value) -> str:
    """Render digits in Persian for display."""
    return _analytics.to_fa(value)


# ---- Layout primitive shortcuts ------------------------------------------- #


def pad_sym(horizontal: int = 0, vertical: int = 0) -> ft.Padding:
    return ft.Padding(left=horizontal, top=vertical,
                      right=horizontal, bottom=vertical)


def pad_only(left: int = 0, top: int = 0, right: int = 0, bottom: int = 0) -> ft.Padding:
    return ft.Padding(left=left, top=top, right=right, bottom=bottom)


def margin_only(left: int = 0, top: int = 0, right: int = 0, bottom: int = 0) -> ft.Margin:
    return ft.Margin(left=left, top=top, right=right, bottom=bottom)


def border_all(width: float = 1, color: str = OUTLINE) -> ft.Border:
    side = ft.BorderSide(color=color, width=width)
    return ft.Border(top=side, bottom=side, left=side, right=side)


CENTER         = ft.Alignment(0, 0)
CENTER_LEFT    = ft.Alignment(-1, 0)
CENTER_RIGHT   = ft.Alignment(1, 0)
TOP_CENTER     = ft.Alignment(0, -1)
BOTTOM_CENTER  = ft.Alignment(0, 1)
BOTTOM_LEFT    = ft.Alignment(-1, 1)
BOTTOM_RIGHT   = ft.Alignment(1, 1)


# ---- Component factory helpers (use these, don't roll your own) ----------- #


def card(content: ft.Control | list[ft.Control],
         padding: int = Layout.card_padding,
         margin: int = 0,
         bgcolor: str = SURFACE) -> ft.Card:
    """Standard surface card.

    Uses CardTheme's shape (set in main.py), so we don't override radius here.
    """
    if isinstance(content, list):
        inner: ft.Control = ft.Column(content, spacing=Spacing.sm, expand=True)
    else:
        inner = content
    return ft.Card(
        content=ft.Container(padding=padding, content=inner, bgcolor=bgcolor),
        margin=margin,
        expand=True,
    )


def screen_title(text: str) -> ft.Text:
    """The page-title at the top of every tab — calm, not a hero banner."""
    return ft.Text(
        value=text, size=Typography.h2,
        weight=ft.FontWeight.W_600,
        color=ON_SURFACE, rtl=True,
    )


def section_title(text: str) -> ft.Text:
    """A sub-section title inside a screen."""
    return ft.Text(
        value=text, size=Typography.body,
        weight=ft.FontWeight.W_600,
        color=ON_SURFACE, rtl=True,
    )


def label(text: str, size: int = Typography.small,
          color: str = ON_SURFACE_VAR) -> ft.Text:
    return ft.Text(value=text, size=size, color=color, rtl=True)


def caption(text: str, color: str = ON_SURFACE_MUT) -> ft.Text:
    """Smallest text — chart axes, metadata."""
    return ft.Text(value=text, size=Typography.tiny, color=color, rtl=True)


def body_text(text: str, color: str = ON_SURFACE,
              size: int = Typography.body) -> ft.Text:
    return ft.Text(value=text, size=size, color=color, rtl=True)


def divider() -> ft.Divider:
    return ft.Divider(height=1, color=OUTLINE)


def primary_button(text: str, on_click=None,
                   icon: Optional[str] = None) -> ft.Control:
    """The ONE primary action on a screen. Filled with accent, min 52dp tall."""
    return ft.FilledButton(
        content=text, icon=icon, on_click=on_click,
        height=Layout.button_height,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=Radius.md),
            bgcolor=ACCENT,
            color=Colors.accent_text,
        ),
    )


def secondary_button(text: str, on_click=None,
                     icon: Optional[str] = None) -> ft.Control:
    """Tonal version of primary — used for the second-priority action."""
    return ft.FilledTonalButton(
        content=text, icon=icon, on_click=on_click,
        height=Layout.button_height,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=Radius.md),
        ),
    )


def tertiary_button(text: str, on_click=None,
                    icon: Optional[str] = None) -> ft.Control:
    """Outlined / text — used for "cancel", "delete key", etc."""
    return ft.OutlinedButton(
        content=text, icon=icon, on_click=on_click,
        height=Layout.button_height,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=Radius.md)),
    )


def text_button(text: str, on_click=None,
                icon: Optional[str] = None) -> ft.Control:
    """Smallest text-only action — never the primary path."""
    return ft.TextButton(
        content=text, icon=icon, on_click=on_click,
        height=Layout.min_touch,
    )


def field_label(text: str) -> ft.Text:
    return ft.Text(value=text, size=Typography.small,
                   color=ON_SURFACE_VAR, rtl=True)


def safe_list(controls: Iterable[ft.Control]) -> list[ft.Control]:
    """Filter out None controls (handy when conditionally building UI)."""
    return [c for c in controls if c is not None]


def screen_scroll(controls: list[ft.Control]) -> ft.ListView:
    """A tab's root scrollable. Standard edge padding + bottom space for FAB."""
    return ft.ListView(
        [
            ft.Container(height=Spacing.sm),
            *controls,
            ft.Container(height=Layout.fab_size + Spacing.xl),
        ],
        spacing=0,
        padding=pad_sym(horizontal=Layout.screen_edge, vertical=0),
        expand=True,
    )
