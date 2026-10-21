"""rasterise_gt.py

Thesis section: 4.4
Inputs: projected FLIP particles of one viewpoint
Outputs: per-pixel backward ground-truth field (EXR)

Step 2 of the dataset ground truth (v3.2 rule, FIXLOG V2-1 fix b' + AUD21-4): from the projected particles of
frame f build a SMOOTH forward field and derive the backward field of frame f+1 from it by forward
scattering, so that tracers (advected with the forward field, no inversion) and the evaluator
(which reads the backward field at the tracer's END position) see the same displacement.

    /opt/anaconda3/envs/pips2/bin/python rasterise_gt.py out/v2/<scene>

Per frame f (gt_particles/p####.npz: x, y, z = particle at f; bx, by = its displacement f -> f-1):
  1. surface layer per pixel: particles with depth <= nearest depth in that pixel + DZ (0.05 m);
  2. forward displacement F_f = -(bx, by) of those particles, averaged over a Gaussian pixel
     neighbourhood (sigma SIG px) -> forward/Forward####.exr (R = F_x, G = F_y, image coords, y down);
     water pixels without a particle within 6 px are filled from the nearest, beyond that 0 = not water;
  3. backward field of f+1 at every pixel q: the source p with p + F_f(p) = q is found by fixed-point
     iteration on the SMOOTH forward field (bilinear; well-posed because |grad F| << 1 after smoothing),
     B_{f+1}(q) = p - q; pixels whose source is not water / does not converge within 0.05 px are filled
     from the nearest converged pixel within 6 px, beyond that 0 = not water -> vector/Vector(f+1).exr in
     the ORIGINAL convention (R = backward x, G = -(backward y), B = 0, A = 1).
  v3.1 vs v3 (AUD21-4): the forward scatter folded on fast scenes (Low_1: 43 % empty destinations, RMSE 7 px);
  the Gaussian estimate is now kept at every pixel where the smoothed count is > 0.05 (no Voronoi copies),
  and sigma scales with the field: sigma = max(1.5 px, 0.08 * median |F|, radius holding ~30 surface particles); inversion damped (0.5, 60 iterations).
  Vector(f0).exr (first frame; the evaluator never scores k = 0) is written from the particles of f0
  directly (v2 rule) so every frame has a file.
Tested by known_answer_eval.py: tracer steps must reproduce the backward EXR at their end position.
"""

import os, sys, glob
import numpy as np, OpenEXR, Imath
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter

DZ, SIG, FILL = 0.05, 1.5, 6.0
out = sys.argv[1]
os.makedirs(os.path.join(out, 'vector'), exist_ok=True)
os.makedirs(os.path.join(out, 'forward'), exist_ok=True)
F = Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))


def write_exr(path, R, G, W, H):
    hdr = OpenEXR.Header(W, H)
    hdr['channels'] = {c: F for c in 'RGBA'}
    o = OpenEXR.OutputFile(path, hdr)
    o.writePixels(
        {
            'R': R.astype(np.float32).tobytes(),
            'G': G.astype(np.float32).tobytes(),
            'B': np.zeros_like(R, np.float32).tobytes(),
            'A': np.ones_like(R, np.float32).tobytes(),
        }
    )
    o.close()


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
    )


def fill(R, G, hit, W, H):
    hy, hx = np.nonzero(hit)
    gy, gx = np.nonzero(~hit)
    if len(hy) and len(gy):
        dist, idx = cKDTree(np.c_[hx, hy]).query(np.c_[gx, gy], distance_upper_bound=FILL)
        good = np.isfinite(dist)
        R[gy[good], gx[good]] = R[hy[idx[good]], hx[idx[good]]]
        G[gy[good], gx[good]] = G[hy[idx[good]], hx[idx[good]]]
        hit = hit.copy()
        hit[gy[good], gx[good]] = True
    return R, G, hit


