"""Figure 5.2  Position accuracy by speed group: fraction of sub-steps within an error threshold.
Output: results/figures/figB_delta_accuracy_by_speed.png      Run:  python fig_5_02_position_accuracy_by_speed.py"""
from fig_common import *

d, labels = load_main()
th = [1, 2, 4, 8, 16]
fig, axes = plt.subplots(1, 4, figsize=(7.4, 3.0), sharey=True)
for ax, grp in zip(axes, labels):
    for m in ORDER:
        s = d[(d.method == m) & (d.speed_group == grp)]
        if len(s) == 0:
            continue
        ax.plot(th, [s['d%d' % t].median() for t in th], marker=MK[m], ms=3.5, lw=1.5, color=COL[m], label=NAME[m])
    ax.set_xscale('log', base=2); ax.set_xticks(th); ax.set_xticklabels(th); ax.set_ylim(0, 1)
    head, tail = grp.split(' (')[0], grp.split(' (')[1].rstrip(')')
    ax.set_title(head, fontsize=8, pad=4)
    ax.set_xlabel('threshold (px)', fontsize=8)
axes[0].set_ylabel('fraction of sub-steps\nbelow threshold')
h, l = next((ax.get_legend_handles_labels() for ax in axes if ax.lines), ([], []))
fig.legend(h, l, loc='lower center', ncol=4, fontsize=7.5, bbox_to_anchor=(0.5, -0.12))
fig.tight_layout()
save(fig, 'figB_delta_accuracy_by_speed.png')
