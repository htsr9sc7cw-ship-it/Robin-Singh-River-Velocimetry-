"""velocity_field_eval.py

Thesis section: 3.5, 5.7
Inputs: evaluation tables of a tracker
Outputs: bias, field RMSE and coverage per variant

Surface-velocity-field accuracy in hydrometry terms (plan: T5.15, pre-registration P-G12).
For every (scene, method) the tracked displacements of the evaluation tables (Outputs/*_Eval_<scene>_<suffix>/Tables/Trajs_F*.txt,
columns: id, x, y, dx, dy, ., dU, dV, . in the run's own pixel units; truth = (dx-dU, dy-dV) [compare_v2.metrics]) are binned on a
CELL x CELL native-px grid per frame; a cell estimate is the median of >= MINS valid sub-steps (k=0 of each block, border steps, frozen
PTV points and still water excluded exactly as in compare_v2).  Per variant:
  bias_pct     mean tracked speed over the field vs mean true speed, in % of the true mean
  rmse_px / rmse_pct  RMS of the cell vector error (px/frame, and % of the true mean speed)
  coverage     fraction of water cells (cells with a true-speed sample > 1e-3 px in the reference run) with an estimate
  dir_bias_deg median signed angle (tracked vs true) over cells
  frac_ok      fraction of water cells with |bias| <= 10 % and error <= 20 % of the local true speed  -> P-G12 target >= 0.80
usage: python velocity_field_eval.py --scenes ... --methods PIPs++_b2_256 PTV_tuned_ncc_fd2 ... [--cell 32] --out results/velocity_field_v3.csv
The velocity-area (discharge) reading of these numbers is in Sect. 6 of the thesis.  Known-answer check: --known <scene> uses the
GT-advected tracks (known_answer_eval.py output folder) -> bias ~ 0, rmse ~ evaluator floor.
"""

import os, sys, glob, re, csv, argparse, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--scenes', nargs='+', required=True)
ap.add_argument('--methods', nargs='+', required=True)
ap.add_argument('--cell', type=int, default=32)
ap.add_argument('--mins', type=int, default=3)
ap.add_argument('--out', default='results/velocity_field_v3.csv')
ap.add_argument(
    '--ref',
    default=None,
    help='method whose samples define the water cells (default: first method)',
)
a = ap.parse_args()


def eval_dir(scene, method):
    if method == 'PIPs++':
        ev = sorted(
            glob.glob(os.path.join(HERE, 'Outputs', 'PIP_Eval_%s_48_256_*' % scene)),
            key=os.path.getmtime,
        )
        return ev[-1] if ev else None
    pre = 'PIP_Eval_%s_%s' if method.startswith('PIPs++_') else 'PTV_Eval_%s_%s'
    d = os.path.join(HERE, 'Outputs', pre % (scene, method.split('_', 1)[1]))
    return d if os.path.isdir(d) else None


def run_of(ev, scene):
    f = os.path.join(ev, 'SOURCE_RUN.txt')
    r = open(f).read().strip() if os.path.exists(f) else None
    if r and not os.path.isdir(r):
        r = os.path.join(HERE, 'Outputs', os.path.basename(r))
    if r is None:
        c = sorted(
            [
                x
                for x in glob.glob(os.path.join(HERE, 'Outputs', 'PIP_Run_%s_48_256_*' % scene))
                if '_fseed_' not in x and os.path.isdir(os.path.join(x, 'frames', 'B0'))
            ],
            key=os.path.getmtime,
        )
        r = c[-1] if c else None
    return r


def frame_size(scene):
    import cv2

    p = sorted(glob.glob(os.path.join(HERE, 'Vectors_and_Images', scene, 'images', '*.png')))[0]
    h, w = cv2.imread(p, 0).shape
    return w, h


