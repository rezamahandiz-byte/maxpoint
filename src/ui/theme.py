"""MAXPOINT design tokens — the single source of truth for the visual language.

Every other file in `ui/` must import colors, sizes, radii, durations, and
layout constants from here. No hardcoded values anywhere else.

Why this exists
---------------
The user's core fear is that the app triggers procrastination instead of
reducing it. The visual language answers that fear by being:
    - quiet (one accent, muted surfaces, no celebration)
    - honest (amber for "needs attention", never red)
    - sparse (one action per screen, big numbers, lots of breath)

Five design laws enforced here:
    1. No red for unmet goals. Use amber (Colors.warning).
    2. Language of distance, not deficit — the UI strings live in the
       tab modules, but the colors here make sure a "behind plan" state
       is rendered in amber, never red.
    3. Show progress, not deficit — progress fills use Colors.accent /
       Colors.success, never the deficit color.
    4. One action per screen — Layout.button_height is large so a primary
       action can be the visually dominant element.
    5. Every chart has one sentence — see the chart-card helpers in
       `ui/__init__.py`; they enforce a sentence slot below the chart.
"""
from __future__ import annotations


class Colors:
    """Dark mode is the only mode in v0.1. Palette is GitHub-dark inspired
    so the eye never has to fight contrast or saturation.

    Rules:
        - Never use pure red (#FF0000), pure black (#000000), pure white
          (#FFFFFF). They feel punitive or sterile.
        - "Behind plan" → warning (amber), never red.
        - "Goal achieved" → success (subtle green), never a celebration
          confetti color.
    """
    # Surfaces
    bg             = "#0D1117"
    surface_1      = "#161B22"   # cards
    surface_2      = "#21262D"   # inputs, inactive chips
    surface_3      = "#30363D"   # borders, dividers

    # Text
    text_primary   = "#E6EDF3"
    text_secondary = "#8B949E"
    text_muted     = "#6E7681"

    # Accent — muted teal for calm focus
    accent         = "#4EA1A1"
    accent_muted   = "#2E6B6B"
    accent_text    = "#E6EDF3"   # text on accent fill

    # Semantic (NEVER red for goals)
    warning        = "#D29922"   # amber — for "needs attention"
    success        = "#3FB950"   # for goal achieved (subtle)
    info           = "#58A6FF"


class Typography:
    """Five sizes max, two weights max. Anything more is noise."""
    h1               = 28   # screen hero numbers (today's minutes, etc.)
    h2               = 20   # section titles
    body             = 16   # default body text
    small            = 14   # captions, labels, form fields
    tiny             = 12   # metadata, chart axes

    weight_regular   = 400
    weight_semibold  = 600
    # NEVER use more than 2 weights, never more than 5 sizes.


class Spacing:
    """A single spacing scale keeps rhythm across cards."""
    xs  = 4
    sm  = 8
    md  = 12
    lg  = 16
    xl  = 24
    xxl = 32


class Radius:
    sm   = 8
    md   = 12
    lg   = 16
    full = 999


class Motion:
    """Three durations. Use `fast` for tap feedback, `standard` for snack
    and modal open, `emphasized` for the first draw of a chart only."""
    fast       = 150
    standard   = 250
    emphasized = 400


class Layout:
    """Layout constants that govern the whole app shell."""
    screen_edge       = 16
    card_padding      = 16
    between_cards     = 12
    between_sections  = 24
    min_touch         = 48
    button_height     = 52
    tab_bar_height    = 64
    fab_size          = 56
