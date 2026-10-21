"""Figure 6.1  Accuracy against coverage, one point per moving-water variant.
Output: results/figures/figS_accuracy_vs_coverage.png      Run:  python fig_6_01_accuracy_vs_coverage.py
"""

from fig_common import *
from matplotlib.patches import Patch, Rectangle

v = pd.read_csv(os.path.join(RES, "velocity_field_surfmove_v3.csv"))
v = v[~v.scene.str.contains("clear")]
fig, ax = plt.subplots(figsize=(6.2, 4.6))
for mm, lab, key, mk in [
    ("PIPs++_b2_256", "PIPs++ pre-trained", "S0", "o"),
    ("PIPs++_S6_b2_256", "PIPs++ retrained (S6)", "S6", "D"),
    ("PTV_tuned_ncc_fd2", "PTV NCC", "NCC", "s"),
    ("PTV_tuned_lk_fd2", "PTV LK", "LK", "^"),
]:
    x = v[v.method == mm]
    ax.scatter(
        x.coverage, x.bias_pct, c=tud.TRACKER[key], s=46, label=lab, zorder=3, **tud.scatter_kw(key)
    )
ax.add_patch(Rectangle((0.8, -10), 0.24, 20, fc=tud.BLUE_TINT, ec=tud.BLUE, lw=1, zorder=1))
ax.axvline(0.8, color=tud.GREY, ls=":", lw=1, zorder=2)
ax.set_xlabel("coverage: fraction of water cells with a velocity estimate")
ax.set_ylabel("mean-speed bias (% of true mean speed)")
ax.set_xlim(0, 1.04)
ax.set_ylim(-105, 18)
h, l = ax.get_legend_handles_labels()
h.append(Patch(fc=tud.BLUE_TINT, ec=tud.BLUE))
l.append("hydrometric target: bias within ±10 %\non at least 80 % of the water")
ax.legend(h, l, loc="lower left", fontsize=7.6)
save(fig, "figS_accuracy_vs_coverage.png")
