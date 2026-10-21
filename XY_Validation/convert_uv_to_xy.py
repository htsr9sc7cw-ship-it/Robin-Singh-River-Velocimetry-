"""convert_uv_to_xy.py

Thesis section: see README.md
Inputs: see README.md
Outputs: see README.md

convert_uv_to_xy.py — converts every Elbersdorf scene's Blender vector EXRs (U,V displacement)
                      into PointOdyssey-style (x,y) track files.

WHAT IT PRODUCES
----------------
For each scene, an `anno.npz` in exactly the format PIPs++ reads
(see pips2-master/datasets/pointodysseydataset.py:160-163):

    trajs_2d : (S, N, 2) float32   x,y pixel position of each point in each frame
    visibs   : (S, N)    float32   point visible in that frame
    valids   : (S, N)    float32   annotation valid in that frame

Run `show_xy_format.py` first if you want to SEE what that format looks like.

THE CONVENTION  (this is the part that must not be guessed — it was verified twice)
----------------------------------------------------------------------------------
The lab tutorial "2024-01-22 Tutorial Flussszene.pdf", section 6.1.2, states:

    "The Red and Green channel contain the X and Y displacement
     from the current frame to previous frame."

So R,G is the BACKWARD flow. I also verified this experimentally, independently of the
tutorial, by warping neighbouring frames on scene Low4 (the one scene whose appearance
genuinely advects) and testing all four sign combinations, averaged over frames 100/150/200:

    prev = (x + U, y - V)   residual 5.70   <-- WINNER   (baseline, no warp: 9.16)
    prev = (x + U, y + V)   residual 12.40

`y - V`, not `y + V`, also wins on Low0 and Path6. The V component MUST be negated, because
Blender's Y axis points UP while numpy image rows increase DOWNWARD. Getting this backwards
mirrors every trajectory vertically and looks completely plausible while being wrong.

    => backward flow in image coordinates:  B = (U, -V)
    => therefore, position in previous frame:  p_prev = p + B(p)

ON THE TUTORIAL'S OWN CONVERSION SCRIPT (section 7) — DELIBERATELY NOT COPIED
-----------------------------------------------------------------------------
The tutorial includes a 2017 script by Johannes Oswald (TU Munich) that converts to .FLO.
Its maths agrees with ours on the signs (it computes u=-R, v=+G), but it also applies two
scale factors that are never explained anywhere in the document:

    img[:,:,0] = R * (-1) * (0.5)      # u = -0.5 * R
    img[:,:,1] = (-G) * (-1) * (0.7)   # v = +0.7 * G

I tested those factors against this actual data (warp test, Low4, frames 100/150/200):

    no warp at all                     -> residual 8.54   (the baseline)
    su=0.5, sv=0.7  (the TUM script)   -> residual 6.22
    su=1.0, sv=1.0  (no scaling)       -> residual 5.65
    su=0.85, sv=0.85 (measured optimum)-> residual 5.25

Read this carefully, because an earlier version of this comment overstated it: 0.5/0.7 is
*better than not warping at all* -- it is not nonsense. It is simply WORSE THAN USING THE RAW
VALUES (6.22 vs 5.65). The measured optimum is also ISOTROPIC (0.85/0.85), whereas 0.5/0.7 is
anisotropic, which is what suggests those two numbers were tuned for a particular setup rather
than being a physical correction.

We therefore use scale 1.0: Blender's vector pass is already in pixels, and 1.0 beats 0.5/0.7
on this data. (The optimum sitting slightly below 1.0 is expected -- the water's *appearance*
advects a little less than its *geometry*, the finding of the earlier audit. Ground truth
should follow the geometry.)

Caveat worth stating: this comparison is strongest on Low4, the one scene whose appearance
genuinely advects. On scenes where the visible pattern barely moves, warping does not beat the
baseline at any scale, so those scenes cannot discriminate between scale factors at all.

That script also hard-codes 256x256 (this data is 512x512) and opens a binary file in text
mode. It is not reused here.

HONEST LIMITATION
-----------------
Optical flow carries NO occlusion information. There is no way to know from a flow field
whether a point became hidden. `visibs` is therefore set equal to `valids`; we do not
fabricate occlusion data. This is printed at runtime so it cannot be forgotten.

HOW TO RUN IT YOURSELF (PyCharm)
--------------------------------
1. Open this file in PyCharm.
2. Bottom-right, set the interpreter to the `pips2` conda env.
3. Right-click -> Run 'convert_uv_to_xy'.

Optional flags (Run -> Edit Configurations -> Parameters):
    --points 256     how many points to track (must be a perfect square; default 1024)
    --scene NAME     do a single scene instead of all 15
    --dense          also write per-pixel X,Y maps as EXR
    --flo            also write Middlebury .FLO files (the tutorial's format, corrected)
    --selftest       run the verification checks only, on one scene, and stop

Reads only from Vectors_and_Images/. Writes only into XY_Format/. Nothing is overwritten.
"""

