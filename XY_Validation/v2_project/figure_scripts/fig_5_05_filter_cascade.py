"""Figure 5.5  FlowVelo filter cascade: tracks remaining after each filter stage, by mode.
Output: results/figures/figD_filter_cascade.png      Run:  python fig_5_05_filter_cascade.py"""
from fig_common import *

d, _ = load_main()
stages = ['raw', 'after_mindist', 'after_maxdist', 'after_mincount', 'after_steady', 'after_range', 'final']
names = ['Detected and\ntracked', 'Minimum\ndistance', 'Maximum\ndistance', 'Minimum\ncount', 'Steadiness', 'Angle\nrange', 'Main-flow\ndirection']
x = np.arange(len(stages)); w = 0.27
fig, ax = plt.subplots(figsize=(6.6, 3.4))
for i, m in enumerate(ORDER[1:]):
    s = d[d.method == m][stages].sum()
    ax.bar(x + (i - 1) * w, s.values, w * 0.92, color=COL[m], label=NAME[m])
    ax.text(x[-1] + (i - 1) * w, s.values[-1] * 1.12, '%d' % s.values[-1], ha='center', va='bottom', fontsize=7.5, color=tud.GREY)
ax.set_xticks(x); ax.set_xticklabels(names, fontsize=7.5)
ax.set_ylabel('tracks remaining (log scale)'); ax.set_yscale('log')
ax.legend()
save(fig, 'figD_filter_cascade.png')
