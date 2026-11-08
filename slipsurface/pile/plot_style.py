"""
Shared Matplotlib styling helpers: theme-aware figure/axis styling and a
semantic colour palette, used by plotting.py (the analysis figures) in a light,
dark or paper (report) theme.
"""

from typing import Dict

from .config import THEMES

#: Serif for figure titles, like the page's headings (Matplotlib ships it)
TITLE_FONT = "DejaVu Serif"


def resolve_theme(theme) -> Dict[str, str]:
    """Accepts a theme name ('light' / 'dark') or an already-resolved dict."""
    return THEMES[theme] if isinstance(theme, str) else theme


def style_figure(fig, theme) -> Dict[str, str]:
    """Sets the figure background to the theme colour and returns the
    resolved theme dict (pass straight to style_axis)."""
    th = resolve_theme(theme)
    fig.patch.set_facecolor(th['bg'])
    return th


def style_axis(ax, th: Dict[str, str], grid: bool = True, axis: str = 'both'):
    """Flat, low-chrome axis: no top/right spine, muted grid and ticks."""
    ax.set_facecolor(th['panel'])
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        ax.spines[s].set_color(th['border'])
        ax.spines[s].set_linewidth(0.9)
    if grid:
        ax.grid(True, axis=axis, color=th['border'], linewidth=0.8, zorder=0)
    ax.tick_params(colors=th['fg_dim'], labelsize=8.5)
    ax.xaxis.label.set_color(th['fg_dim'])
    ax.yaxis.label.set_color(th['fg_dim'])
    ax.title.set_color(th['fg'])


def label_box(th: Dict[str, str], alpha: float = 0.95) -> dict:
    """Rounded label bbox kwargs matching the theme."""
    return dict(boxstyle='round,pad=0.32', fc=th['panel'], ec=th['border'],
                lw=0.8, alpha=alpha)


