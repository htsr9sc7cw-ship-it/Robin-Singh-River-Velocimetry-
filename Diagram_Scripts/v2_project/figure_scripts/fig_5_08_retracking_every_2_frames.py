"""Figure 5.8  Re-tracking every 2 frames: all 28 variants, Error ratio against flow speed.
Output: results/figures/figI_reinit_full_vs_speed.png      Run:  python fig_5_08_retracking_every_2_frames.py
"""

from fig_common import *

full = load_run_table("three_way_v3_k2.csv")
nv = full.groupby("method").scene.count()
full = full[full.method.isin(nv[nv == nv.max()].index)]  # methods run on all 28 variants
fig, ax = plt.subplots(figsize=(7.0, 4.4))
for m in sorted(full.method.unique(), key=lambda m: (not m.startswith("PIPs++"), m)):
    s = full[full.method == m]
    once = m.startswith("PIPs++") and "_r" not in m
    k = tud.method_key(m)
    kw = (
        dict(marker="P", s=40, edgecolors=tud.GREY, linewidths=0.5)
        if once
        else dict(tud.scatter_kw(k), s=34)
    )
    kw.setdefault("s", 24)
    ax.scatter(s.truth_med, s.ratio, color=run_colour(m), alpha=0.9, label=run_name(m), **kw)
ax.axhline(1, color=tud.GREY, lw=0.9, ls="--")
ax.axhline(0.8, color=tud.GREY, lw=0.8, ls=":")
ax.set_xlabel("median true displacement (px/frame)")
ax.set_ylabel("Error ratio (1 = no gain)")
from matplotlib.lines import Line2D

h, l = ax.get_legend_handles_labels()
h.append(Line2D([], [], ls="", marker="P", color=tud.GREY_MID, ms=6, mew=0.5))
l.append("plus sign = tracker started once per 48-frame block (not restarted)")
ax.legend(h, l, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=1, fontsize=9.0)
save(fig, "figI_reinit_full_vs_speed.png")
