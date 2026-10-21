"""rebuild_xy_seeds.py

Thesis section: see README.md
Inputs: see README.md
Outputs: see README.md

rebuild_xy_seeds.py -- rebuild the X,Y seed tracks in the real PointOdyssey format.

WHAT "X,Y" ACTUALLY IS
----------------------
Counted from the PointOdyssey sample tar: 7198 png, 7198 jpg, 4 npz, 2 mp4, 2 json, and
ZERO exr. PointOdyssey ships no EXR at all. Its X,Y lives in anno.npz as `trajs_2d`, shaped
(frames, seeds, 2) -- seeds carrying their (x, y) across frames.

So the dense position EXRs we made earlier are our own invention. They are arithmetically
correct (verified 0.00e+00 on all 4,515 files) but they are not the PointOdyssey format, and
they are not what PIPs++ consumes. This script produces the real thing.

THE DEFECT BEING FIXED: SEED DENSITY
------------------------------------
    real PointOdyssey   849 frames, 11,721 seeds, 99.4% valid on average
    ours (before)       301 frames,  1,024 seeds,  4.7% valid  -- only 188-602 alive per frame

With so few live points the flow cannot be seen. PointOdyssey reaches 99.4% because it exports
tracked MESH VERTICES (paper 3.5) -- points welded to geometry, which cannot wash away. We
cannot do that: the water is a Mantaflow liquid with use_mesh=True, RE-MESHED every frame, so
there is no stable vertex identity to export. Flow advection is the only route, and advected
points on a fixed camera MUST leave frame.

THE FIX: BATCH RESET, FOLLOWING HENDRICKX ET AL. 2025
-----------------------------------------------------
That paper (Eltner group) runs PIPs on alpine rock glaciers with the same fixed-camera setup:

    "If a regular grid is used, it is reset each time a new batch starts."

So: a regular grid, reset at the start of every batch. Not an invention -- the accepted method,
and what PIPs is designed for. Reset every `--stride` frames (8 for visualisation, 36 for the
training export that train.py consumes).

Blender convention (tutorial 6.1.2): R = X displacement (HORIZONTAL), G = Y displacement
(VERTICAL), current frame -> previous frame. V is negated on read for image rows.

HOW TO RUN IT YOURSELF (PyCharm)
--------------------------------
Interpreter: the `pips2` conda env. Right-click -> Run.
    --stride 8      frames between grid resets
    --grid 32       grid is grid x grid points per reset
    --scene NAME    one scene (default: all 15)
"""

import os
import sys
import time
import argparse
import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import flow_core as FC

OUT = os.path.join(HERE, 'out', 'xy_seeds')


