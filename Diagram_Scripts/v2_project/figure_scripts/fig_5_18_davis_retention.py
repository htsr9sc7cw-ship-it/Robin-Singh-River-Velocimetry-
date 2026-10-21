"""Figure 5.18  TAP-Vid-DAVIS after retraining: delta_avg of the reference weights and of each strategy
(32-frame windows, 30 videos; mean of d_avg over the videos in finetune/results_davis/*_S32.csv).
Output: results/figures/figR4_davis.png      Run:  python fig_5_18_davis_retention.py"""

from fig_common import *

FT = os.path.join(os.path.dirname(PROJECT), "finetune", "results_davis")
rows = [
    ("reference", "Published weights", "S0"),
    ("S3", "S3 long clips", "S3"),
    ("S6", "S6 final model", "S6"),
    ("S4", "S4 rehearsal", "S4"),
    ("S1", "S1 short clips", "S1"),
    ("S2", "S2 + data", "S2"),
    ("S5", "S5 from scratch", "S5"),
]
vals = [pd.read_csv(os.path.join(FT, "%s_S32.csv" % f)).d_avg.mean() for f, _, _ in rows]
fig, ax = plt.subplots(figsize=(6.0, 3.0))
for i, ((f, lab, key), v) in enumerate(zip(rows, vals)):
    ax.barh(i, v, color=tud.TRACKER[key], height=0.65, zorder=2, **tud.bar_kw(key))
    ax.text(v + 1, i, "%.1f" % v, va="center", fontsize=8.5)
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([r[1] for r in rows])
ax.invert_yaxis()
ax.grid(axis="y", visible=False)
ax.set_xlim(0, 80)
ax.set_xlabel("TAP-Vid-DAVIS accuracy $\\delta_{avg}$ in % (higher is better)")
save(fig, "figR4_davis.png")
