"""Figure 5.11  Fine-tuned PIPs++ on the held-out camera views: Error ratio over the 15-frame horizon per variant.
Output: results/figures/figJ_finetune_heldout.png      Run:  python fig_5_11_finetune_heldout.py"""
from fig_common import *

ft = load_run_table('finetune_v3.csv')
ft = ft[~ft.scene.eq('v2_Path2_dense')]                           # Path2 dense is a training view
keep = ft[ft.method.isin(['PIPs++', 'PIPs++_r2_256', 'PIPs++_ft3000_r2_256', 'PTV_tuned_ncc_fd2', 'PTV_tuned_lk_fd2'])]
ms = sorted(keep.method.unique(), key=lambda m: (not m.startswith('PIPs++'), m)); vs = sorted(keep.variant.unique())
x = np.arange(len(vs)); w = 0.8 / len(ms)
shade = {'PIPs++': 1.0, 'PIPs++_r2_256': 0.6}
fig, ax = plt.subplots(figsize=(7.2, 4.0))
for i, m in enumerate(ms):
    y = [keep[(keep.method == m) & (keep.variant == v)].ratio_h15.mean() for v in vs]
    ax.bar(x + (i - len(ms) / 2 + 0.5) * w, y, w, color=run_colour(m), alpha=shade.get(m, 1.0) if m.startswith('PIPs++') and '_ft' not in m else 1.0,
           edgecolor='white', linewidth=0.5, label=run_name(m))
ax.axhline(1, color=tud.GREY, lw=0.9, ls='--')
ax.set_xticks(x); ax.set_xticklabels(vs, rotation=30, ha='right'); ax.set_ylabel('Error ratio, 15 frames')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.32), ncol=2, fontsize=7.5)
save(fig, 'figJ_finetune_heldout.png')
