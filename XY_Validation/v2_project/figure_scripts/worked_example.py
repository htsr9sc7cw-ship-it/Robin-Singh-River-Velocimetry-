"""Helper of the three worked-example figures (5.9, 5.10, 5.12): one frame, the true displacement and the tracks of
FlowVelo and PIPs++ on the same block of frames. Needs the pips2 interpreter (flow_core -> torch, OpenEXR; cv2).
"""
import csv
import glob
import os
import textwrap
import re
import sys

import matplotlib

matplotlib.use('Agg')
import cv2
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np

import tud_style as tud

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(PROJECT))


def data_root(scenes=None):
    """Vectors_and_Images of the project. The scene links inside it point to the drive under its old name; if they are
    broken, a temporary copy of the links with the current drive path is made (the project itself is never changed)."""
    import tempfile
    root = os.path.join(PROJECT, 'Vectors_and_Images')
    probe = os.path.join(root, 'v2_Path4_dense', 'images')
    if os.path.isdir(probe) and os.listdir(probe):
        return root
    here = os.path.dirname(PROJECT)                                  # .../XY_Validation
    tmp = os.path.join(tempfile.gettempdir(), 'XYV_links')
    for sc in os.listdir(root):
        d = os.path.join(root, sc)
        if not os.path.isdir(d):
            continue
        os.makedirs(os.path.join(tmp, sc), exist_ok=True)
        for name in os.listdir(d):
            t = os.path.join(d, name)
            if os.path.islink(t):
                tgt = os.readlink(t)
                tgt = here + tgt.split('XY_Validation', 1)[1] if 'XY_Validation' in tgt else tgt
                link = os.path.join(tmp, sc, name)
                if not os.path.lexists(link):
                    os.symlink(tgt, link)
    return tmp


DATA = data_root()
os.environ['XYV_DATA'] = DATA
import flow_core as fc  # noqa: E402

OUT = os.path.join(PROJECT, 'results', 'figures')
tud.apply()
COL = {'GT': '#000000', 'NCC': '#000000', 'LK': '#000000', 'PIPs': '#000000'}      # plain black lines; the panel titles say which method is drawn
HALO = [pe.withStroke(linewidth=2.2, foreground='#E6E6E6')]


def ptv_tracks(scene, mode, f0, nfr):
    """FlowVelo tracks that start at frame f0 and last at most nfr frames"""
    hits = glob.glob(os.path.join(PROJECT, 'out_ptv', scene, mode, 'Tracking_FT_*.txt'))
    if not hits:
        return None
    rows = [(int(r['frame'][:4]), int(float(r['id'])), float(r['x']) + 1, float(r['y']) + 1) for r in csv.DictReader(open(hits[0]), delimiter='\t')]
    first = {}
    for fr, i, x, y in rows:
        first[i] = min(first.get(i, 1e9), fr)
    out = {}
    for fr, i, x, y in rows:
        if first[i] == f0 and fr < f0 + nfr:
            out.setdefault(i, []).append((fr, x, y))
    return {i: np.array(sorted(v)) for i, v in out.items()}


def pips_tracks(scene, suffix, W, H):
    """PIPs++ trajectories of the first block, in native pixels"""
    pat = 'PIP_Run_%s_%s_48_*' % (scene, suffix) if suffix else 'PIP_Run_%s_48_256_*' % scene
    runs = [r for r in glob.glob(os.path.join(PROJECT, 'Outputs', pat)) if '_fseed_' not in r and os.path.isdir(os.path.join(r, 'frames', 'B0'))]
    run = sorted(runs, key=os.path.getmtime)[-1]
    fmt = np.loadtxt(os.path.join(run, 'frames', 'Out_Format.txt')).astype(int)
    b, h, w = fmt[1], fmt[4], fmt[5]
    P = np.stack([np.loadtxt(os.path.join(run, 'frames', 'B0', 'trajs_tensor_B0_F%d.txt' % k), delimiter=',') for k in range(b)])
    P[..., 0] *= W / w
    P[..., 1] *= H / h
    return P