def samples(scene, method):
    """-> per frame list of (x, y, tdx, tdy, gdx, gdy) in native px, after the compare_v2 exclusions"""
    ev = eval_dir(scene, method)
    if ev is None:
        return None
    T = sorted(
        glob.glob(os.path.join(ev, 'Tables', 'Trajs_F*.txt')),
        key=lambda p: int(re.findall(r'F(\d+)', p)[0]),
    )
    A = np.stack([np.loadtxt(p, delimiter=',') for p in T])
    run = run_of(ev, scene)
    fmt = np.loadtxt(os.path.join(run, 'frames', 'Out_Format.txt')).astype(int)
    b, h, w = fmt[1], fmt[4], fmt[5]
    W, H = frame_size(scene)
    sx, sy = W / w, H / h
    keep = np.ones(A.shape[:2], bool)
    keep[0::b] = False
    px, py = A[..., 1], A[..., 2]
    onb = (px <= 0) | (px >= w - 1) | (py <= 0) | (py >= h - 1)
    onb_step = onb.copy()
    onb_step[1:] |= onb[:-1]
    keep &= ~onb_step
    m = os.path.join(run, 'frames', 'ptv_dropout_mask.npy')
    if os.path.exists(m):
        keep &= np.load(m)
    dx, dy, dU, dV = A[..., 3] * sx, A[..., 4] * sy, A[..., 6] * sx, A[..., 7] * sy
    tx, ty = dx - dU, dy - dV
    keep &= np.isfinite(dx) & np.isfinite(tx) & (np.hypot(tx, ty) > 1e-3)
    return dict(x=px * sx, y=py * sy, tdx=dx, tdy=dy, gdx=tx, gdy=ty, keep=keep, W=W, H=H)


def field(S, cell, mins):
    """cell medians over all frames -> dict cell -> (tracked vec, true vec, n)"""
    cx = (S['x'] // cell).astype(int)
    cy = (S['y'] // cell).astype(int)
    out = {}
    k = S['keep']
    keys = cy[k] * 10000 + cx[k]
    for key in np.unique(keys):
        sel = keys == key
        if sel.sum() < mins:
            continue
        out[key] = (
            np.median(S['tdx'][k][sel]),
            np.median(S['tdy'][k][sel]),
            np.median(S['gdx'][k][sel]),
            np.median(S['gdy'][k][sel]),
            int(sel.sum()),
        )
    return out


rows = []
ref = a.ref or a.methods[0]
for scene in a.scenes:
    R = samples(scene, ref)
    if R is None:
        print('no reference run', scene, ref)
        continue
    water = set(field(R, a.cell, 1).keys())
    for method in a.methods:
        S = samples(scene, method)
        if S is None:
            print('missing', scene, method)
            continue
        F = field(S, a.cell, a.mins)
        cells = [F[c] for c in F if c in water]
        if not cells:
            rows.append(dict(scene=scene, method=method, n_cells=0, coverage=0.0))
            continue
        C = np.array(cells)
        t = C[:, :2]
        g = C[:, 2:4]
        gs = np.hypot(*g.T)
        ts = np.hypot(*t.T)
        err = np.hypot(*(t - g).T)
        ang = np.degrees(np.arctan2(t[:, 1], t[:, 0]) - np.arctan2(g[:, 1], g[:, 0]))
        ang = (ang + 180) % 360 - 180
        ok = (np.abs(ts - gs) <= 0.10 * gs) & (err <= 0.20 * gs)
        rows.append(
            dict(
                scene=scene,
                method=method,
                n_cells=len(cells),
                coverage=round(len(cells) / len(water), 3),
                true_mean_px=round(gs.mean(), 3),
                bias_pct=round(100 * (ts.mean() - gs.mean()) / gs.mean(), 2),
                rmse_px=round(float(np.sqrt((err**2).mean())), 3),
                rmse_pct=round(100 * float(np.sqrt((err**2).mean())) / gs.mean(), 1),
                dir_bias_deg=round(float(np.median(ang)), 2),
                dir_agree=round(float((np.abs(ang) < 45).mean()), 3),
                frac_ok=round(float(ok.mean() * len(cells) / len(water)), 3),
            )
        )
        print(scene, method, rows[-1])
os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
with open(a.out, 'w', newline='') as f:
    keys = sorted({k for r in rows for k in r}, key=lambda k: (k not in ('scene', 'method'), k))
    w = csv.DictWriter(f, fieldnames=keys)
    w.writeheader()
    w.writerows(rows)
print('wrote', a.out, len(rows), 'rows')