import os
import sys
import glob
import csv
import argparse
import numpy as np
import OpenEXR as oexr
import Imath
import array as arr

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.environ.get('XYV_DATA') or os.path.join(HERE, 'Vectors_and_Images')
OUT_ROOT = os.environ.get('XY_FORMAT_OUT') or os.path.join(HERE, 'XY_Format')
FLOAT = Imath.PixelType(Imath.PixelType.FLOAT)

# Scale applied to the raw Blender vectors. 1.0 = use them as-is (see header for why).
SCALE_U = 1.0
SCALE_V = 1.0


# --------------------------------------------------------------------------- reading
def read_flow(path):
    """Read one vector EXR and return backward flow in IMAGE coordinates.

    Returns (fx, fy) each shaped (H, W), where moving a point p by (fx,fy) at p takes it to
    where that point was in the PREVIOUS frame.

    Two things here are easy to get wrong, and both silently corrupt everything downstream:
      * the flat channel buffer must be reshaped (H, W) -- NOT (W, H)
      * the V channel must be negated (Blender Y-up vs numpy rows going down)
    """
    f = oexr.InputFile(path)
    dw = f.header()['dataWindow']
    W = dw.max.x - dw.min.x + 1
    H = dw.max.y - dw.min.y + 1
    U = np.array(arr.array('f', f.channel('R', FLOAT)).tolist(), np.float32).reshape(H, W)
    V = np.array(arr.array('f', f.channel('G', FLOAT)).tolist(), np.float32).reshape(H, W)
    f.close()
    return U * SCALE_U, -V * SCALE_V, H, W


def scene_vector_files(scene):
    """All vector EXRs for a scene, EXPLICITLY SORTED.

    Sorting is not optional. An earlier audit of this project found that the tracking pipeline
    had been feeding frames to the model in raw os.listdir() order -- which on this filesystem
    is effectively random -- for months, invalidating every result. Never rely on listdir order.
    """
    return sorted(glob.glob(os.path.join(DATA_ROOT, scene, 'vector', '*.exr')))


def list_scenes():
    out = []
    for d in sorted(os.listdir(DATA_ROOT)):
        if os.path.isdir(os.path.join(DATA_ROOT, d, 'vector')):
            out.append(d)
    return out


# --------------------------------------------------------------------------- sampling
def bilinear(field, xs, ys):
    """Sample `field` (H,W) at floating-point positions (xs, ys). Note the [y, x] order."""
    H, W = field.shape
    x0 = np.clip(np.floor(xs).astype(np.int32), 0, W - 2)
    y0 = np.clip(np.floor(ys).astype(np.int32), 0, H - 2)
    x1, y1 = x0 + 1, y0 + 1
    wx = np.clip(xs - x0, 0.0, 1.0)
    wy = np.clip(ys - y0, 0.0, 1.0)
    return (
        field[y0, x0] * (1 - wx) * (1 - wy)
        + field[y0, x1] * wx * (1 - wy)
        + field[y1, x0] * (1 - wx) * wy
        + field[y1, x1] * wx * wy
    )


