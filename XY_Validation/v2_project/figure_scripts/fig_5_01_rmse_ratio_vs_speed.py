"""Figure 5.1  Error ratio against flow speed (28 muddy variants, four methods).
Output: results/figures/figA_rmse_ratio_vs_speed.png      Run:  python fig_5_01_rmse_ratio_vs_speed.py"""
from fig_common import *

d, _ = load_main()
fig, ax = plt.subplots(figsize=(6.6, 3.9))
ax.axhline(1.0, color=tud.GREY, lw=1, ls='--')
ax.text(118, 1.02, 'no movement (ratio = 1)', color=tud.GREY, ha='right', va='bottom', fontsize=8)
for m in ORDER:
    s = d[d.method == m]
    ax.scatter(s.gt_speed, s.ratio, s=SZ[m], zorder=ZO[m], alpha=0.9, marker=MK[m], color=COL[m], label=NAME[m], edgecolor='white', linewidth=0.6)
ax.set_xlabel('True surface speed (px/frame)')
ax.set_ylabel('Error ratio (1 = no gain)')
ax.set_ylim(0, 1.5); ax.set_xlim(0, 120)
ax.legend(loc='lower right')
save(fig, 'figA_rmse_ratio_vs_speed.png')