def build(scene, stride=0, grid=48, device='mps', verbose=True):
    """stride=0 means: choose it from the scene's own speed (see below)."""
    t0 = time.time()
    d = FC.pick_device(device)
    vfs = FC.vector_files(scene)
    if not vfs:
        return None
    U, V, H, W = FC.read_flow(vfs[0])
    S = len(vfs)

    # [ADAPTIVE STRIDE] A fixed stride is wrong because the scenes differ 9x in speed.
    # Measured: Low5 runs at 99 px/frame and crosses a 512 px frame in ~5 frames, so with an
    # 8-frame reset its seeds were dead before the next batch was sown -- only 238 alive at the
    # worst frame. Path1 at 14 px/frame had 24,455. Setting the reset to about a third of the
    # seed lifetime keeps every scene populated.
    if stride == 0:
        speed = float(np.hypot(U, V).mean())
        lifetime = max(W, H) / max(speed, 1e-3)
        stride = int(np.clip(round(lifetime / 3.0), 2, 8))

    starts = list(range(0, S - 1, stride))
    per = grid * grid
    N = len(starts) * per

    trajs = np.zeros((S, N, 2), np.float32)
    valids = np.zeros((S, N), bool)

    # A regular grid, following Hendrickx et al., but JITTERED within each cell on every reset.
    # Without jitter the picture is a visible lattice rather than flow: most live seeds at any
    # moment are freshly born, so they all sit on identical grid coordinates and the eye reads a
    # fixed dot pattern. Jittering keeps the grid's even coverage while removing that artefact.
    gy, gx = np.mgrid[0:grid, 0:grid].astype(np.float32)
    cw, ch = (W - 1) / grid, (H - 1) / grid
    rng = np.random.default_rng(0)  # fixed seed: reruns are reproducible

    batches = []
    for bi, s0 in enumerate(starts):
        sl = slice(bi * per, (bi + 1) * per)
        bx = (gx.ravel() + rng.uniform(0.1, 0.9, per).astype(np.float32)) * cw
        by = (gy.ravel() + rng.uniform(0.1, 0.9, per).astype(np.float32)) * ch
        trajs[s0, sl, 0] = bx
        trajs[s0, sl, 1] = by
        valids[s0, sl] = True
        batches.append(
            dict(
                start=s0,
                sl=sl,
                x=torch.from_numpy(bx.copy()).to(d),
                y=torch.from_numpy(by.copy()).to(d),
                live=np.ones(per, bool),
            )
        )

    # frames are the OUTER loop: each flow field is read once and shared by every live batch
    for t in range(1, S):
        act = [b for b in batches if b['start'] < t and b['live'].any()]
        if not act:
            continue
        U, V, _, _ = FC.read_flow(vfs[t])
        Ut, Vt = FC.to_field(U, d), FC.to_field(V, d)
        for b in act:
            nx, ny = FC.step_forward(b['x'], b['y'], Ut, Vt, H, W)
            cx = nx.cpu().numpy()
            cy = ny.cpu().numpy()
            inb = (cx >= 0) & (cx <= W - 1) & (cy >= 0) & (cy <= H - 1)
            b['live'] &= inb
            px = np.where(b['live'], cx, trajs[t - 1, b['sl'], 0])
            py = np.where(b['live'], cy, trajs[t - 1, b['sl'], 1])
            trajs[t, b['sl'], 0] = px
            trajs[t, b['sl'], 1] = py
            valids[t, b['sl']] = b['live']
            b['x'] = torch.from_numpy(px.astype(np.float32)).to(d)
            b['y'] = torch.from_numpy(py.astype(np.float32)).to(d)
        del Ut, Vt

    od = os.path.join(OUT, scene)
    os.makedirs(od, exist_ok=True)
    # field names and dtypes chosen to match real PointOdyssey anno.npz
    np.savez(os.path.join(od, 'anno.npz'), trajs_2d=trajs, visibs=valids.copy(), valids=valids)

    per_frame = valids.sum(1)
    r = dict(
        scene=scene,
        S=S,
        N=N,
        H=H,
        W=W,
        stride=stride,
        live_min=int(per_frame.min()),
        live_med=int(np.median(per_frame)),
        live_max=int(per_frame.max()),
        pct=100.0 * valids.mean(),
        seconds=time.time() - t0,
        out=od,
    )
    if verbose:
        print(
            '  %-40s str%d %7d seeds | live/frame min %5d med %6d max %6d | %5.1f%% | %5.1fs'
            % (
                scene.replace('Elbersdorf_3ms_', '')[:40],
                stride,
                N,
                r['live_min'],
                r['live_med'],
                r['live_max'],
                r['pct'],
                r['seconds'],
            )
        )
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stride', type=int, default=0)  # 0 = adaptive, from scene speed
    ap.add_argument('--grid', type=int, default=48)
    ap.add_argument('--device', default='mps')
    ap.add_argument('--scene', default=None)
    a = ap.parse_args()
    scenes = [a.scene] if a.scene else FC.scene_list()
    os.makedirs(OUT, exist_ok=True)
    print(
        'Rebuilding X,Y seed tracks  |  grid %dx%d jittered  |  stride %s  |  device %s'
        % (a.grid, a.grid, 'adaptive' if a.stride == 0 else a.stride, a.device)
    )
    print('Method follows Hendrickx et al. 2025: "the grid is reset each time a new batch starts"')
    print('=' * 118)
    T0 = time.time()
    rows = [r for r in (build(s, a.stride, a.grid, a.device) for s in scenes) if r]
    print('=' * 118)
    worst = min(r['live_min'] for r in rows)
    print(
        '%d scenes in %.1f min   |   worst live-per-frame across all scenes: %d'
        % (len(rows), (time.time() - T0) / 60, worst)
    )
    print('(before this rebuild the same figure was 188)')


if __name__ == '__main__':
    main()