def step_forward(px, py, fx, fy, iters=6):
    """Advance points from frame t to frame t+1.

    We only have BACKWARD flow (frame t+1 -> t), so advancing forward means inverting it.
    Solve  q + B(q) = p  for q by fixed-point iteration, starting from q = p - B(p).

    [F3] This is GAUSS-SEIDEL, not Jacobi: qy is computed using the already-updated qx on the
    same sweep. That is deliberate -- it converges faster -- but an earlier docstring described
    it as Jacobi, which was simply wrong. Documenting what the code actually does.

    [F4] The iteration count was 3, which was NOT enough on fast scenes. Measured residual on
    Low1 (mean |flow| 47 px/frame), 1024 points, frame 150:

        iters=3   mean 0.30 px   p95 1.24 px   max 2.22 px   9.4% of points over 1 px
        iters=6   mean 0.007     p95 0.033     max 0.098     0.0%
        iters=10  mean 0.0001    p95 0.0003    max 0.0015    0.0%

    The old default passed the self-test only because that test gated on the MEAN, which hid
    the tail entirely. Default is now 6: it removes the tail on every scene tested, at
    negligible cost. This is a real accuracy fix, not a cosmetic one.
    """
    qx = px - bilinear(fx, px, py)
    qy = py - bilinear(fy, px, py)
    for _ in range(iters):
        qx = px - bilinear(fx, qx, qy)
        qy = py - bilinear(fy, qx, qy)
    return qx, qy


# --------------------------------------------------------------------------- conversion
def make_grid(n_points, H, W, margin=8):
    side = int(round(np.sqrt(n_points)))
    if side * side != n_points:
        raise ValueError('--points must be a perfect square, got %d' % n_points)
    ys, xs = np.meshgrid(
        np.linspace(margin, H - 1 - margin, side),
        np.linspace(margin, W - 1 - margin, side),
        indexing='ij',
    )
    return xs.ravel().astype(np.float32), ys.ravel().astype(np.float32)


def track_range(files, i0, i1, n_points, H, W, side_effects=None):
    """Seed a fresh grid at frame i0 and follow it to frame i1-1.

    Returns (trajs (T,N,2), valids (T,N), mean_disp, half_life).
    `half_life` = how many frames until fewer than half the points remain inside the frame.
    On flowing water this is short, and it is important to report it rather than hide it.
    """
    px, py = make_grid(n_points, H, W)
    N = px.size
    T = i1 - i0
    trajs = np.zeros((T, N, 2), np.float32)
    valids = np.zeros((T, N), np.float32)
    trajs[0, :, 0], trajs[0, :, 1] = px, py
    valids[0] = 1.0
    alive = np.ones(N, bool)
    disp_sum, disp_n, half = 0.0, 0, None

    for k in range(1, T):
        fx, fy, Ht, Wt = read_flow(files[i0 + k])
        if (Ht, Wt) != (H, W):
            raise RuntimeError('frame %d is %dx%d, expected %dx%d' % (i0 + k, Wt, Ht, W, H))
        nx, ny = step_forward(px, py, fx, fy)

        if alive.any():
            disp_sum += float(np.hypot(nx - px, ny - py)[alive].sum())
            disp_n += int(alive.sum())

        inb = (nx >= 0) & (nx <= W - 1) & (ny >= 0) & (ny <= H - 1)
        alive &= inb
        # points that left keep their last in-frame position, so the array stays well-formed
        px = np.where(alive, nx, px)
        py = np.where(alive, ny, py)
        trajs[k, :, 0], trajs[k, :, 1] = px, py
        valids[k] = alive.astype(np.float32)

        if half is None and alive.mean() < 0.5:
            half = k
        if side_effects is not None:
            side_effects(i0 + k, fx, fy, H, W)

    return trajs, valids, disp_sum / max(disp_n, 1), (half if half is not None else T)


