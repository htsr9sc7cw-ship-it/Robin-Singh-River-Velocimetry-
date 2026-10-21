"""Figure 4.4  Concept of the ratio for one step (schematic; the numbers are those of the illustration in Sect. 4.5).
Output: results/figures/figW_ratio_concept.png      Run:  python fig_3_08_ratio_concept.py"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tud_style as tud
from fig_1_01_route_map import OUT

tud.apply()


def concept():
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    t, d = (10, 0), (8, 1)
    kw = dict(head_width=0.3, length_includes_head=True)
    ax.arrow(0, 0, *t, color=tud.BLUE, lw=2, **kw)
    ax.arrow(0, 0, *d, color=tud.BLUE_MID, lw=2, **kw)
    ax.plot([d[0], t[0]], [d[1], t[1]], color=tud.GREY, lw=2)
    ax.text(5, -0.7, "true step t = (10, 0)", color=tud.BLUE, ha="center", fontsize=8)
    ax.text(4, 1.0, "tracked step d = (8, 1)", color=tud.BLUE_MID, ha="center", fontsize=8)
    ax.text(9.0, 0.95, "error |d − t| = 2.2", color=tud.GREY, ha="left", fontsize=8)
    ax.text(
        5,
        2.9,
        "reference without movement: error |t| = 10\nratio = |d − t| / |t| = 0.22",
        ha="center",
        fontsize=8.5,
        fontweight="bold",
        color=tud.INK,
    )
    ax.set_xlim(-0.5, 12.5)
    ax.set_ylim(-1.5, 4.2)
    ax.set_xlabel("x movement (px/frame)")
    ax.set_ylabel("y movement (px/frame)")
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "figW_ratio_concept.png"), dpi=200, facecolor="white")
    print("wrote figW_ratio_concept.png")


if __name__ == "__main__":
    concept()
