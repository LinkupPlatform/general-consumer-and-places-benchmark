"""Graph-paper charts in the linkup-benchmarks hero format.

One image per set: all queries, places, general consumer.
Each image stacks overall, relevance, completeness, and accuracy.
"""
import os

import numpy as np
from PIL import Image
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(OUT)
LOGO = os.path.join(OUT, "logos", "linkup.png")

BG = "#F8F8F8"
GREEN = "#7EA995"
GREY_BAR = "#D2D2D2"
GRID = "#E4E4E4"
FRAME = "#C4C4C4"
INK = "#3F3F46"
MUTED = "#9AA0A6"
GREEN_INK = "#4F7D68"
DATE = "2026-10"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
    "font.monospace": ["Menlo", "DejaVu Sans Mono", "Courier New"],
    "figure.dpi": 200,
    "savefig.dpi": 200,
})


def white_logo(px=110):
    img = Image.open(LOGO).convert("RGBA")
    side = max(img.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    sq = sq.resize((px, px), Image.LANCZOS)
    arr = np.asarray(sq).astype(float) / 255.0
    lum = arr[..., :3].max(axis=-1)
    out = np.zeros_like(arr)
    out[..., :3] = 1.0
    out[..., 3] = np.clip((lum - 0.35) / 0.5, 0, 1)
    return out


_WLOGO = None


def panel(ax, title, subtitle, data):
    global _WLOGO
    labels = [d[0] for d in data]
    vals = [d[1] for d in data]
    dmin, dmax, step = 0, 10, 2
    span = dmax - dmin
    band = span * 0.30
    top_pad = span * 0.18
    ax.set_ylim(dmin - band, dmax + top_pad)
    n = len(labels)
    ax.set_xlim(-0.7, n - 0.3)

    for gy in range(dmin, dmax + 1, step):
        ax.plot([-0.7, n - 0.3], [gy, gy], color=GRID, lw=0.9, zorder=1)
    for gx in np.linspace(-0.7, n - 0.3, 13):
        ax.plot([gx, gx], [dmin, dmax], color=GRID, lw=0.9, zorder=1)
    ax.plot([-0.7, n - 0.3], [dmin, dmin], color=FRAME, lw=1.1, zorder=2)

    for i, (lab, v) in enumerate(zip(labels, vals)):
        is_lk = "linkup" in lab.lower()
        ax.bar(i, v - dmin, bottom=dmin, width=0.62,
               color=GREEN if is_lk else GREY_BAR, zorder=3, edgecolor="none")
        ax.text(i, v + span * 0.025, f"{v:.1f}",
                ha="center", va="bottom", zorder=5,
                family="monospace", fontsize=10.5,
                fontweight="bold" if is_lk else "normal",
                color=GREEN_INK if is_lk else INK)
        ax.text(i, dmin - band * 0.18, lab,
                ha="center", va="top", zorder=5,
                fontsize=10.5, fontweight="bold" if is_lk else "normal",
                color=GREEN_INK if is_lk else MUTED)
        if is_lk:
            if _WLOGO is None:
                _WLOGO = white_logo()
            ax.add_artist(AnnotationBbox(
                OffsetImage(_WLOGO, zoom=0.22),
                (i, dmin + span * 0.16),
                frameon=False, box_alignment=(0.5, 0.5), zorder=6))

    for gy in range(dmin, dmax + 1, step):
        ax.text(-0.62, gy, str(gy), ha="left", va="center",
                family="monospace", fontsize=8.5, color=MUTED, zorder=4)

    cap_y = dmin - band * 0.72
    ax.text(-0.66, cap_y, subtitle, ha="left", va="center",
            family="monospace", fontsize=8.5, color=MUTED, zorder=5)
    ax.text(n - 0.34, cap_y, DATE, ha="right", va="center",
            family="monospace", fontsize=8.5, color=MUTED, zorder=5)

    for s in ax.spines.values():
        s.set_visible(True)
        s.set_color(FRAME)
        s.set_linewidth(1.1)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title, loc="left", fontsize=12.5, fontweight="bold", color=INK, pad=8)
    ax.set_facecolor(BG)


def hero(fname, header, panels):
    n = len(panels)
    fig, axes = plt.subplots(n, 1, figsize=(8.0, 3.15 * n + 0.55))
    fig.patch.set_facecolor("white")
    if n == 1:
        axes = [axes]
    fig.text(0.02, 0.995, header, fontsize=15, fontweight="bold",
             color=GREEN_INK, ha="left", va="top")
    for ax, p in zip(axes, panels):
        panel(ax, **p)
    fig.subplots_adjust(top=1 - 0.85 / (3.15 * n + 0.55),
                        left=0.055, right=0.975, bottom=0.02, hspace=0.38)
    path = os.path.join(ROOT, "results", fname)
    fig.savefig(path, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


def one(title, n, rows):
    return [dict(
        title=title,
        subtitle=f"average of 3 grades  /  score 0–10  /  n={n}",
        data=[(name, overall) for name, overall, *_ in rows],
    )]


# Linkup, Perplexity, Exa. First number is the 3-grade overall average.
ALL = [
    ("Linkup", 8.41, 8.73, 7.42, 7.87),
    ("Perplexity", 5.63, 6.91, 5.58, 6.36),
    ("Exa", 5.19, 6.53, 5.59, 6.06),
]
PLACES = [
    ("Linkup", 8.32, 8.72, 7.42, 7.76),
    ("Perplexity", 5.71, 7.07, 5.79, 6.28),
    ("Exa", 4.99, 6.41, 5.50, 5.77),
]
GENERAL = [
    ("Linkup", 8.53, 8.75, 7.41, 8.01),
    ("Perplexity", 5.52, 6.69, 5.30, 6.47),
    ("Exa", 5.43, 6.67, 5.72, 6.43),
]

hero("chart.png", "All queries  ·  Linkup leads", one("Overall", 200, ALL))
hero("places.png", "Places  ·  Linkup leads", one("Overall", 112, PLACES))
hero("general.png", "General consumer  ·  Linkup leads", one("Overall", 88, GENERAL))
