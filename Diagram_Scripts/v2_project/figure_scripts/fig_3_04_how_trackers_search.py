"""Figure 3.4  How the three trackers find the next position: NCC, LK and PIPs++ in three plain rows.
Output: results/figures/figR_mechanisms.png      Run:  python fig_3_04_how_trackers_search.py"""

import textwrap

from fig_common import *
from matplotlib.patches import Rectangle

cols = [
    (
        "PTV NCC",
        "template matching",
        ["A small picture of the tracer", "in frame t (the template)"],
        ["Slides the template over a search", "window in frame t+1 and takes the", "best match"],
        ["The tracer moves out of the window,", "or a similar tracer matches better"],
    ),
    (
        "PTV LK",
        "image gradients",
        ["The brightness around the", "tracer in frame t"],
        ["Estimates the small shift that", "makes frame t look like frame t+1,", "in a few steps"],
        ["The shift is larger than the", "range of the steps: the tracer is lost"],
    ),
    (
        "PIPs++",
        "learned refinement",
        ["Learned features of the tracer", "in all frames of a 48-frame clip"],
        [
            "Starts at the tracer position and",
            "improves the estimate 16 times,",
            "looking at all frames",
        ],
        [
            "Pre-trained: the point stays still.",
            "Retrained: it follows, up to the",
            "reach of the feature pyramid",
        ],
    ),
]
rows = ["Looks at", "Finds the next\nposition by", "Fails when"]
FS = tud.fs_min(7.4)  # smallest allowed size: layout is computed for it, so nothing overlaps
LH = 0.19  # line height in inches at that size
fig, ax = plt.subplots(figsize=(7.4, 5.2))
ax.set_xlim(0, 7.4)
ax.set_ylim(0, 5.2)
ax.axis("off")
X0, W, GAP = 1.2, 2.0, 0.1
for j, (name, sub, *_) in enumerate(cols):
    x = X0 + j * (W + GAP)
    ax.add_patch(Rectangle((x, 4.45), W, 0.75, fc=tud.BLUE, ec="none"))
    ax.text(
        x + W / 2,
        4.95,
        name,
        color="white",
        fontsize=9,
        fontweight="bold",
        ha="center",
        va="center",
    )
    ax.text(x + W / 2, 4.64, sub, color="white", fontsize=FS, ha="center", va="center")
Y = [3.25, 1.85, 0.2]
H = [1.15, 1.35, 1.35]
for r, (lab, y, h) in enumerate(zip(rows, Y, H)):
    ax.text(
        0.0, y + h / 2, lab, fontsize=FS, fontweight="bold", color=tud.BLUE, ha="left", va="center"
    )
    ax.plot(
        [0, 7.4], [y + h + 0.05, y + h + 0.05] if r else [4.4, 4.4], color=tud.GREY_LIGHT, lw=0.7
    )
    for j, c in enumerate(cols):
        txt = "\n".join(textwrap.fill(l, 24) for l in [" ".join(c[2 + r])])
        ax.text(
            X0 + j * (W + GAP) + 0.05,
            y + h / 2,
            txt,
            fontsize=FS,
            color=tud.INK,
            ha="left",
            va="center",
            linespacing=1.3,
        )
ax.plot([0, 7.4], [0.12, 0.12], color=tud.GREY_LIGHT, lw=0.7)
save(fig, "figR_mechanisms.png")
