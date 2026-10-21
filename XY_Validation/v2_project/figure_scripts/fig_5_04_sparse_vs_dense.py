"""Figure 5.4  Sparse against dense tracers: Error ratio per camera view and method.
Output: results/figures/figE_sparse_vs_dense.png      Run:  python fig_5_04_sparse_vs_dense.py"""
from fig_common import *

d, _ = load_main()
pv = d.pivot_table(index=['view', 'method'], columns='density', values='ratio').reset_index()
fig, ax = plt.subplots(figsize=(5.4, 4.6))
for m in ORDER:
    s = pv[pv.method == m]
    ax.scatter(s['sparse'], s['dense'], s=SZ[m], zorder=ZO[m], alpha=0.9, marker=MK[m], color=COL[m], label=NAME[m], edgecolor='white', linewidth=0.5)
ax.plot([0, 1.5], [0, 1.5], color=tud.GREY, lw=1, ls='--')
ax.set_xlim(0, 1.5); ax.set_ylim(0, 1.5); ax.set_aspect('equal')
ax.set_xlabel('Error ratio, sparse tracers')
ax.set_ylabel('Error ratio, dense tracers')
ax.legend(loc='upper left')
save(fig, 'figE_sparse_vs_dense.png')
