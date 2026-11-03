"""
Shared Matplotlib styling helpers: theme-aware figure/axis styling and a
semantic colour palette, used by plotting.py (the analysis figures) and
study_plots.py (the study figures) so every figure the app draws matches the
current light/dark UI theme.
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
    resolved theme dict (pass straight to style_axis / annotate_point)."""
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


def annotate_point(ax, x: float, y: float, label: str, th: Dict[str, str],
                   color: str, dx: float = 22, dy: float = 0,
                   ha: str = 'left', va: str = 'center', fontsize: float = 8.5):
    """A small coloured dot at (x, y) with a themed label, connected by a
    thin line when offset."""
    ax.scatter([x], [y], s=26, color=color, zorder=5,
               edgecolor=th['panel'], linewidth=1.2)
    arrow = (dict(arrowstyle='-', color=th['fg_dim'], lw=0.8,
                  shrinkA=0, shrinkB=6) if (dx or dy) else None)
    ax.annotate(label, xy=(x, y), xytext=(dx, dy), textcoords='offset points',
                ha=ha, va=va, fontsize=fontsize, color=th['fg'],
                bbox=label_box(th), arrowprops=arrow)


def figure_title(fig, th: Dict[str, str], text: str, size: float = 12.5):
    """The figure's own title, in the serif the page uses for headings."""
    fig.suptitle(text, fontfamily=TITLE_FONT, fontsize=size, color=th['fg'])
