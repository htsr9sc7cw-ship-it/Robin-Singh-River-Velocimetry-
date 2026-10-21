"""flow_trials.py

Thesis section: see README.md
Inputs: see README.md
Outputs: see README.md

S1: low-resolution trial bakes to find a setting that sustains a current after the domain fills.

  $BLENDER --background Basefile_a_TRACERS.blend --python flow_trials.py -- --variant wind0.5
Variants: asis | wind0.5 | wind1.0 | wind1.5 | inflow1.0 | inflow2.0
Metrics (from particle POSITIONS, not the velocity attribute whose units proved ambiguous):
  - front speed during filling (y-min of the cloud, frames 2..40)  [sanity]
  - steady-state speed: displacement of the cloud's y-centroid of the *newest* particles is
    useless in steady state, so instead we measure the mean speed by the exact-match method:
    for a random sample of particles at frame f, the nearest neighbour at frame f+1 after
    shifting by k*V for k in {0, 0.04, 1} -- the k with smallest residual tells the units;
    plus we report |V| median so the two can be reconciled.
  - water depth under Camera.Low_1 (z-range of particles within 1 m of the camera's ground
    point) and particle count at frames 100, 150, 200.
Appends one row per variant/frame to veltest/flow_trials.csv.
"""

import bpy, os, sys, csv, shutil, argparse, time
import numpy as np
from mathutils.kdtree import KDTree

argv = sys.argv[sys.argv.index('--') + 1 :]
ap = argparse.ArgumentParser()
ap.add_argument('--variant', required=True)
ap.add_argument('--res', type=int, default=64)
ap.add_argument('--frames', nargs=2, type=int, default=[1, 200])
a = ap.parse_args(argv)
HERE = os.path.dirname(bpy.data.filepath)
s = bpy.context.scene
dom = bpy.data.objects['Liquid Domain']
d = [m for m in dom.modifiers if m.type == 'FLUID'][0].domain_settings
inflow = [m for m in bpy.data.objects['Manta.Inflow'].modifiers if m.type == 'FLUID'][
    0
].flow_settings
wind = bpy.data.objects['Wind']
v = a.variant
if v.startswith('wind'):
    wind.field.type = 'WIND'
    wind.field.strength = float(v[4:])
    wind.field.flow = 1.0
    wind.field.noise = 0.0
elif v.startswith('inflow'):
    inflow.velocity_coord = (0.0, -float(v[6:]), 0.0)
cache = '//veltest/cache_trial_' + v
p = bpy.path.abspath(cache)
shutil.rmtree(p, ignore_errors=True)
d.cache_directory = cache
d.resolution_max = a.res
d.cache_frame_start, d.cache_frame_end = a.frames
d.cache_type = 'MODULAR'
t = time.time()
with bpy.context.temp_override(
    object=dom, active_object=dom, selected_objects=[dom], scene=s, view_layer=s.view_layers[0]
):
    r = bpy.ops.fluid.bake_data()
print('TRIAL', v, 'bake', r, '%.0f s' % (time.time() - t), flush=True)


def get(fr):
    s.frame_set(fr)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = dom.evaluated_get(dg)
    ps = ev.particle_systems['Liquid']
    n = len(ps.particles)
    loc = np.empty(n * 3, np.float32)
    vel = np.empty(n * 3, np.float32)
    if n:
        ps.particles.foreach_get('location', loc)
        ps.particles.foreach_get('velocity', vel)
    return loc.reshape(-1, 3), vel.reshape(-1, 3)


cam = bpy.data.objects['Camera.Low_1']
ground = np.array(cam.location)
ground[2] = 0
rows = []
front = []
for fr in (2, 10, 20, 30, 40):
    P, _ = get(fr)
    front.append((fr, float(P[:, 1].min()) if len(P) else np.nan))
for fr in (100, 150, 200):
    if fr > a.frames[1]:
        continue
    P0, V0 = get(fr)
    P1, V1 = get(fr + 1)
    if len(P0) < 1000 or len(P1) < 1000:
        rows.append(dict(variant=v, frame=fr, n=len(P0), note='too few particles'))
        continue
    kd = KDTree(len(P1))
    [kd.insert(tuple(q), k) for k, q in enumerate(P1)]
    kd.balance()
    idx = np.random.default_rng(0).choice(len(P0), 3000, replace=False)
    res = {
        k: float(np.median([kd.find(tuple(P0[i] + k * V0[i]))[2] for i in idx]))
        for k in (0.0, 0.04, 1.0)
    }
    near = np.linalg.norm(P0[:, :2] - ground[:2], axis=1) < 1.5
    depth = float(P0[near, 2].max() - P0[near, 2].min()) if near.sum() > 50 else 0.0
    rows.append(
        dict(
            variant=v,
            frame=fr,
            n=len(P0),
            v_attr_median=float(np.median(np.linalg.norm(V0, axis=1))),
            mean_vy=float(V0[:, 1].mean()),
            nn_k0=res[0.0],
            nn_k004=res[0.04],
            nn_k1=res[1.0],
            depth_near_Low1=depth,
            front=str(front),
        )
    )
    print('TRIAL', v, rows[-1], flush=True)
out = os.path.join(HERE, 'veltest', 'flow_trials.csv')
new = not os.path.exists(out)
with open(out, 'a', newline='') as f:
    w = csv.DictWriter(
        f,
        fieldnames=[
            'variant',
            'frame',
            'n',
            'v_attr_median',
            'mean_vy',
            'nn_k0',
            'nn_k004',
            'nn_k1',
            'depth_near_Low1',
            'front',
            'note',
        ],
    )
    if new:
        w.writeheader()
    for r_ in rows:
        w.writerow(r_)
print('DONE trial', v, flush=True)
