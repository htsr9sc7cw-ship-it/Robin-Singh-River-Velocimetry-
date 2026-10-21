"""Figure 5.16  Heat map of all variants: Error ratio (15-frame horizon) of every method on every moving-water variant,
variants ordered by mean flow speed (rows), one column per method.
Output: results/figures/figM_heatmap_surfmove.png      Run:  python fig_5_16_heatmap_all_variants.py
"""

from fig_common import *

m = pd.read_csv(os.path.join(RES, "surfmove_headline_v3.csv"))
m = m[~m.scene.str.contains("clear")]
meth = [
    ("PIPs++_b2_256", "PIPs++\npre-trained"),
    ("PIPs++_S6_b2_256", "PIPs++\nretrained (S6)"),
    ("PTV_tuned_ncc_fd2", "PTV\nNCC"),
    ("PTV_tuned_lk_fd2", "PTV\nLK"),
]
vf = pd.read_csv(os.path.join(RES, "velocity_field_surfmove_v3.csv"))
sp = vf.groupby(
    "scene"
).true_mean_px.first()  # mean true flow speed of the scene, the same value as in Table heat of the thesis
sc = sorted(m.scene.unique(), key=lambda s: sp.get(s, 0))
lab = (
    lambda s: s.replace("v2_", "")
    .replace("_surfmove", "")
    .replace("_dense", " · dense")
    .replace("_sparse", " · sparse")
    .replace("_", " ")
)
M = np.array(
    [[m[(m.scene == s) & (m.method == mm)].ratio_h15.values[0] for s in sc] for mm, _ in meth]
).T  # rows = variants
fig, ax = plt.subplots(figsize=(5.2, 7.6))
im = ax.imshow(M, cmap=tud.CMAP, vmin=0.2, vmax=1.1, aspect="auto")
ax.xaxis.tick_top()
ax.set_xticks(range(4))
ax.set_xticklabels([x[1] for x in meth], fontsize=7.6)
ax.set_yticks(range(len(sc)))
ax.set_yticklabels(["%s   %.0f px/frame" % (lab(s), sp.get(s, 0)) for s in sc], fontsize=7)
for i in range(len(sc)):
    for j in range(4):
        ax.text(
            j,
            i,
            "%.2f" % M[i, j],
            ha="center",
            va="center",
            fontsize=7,
            color="white" if M[i, j] < 0.55 else tud.INK,
        )
ax.set_xticks(np.arange(-0.5, 4, 1), minor=True)
ax.set_yticks(np.arange(-0.5, len(sc), 1), minor=True)
ax.grid(which="minor", color="white", lw=0.8)
ax.grid(which="major", visible=False)
ax.tick_params(which="minor", length=0)
ax.tick_params(length=0)
for s_ in ax.spines.values():
    s_.set_visible(False)
cb = fig.colorbar(im, ax=ax, pad=0.03, fraction=0.04, shrink=0.5, location="bottom")
cb.set_label("Error ratio (dark = skill, white = none)", fontsize=7.6)
cb.outline.set_visible(False)
save(fig, "figM_heatmap_surfmove.png")
