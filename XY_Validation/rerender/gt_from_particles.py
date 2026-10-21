"""gt_from_particles.py

Thesis section: see README.md
Inputs: see README.md
Outputs: see README.md

Ground truth for dataset v2: project the simulation's own particles through the render camera
and write the per-pixel BACKWARD flow in the original Vector-pass convention.

  step 1 (Blender): $BLENDER --background Basefile_a_TRACERS.blend --python gt_from_particles.py -- --camera Camera.Low_1 --frames 100 130 --out out/pilot_Low_1 [--path-target Empty.003]
      -> <out>/gt_particles/p####.npz  (x, y, z, bx, by per particle in view)
  step 2 (pips2):   python rasterise_gt.py out/pilot_Low_1   -> <out>/vector/Vector####.exr

Why not Cycles' Vector pass: on this Blender build the re-baked fluid mesh carries a 'velocity'
attribute that is identically zero (verified with cache_type ALL and MODULAR), so the surface
reports no motion. The rendered tracers are the FLIP particles, whose position and velocity per
frame are in the cache; their projected motion is exactly the motion of what is visible.

Convention (identical to the original Vector####.exr, verified in verify_xy_convention.py):
  R = backward flow x  = x(t-1) - x(t)     [image px, x to the right]
  G = -(y(t-1) - y(t))                     [Blender Y-up: image-row flow negated]
  B = 0, A = 1
Per pixel the particle CLOSEST to the camera wins (it is the one seen). Pixels on water with no
particle within 2 px are filled from the nearest particle; pixels with no particle within 6 px
are left 0 (not water). Velocity is Mantaflow's per-particle velocity [m/s]; displacement per
frame = v * time_scale (velocity attribute is per frame, measured); the backward flow is the projected displacement negated.
"""

import bpy, os, sys, argparse, array
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1 :]
ap = argparse.ArgumentParser()
ap.add_argument('--camera', required=True)
ap.add_argument('--frames', nargs=2, type=int, required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--path-target', default=None)
ap.add_argument('--size', nargs=2, type=int, default=[512, 512])
ap.add_argument(
    '--vscale',
    type=float,
    default=1.35,
    help='velocity-attribute calibration: front speed 0.281 m/frame vs attribute 0.205 (FIXLOG S4)',
)
a = ap.parse_args(argv)

scene = bpy.context.scene
dom = bpy.data.objects['Liquid Domain']
d = [m for m in dom.modifiers if m.type == 'FLUID'][0].domain_settings
cam = bpy.data.objects[a.camera]
if a.path_target:
    [c for c in cam.constraints if c.type == 'COPY_LOCATION'][0].target = bpy.data.objects[
        a.path_target
    ]
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = a.size
W, H = a.size
fps = scene.render.fps
dt = (
    d.time_scale
)  # particle velocity attribute is in metres PER FRAME (measured: 0.075 m/frame = 1.9 m/s at fps 25, matching the visual motion); not per second
os.makedirs(os.path.join(a.out, 'gt_particles'), exist_ok=True)


def project(P, cam_mat_inv, f_px, cx, cy):
    """world (N,3) -> pixel x (right), y (down), depth. Blender camera looks down -Z."""
    C = (cam_mat_inv @ np.c_[P, np.ones(len(P))].T).T[:, :3]
    z = -C[:, 2]
    ok = z > 1e-6
    x = cx + f_px * C[:, 0] / np.where(ok, z, 1)
    y = cy - f_px * C[:, 1] / np.where(ok, z, 1)
    return x, y, z, ok


for fr in range(a.frames[0], a.frames[1] + 1):
    scene.frame_set(fr)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = dom.evaluated_get(dg)
    camd = cam.data
    sensor = camd.sensor_width if camd.sensor_fit != 'VERTICAL' else camd.sensor_height
    f_px = camd.lens / sensor * max(W, H)
    cx, cy = W / 2.0, H / 2.0
    M = np.array(cam.matrix_world.inverted())
    Ps, Vs = [], []
    for ps in ev.particle_systems:
        n = len(ps.particles)
        if n == 0:
            continue
        loc = np.empty(n * 3, np.float32)
        vel = np.empty(n * 3, np.float32)
        ps.particles.foreach_get('location', loc)
        ps.particles.foreach_get('velocity', vel)
        Ps.append(loc.reshape(-1, 3))
        Vs.append(vel.reshape(-1, 3))
    P = np.concatenate(Ps).astype(np.float64)
    V = np.concatenate(Vs).astype(np.float64)
    x1, y1, z1, ok1 = project(P, M, f_px, cx, cy)
    x0, y0, z0, ok0 = project(
        P - V * dt * a.vscale, M, f_px, cx, cy
    )  # where it was one frame earlier (calibrated)
    ok = ok1 & ok0 & (x1 >= 0) & (x1 < W) & (y1 >= 0) & (y1 < H)
    x1, y1, z1, bx, by = x1[ok], y1[ok], z1[ok], (x0 - x1)[ok], (y0 - y1)[ok]
    np.savez_compressed(
        os.path.join(a.out, 'gt_particles', 'p%04d.npz' % fr),
        W=W,
        H=H,
        x=x1.astype(np.float32),
        y=y1.astype(np.float32),
        z=z1.astype(np.float32),
        bx=bx.astype(np.float32),
        by=by.astype(np.float32),
    )
    mag = np.hypot(bx, by)
    print(
        'GT frame %d: particles %d in view, |disp| median %.2f p95 %.2f px'
        % (fr, ok.sum(), np.median(mag), np.percentile(mag, 95)),
        flush=True,
    )
print('DONE gt')
