"""Figure 3.1  Methodology at a glance.
Output: results/figures/figV_methodology.png      Run:  python fig_3_01_methodology.py
Drawn with the verified numbers of Chapter 5; colours and fonts come from tud_style.py (TU Dresden style, no title in the picture).
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tud_style as tud
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "results", "figures")
tud.apply()


def save(fig, name, **kw):
    fig.savefig(os.path.join(OUT, name), dpi=200, facecolor="white", **kw)
    plt.close(fig)
    print("wrote", os.path.join(OUT, name))


def method_fig():
    """Fig. 3.1: methodology at a glance, four phases; schematic icons instead of dark thumbnails"""
    import numpy as np

    FW, FH, YM = 6.3, 7.5, 150.0
    fig = plt.figure(figsize=(FW, FH))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, YM)
    ax.axis("off")
    rng = np.random.RandomState(3)
    T_SUB, T_TTL = 8.2, 8.8

    def pane(x0, y0, w, h):
        ax.add_patch(
            Rectangle((x0, y0), w, h, fc=tud.BLUE_TINT, ec=tud.BLUE_LIGHT, lw=0.8, zorder=3)
        )

    def path(x0, y0, x1, y1, col, wob=0.0, ls="-", arrow=False, lw=1.3):
        t = np.linspace(0, 1, 30)
        xs = x0 + (x1 - x0) * t
        ys = y0 + (y1 - y0) * t + wob * np.sin(t * 9)
        ax.plot(xs, ys, color=col, lw=lw, ls=ls, zorder=4, solid_capstyle="round")
        ax.plot([xs[0]], [ys[0]], "o", color=col, ms=2.6, zorder=5)
        if arrow:
            ax.plot([xs[-1]], [ys[-1]], ">", color=col, ms=3.6, zorder=5)

    def ic_river(x0, y0, w, h):
        pane(x0, y0, w, h)
        xs = np.linspace(x0, x0 + w, 40)
        ax.plot(xs, y0 + h - 1.5 + 0.7 * np.sin(xs * 0.5), color=tud.GREY, lw=1.5, zorder=4)
        ax.plot(xs, y0 + 1.5 + 0.7 * np.sin(xs * 0.5 + 1), color=tud.GREY, lw=1.5, zorder=4)
        for yy in (y0 + h * 0.38, y0 + h * 0.62):
            path(x0 + 2, yy, x0 + w - 2, yy, tud.BLUE_MID, arrow=True, lw=1.2)

    def ic_sim(x0, y0, w, h):
        pane(x0, y0, w, h)
        px = x0 + 1.5 + rng.rand(38) * (w - 3)
        py = y0 + 1.2 + rng.rand(38) * (h - 2.4)
        ax.plot(px, py, "o", color=tud.BLUE_MID, ms=2.8, zorder=4, mew=0)

    def ic_render(x0, y0, w, h):
        pane(x0, y0, w, h)
        cx, cy = x0 + 3.2, y0 + h / 2
        ax.add_patch(Rectangle((cx - 2.2, cy - 2.2), 4.4, 4.4, fc=tud.BLUE, ec=tud.BLUE, zorder=5))
        ax.add_patch(Rectangle((cx + 2.2, cy - 1.1), 1.4, 2.2, fc=tud.BLUE, ec=tud.BLUE, zorder=5))
        fx = x0 + w * 0.55
        ax.plot(
            [cx + 3.6, fx, fx, cx + 3.6],
            [cy + 0.4, y0 + h - 1.2, y0 + 1.2, cy - 0.4],
            color=tud.GREY,
            lw=0.9,
            zorder=4,
        )
        px = fx + 0.5 + rng.rand(14) * (x0 + w - fx - 2)
        py = y0 + 1.5 + rng.rand(14) * (h - 3)
        ax.plot(px, py, "o", color=tud.BLUE_MID, ms=2.4, zorder=4, mew=0)

    def ic_gt(x0, y0, w, h):
        pane(x0, y0, w, h)
        for k in range(4):
            path(
                x0 + 2.5,
                y0 + 2 + k * (h - 4) / 3,
                x0 + w - 3,
                y0 + 2 + k * (h - 4) / 3,
                tud.BLUE,
                arrow=True,
            )

    def ic_pre(x0, y0, w, h):
        pane(x0, y0, w, h)
        for k in range(4):
            yy = y0 + 2 + k * (h - 4) / 3
            path(x0 + 2, yy, x0 + w - 2, yy, tud.BLUE_LIGHT, ls=(0, (2, 2)), lw=0.9)
            path(
                x0 + 2,
                yy,
                x0 + w - 2,
                yy + (-1.5 if k % 2 else 1.5) * (1 + k * 0.3),
                tud.GREY,
                wob=0.5,
                arrow=True,
            )

    def ic_ptv(x0, y0, w, h):
        pane(x0, y0, w, h)
        sw = w * 0.36
        for xx, off in ((x0 + 1.2, 0.0), (x0 + w - sw - 1.2, 0.0)):
            ax.add_patch(
                Rectangle((xx, y0 + 1.2), sw, h - 2.4, fc=tud.WHITE, ec=tud.GREY, lw=0.8, zorder=4)
            )
        ax.add_patch(
            Rectangle(
                (x0 + 1.2 + sw * 0.2, y0 + h * 0.3),
                sw * 0.3,
                h * 0.38,
                fc="none",
                ec=tud.BLUE_MID,
                lw=1.4,
                zorder=5,
            )
        )
        ax.add_patch(
            Rectangle(
                (x0 + w - sw - 1.2 + sw * 0.5, y0 + h * 0.3),
                sw * 0.3,
                h * 0.38,
                fc="none",
                ec=tud.BLUE_MID,
                lw=1.4,
                zorder=5,
            )
        )
        tud.arrow(ax, x0 + 1.2 + sw + 0.5, y0 + h / 2, x0 + w - sw - 1.7, y0 + h / 2, lw=1.2)

    def ic_ft(x0, y0, w, h):
        pane(x0, y0, w, h)
        for k in range(4):
            yy = y0 + 2 + k * (h - 4) / 3
            path(x0 + 2, yy, x0 + w - 2, yy, tud.BLUE_LIGHT, ls=(0, (2, 2)), lw=0.9)
            path(x0 + 2, yy, x0 + w - 2, yy + 0.3 * (k % 2 - 0.5), tud.BLUE, arrow=True)

    def box(
        x, y, w, h, title, sub, sect, icon=None, cap=None, fc=tud.WHITE, lw=1.4, tint=False, ih=11.0
    ):
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.0,rounding_size=1.2",
                fc=tud.BLUE_TINT if tint else fc,
                ec=tud.BLUE,
                lw=lw,
                zorder=2,
            )
        )
        ax.text(
            x + 1.2,
            y + h - 1.6,
            title,
            ha="left",
            va="top",
            fontsize=T_TTL,
            fontweight="bold",
            color=tud.BLUE,
            zorder=3,
        )
        ax.text(
            x + 1.2,
            y + h - 5.2,
            sub,
            ha="left",
            va="top",
            fontsize=T_SUB,
            color=tud.INK,
            zorder=3,
            linespacing=1.25,
        )
        if icon is not None:
            iw = w - 2.4
            iy = y + (5.4 if cap else 1.6)
            icon(x + 1.2, iy, iw, ih)
            if cap:
                ax.text(
                    x + 1.2,
                    y + 1.4,
                    cap,
                    ha="left",
                    va="bottom",
                    fontsize=T_SUB,
                    color=tud.INK,
                    zorder=3,
                )

    def arrow(x0, y0, x1, y1):
        tud.arrow(ax, x0, y0, x1, y1, lw=1.4)

    def phase(ytop, ybot, name):
        ax.plot([2, 98], [ytop + 1.0, ytop + 1.0], color=tud.GREY_MID, lw=0.9, ls=(0, (5, 4)))
        ax.text(
            2,
            (ytop + ybot) / 2,
            name,
            rotation=90,
            ha="center",
            va="center",
            fontsize=9.5,
            fontweight="bold",
            color=tud.BLUE,
        )

    y, h, w = 119, 29, 21.5
    xs = [6, 29.5, 53, 76.5]
    box(
        xs[0],
        y,
        w,
        h,
        "1  Real reach",
        "Wesenitz river,\nvalidation site\nof the PTV method",
        "Sect. 3.1",
        ic_river,
    )
    box(
        xs[1],
        y,
        w,
        h,
        "2  Simulation",
        "Blender FLIP fluid,\n14 m x 8 m domain",
        "Sect. 3.2",
        ic_sim,
    )
    box(
        xs[2],
        y,
        w,
        h,
        "3  Rendering",
        "16 camera views,\n2 tracer densities,\n201 frames each",
        "Sect. 3.3",
        ic_render,
    )
    box(xs[3], y, w, h, "4  Ground truth", "exact tracer\npaths", "Sect. 3.4-3.5", ic_gt, lw=2.2)
    for i in range(3):
        arrow(xs[i] + w, y + h / 2, xs[i + 1], y + h / 2)
    phase(y + h, y, "DATA")
    y2, h2, w2 = 80, 33, 29.6
    xt = [6, 36.2, 66.4]
    box(
        xt[0],
        y2,
        w2,
        h2,
        "5a  Pre-trained PIPs++",
        "model used as released",
        "Sect. 4.2",
        ic_pre,
        "paths drift from the truth",
        ih=12,
    )
    box(
        xt[1],
        y2,
        w2,
        h2,
        "5b  PTV",
        "NCC and LK tracking,\nparameters from data",
        "Sect. 4.3",
        ic_ptv,
        "patch matched per frame",
        ih=12,
    )
    box(
        xt[2],
        y2,
        w2,
        h2,
        "5c  Retrained PIPs++",
        "five strategies S1-S5,\none rule picks S6",
        "Sect. 4.4",
        ic_ft,
        "paths follow the flow",
        ih=12,
    )
    bus = y - 3.5
    ax.plot([xt[0] + w2 / 2, 87.2], [bus, bus], color=tud.BLUE, lw=1.4, zorder=1)
    ax.plot([87.2, 87.2], [y - 0.3, bus], color=tud.BLUE, lw=1.4, zorder=1)
    for xx in (xt[0] + w2 / 2, xt[1] + w2 / 2, xt[2] + w2 / 2):
        arrow(xx, bus, xx, y2 + h2 + 0.2)
    phase(y2 + h2, y2, "TRACKERS")
    y3, h3 = 58, 15
    box(
        6,
        y3,
        90,
        h3,
        "6  One scorer for all trackers",
        "ratio  |  direction  |  speed ratio  |  coverage  |  bias  |  TAP-Vid metrics",
        "Sect. 4.5",
    )
    ax.text(
        6 + 1.2,
        y3 + 2.6,
        "ratio = RMSE / RMSE of a tracker without movement;  skill = ratio below 0.8",
        ha="left",
        fontsize=T_SUB,
        color=tud.BLUE,
        fontweight="bold",
        zorder=3,
    )
    for xx in (xt[0] + w2 / 2, xt[1] + w2 / 2, xt[2] + w2 / 2):
        arrow(xx, y2 - 0.3, xx, y3 + h3 + 0.2)
    phase(y3 + h3, y3, "SCORING")
    cond = [
        ("Speed", "speed\nladder", "Sect. 5.2.3"),
        ("Density", "sparse and\ndense", "Sect. 5.4.3"),
        ("View", "10 held-out\nvariants", "Sect. 5.3.5"),
        ("Water", "muddy,\nclear,\nmoving", "Sect. 5.4.4-5"),
        ("Run mode", "modes\nD1 to D4", "Sect. 5.3.2"),
        ("Retention", "TAP-Vid\nDAVIS", "Sect. 5.3.7"),
    ]
    y4, h4, w4 = 28, 16, 14.2
    for i, (t, sub, sc) in enumerate(cond):
        box(6 + i * (w4 + 1.0), y4, w4, h4, t, sub, sc, lw=1.0, tint=True)
    ax.text(
        51,
        y4 + h4 + 2.6,
        "7  Comparison under different conditions",
        ha="center",
        fontsize=9.4,
        fontweight="bold",
        color=tud.BLUE,
    )
    arrow(51, y3 - 0.3, 51, y4 + h4 + 6.0)
    phase(y4 + h4 + 5, y4, "COMPARISON")
    box(
        6,
        6,
        90,
        13,
        "Findings",
        "Objective 1: pre-trained PIPs++   |   Objective 2: retraining\nObjective 3: comparison and cost",
        "Sect. 5.4 and Chapter 7",
        lw=2.2,
    )
    arrow(51, y4 - 0.3, 51, 19.3)
    save(fig, "figV_methodology.png")


if __name__ == "__main__":
    method_fig()
