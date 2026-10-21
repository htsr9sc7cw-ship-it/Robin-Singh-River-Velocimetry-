"""Figure 5.8  Re-tracking every 2 frames: all 28 variants, Error ratio against flow speed.
Output: results/figures/figI_reinit_full_vs_speed.png      Run:  python fig_5_08_retracking_every_2_frames.py"""
from fig_common import *

full = load_run_table('three_way_v3_k2.csv')
nv = full.groupby('method').scene.count()
full = full[full.method.isin(nv[nv == nv.max()].index)]          # methods run on all 28 variants
fig, ax = plt.subplots(figsize=(7.0, 4.4))
for m in sorted(full.method.unique(), key=lambda m: (not m.startswith('PIPs++'), m)):
    s = full[full.method == m]
    ax.scatter(s.truth_med, s.ratio, s=24, color=run_colour(m), marker='x' if m.startswith('PIPs++') and '_r' not in m else 'o',
               alpha=0.9, label=run_name(m), edgecolor='white', linewidth=0.4)
ax.axhline(1, color=tud.GREY, lw=0.9, ls='--'); ax.axhline(0.8, color=tud.GREY, lw=0.8, ls=':')
ax.set_xlabel('median true displacement (px/frame)'); ax.set_ylabel('Error ratio (1 = no gain)')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, fontsize=7.5)
save(fig, 'figI_reinit_full_vs_speed.png')