def convert_scene(scene, n_points, want_dense=False, want_flo=False, clip=0):
    files = scene_vector_files(scene)
    if not files:
        return None
    S = len(files)
    _, _, H, W = read_flow(files[0])

    out_dir = os.path.join(OUT_ROOT, scene)
    os.makedirs(out_dir, exist_ok=True)
    if want_dense:
        os.makedirs(os.path.join(out_dir, 'dense_xy'), exist_ok=True)
    if want_flo:
        os.makedirs(os.path.join(out_dir, 'flo'), exist_ok=True)

    # NOTE: dense conversion is handled separately by convert_dense_scene() -- it must cover
    # EVERY frame including frame 0, whereas this tracking loop necessarily starts at frame 1.
    def extras(idx, fx, fy, Hh, Ww):
        if want_flo:
            write_flo(os.path.join(out_dir, 'flo', 'flow_%04d.flo' % idx), -fx, -fy)

    sfx = extras if want_flo else None

    if clip and clip > 1:
        # split into independent clips, each re-seeded -- this is how PointOdyssey stores
        # separate sequences, and it matches the 48-frame blocks the PIPs pipeline uses
        bounds = [(i, min(i + clip, S)) for i in range(0, S, clip)]
        bounds = [b for b in bounds if b[1] - b[0] >= 2]
        disps, halves, finals, n_clips = [], [], [], 0
        for ci, (i0, i1) in enumerate(bounds):
            tr, va, md, hl = track_range(files, i0, i1, n_points, H, W, sfx)
            cd = os.path.join(out_dir, 'clip_%03d' % ci)
            os.makedirs(cd, exist_ok=True)
            np.savez(os.path.join(cd, 'anno.npz'), trajs_2d=tr, visibs=va.copy(), valids=va)
            disps.append(md)
            halves.append(hl)
            finals.append(100.0 * float(va[-1].mean()))
            n_clips += 1
        return dict(
            scene=scene,
            S=S,
            N=n_points,
            H=H,
            W=W,
            clips=n_clips,
            clip_len=clip,
            mean_disp=float(np.mean(disps)),
            half_life=float(np.mean(halves)),
            pct_valid_final=float(np.mean(finals)),
            out=os.path.join(out_dir, 'clip_000', 'anno.npz'),
        )

    trajs, valids, mean_disp, half = track_range(files, 0, S, n_points, H, W, sfx)
    # No occlusion information exists in a flow field -- see header.
    np.savez(os.path.join(out_dir, 'anno.npz'), trajs_2d=trajs, visibs=valids.copy(), valids=valids)
    return dict(
        scene=scene,
        S=S,
        N=trajs.shape[1],
        H=H,
        W=W,
        clips=1,
        clip_len=S,
        pct_valid_final=100.0 * float(valids[-1].mean()),
        mean_disp=mean_disp,
        half_life=float(half),
        out=os.path.join(out_dir, 'anno.npz'),
    )


def write_dense(path, fx, fy, H, W):
    """Per-pixel absolute coordinates: X = x + fx, Y = y + fy (the 'RGB(X,Y)' reading).

    fx,fy are the BACKWARD flow already in image coordinates (V negated by read_flow), so
    (X,Y) is where this pixel's content was in the PREVIOUS frame -- a position, not a
    displacement. B is written as 0 so the file is a normal 3-channel RGB EXR.
    """
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    X = (xx + fx).astype(np.float32)
    Y = (yy + fy).astype(np.float32)
    Z = np.zeros((H, W), np.float32)
    hdr = oexr.Header(W, H)
    hdr['channels'] = {c: Imath.Channel(FLOAT) for c in ('R', 'G', 'B')}
    o = oexr.OutputFile(path, hdr)
    o.writePixels({'R': X.tobytes(), 'G': Y.tobytes(), 'B': Z.tobytes()})
    o.close()


