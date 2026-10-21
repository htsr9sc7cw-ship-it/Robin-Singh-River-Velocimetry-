"""Figure 1.1  Route map of the study.
Output: results/figures/figT_route_map.png      Run:  python fig_1_01_route_map.py
Drawn with the verified numbers of Chapter 5; colours and fonts come from tud_style.py (TU Dresden style, no title in the picture).
"""

import os

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tud_style as tud
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "results", "figures")
tud.apply()

RES = os.path.join(os.path.dirname(HERE), "results")
DAVIS = os.path.join(os.path.dirname(os.path.dirname(HERE)), "finetune", "results_davis")


def results():
    """every number of this picture, computed from the result files of the real runs (nothing is typed in)"""
    m = pd.read_csv(os.path.join(RES, "surfmove_headline_v3.csv"))
    m = m[~m.scene.str.contains("clear")]
    v = pd.read_csv(os.path.join(RES, "velocity_field_surfmove_v3.csv"))
    v = v[~v.scene.str.contains("clear")]
    h = pd.concat(
        [
            pd.read_csv(os.path.join(RES, "strategies_v3.csv")),
            pd.read_csv(os.path.join(RES, "s6_heldout_v3.csv")),
        ]
    ).drop_duplicates(["scene", "method"])
    h = h[h.scene != "v2_Path2_dense"]
    mw = {
        k: m[m.method == x]
        for k, x in dict(
            S0="PIPs++_b2_256",
            S6="PIPs++_S6_b2_256",
            NCC="PTV_tuned_ncc_fd2",
            LK="PTV_tuned_lk_fd2",
        ).items()
    }
    vf = {
        k: v[v.method == x] for k, x in dict(S6="PIPs++_S6_b2_256", NCC="PTV_tuned_ncc_fd2").items()
    }
    ho = lambda x: float(h[h.method == x].ratio_h15.median())
    davis = {
        k: float(pd.read_csv(os.path.join(DAVIS, "%s_S32.csv" % k)).d_avg.mean())
        for k in ("reference", "S1", "S2", "S3", "S4", "S5", "S6")
    }
    return dict(n_var=int(m.scene.nunique()), mw=mw, vf=vf, ho=ho, davis=davis)


def save(fig, name, **kw):
    fig.savefig(os.path.join(OUT, name), dpi=200, facecolor="white", **kw)
    plt.close(fig)
    print("wrote", os.path.join(OUT, name))


def canvas(w_in, h_in, w_units, h_units, x0=0):
    """figure whose data units are 0.1 inch (so box sizes are easy to reason about)"""
    fig = plt.figure(figsize=(w_in, h_in))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(x0, x0 + w_units)
    ax.set_ylim(0, h_units)
    ax.axis("off")
    return fig, ax


def tbox(
    ax,
    x,
    y,
    w,
    lines,
    h=None,
    bold=1,
    lw=1.4,
    ec=tud.BLUE,
    ls="-",
    fs=7.6,
    align="left",
    fc=tud.WHITE,
    pitch=1.75,
):
    """outlined box with text lines; the first `bold` lines are bold. Returns (left, right, bottom, top, mid_y)."""
    h = h or len(lines) * pitch + 3.0
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0,rounding_size=0.8",
            fc=fc,
            ec=ec,
            lw=lw,
            ls=ls,
            zorder=2,
        )
    )
    top = y + h / 2 + (len(lines) - 1) * pitch / 2
    for i, t in enumerate(lines):
        tx = x + 1.3 if align == "left" else x + w / 2
        ax.text(
            tx,
            top - i * pitch,
            t,
            ha=align,
            va="center",
            fontsize=fs,
            zorder=3,
            fontweight="bold" if i < bold else "normal",
            color=tud.BLUE if i < bold else tud.INK,
        )
    return x, x + w, y, y + h, y + h / 2


def route_map():
    """Fig. 1.1: study design - aim, simulated data with ground truth, three methods in parallel, comparison"""
    fig, ax = canvas(7.2, 6.4, 72, 64, x0=-1)
    R = results()
    med = lambda k: float(R["mw"][k].ratio_h15.median())
    nv = R["n_var"]
    # row 1: aim -> data -> ground truth
    cw, cx = 20, [3, 26, 49]
    top = [
        ["Aim", "Evaluation of a learned tracker", "for river surface velocity"],
        ["Simulated reach", "Blender, 16 camera views,", "32 variants (%d muddy)" % nv],
        ["Ground truth", "true trajectory of every tracer,", "checked before use"],
    ]
    for x, lines in zip(cx, top):
        tbox(ax, x, 54, cw, lines, h=8.5)
    for i in range(2):
        tud.arrow(ax, cx[i] + cw, 58.25, cx[i + 1], 58.25)
    # bracket from ground truth to the three columns
    ax.plot([cx[2] + cw / 2, cx[2] + cw / 2], [54, 51.5], color=tud.BLUE, lw=1.3, zorder=1)
    colx = [3, 26, 49]
    ax.plot([colx[0] + cw / 2, colx[2] + cw / 2], [51.5, 51.5], color=tud.BLUE, lw=1.3, zorder=1)
    cols = [
        (
            "Pre-trained PIPs++",
            "Objective 1",
            ["Applied without", "modification"],
            ["no skill", "ratio %.2f" % med("S0")],
        ),
        (
            "Retrained PIPs++",
            "Objective 2",
            ["Five strategies,", "selection rule fixed"],
            ["final model S6", "ratio %.2f" % med("S6")],
        ),
        (
            "PTV (NCC, LK)",
            "Reference method",
            ["Parameters tuned", "on the same data"],
            ["NCC %.2f" % med("NCC"), "LK %.2f" % med("LK")],
        ),
    ]
    for x, (name, obj, step, res) in zip(colx, cols):
        xm = x + cw / 2
        tud.arrow(ax, xm, 51.5, xm, 47.5)
        tbox(ax, x, 39, cw, [name, obj], h=8.5)
        tud.arrow(ax, xm, 39, xm, 35)
        tbox(ax, x, 27, cw, step, h=8, bold=0, lw=1.0)
        tud.arrow(ax, xm, 27, xm, 23)
        tbox(ax, x, 15, cw, res, h=8, lw=1.8)
        ax.plot([xm, xm], [15, 12.5], color=tud.BLUE, lw=1.3, zorder=1)
    ax.plot([colx[0] + cw / 2, colx[2] + cw / 2], [12.5, 12.5], color=tud.BLUE, lw=1.3, zorder=1)
    tud.arrow(ax, colx[1] + cw / 2, 12.5, colx[1] + cw / 2, 9.5)
    tbox(
        ax,
        3,
        1,
        66,
        [
            "Comparison (Objective 3)",
            "speed, tracer density, camera view, water clarity and run mode;",
            "ratio = RMSE of the tracker / RMSE of a reference reporting no movement",
        ],
        h=8.5,
        lw=2.0,
    )
    save(fig, "figT_route_map.png")


if __name__ == "__main__":
    route_map()
