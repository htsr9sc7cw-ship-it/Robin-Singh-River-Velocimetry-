"""Figure 5.3  Direction agreement and speed ratio against flow speed.
Output: results/figures/figC_direction_and_speed_ratio.png      Run:  python fig_5_03_direction_and_speed.py"""
from fig_common import *

d, _ = load_main()
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 3.5))
for m in ORDER:
    s = d[d.method == m]
    a1.scatter(s.gt_speed, s.frac_cos08, s=SZ[m] * 0.8, zorder=ZO[m], alpha=0.9, marker=MK[m], color=COL[m], label=NAME[m], edgecolor='white', linewidth=0.5)
    a2.scatter(s.gt_speed, s.speed_ratio, s=SZ[m] * 0.8, zorder=ZO[m], alpha=0.9, marker=MK[m], color=COL[m], edgecolor='white', linewidth=0.5)
a1.set_ylim(0, 1.05); a1.set_ylabel('fraction of sub-steps\nwithin 37° of the truth'); a1.set_xlabel('ground-truth speed (px/frame)')
a2.axhline(1, color=tud.GREY, lw=1, ls='--'); a2.set_ylim(0, 1.6); a2.set_ylabel('measured / true displacement'); a2.set_xlabel('ground-truth speed (px/frame)')
a1.set_title('(a) Direction agreement'); a2.set_title('(b) Speed ratio (1 = correct)')
h, l = a1.get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=4, fontsize=7.5, bbox_to_anchor=(0.5, -0.07))
fig.tight_layout()
save(fig, 'figC_direction_and_speed_ratio.png')