def pips_label(suffix):
    if not suffix:
        return 'PIPs++ pre-trained'
    ft = re.match(r'ft(\d+)_', suffix)
    k, img = re.match(r'(?:ft\d+_)?r(\d+)_(\d+)', suffix).groups()
    return '%s PIPs++, restarted every %s frame%s' % ('Fine-tuned' if ft else 'Pre-trained', k, '' if k == '1' else 's')


def worked_example(scene, suffix, out_png, with_lk=False, nfr=15, first_letter='a', row_tag=None):
    """first_letter: panel letters run on from this one (a stacked second row continues with e-h, so no letter appears twice);
    row_tag: bold label at the left of the row, e.g. 'Top row: Path4, dense'"""
    L = lambda i: chr(ord(first_letter) + i)
    imgs = sorted(glob.glob(os.path.join(DATA, scene, 'images', '*.png')))
    by_f = {int(os.path.basename(p)[:4]): p for p in imgs}
    f0 = min(by_f); img = cv2.cvtColor(cv2.imread(by_f[f0], cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB); H, W = img.shape[:2]      # the frame as it was rendered, in colour
    vec = [p for p in fc.vector_files(scene) if p.endswith('Vector%04d.exr' % (f0 + 1))][0]
    U, V, _, _ = fc.read_flow(vec); fx, fy = -U, -V
    ncc = ptv_tracks(scene, 'tuned_ncc', f0, nfr); lk = ptv_tracks(scene, 'tuned_lk', f0, nfr) if with_lk else None
    pip = pips_tracks(scene, suffix, W, H)
    panels = ['GT', 'NCC'] + (['LK'] if lk else []) + ['PIPs']
    fig, axes = plt.subplots(1, len(panels), figsize=(7.4, 7.4 / len(panels) * H / W + 0.7))
    for ax in axes:
        ax.imshow(img); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        for s in ax.spines.values():
            s.set_color(tud.GREY)
    ys, xs = np.mgrid[16:H:32, 16:W:32]; m = np.hypot(fx[ys, xs], fy[ys, xs]) > 1e-3
    for ax, p in zip(axes, panels):
        if p == 'GT':
            ax.quiver(xs[m], ys[m], fx[ys, xs][m] * nfr, -fy[ys, xs][m] * nfr, color=COL['GT'], angles='xy', scale_units='xy', scale=1, width=0.004)
            ax.set_title('(%s) True movement\nover %d frames' % (L(0), nfr), fontsize=6.8, pad=4)
        elif p in ('NCC', 'LK'):
            T = ncc if p == 'NCC' else lk
            for t in T.values():
                ax.plot(t[:, 1], t[:, 2], '-', color=COL[p], lw=1.0, path_effects=HALO); ax.plot(t[0, 1], t[0, 2], '.', color=COL[p], ms=3)
            ax.set_title('(%s) PTV %s\n%d tracks' % (L(1) if p == 'NCC' else L(2), p, len(T)), fontsize=6.8, pad=4)
        else:
            sel = np.random.default_rng(0).choice(pip.shape[1], min(120, pip.shape[1]), replace=False)
            for j in sel:
                ax.plot(pip[:nfr, j, 0], pip[:nfr, j, 1], '-', color=COL['PIPs'], lw=0.9, path_effects=HALO); ax.plot(pip[0, j, 0], pip[0, j, 1], '.', color=COL['PIPs'], ms=3)
            ax.set_title('(%s) %s\n%d of %d paths' % (L(3) if lk else L(2), textwrap.fill(pips_label(suffix), 26), len(sel), pip.shape[1]), fontsize=6.8, pad=4)
    if row_tag:
        axes[0].set_ylabel(row_tag, fontsize=7, fontweight='bold', color=tud.BLUE, labelpad=4)
    fig.tight_layout()
    path = os.path.join(OUT, out_png)
    fig.savefig(path, dpi=200, facecolor='white', bbox_inches='tight', pad_inches=0.1); plt.close(fig)
    print('wrote', path)