def convert_dense_scene(scene):
    """Standalone per-file conversion: 301 vector EXRs in -> 301 X,Y EXRs out.

    Deliberately NOT driven from the trajectory loop. That loop starts at frame 1, which would
    silently skip frame 0 and produce 300 files instead of 301. Dense conversion is per-frame
    and independent of tracking, so it runs on its own over every file.
    """
    files = scene_vector_files(scene)
    if not files:
        return None
    out_dir = os.path.join(OUT_ROOT, scene, 'dense_xy')
    os.makedirs(out_dir, exist_ok=True)
    n = 0
    for f in files:  # EVERY file, including frame 0
        fx, fy, H, W = read_flow(f)
        stem = os.path.splitext(os.path.basename(f))[0]  # e.g. Vector0080
        num = ''.join(c for c in stem if c.isdigit())
        write_dense(os.path.join(out_dir, 'XY%s.exr' % num), fx, fy, H, W)
        n += 1
    return dict(scene=scene, n_in=len(files), n_out=n, out_dir=out_dir)


def write_flo(path, u, v):
    """Middlebury .FLO. Note 'wb' -- the tutorial's script used text mode, which is a bug."""
    h, w = u.shape
    with open(path, 'wb') as f:
        f.write(b'PIEH')
        np.array(w, np.int32).tofile(f)
        np.array(h, np.int32).tofile(f)
        tmp = np.zeros((h, w * 2), np.float32)
        tmp[:, 0::2] = u
        tmp[:, 1::2] = v
        tmp.astype(np.float32).tofile(f)


