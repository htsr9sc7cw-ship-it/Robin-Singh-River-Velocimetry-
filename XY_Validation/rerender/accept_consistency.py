"""accept_consistency.py

Thesis section: see README.md
Inputs: see README.md
Outputs: see README.md

Data-consistency acceptance for dataset v2 (tracker-independent):
for every tracer alive at frame f, advect its position through the exported Vector pass to f+1
and read the image brightness there. If frames and EXRs are consistent (same field, same frame
alignment), the advected position lands on the tracer's blob (bright); a one-frame offset or a
wrong sign lands on plain water (dark). Reports the same for f-1 and f+2 as controls.

    /opt/anaconda3/envs/pips2/bin/python accept_consistency.py <out>
"""

import os, sys, glob, numpy as np, cv2, torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import flow_core as fc
import argparse

_ap = argparse.ArgumentParser()
_ap.add_argument('out')
_ap.add_argument('--tag', default='', help='tracer folder suffix, e.g. _dense (AUD10-4)')
_a = _ap.parse_args()
out = _a.out
TAG = _a.tag
dev = fc.pick_device('mps')
z = np.load(os.path.join(out, 'tracers' + TAG, 'trajs.npz'))
frames = [int(f) for f in z['frames']]
TR = z['trajs_2d']
imgs = {
    f: cv2.imread(os.path.join(out, 'images_tracers' + TAG, '%04d.png' % f), 0).astype(np.float32)
    for f in frames
}


def bright_at(img, x, y):
    ix = np.clip(np.round(x).astype(int), 0, img.shape[1] - 1)
    iy = np.clip(np.round(y).astype(int), 0, img.shape[0] - 1)
    return img[iy, ix]


res = {
    k: []
    for k in (
        'advected->f+1',
        'stay->f+1 (control)',
        'advected->f+2 (control)',
        'advected->f-1 (control)',
    )
}
for i, f in enumerate(frames[1:-2], 1):
    P = TR[i]
    ok = np.isfinite(P[:, 0])
    px = torch.tensor(P[ok, 0], device=dev)
    py = torch.tensor(P[ok, 1], device=dev)
    U, V, H, W = fc.read_flow(os.path.join(out, 'vector', 'Vector%04d.exr' % frames[i + 1]))
    qx, qy = fc.step_forward(px, py, fc.to_field(U, dev), fc.to_field(V, dev), H, W)
    qx = qx.cpu().numpy()
    qy = qy.cpu().numpy()
    inb = (qx > 2) & (qx < W - 2) & (qy > 2) & (qy < H - 2)
    res['advected->f+1'].append(bright_at(imgs[frames[i + 1]], qx[inb], qy[inb]))
    res['stay->f+1 (control)'].append(bright_at(imgs[frames[i + 1]], P[ok, 0][inb], P[ok, 1][inb]))
    res['advected->f+2 (control)'].append(bright_at(imgs[frames[i + 2]], qx[inb], qy[inb]))
    res['advected->f-1 (control)'].append(bright_at(imgs[frames[i - 1]], qx[inb], qy[inb]))
bg = np.median(np.concatenate([imgs[f].ravel() for f in frames[:3]]))
lines = ['CONSISTENCY %s (background median grey %.0f)' % (out, bg)]
for k, v in res.items():
    v = np.concatenate(v)
    lines.append(
        '  %-28s median grey %5.1f | fraction > bg+40: %.3f'
        % (k, np.median(v), (v > bg + 40).mean())
    )
ok = (np.concatenate(res['advected->f+1']) > bg + 40).mean() > 0.9 and (
    np.concatenate(res['stay->f+1 (control)']) > bg + 40
).mean() < 0.3
lines.append(
    'OVERALL: %s  (advected positions bright, stay-still positions dark)'
    % ('PASS' if ok else 'FAIL')
)
print('\n'.join(lines))
open(os.path.join(out, 'ACCEPT_CONSISTENCY.txt'), 'w').write('\n'.join(lines) + '\n')