files = sorted(glob.glob(os.path.join(out, 'gt_particles', 'p*.npz')))
for i, f in enumerate(files):
    fr = int(os.path.basename(f)[1:5])
    a = np.load(f)
    W = int(a['W'])
    H = int(a['H'])
    x1, y1, z1, bx, by = a['x'], a['y'], a['z'], a['bx'], a['by']
    ix = np.clip(x1.astype(int), 0, W - 1)
    iy = np.clip(y1.astype(int), 0, H - 1)
    # 1. surface layer
    znear = np.full((H, W), np.inf, np.float32)
    np.minimum.at(znear, (iy, ix), z1)
    surf = z1 <= znear[iy, ix] + DZ
    # 2. smooth forward field (v3.1: sigma scales with speed; estimate kept wherever the smoothed count is > 0.05)
    S = np.zeros((H, W), np.float64)
    Sx = np.zeros((H, W))
    Sy = np.zeros((H, W))
    np.add.at(S, (iy[surf], ix[surf]), 1.0)
    np.add.at(Sx, (iy[surf], ix[surf]), -bx[surf])
    np.add.at(Sy, (iy[surf], ix[surf]), -by[surf])
    hit = S > 0
    med_speed = float(np.median(np.hypot(bx[surf], by[surf]))) if surf.any() else 0.0
    dens = surf.sum() / max(hit.sum(), 1)  # surface particles per hit pixel
    sig = max(
        SIG, 0.08 * med_speed, np.sqrt(30.0 / (np.pi * max(dens * hit.mean(), 1e-6)))
    )  # >= ~30 particles per kernel (AUD21-4: sparse fast scenes were under-smoothed)
    Sg, Sxg, Syg = gaussian_filter(S, sig), gaussian_filter(Sx, sig), gaussian_filter(Sy, sig)
    est = Sg > 0.05
    Fx = np.where(est, Sxg / np.maximum(Sg, 1e-9), 0).astype(np.float32)
    Fy = np.where(est, Syg / np.maximum(Sg, 1e-9), 0).astype(np.float32)
    Fx, Fy, water = fill(Fx, Fy, est, W, H)
    Fx[~water] = 0
    Fy[~water] = 0
    write_exr(os.path.join(out, 'forward', 'Forward%04d.exr' % fr), Fx, Fy, W, H)
    if i == 0:  # first frame: v2 rule from the particles themselves (never scored)
        order = np.argsort(-z1)
        R = np.zeros((H, W), np.float32)
        G = np.zeros((H, W), np.float32)
        h0 = np.zeros((H, W), bool)
        R[iy[order], ix[order]] = bx[order]
        G[iy[order], ix[order]] = by[order]
        h0[iy[order], ix[order]] = True
        R, G, _ = fill(R, G, h0, W, H)
        write_exr(os.path.join(out, 'vector', 'Vector%04d.exr' % fr), R, -G, W, H)
    # 3. backward field of f+1 by inverting the smooth forward field at every pixel centre
    qy, qx = np.mgrid[0:H, 0:W].astype(np.float64)
    px_ = qx.copy()
    py_ = qy.copy()
    for _ in range(60):  # damped fixed point (0.5): converges where the plain iteration oscillates
        px_ = px_ + 0.5 * ((qx - bilinear(Fx, px_, py_)) - px_)
        py_ = py_ + 0.5 * ((qy - bilinear(Fy, px_, py_)) - py_)
    res = np.hypot(px_ + bilinear(Fx, px_, py_) - qx, py_ + bilinear(Fy, px_, py_) - qy)
    sx_ = np.clip(np.rint(px_).astype(int), 0, W - 1)
    sy_ = np.clip(np.rint(py_).astype(int), 0, H - 1)
    conv = (
        (res < 0.05) & (px_ >= 0) & (px_ <= W - 1) & (py_ >= 0) & (py_ <= H - 1) & water[sy_, sx_]
    )
    R = np.where(conv, px_ - qx, 0).astype(np.float32)
    G = np.where(conv, py_ - qy, 0).astype(np.float32)
    R, G, wb = fill(R, G, conv, W, H)
    # v3.2: ONE water mask per frame pair — Vector(f+1) is water exactly where Forward(f) is water (the region moves by
    # far less than a pixel per frame). Pixels of that mask without a converged source within 6 px (folds of the forward
    # map on fast, perspective-compressed views) get the locally-uniform fallback B(q) = -F_f(q); counted and printed.
    # (v3.1 filled the two fields from different hit sets, so tracers in the boundary band stood still while B != 0.)
    fb = water & ~wb
    R[fb] = -Fx[fb]
    G[fb] = -Fy[fb]
    wb = water.copy()
    R[~wb] = 0
    G[~wb] = 0
    write_exr(os.path.join(out, 'vector', 'Vector%04d.exr' % (fr + 1)), R, -G, W, H)
    stats = 'sigma %.1f  inv converged %.1f%%  fallback %.1f%%  water(f+1) %.1f%%' % (
        sig,
        100 * conv.mean(),
        100 * fb.mean(),
        100 * wb.mean(),
    )
    m = np.hypot(Fx, Fy)
    print(
        'Forward%04d -> Vector%04d: water %.1f%% |F| median %.2f p95 %.2f  surface particles %d/%d  %s'
        % (
            fr,
            fr + 1,
            100 * water.mean(),
            np.median(m[water]) if water.any() else 0,
            np.percentile(m[water], 95) if water.any() else 0,
            surf.sum(),
            len(x1),
            stats,
        ),
        flush=True,
    )
