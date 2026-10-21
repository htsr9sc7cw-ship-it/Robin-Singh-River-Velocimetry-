"""Figure 3.2  Retraining strategies as a tree.
Output: results/figures/figP_strategy_tree.png      Run:  python fig_3_02_retraining_tree.py
Drawn with the verified numbers of Chapter 5; colours and fonts come from tud_style.py (TU Dresden style, no title in the picture)."""
import os

import matplotlib
import pandas as pd

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

import tud_style as tud

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'results', 'figures')
tud.apply()

RES = os.path.join(os.path.dirname(HERE), 'results')
DAVIS = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'finetune', 'results_davis')


def results():
    """every number of this picture, computed from the result files of the real runs (nothing is typed in)"""
    m = pd.read_csv(os.path.join(RES, 'surfmove_headline_v3.csv')); m = m[~m.scene.str.contains('clear')]
    v = pd.read_csv(os.path.join(RES, 'velocity_field_surfmove_v3.csv')); v = v[~v.scene.str.contains('clear')]
    h = pd.concat([pd.read_csv(os.path.join(RES, 'strategies_v3.csv')), pd.read_csv(os.path.join(RES, 's6_heldout_v3.csv'))]).drop_duplicates(['scene', 'method'])
    h = h[h.scene != 'v2_Path2_dense']
    mw = {k: m[m.method == x] for k, x in dict(S0='PIPs++_b2_256', S6='PIPs++_S6_b2_256', NCC='PTV_tuned_ncc_fd2', LK='PTV_tuned_lk_fd2').items()}
    vf = {k: v[v.method == x] for k, x in dict(S6='PIPs++_S6_b2_256', NCC='PTV_tuned_ncc_fd2').items()}
    ho = lambda x: float(h[h.method == x].ratio_h15.median())
    davis = {k: float(pd.read_csv(os.path.join(DAVIS, '%s_S32.csv' % k)).d_avg.mean()) for k in ('reference', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6')}
    return dict(n_var=int(m.scene.nunique()), mw=mw, vf=vf, ho=ho, davis=davis)


def save(fig, name, **kw):
    fig.savefig(os.path.join(OUT, name), dpi=200, facecolor='white', **kw)
    plt.close(fig)
    print('wrote', os.path.join(OUT, name))


def canvas(w_in, h_in, w_units, h_units, x0=0):
    """figure whose data units are 0.1 inch (so box sizes are easy to reason about)"""
    fig = plt.figure(figsize=(w_in, h_in))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(x0, x0 + w_units); ax.set_ylim(0, h_units); ax.axis('off')
    return fig, ax


def tbox(ax, x, y, w, lines, h=None, bold=1, lw=1.4, ec=tud.BLUE, ls='-', fs=7.6, align='left', fc=tud.WHITE, pitch=1.75):
    """outlined box with text lines; the first `bold` lines are bold. Returns (left, right, bottom, top, mid_y)."""
    h = h or len(lines) * pitch + 3.0
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=0.8', fc=fc, ec=ec, lw=lw, ls=ls, zorder=2))
    top = y + h / 2 + (len(lines) - 1) * pitch / 2
    for i, t in enumerate(lines):
        tx = x + 1.3 if align == 'left' else x + w / 2
        ax.text(tx, top - i * pitch, t, ha=align, va='center', fontsize=fs, zorder=3,
                fontweight='bold' if i < bold else 'normal', color=tud.BLUE if i < bold else tud.INK)
    return x, x + w, y, y + h, y + h / 2


def strategy_tree():
    """Fig. 3.2: what was trained from what; held-out ratio and DAVIS score in every box"""
    fig, ax = canvas(7.6, 5.4, 76, 54)
    R = results(); ho = R['ho']; dv = R['davis']; mw = R['mw']
    A = tbox(ax, 1, 25, 15.5, ['PointOdyssey', 'reference weights', '(Zheng et al. 2023)', 'DAVIS %.1f' % dv['reference']], bold=2, ec=tud.GREY_MID, lw=1.2)
    B = tbox(ax, 1, 4, 15.5, ['random', 'initialisation'], bold=2, ec=tud.GREY_MID, lw=1.2)
    S1 = tbox(ax, 21, 42, 17, ['S1  short-clip', 'fine-tuning', '%.2f   DAVIS %.1f' % (ho('PIPs++_ft3000_b2_256'), dv['S1'])], bold=2)
    S3 = tbox(ax, 21, 24, 17, ['S3  long clips', '(paper recipe)', '%.2f / %.2f long-term' % (ho('PIPs++_S3_b2_256'), ho('PIPs++_S3_r48_256')), 'DAVIS %.1f' % dv['S3']], bold=2)
    S5 = tbox(ax, 21, 4, 17, ['S5  from scratch', '%.2f   DAVIS %.1f' % (ho('PIPs++_S5_b2_256'), dv['S5'])], bold=1, ec=tud.GREY)
    S2 = tbox(ax, 42, 44, 17, ['S2  + data and', 'augmentation', '%.2f   DAVIS %.1f' % (ho('PIPs++_S2_b2_256'), dv['S2'])], bold=2)
    S4 = tbox(ax, 42, 31, 17, ['S4  rehearsal,', '50 % PointOdyssey', '%.2f   DAVIS %.1f' % (ho('PIPs++_S4_b2_256'), dv['S4'])], bold=2)
    S6 = tbox(ax, 42, 7, 17, ['S6  final model', '384 px, 12-frame clips', 'held-out %.2f' % ho('PIPs++_S6_b2_256'), 'DAVIS %.1f' % dv['S6'], 'moving water %.2f' % mw['S6'].ratio_h15.median(), '%d of %d variants' % ((mw['S6'].ratio_h15 < 0.8).sum(), R['n_var'])], bold=1, lw=2.6)
    tud.arrow(ax, A[1], A[4] + 3, S1[0], S1[4])
    tud.arrow(ax, A[1], A[4] - 1.5, S3[0], S3[4])
    tud.arrow(ax, B[1], B[4], S5[0], S5[4])
    tud.arrow(ax, S1[1], S1[4] + 2, S2[0], S2[4])
    tud.arrow(ax, S1[1], S1[4] - 2, S4[0], S4[4])
    tud.arrow(ax, S3[1], S3[4] - 2, S6[0], S6[4] + 2)
    ax.text(50.5, 27.5, 'selection rule: lowest\nheld-out median', ha='center', va='center', fontsize=6.8, style='italic', color=tud.GREY, linespacing=1.3)
    ax.plot([61.5, 61.5], [2, 52], color=tud.GREY_MID, lw=0.8, ls='--')
    ax.text(69, 52, 'reference tools\n(not retrained)', ha='center', va='top', fontsize=7, style='italic', color=tud.GREY)
    tbox(ax, 63, 33, 12, ['PTV NCC', 'held-out %.2f' % ho('PTV_tuned_ncc_fd2'), 'moving water', '%.2f' % mw['NCC'].ratio_h15.median()], bold=1, ec=tud.GREY_MID, lw=1.2, fs=7.0)
    tbox(ax, 63, 14, 12, ['PTV LK', 'held-out %.2f' % ho('PTV_tuned_lk_fd2'), 'moving water', '%.2f' % mw['LK'].ratio_h15.median()], bold=1, ec=tud.GREY_MID, lw=1.2, fs=7.0)
    save(fig, 'figP_strategy_tree.png')


if __name__ == '__main__':
    strategy_tree()
