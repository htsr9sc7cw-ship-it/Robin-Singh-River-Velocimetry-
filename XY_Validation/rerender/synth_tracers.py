"""synth_tracers.py

Thesis section: see README.md
Inputs: see README.md
Outputs: see README.md

Composite sparse, persistent foam-like tracers onto surface-only renders, advected through the
scene's own ground-truth flow field, so their motion equals the exported Vector pass by
construction (the PointOdyssey relation between frames and annotations).

    /opt/anaconda3/envs/pips2/bin/python synth_tracers.py <out> [--density 0.0025] [--seed 0]

Reads  <out>/images/NNNN.png (surface only) and <out>/vector/VectorNNNN.exr (backward flow)
Writes <out>/images_tracers/NNNN.png and <out>/tracers/trajs.npz (frames x tracers x 2, valids)
       -- the latter IS an exact PointOdyssey-style annotation of the visible tracers.
Tracers: Gaussian blobs, radius 1.5-3.5 px, brightness 0.6-1.0 of white, persistent per tracer
(identity is ours, so persistence is exact); lifetime 40-120 frames; respawned uniformly over the
water when they die or leave the frame, keeping the density constant (Poisson-like seeding).
Advection (v3, FIXLOG V2-1 b'): tracers step by the SMOOTH FORWARD field forward/Forward####.exr of frame f-1,
sampled bilinearly at their position (no inversion); the backward Vector(f).exr the evaluator reads was scattered
from the same field (rasterise_gt.py), so the two agree by construction. If no forward/ folder exists the v2
inversion path (flow_core.step_forward) is used and reported.
"""

import os, sys, glob, argparse
import numpy as np, cv2, torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import flow_core as fc

ap = argparse.ArgumentParser()
ap.add_argument('out')
ap.add_argument('--density', type=float, default=0.0025, help='tracers per water pixel')
ap.add_argument('--seed', type=int, default=0)
ap.add_argument('--tag', default='', help='suffix for images_tracers<tag>/ and tracers<tag>/')
a = ap.parse_args()
dev = fc.pick_device('mps')
rng = np.random.default_rng(a.seed)
imgs = {int(os.path.basename(p)[:4]): p for p in glob.glob(os.path.join(a.out, 'images', '*.png'))}
vecs = {
    int(os.path.basename(p)[6:10]): p
    for p in glob.glob(os.path.join(a.out, 'vector', 'Vector*.exr'))
}
frames = sorted(f for f in imgs if f in vecs)
fwd = {
    int(os.path.basename(p)[7:11]): p
    for p in glob.glob(os.path.join(a.out, 'forward', 'Forward*.exr'))
}
if fwd and not all(f in fwd for f in frames[:-1]):
    raise SystemExit(
        'forward/ incomplete: %d of %d frames'
        % (sum(f in fwd for f in frames[:-1]), len(frames) - 1)
    )
print('ADVECTION', 'forward field (v3)' if fwd else 'inversion of backward field (v2)', flush=True)


def read_forward(path):
    import OpenEXR, Imath

    e = OpenEXR.InputFile(path)
    dw = e.header()['dataWindow']
    w = dw.max.x - dw.min.x + 1
    h = dw.max.y - dw.min.y + 1
    pt = Imath.PixelType(Imath.PixelType.FLOAT)
    return (
        np.frombuffer(e.channel('R', pt), np.float32).reshape(h, w),
        np.frombuffer(e.channel('G', pt), np.float32).reshape(h, w),
    )


def bilinear(Fld, x, y):
    Hh, Ww = Fld.shape
    x = np.clip(x, 0, Ww - 1.001)
    y = np.clip(y, 0, Hh - 1.001)
    x0 = np.floor(x).astype(int)
    y0 = np.floor(y).astype(int)
    fx = x - x0
    fy = y - y0
    return (
        Fld[y0, x0] * (1 - fx) * (1 - fy)
        + Fld[y0, x0 + 1] * fx * (1 - fy)
        + Fld[y0 + 1, x0] * (1 - fx) * fy
        + Fld[y0 + 1, x0 + 1] * fx * fy
    ).astype(np.float32)


IMD, TRD = 'images_tracers' + a.tag, 'tracers' + a.tag
os.makedirs(os.path.join(a.out, IMD), exist_ok=True)
os.makedirs(os.path.join(a.out, TRD), exist_ok=True)
U, V, H, W = fc.read_flow(vecs[frames[0]])
water0 = np.hypot(U, V) > 1e-4
N = int(a.density * water0.sum())
yy, xx = np.mgrid[0:H, 0:W]


