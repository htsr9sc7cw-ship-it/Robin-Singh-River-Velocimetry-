"""Figure 5.7  Re-initialisation pilot: Error ratio of every setting on the four pilot variants.
Output: results/figures/figH_reinit_pilot.png      Run:  python fig_5_07_reinit_pilot.py"""

from fig_common import *

pil = load_run_table("pips_reinit_pilot.csv")
order = sorted(pil.method.unique(), key=lambda m: (not m.startswith("PIPs++"), m))
vs = sorted(pil.variant.unique())
x = np.arange(len(vs))
w = 0.8 / len(order)
fig, ax = plt.subplots(figsize=(7.2, 4.2))
for i, m in enumerate(order):
    y = [pil[(pil.method == m) & (pil.variant == v)].ratio.mean() for v in vs]
    light = 0.45 + 0.55 * (i % 2 == 0) if m.startswith("PIPs++") else 0.95
    ax.bar(
        x + (i - len(order) / 2 + 0.5) * w,
        y,
        w,
        color=run_colour(m),
        alpha=light,
        label=run_name(m),
        **tud.bar_kw(tud.method_key(m))
    )
ax.axhline(1, color=tud.GREY, lw=0.9, ls="--")
ax.set_xticks(x)
ax.set_xticklabels(vs)
ax.set_ylabel("Error ratio (1 = no gain)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2, fontsize=7.5)
save(fig, "figH_reinit_pilot.png")
