"""Figure 5.17  Surface-velocity field on Path4 dense (moving water, 32-px cells): ground truth, S6 and NCC.
Cell medians of at least 3 sub-steps, built exactly as in velocity_field_eval.py (same functions).
Output: results/figures/figN_velocity_field_maps.png
Run with the pips2 interpreter:  /opt/anaconda3/envs/pips2/bin/python fig_5_17_velocity_field_maps.py"""
import glob
import os
import re

import matplotlib

matplotlib.use('Agg')
import cv2
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

import tud_style as tud
from worked_example import DATA  # repoints the scene links if the drive was renamed

tud.apply()
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'results', 'figures')
SCENE, CELL, MINS = 'v2_Path4_surfmove_dense', 32, 3


def eval_dir(scene, method):
    pre = 'PIP_Eval_%s_%s' if method.startswith('PIPs++_') else 'PTV_Eval_%s_%s'
    d = os.path.join(PROJECT, 'Outputs', pre % (scene, method.split('_', 1)[1]))
    return d if os.path.isdir(d) else None


def run_of(ev, scene):
    f = os.path.join(ev, 'SOURCE_RUN.txt')
    r = open(f).read().strip() if os.path.exists(f) else None
    if r and not os.path.isdir(r):
        r = os.path.join(PROJECT, 'Outputs', os.path.basename(r))
    return r


def samples(scene, method):
    """per tracked step: position, tracked and true displacement in native px (after the compare_v2 exclusions)"""
    ev = eval_dir(scene, method)
    T = sorted(glob.glob(os.path.join(ev, 'Tables', 'Trajs_F*.txt')), key=lambda p: int(re.findall(r'F(\d+)', p)[0]))
    A = np.stack([np.loadtxt(p, delimiter=',') for p in T]); run = run_of(ev, scene)
    fmt = np.loadtxt(os.path.join(run, 'frames', 'Out_Format.txt')).astype(int); b, h, w = fmt[1], fmt[4], fmt[5]
    p0 = sorted(glob.glob(os.path.join(DATA, scene, 'images', '*.png')))[0]
    H, W = cv2.imread(p0, 0).shape; sx, sy = W / w, H / h
    keep = np.ones(A.shape[:2], bool); keep[0::b] = False
    px, py = A[..., 1], A[..., 2]
    onb = (px <= 0) | (px >= w - 1) | (py <= 0) | (py >= h - 1); step = onb.copy(); step[1:] |= onb[:-1]; keep &= ~step
    m = os.path.join(run, 'frames', 'ptv_dropout_mask.npy')
    if os.path.exists(m):
        keep &= np.load(m)
    dx, dy, dU, dV = A[..., 3] * sx, A[..., 4] * sy, A[..., 6] * sx, A[..., 7] * sy
    tx, ty = dx - dU, dy - dV
    keep &= np.isfinite(dx) & np.isfinite(tx) & (np.hypot(tx, ty) > 1e-3)
    return dict(x=px * sx, y=py * sy, tdx=dx, tdy=dy, gdx=tx, gdy=ty, keep=keep, W=W, H=H, img=p0)


def field(S, cell, mins):
    """cell medians over all frames: cell -> (tracked dx, dy, true dx, dy, n)"""
    cx = (S['x'] // cell).astype(int); cy = (S['y'] // cell).astype(int); k = S['keep']; keys = cy[k] * 10000 + cx[k]; out = {}
    for key in np.unique(keys):
        sel = keys == key
        if sel.sum() >= mins:
            out[key] = tuple(np.median(S[c][k][sel]) for c in ('tdx', 'tdy', 'gdx', 'gdy')) + (int(sel.sum()),)
    return out


S6 = samples(SCENE, 'PIPs++_S6_b2_256'); NCC = samples(SCENE, 'PTV_tuned_ncc_fd2')
water = set(field(S6, CELL, 1).keys())                              # the water cells are those the reference run reaches
F6, FN = field(S6, CELL, MINS), field(NCC, CELL, MINS)
panels = [('True movement', {c: F6[c] for c in F6 if c in water}, 'gt'),
          ('PIPs++ retrained S6', {c: F6[c] for c in F6 if c in water}, 'trk'),
          ('PTV NCC', {c: FN[c] for c in FN if c in water}, 'trk')]
img = cv2.imread(S6['img'], 0)
fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.9))
sm = None
for ax, (title, F, kind) in zip(axes, panels):
    ax.imshow(img, cmap='gray', vmin=0, vmax=255, alpha=0.55); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    xs = np.array([(c % 10000 + 0.5) * CELL for c in F]); ys = np.array([(c // 10000 + 0.5) * CELL for c in F])
    u = np.array([F[c][0 if kind == 'trk' else 2] for c in F]); v = np.array([F[c][1 if kind == 'trk' else 3] for c in F])
    q = ax.quiver(xs, ys, u, v, np.hypot(u, v), angles='xy', scale_units='xy', scale=0.55, width=0.007, cmap=LinearSegmentedColormap.from_list('tudspeed', [tud.BLUE_LIGHT, tud.BLUE]), clim=(0, 40))
    sm = q
    ax.set_title(title, fontsize=8)
    for s in ax.spines.values():
        s.set_color(tud.BLUE)
cb = fig.colorbar(sm, ax=axes, fraction=0.025, pad=0.02); cb.set_label('px / frame', fontsize=8); cb.outline.set_visible(False)
path = os.path.join(OUT, 'figN_velocity_field_maps.png')
fig.savefig(path, dpi=200, facecolor='white', bbox_inches='tight', pad_inches=0.1); plt.close(fig); print('wrote', path)