# --------------------------------------------------------------------------- verification
def selftest(scene, n_points=256):
    """Prove the conversion is sound instead of assuming it."""
    print('=' * 78)
    print('SELF-TEST on %s' % scene)
    print('=' * 78)
    files = scene_vector_files(scene)
    print('1. frame ordering')
    print('     first three files: %s' % [os.path.basename(f) for f in files[:3]])
    print('     last file        : %s' % os.path.basename(files[-1]))
    assert files == sorted(files), 'files are not sorted'
    print('     -> sorted, %d frames  OK' % len(files))

    fx, fy, H, W = read_flow(files[150])
    print(
        '2. flow field       : %dx%d, mean |flow| = %.2f px/frame'
        % (W, H, float(np.hypot(fx, fy).mean()))
    )

    print('3. round-trip test (does the fixed-point inversion actually invert?)')
    px, py = make_grid(n_points, H, W)
    ok = True
    # [F4] This used to gate on the MEAN only, which hid the tail completely: on Low1 the mean
    # was 0.30 px (passing) while 9.4% of points exceeded 1 px and the worst was 2.22 px.
    # Now the tail is reported and gated on.
    for t in (100, 150, 200):
        fxt, fyt, _, _ = read_flow(files[t])
        nx, ny = step_forward(px, py, fxt, fyt)  # forward t-1 -> t
        bx = nx + bilinear(fxt, nx, ny)  # exact backward step t -> t-1
        by = ny + bilinear(fyt, nx, ny)
        e = np.hypot(bx - px, by - py)
        mean_e, p95, mx = float(e.mean()), float(np.percentile(e, 95)), float(e.max())
        frac = 100.0 * float((e > 1.0).mean())
        bad = (mx >= 1.0) or (frac > 0.0)
        if bad:
            ok = False
        print(
            '     frame %3d: mean %.4f  p95 %.4f  MAX %.4f  %.1f%% over 1px   %s'
            % (t, mean_e, p95, mx, frac, 'HIGH' if bad else 'OK')
        )

    print('4. write + reload exactly the way PIPs++ does')
    r = convert_scene(scene, n_points)
    a = np.load(r['out'], allow_pickle=True)
    t2 = a['trajs_2d']
    assert t2.shape == (r['S'], r['N'], 2), 'bad shape %s' % (t2.shape,)
    assert t2.dtype == np.float32, 'bad dtype %s' % t2.dtype
    print(
        '     trajs_2d %s %s, visibs %s, valids %s  OK'
        % (t2.shape, t2.dtype, a['visibs'].shape, a['valids'].shape)
    )

    print('5. sanity')
    print('     mean per-frame displacement of tracked points = %.2f px' % r['mean_disp'])
    print('     points still inside the frame at the end      = %.1f %%' % r['pct_valid_final'])
    print()
    print('SELF-TEST %s' % ('PASSED' if ok else 'COMPLETED WITH WARNINGS (see round-trip)'))
    return ok


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--points', type=int, default=1024, help='perfect square; default 1024')
    ap.add_argument('--scene', default=None)
    ap.add_argument(
        '--clip',
        type=int,
        default=0,
        help='split into re-seeded clips of this many frames (e.g. 48 to match the '
        'PIPs blocks). 0 = one long sequence per scene (default).',
    )
    ap.add_argument('--dense', action='store_true')
    ap.add_argument('--flo', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    scenes = list_scenes()
    if not scenes:
        sys.exit('No scenes found under %s' % DATA_ROOT)

    if args.selftest:
        # [F4] the return value used to be discarded, so a FAILING self-test still exited 0
        passed = selftest(args.scene or scenes[0], min(args.points, 256))
        sys.exit(0 if passed else 1)

    todo = [args.scene] if args.scene else scenes
    os.makedirs(OUT_ROOT, exist_ok=True)

    print('Converting (U,V) displacement  ->  (x,y) tracks, PointOdyssey format')
    print('  scenes      : %d' % len(todo))
    print('  points/scene: %d' % args.points)
    print(
        '  scale       : U x%.2f, V x%.2f  (V negated: Blender Y-up -> image rows down)'
        % (SCALE_U, SCALE_V)
    )
    print(
        '  clips       : %s'
        % (
            'one %d-frame sequence per scene' % 301
            if not args.clip
            else 're-seeded every %d frames' % args.clip
        )
    )
    print('  NOTE: flow carries no occlusion info, so visibs = valids (not fabricated).')
    print()
    print('%-44s %5s %6s %9s %9s %10s' % ('scene', 'S', 'N', 'mean px/f', 'half-life', 'valid@end'))
    print('-' * 88)

    rows = []
    for s in todo:
        r = convert_scene(s, args.points, args.dense, args.flo, args.clip)
        if r is None:
            print('%-44s  (no vector files, skipped)' % s[:44])
            continue
        if args.dense:
            d = convert_dense_scene(s)  # every frame, including frame 0
            r['dense_files'] = d['n_out']
            assert d['n_out'] == d['n_in'], '%s: dense wrote %d files for %d inputs' % (
                s,
                d['n_out'],
                d['n_in'],
            )
        if args.flo:
            # [F12] .flo used to be written only from inside the tracking loop, which starts at
            # frame 1 -- so the first frame's .flo was silently missing. Written here instead,
            # over every frame.
            fd = os.path.join(OUT_ROOT, s, 'flo')
            os.makedirs(fd, exist_ok=True)
            for f in scene_vector_files(s):
                fx, fy, _, _ = read_flow(f)
                num = ''.join(c for c in os.path.basename(f) if c.isdigit())
                write_flo(os.path.join(fd, 'flow%s.flo' % num), -fx, -fy)
        rows.append(r)
        print(
            '%-44s %5d %6d %9.2f %8.0ff %9.1f%%'
            % (s[:44], r['S'], r['N'], r['mean_disp'], r['half_life'], r['pct_valid_final']),
            flush=True,
        )

    if rows:
        csv_path = os.path.join(OUT_ROOT, 'CONVERSION_SUMMARY.csv')
        cols = [
            'scene',
            'S',
            'N',
            'H',
            'W',
            'clips',
            'clip_len',
            'mean_disp',
            'half_life',
            'pct_valid_final',
            'out',
        ]
        with open(csv_path, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print('-' * 88)
        print('Wrote track files for %d scenes into %s' % (len(rows), OUT_ROOT))
        print('Summary: %s' % csv_path)
        print()
        print('READ THIS — "half-life" is how many frames until under half the points are still')
        print('inside the frame. On flowing water it is SHORT, because the water carries points')
        print('out of view. That is real, not a bug: unlike PointOdyssey (points on solid objects')
        print('that stay in frame), a river continuously flushes points out. If you need clips')
        print('where most points survive, re-run with e.g.  --clip 8  or  --clip 16.')


if __name__ == '__main__':
    main()