def spawn(k, water):
    ys, xs = np.nonzero(water)
    i = rng.choice(len(ys), k)
    return xs[i] + rng.uniform(0, 1, k), ys[i] + rng.uniform(0, 1, k)


px, py = spawn(N, water0)
px = px.astype(np.float32)
py = py.astype(np.float32)
life = rng.integers(40, 121, N)
age = rng.integers(0, 80, N)
rad = rng.uniform(1.5, 3.5, N).astype(np.float32)
bright = rng.uniform(0.6, 1.0, N).astype(np.float32)
tid = np.arange(N)
next_id = N
trajs = {}
valid = {}
for fi, f in enumerate(frames):
    img = cv2.imread(imgs[f]).astype(np.float32)
    if fi > 0:
        U, V, H, W = fc.read_flow(vecs[f])  # backward flow at f (water mask / evaluator field)
        if fwd:
            Fx, Fy = read_forward(fwd[frames[fi - 1]])  # forward field of f-1, image coords
            dx = bilinear(Fx, px, py)
            dy = bilinear(Fy, px, py)
            px, py = (px + dx).astype(np.float32), (py + dy).astype(np.float32)
        else:
            qx, qy = fc.step_forward(
                torch.tensor(px, device=dev),
                torch.tensor(py, device=dev),
                fc.to_field(U, dev),
                fc.to_field(V, dev),
                H,
                W,
            )
            px, py = qx.cpu().numpy(), qy.cpu().numpy()
    water = np.hypot(U, V) > 1e-4
    age += 1
    ix = np.clip(px.astype(int), 0, W - 1)
    iy = np.clip(py.astype(int), 0, H - 1)
    dead = (age > life) | (px < 0) | (px >= W) | (py < 0) | (py >= H) | (~water[iy, ix])
    for k in np.nonzero(dead)[0]:
        trajs.setdefault(tid[k], {})
        valid.setdefault(tid[k], {})
    k = dead.sum()
    if k:
        nx, ny = spawn(k, water)
        px[dead] = nx
        py[dead] = ny
        age[dead] = 0
        life[dead] = rng.integers(40, 121, k)
        rad[dead] = rng.uniform(1.5, 3.5, k)
        bright[dead] = rng.uniform(0.6, 1.0, k)
        tid[dead] = np.arange(next_id, next_id + k)
        next_id += k
    # draw
    canvas = np.zeros((H, W), np.float32)
    for x, y, r, b in zip(px, py, rad, bright):
        x0, x1 = int(max(0, x - 4 * r)), int(min(W, x + 4 * r + 1))
        y0, y1 = int(max(0, y - 4 * r)), int(min(H, y + 4 * r + 1))
        if x1 <= x0 or y1 <= y0:
            continue
        g = b * np.exp(
            -((xx[y0:y1, x0:x1] + 0.5 - x) ** 2 + (yy[y0:y1, x0:x1] + 0.5 - y) ** 2)
            / (2 * (r / 2.0) ** 2)
        )
        canvas[y0:y1, x0:x1] = np.maximum(canvas[y0:y1, x0:x1], g)
    outimg = img * (1 - canvas[..., None]) + 255.0 * canvas[..., None] * np.array([0.92, 0.96, 1.0])
    cv2.imwrite(os.path.join(a.out, IMD, '%04d.png' % f), np.clip(outimg, 0, 255).astype(np.uint8))
    for k in range(N):
        trajs.setdefault(tid[k], {})[f] = (float(px[k]), float(py[k]))
        valid.setdefault(tid[k], {})[f] = True
    if fi % 50 == 0:
        print('TRACERS frame %d: %d alive' % (f, N), flush=True)
ids = sorted(trajs)
T = len(frames)
fidx = {f: i for i, f in enumerate(frames)}
arr = np.full((T, len(ids), 2), np.nan, np.float32)
val = np.zeros((T, len(ids)), bool)
for j, i in enumerate(ids):
    for f, (x, y) in trajs[i].items():
        arr[fidx[f], j] = (x, y)
        val[fidx[f], j] = True
np.savez_compressed(
    os.path.join(a.out, TRD, 'trajs.npz'),
    trajs_2d=arr,
    valids=val,
    visibs=val,
    frames=np.array(frames),
)
print(
    'TRACERS DONE: %d frames, %d tracers total (%d alive per frame), density %.4f'
    % (T, len(ids), N, a.density)
)
