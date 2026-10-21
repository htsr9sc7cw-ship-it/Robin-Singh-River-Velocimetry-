"""Figure 5.19  Results at a glance.
Output: results/figures/figU_results_at_glance.png      Run:  python fig_5_19_results_at_a_glance.py
Drawn with the verified numbers of Chapter 5; colours and fonts come from tud_style.py (TU Dresden style, no title in the picture).
"""

import os
import textwrap

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tud_style as tud
from matplotlib.patches import FancyBboxPatch, Rectangle

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


def glance():
    """Fig. 5.19: five panels, one message each (28 moving-water variants)"""
    FS = tud.fs_min(7.4)
    fig = plt.figure(figsize=(7.4, 10.0))
    gs = fig.add_gridspec(
        3, 2, height_ratios=[1, 0.95, 2.1], width_ratios=[1, 1.15], hspace=0.7, wspace=0.5
    )
    names = ["Pre-trained PIPs++", "PTV LK", "Retrained PIPs++ (S6)", "PTV NCC"]
    R = results()
    mw, vf, ho, dv = R["mw"], R["vf"], R["ho"], R["davis"]
    order = ["S0", "LK", "S6", "NCC"]
    cols = [tud.TRACKER[k] for k in order]  # the one colour per method (tud_style)
    ratio = [float(mw[k].ratio_h15.median()) for k in order]
    skill = [int((mw[k].ratio_h15 < 0.8).sum()) for k in order]

    ax = fig.add_subplot(gs[0, :])  # A: median ratio
    ax.axvspan(0, 0.8, color=tud.BLUE_TINT, zorder=0)
    ax.axvline(0.8, color=tud.BLUE, ls=":", lw=1.3)
    ax.axvline(1.0, color=tud.INK, ls="--", lw=0.9)
    for i, (r, c) in enumerate(zip(ratio, cols)):
        y = len(names) - 1 - i
        ax.plot([r, 1.0], [y, y], color=c, lw=2.5, solid_capstyle="round")
        ax.scatter([r], [y], s=110, color=c, zorder=3, edgecolor=tud.WHITE, linewidth=1.2)
        ax.text(
            r - 0.02,
            y,
            "%.2f" % r,
            ha="right",
            va="center",
            fontsize=8.5,
            fontweight="bold",
            color=tud.INK,
        )
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names[::-1], fontsize=8.5)
    ax.set_xlim(0.3, 1.08)
    ax.set_ylim(-0.6, 3.7)
    ax.grid(False)
    ax.set_xlabel("Median error ratio (1.0 = no better than a tracker without movement)")
    ax.text(0.79, 3.55, "skill zone < 0.8", ha="right", va="top", fontsize=7.8, color=tud.BLUE)
    ax.set_title("A  How far each method beats a tracker without movement")

    ax = fig.add_subplot(gs[1, 0])  # B: waffle
    ax.set_xlim(0, 14.6)
    ax.set_ylim(-0.3, 4.4)
    ax.axis("off")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("B  Variants with skill (of 28)")
    for i, (k, c) in enumerate(zip(skill, cols)):
        y0 = 3.2 - i * 1.05
        for j in range(28):
            col, row = j % 14, j // 14
            ax.add_patch(
                Rectangle(
                    (col * 0.85 + 0.05, y0 - row * 0.4),
                    0.7,
                    0.32,
                    fc=c if j < k else tud.GREY_LIGHT,
                    ec="none",
                )
            )
        ax.text(
            12.1, y0 - 0.05, "%d" % k, fontsize=9, fontweight="bold", color=tud.INK, va="bottom"
        )
        ax.text(
            -0.25, y0 - 0.04, names[i], fontsize=8.5, color=tud.INK, va="center", ha="right"
        )  # row label: which method the squares belong to

    ax = fig.add_subplot(gs[1, 1])  # C: trade-off
    labs = ["Covers\nthe water", "Reads the\nspeed right"]
    s6 = [
        round(100 * float(vf["S6"].coverage.median())),
        round(100 * float(mw["S6"].speed_ratio.median())),
    ]
    ncc = [
        round(100 * float(vf["NCC"].coverage.median())),
        round(100 * float(mw["NCC"].speed_ratio.median())),
    ]
    for i, (l, a, b) in enumerate(zip(labs, s6, ncc)):
        y = 1 - i
        ax.barh(y + 0.17, a, height=0.3, color=tud.TRACKER["S6"])
        ax.barh(y - 0.17, b, height=0.3, color=tud.TRACKER["NCC"], **tud.bar_kw("NCC"))
        ax.text(a + 2, y + 0.17, "%d %%" % a, va="center", fontsize=8.3, fontweight="bold")
        ax.text(b + 2, y - 0.17, "%d %%" % b, va="center", fontsize=8.3, fontweight="bold")
    ax.set_yticks([1, 0])
    ax.set_yticklabels(labs, fontsize=8.3)
    ax.set_xlim(0, 125)
    ax.set_ylim(-1.5, 1.7)
    ax.grid(False)
    ax.set_xlabel("% (100 = ideal)")
    ax.set_title("C  The trade-off")
    ax.legend(
        handles=[
            Rectangle((0, 0), 1, 1, fc=tud.TRACKER["S6"]),
            Rectangle(
                (0, 0),
                1,
                1,
                fc=tud.TRACKER["NCC"],
                hatch=tud.HATCH["NCC"],
                ec=tud.HATCH_EC["NCC"],
                lw=0,
            ),
        ],
        labels=["Retrained PIPs++", "PTV NCC"],
        fontsize=7.6,
        loc="lower right",
    )

    ax = fig.add_subplot(gs[2, 0])  # D: strategies
    st = [
        "S0 pre-trained",
        "S1 short clips",
        "S2 + augmentation",
        "S3 long clips",
        "S4 + rehearsal",
        "S5 from scratch",
        "S6 final",
    ]
    v = [
        ho("PIPs++_b2_256"),
        ho("PIPs++_ft3000_b2_256"),
        ho("PIPs++_S2_b2_256"),
        ho("PIPs++_S3_r48_256"),
        ho("PIPs++_S4_b2_256"),
        ho("PIPs++_S5_b2_256"),
        ho("PIPs++_S6_b2_256"),
    ]
    key = ["S0", "S1", "S2", "S3", "S4", "S5", "S6"]
    ax.axvline(0.8, color=tud.BLUE, ls=":", lw=1.2)
    ncc_h = ho("PTV_tuned_ncc_fd2")
    ax.axvline(ncc_h, color=tud.TRACKER["NCC"], ls="-", lw=1.1)
    ax.text(
        ncc_h - 0.012,
        6.8,
        "NCC %.2f" % ncc_h,
        color=tud.TRACKER["NCC"],
        fontsize=FS,
        ha="right",
        va="center",
    )
    for i, (x, k) in enumerate(zip(v, key)):
        y = len(st) - 1 - i
        ax.plot([0.36, x], [y, y], color=tud.TRACKER[k], lw=1.8, alpha=0.7)
        ax.scatter([x], [y], s=55, color=tud.TRACKER[k], zorder=3, **tud.scatter_kw(k))
        ax.text(1.10, y, "%.2f" % x, va="center", fontsize=FS)
    ax.set_yticks(range(len(st)))
    ax.set_yticklabels(st[::-1], fontsize=8)
    ax.set_xlim(0.36, 1.24)
    ax.set_ylim(-0.6, 7.5)
    ax.grid(False)
    ax.set_xlabel("Median ratio, 10 unseen variants")
    ax.set_title("D  Five recipes, same result")

    ax = fig.add_subplot(gs[2, 1])
    ax.axis("off")  # E: take-away
    ax.add_patch(
        FancyBboxPatch(
            (0, 0),
            1,
            1,
            transform=ax.transAxes,
            boxstyle="round,pad=0.0,rounding_size=0.03",
            fc=tud.WHITE,
            ec=tud.BLUE,
            lw=1.4,
        )
    )
    ax.text(
        0.05,
        0.95,
        "E  What to take away",
        transform=ax.transAxes,
        fontsize=9.5,
        fontweight="bold",
        color=tud.BLUE,
        va="top",
    )
    pts = [
        "Published PIPs++ does not follow water.",
        "Retraining on the simulated river gives\nskill on %d of %d variants."
        % (skill[2], R["n_var"]),
        "The recipe hardly matters; starting from\nthe published weights does.",
        "S6 sees all the water but reads the\nflow about %d %% too slow."
        % (10 * round(-float(vf["S6"].bias_pct.median()) / 10)),
        "NCC is more accurate but sees only\nabout half of the water.",
        "Retraining costs %d %% general accuracy\n(DAVIS %.1f to %.1f)."
        % (round(100 * (dv["reference"] - dv["S6"]) / dv["reference"]), dv["reference"], dv["S6"]),
    ]
    ypos = 0.855
    rend = fig.canvas.get_renderer()
    for (
        t
    ) in (
        pts
    ):  # each bullet starts below the measured end of the previous one, so they can never overlap
        tx = ax.text(
            0.05,
            ypos,
            textwrap.fill(t.replace("\n", " "), 36, initial_indent="• ", subsequent_indent="   "),
            transform=ax.transAxes,
            fontsize=FS,
            va="top",
            linespacing=1.25,
        )
        bb = tx.get_window_extent(rend).transformed(ax.transAxes.inverted())
        ypos = bb.y0 - 0.025
    save(fig, "figU_results_at_glance.png", bbox_inches="tight")


if __name__ == "__main__":
    glance()
