"""Figure 5.15  Headline comparison on moving water: ratio (15-frame horizon), speed ratio and coverage.
Output: results/figures/figL_surfmove_headline.png      Run:  python fig_5_15_headline_moving_water.py
"""

from fig_common import *

m = pd.read_csv(os.path.join(RES, "surfmove_headline_v3.csv"))
m = m[~m.scene.str.contains("clear")]
v = pd.read_csv(os.path.join(RES, "velocity_field_surfmove_v3.csv"))
v = v[~v.scene.str.contains("clear")]
meth = [
    ("PIPs++_b2_256", "PIPs++ pre-trained", "S0"),
    ("PIPs++_S6_b2_256", "PIPs++ retrained (S6)", "S6"),
    ("PTV_tuned_ncc_fd2", "PTV NCC", "NCC"),
    ("PTV_tuned_lk_fd2", "PTV LK", "LK"),
]
panels = [
    ("Error ratio", "lower is better; 1 = no skill"),
    ("Speed ratio", "1 = unbiased speed"),
    ("Water measured", "share of water cells"),
]
fig, axes = plt.subplots(1, 3, figsize=(7.4, 3.0), gridspec_kw={"wspace": 0.3})
for k, (ax, (title, xlab)) in enumerate(zip(axes, panels)):
    for i, (mm, lab, key) in enumerate(meth):
        if k == 0:
            x = m[m.method == mm].ratio_h15.values
            val = np.median(x)
            lo, hi = ci(x)
            right = hi
            ax.errorbar(
                val,
                i,
                xerr=[[val - lo], [hi - val]],
                fmt="none",
                ecolor=tud.INK,
                capsize=2.5,
                lw=1.0,
                zorder=3,
            )
            note = " %d/28" % int((x < 0.8).sum())
        elif k == 1:
            val = m[m.method == mm].speed_ratio.median()
            right = val
            note = ""
        else:
            val = v[v.method == mm].coverage.median()
            right = val
            note = ""
        ax.barh(i, val, color=tud.TRACKER[key], height=0.66, zorder=2, **tud.bar_kw(key))
        ax.text(1.08, i, "%.2f%s" % (val, note), va="center", ha="left", fontsize=7.6, zorder=4)
    ax.axvline(1, color=tud.GREY, ls="--", lw=0.9, zorder=1)
    if k == 0:
        ax.axvline(0.8, color=tud.GREY, ls=":", lw=0.9, zorder=1)
    ax.set_yticks(range(4))
    ax.set_yticklabels([x[1] for x in meth] if k == 0 else [""] * 4)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, 1.75 if k == 0 else 1.40)
    ax.set_xticks([0, 0.5, 1.0])
    ax.set_title(title, fontsize=8.6)
    ax.set_xlabel(xlab, fontsize=7.6)
save(fig, "figL_surfmove_headline.png")
