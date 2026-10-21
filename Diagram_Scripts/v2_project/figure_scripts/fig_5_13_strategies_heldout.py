"""Figure 5.13  Retraining strategies on the ten held-out variants: median ratio with 95 % bootstrap interval.
Output: results/figures/figK_strategies_heldout.png      Run:  python fig_5_13_strategies_heldout.py
"""

from fig_common import *

d = pd.concat(
    [
        pd.read_csv(os.path.join(RES, "strategies_v3.csv")),
        pd.read_csv(os.path.join(RES, "s6_heldout_v3.csv")),
    ]
).drop_duplicates(["scene", "method"])
d = d[d.scene != "v2_Path2_dense"]
rows = [
    ("PIPs++_b2_256", "S0  pre-trained", "S0"),
    ("PIPs++_ft3000_b2_256", "S1  short-clip fine-tuning", "S1"),
    ("PIPs++_S2_b2_256", "S2  + data and augmentation", "S2"),
    ("PIPs++_S3_r48_256", "S3  long clips (long-term mode)", "S3"),
    ("PIPs++_S4_b2_256", "S4  rehearsal with PointOdyssey", "S4"),
    ("PIPs++_S5_b2_256", "S5  from scratch", "S5"),
    ("PIPs++_S6_b2_256", "S6  final model", "S6"),
    ("PTV_tuned_ncc_fd2", "PTV NCC", "NCC"),
    ("PTV_tuned_lk_fd2", "PTV LK", "LK"),
]
LBL = 0.02 + max(
    ci(d[d.method == r[0]].ratio_h15.values)[1] for r in rows
)  # value labels in one column right of the longest whisker
fig, ax = plt.subplots(figsize=(6.8, 3.8))
for i, (m, lab, k) in enumerate(rows):
    x = d[d.method == m].ratio_h15.values
    med = np.median(x)
    lo, hi = ci(x)
    ax.barh(i, med, color=tud.TRACKER[k], height=0.68, zorder=2, **tud.bar_kw(k))
    ax.errorbar(
        med,
        i,
        xerr=[[med - lo], [hi - med]],
        fmt="none",
        ecolor=tud.INK,
        capsize=3,
        lw=1.1,
        zorder=3,
    )
    ax.text(LBL, i, "%.2f" % med, va="center", ha="left", fontsize=8.5, zorder=4, fontweight="bold")
ax.axvline(1, color=tud.GREY, ls="--", lw=0.9, zorder=1)
ax.axvline(0.8, color=tud.GREY, ls=":", lw=0.9, zorder=1)
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([r[1] for r in rows])
ax.invert_yaxis()
ax.grid(axis="y", visible=False)
ax.set_xlim(0, LBL + 0.2)
ax.set_xticks(np.arange(0, 1.21, 0.2))
ax.set_xlabel(
    "Error ratio, first 15 frames (lower is better)\ndotted 0.8 = skill threshold, dashed 1.0 = no skill"
)
save(fig, "figK_strategies_heldout.png")
