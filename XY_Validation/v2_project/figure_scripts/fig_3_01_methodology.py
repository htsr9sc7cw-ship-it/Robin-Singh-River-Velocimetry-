"""Figure 3.1  Methodology at a glance.
Output: results/figures/figV_methodology.png      Run:  python fig_3_01_methodology.py
Drawn with the verified numbers of Chapter 5; colours and fonts come from tud_style.py (TU Dresden style, no title in the picture)."""
import os

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

import tud_style as tud

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'results', 'figures')
tud.apply()


def save(fig, name, **kw):
    fig.savefig(os.path.join(OUT, name), dpi=200, facecolor='white', **kw)
    plt.close(fig)
    print('wrote', os.path.join(OUT, name))


def method_fig():
    """Fig. 3.1: methodology at a glance, four phases, section number on every box"""
    from PIL import Image
    g = Image.open(os.path.join(OUT, 'gallery', 'v2_Path4_dense.png')).convert('RGB')
    crop = lambda x0, x1: g.crop((x0, 176, x1, 909))
    thumbs = {'gt': crop(24, 760), 'ncc': crop(783, 1515), 'pips': crop(1540, 2273), 'ft': crop(2300, 3033)}
    FW, FH, YM = 7.2, 7.75, 131.0
    fig = plt.figure(figsize=(FW, FH)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, YM); ax.axis('off')

    def box(x, y, w, h, title, sub, sect, thumb=None, fc=tud.WHITE, lw=1.4, tint=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.0,rounding_size=1.2', fc=tud.BLUE_TINT if tint else fc, ec=tud.BLUE, lw=lw, zorder=2))
        ax.text(x + 1.2, y + h - 1.6, title, ha='left', va='top', fontsize=9.2, fontweight='bold', color=tud.BLUE, zorder=3)
        ax.text(x + 1.2, y + h - 5.4, sub, ha='left', va='top', fontsize=7.6, color=tud.INK, zorder=3, linespacing=1.3)
        if thumb is not None:
            ia = fig.add_axes([(x + 1.2) / 100, (y + 2.0) / YM, 0.55 / FW, 0.55 / FH]); ia.imshow(thumb); ia.set_xticks([]); ia.set_yticks([])
            for sp in ia.spines.values(): sp.set_color(tud.BLUE); sp.set_linewidth(1.0)

    def arrow(x0, y0, x1, y1): tud.arrow(ax, x0, y0, x1, y1, lw=1.4)

    def phase(ytop, ybot, name):
        ax.plot([2, 98], [ytop + 1.0, ytop + 1.0], color=tud.GREY_MID, lw=0.9, ls=(0, (5, 4)))
        ax.text(2, (ytop + ybot) / 2, name, rotation=90, ha='center', va='center', fontsize=10, fontweight='bold', color=tud.BLUE)

    y, h, w = 108, 20, 21.5; xs = [6, 29.5, 53, 76.5]
    box(xs[0], y, w, h, '1  Real reach', 'Wesenitz at Elbersdorf,\nvalidation site of\nthe PTV method', 'Sect. 3.1')
    box(xs[1], y, w, h, '2  Simulation', 'Blender FLIP fluid\nin a 14 m x 8 m domain', 'Sect. 3.2')
    box(xs[2], y, w, h, '3  Rendering', '16 camera views x\n2 tracer densities,\n201 frames each', 'Sect. 3.3')
    box(xs[3], y, w, h, '4  Ground truth', 'exact tracer paths', 'Sect. 3.4-3.5', thumbs['gt'], lw=2.2)
    for i in range(3): arrow(xs[i] + w, y + h / 2, xs[i + 1], y + h / 2)
    phase(y + h, y, 'DATA')
    y2, h2, w2 = 71, 29, 29.6; xt = [6, 36.2, 66.4]
    box(xt[0], y2, w2, h2, '5a  Pre-trained PIPs++', 'pre-trained model,\nused as released', 'Sect. 4.2', thumbs['pips'])
    box(xt[1], y2, w2, h2, '5b  PTV', 'NCC and LK tracking,\nparameters from the data', 'Sect. 4.3', thumbs['ncc'])
    box(xt[2], y2, w2, h2, '5c  Retrained PIPs++', 'five strategies S1-S5,\none rule picks S6', 'Sect. 4.4', thumbs['ft'])
    bus = y - 3.5
    ax.plot([xt[0] + w2 / 2, 87.2], [bus, bus], color=tud.BLUE, lw=1.4, zorder=1); ax.plot([87.2, 87.2], [y - 0.3, bus], color=tud.BLUE, lw=1.4, zorder=1)
    for xx in (xt[0] + w2 / 2, xt[1] + w2 / 2, xt[2] + w2 / 2): arrow(xx, bus, xx, y2 + h2 + 0.2)
    phase(y2 + h2, y2, 'TRACKERS')
    y3, h3 = 50, 15
    box(6, y3, 90, h3, '6  One scorer for all trackers', 'ratio  |  direction  |  speed ratio  |  coverage  |  bias  |  TAP-Vid metrics', 'Sect. 4.5')
    ax.text(6 + 1.2, y3 + 4.4, 'ratio = RMSE / RMSE of a tracker without movement;  skill = ratio below 0.8', ha='left', fontsize=7.8, color=tud.BLUE, fontweight='bold', zorder=3)
    for xx in (xt[0] + w2 / 2, xt[1] + w2 / 2, xt[2] + w2 / 2): arrow(xx, y2 - 0.3, xx, y3 + h3 + 0.2)
    phase(y3 + h3, y3, 'SCORING')
    cond = [('Flow speed', 'speed ladder,\nbreak points', 'Sect. 5.2.3'), ('Density', 'sparse and\ndense tracers', 'Sect. 5.4.3'), ('View', '10 held-out\nvariants', 'Sect. 5.3.5'),
            ('Water', 'muddy,\nclear, moving\nsurface', 'Sect. 5.4.4-5'), ('Run mode', 'modes\nD1 to D4', 'Sect. 5.3.2'), ('Retention', 'TAP-Vid\nDAVIS', 'Sect. 5.3.7')]
    y4, h4, w4 = 25, 14, 14.2
    for i, (t, sub, sc) in enumerate(cond): box(6 + i * (w4 + 1.0), y4, w4, h4, t, sub, sc, lw=1.0, tint=True)
    ax.text(51, y4 + h4 + 2.6, '7  Comparison under different conditions', ha='center', fontsize=9.4, fontweight='bold', color=tud.BLUE)
    arrow(51, y3 - 0.3, 51, y4 + h4 + 6.0)
    phase(y4 + h4 + 5, y4, 'COMPARISON')
    box(6, 4, 90, 13, 'Findings', 'Objective 1: pre-trained PIPs++   |   Objective 2: retraining   |   Objective 3: comparison and cost', 'Sect. 5.4 and Chapter 7', lw=2.2)
    arrow(51, y4 - 0.3, 51, 17.3)
    save(fig, 'figV_methodology.png')


if __name__ == '__main__':
    method_fig()
