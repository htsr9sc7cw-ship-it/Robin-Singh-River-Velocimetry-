"""Figure 3.3  Deployment modes: the same 48 frames, four ways of driving a tracker (D3, D1, D4, FlowVelo).
Output: results/figures/figQ_deployment_modes.png      Run:  python fig_3_03_deployment_modes.py"""
from fig_common import *

lanes = [(0, 'D3  long-term\none call per block, points persist', tud.TRACKER['S6'], 48, None),
         (1, 'D1  re-tracked every 2 frames\n8-frame window', tud.TRACKER['S6'], 8, 2),
         (2, 'D4  fresh seeds every 2 frames\neach followed 16 frames (headline)', tud.TRACKER['S6'], 16, 2),
         (3, 'PTV NCC / LK\nnew features every 2 frames, each set\nfollowed for FT frames (drawn: 10)', tud.TRACKER['NCC'], 10, 2)]
fig, ax = plt.subplots(figsize=(7.4, 4.2)); ax.set_xlim(-1, 58); ax.set_ylim(-0.7, 4.6)
for y, lab, c, length, every in lanes:
    if every is None:
        ax.plot([0, 48], [y, y], color=c, lw=6, solid_capstyle='butt', zorder=2); ax.plot([0], [y], 'o', color=tud.INK, ms=4, zorder=3)
    else:
        for k, t in enumerate(range(0, 16, every)):          # first eight births, staggered so the overlap is visible
            yy = y - 0.30 + k * 0.075
            ax.plot([t, min(t + length, 48)], [yy, yy], color=c, lw=2.2, solid_capstyle='butt', zorder=2)
            ax.plot([t], [yy], 'o', color=tud.INK, ms=3, zorder=3)
        ax.text(51, y - 0.02, '... continues every %d frames\nto frame 46' % every, fontsize=6.8, color=tud.GREY, va='center', ha='right', style='italic')
ax.set_yticks(range(4)); ax.set_yticklabels([l for _, l, _, _, _ in lanes], fontsize=7.6); ax.invert_yaxis(); ax.grid(axis='y', visible=False)
ax.set_xlabel('Frame in the 48-frame block'); ax.set_xticks(range(0, 49, 6))
ax.spines['left'].set_visible(False); ax.tick_params(axis='y', length=0)
ax.text(28, 4.25, 'dot = new points or features detected;  bar = how long each set is tracked\nall methods are scored over the same 15 frames after birth',
        ha='center', va='center', fontsize=6.6, color=tud.GREY, style='italic', linespacing=1.3)
save(fig, 'figQ_deployment_modes.png')
