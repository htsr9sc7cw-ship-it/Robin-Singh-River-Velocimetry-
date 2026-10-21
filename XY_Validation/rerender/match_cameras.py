"""match_cameras.py

Thesis section: 4.3
Inputs: rendered candidate cameras, original scene frames
Outputs: camera_to_scene.csv and SIFT evidence

R5: which camera produced which of the 15 original scenes?  Not recorded anywhere, so it is
measured.  Two steps:

  1. (pips2)    particle-projected GT at frame 80 from every candidate camera:
       /opt/anaconda3/envs/pips2/bin/python match_cameras.py render
     Candidates: the 8 fixed cameras + Camera.Path placed on each of Empty.001..Empty.007.
  2. (pips2)    compare each candidate's |flow| map with every original scene's |flow| map at
     frame 80 (lighting-independent, viewpoint-dependent) and print the best assignment:
       /opt/anaconda3/envs/pips2/bin/python match_cameras.py compare

Writes camera_to_scene.csv.  The re-baked simulation is not identical to the original one, so
the match is on the spatial pattern (normalised correlation of log-speed maps + water-mask IoU),
which depends on the viewpoint far more than on the exact flow values.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, 'out', 'camera_probe')
FRAME = 80

if len(sys.argv) > 1 and sys.argv[1] == 'render':
    # step 1 runs OUTSIDE Blender: for every candidate camera, the particle-projected GT at FRAME
    # (the Cycles Vector pass is zero on this build, audit D5 #6), then the rasterised EXR.
    import subprocess

    BLENDER = '/Applications/Blender.app/Contents/MacOS/Blender'
    BLEND = os.path.join(HERE, 'Basefile_a_TRACERS.blend')
    cands = [
        (c, None)
        for c in (
            'Camera.initial_high_angle',
            'Camera.initial_low_angle',
            'Camera.Low_1',
            'Camera.Low_1.001',
            'Camera.Low_1.002',
            'Camera.Low_1.003',
            'Camera.Low_2',
            'Camera.Overview',
        )
    ]
    cands += [('Camera.Path', 'Empty.%03d' % i) for i in range(1, 8)]
    os.makedirs(PROBE, exist_ok=True)
    for cam, target in cands:
        tag = (cam if target is None else cam + '@' + target).replace('.', '_')
        d = os.path.join(PROBE, tag)
        cmd = (
            [
                BLENDER,
                '--background',
                BLEND,
                '--python',
                os.path.join(HERE, 'gt_from_particles.py'),
                '--',
                '--camera',
                cam,
                '--frames',
                str(FRAME),
                str(FRAME),
                '--out',
                d,
                '--size',
            ]
            + (['1024', '512'] if cam == 'Camera.Overview' else ['512', '512'])
            + (['--path-target', target] if target else [])
        )
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(
            ['/opt/anaconda3/envs/pips2/bin/python', os.path.join(HERE, 'rasterise_gt.py'), d],
            stdout=subprocess.DEVNULL,
        )
        print(
            'PROBE',
            tag,
            os.path.exists(os.path.join(d, 'vector', 'Vector%04d.exr' % FRAME)),
            flush=True,
        )
    print('DONE probe')
else:
    import glob
    import csv
    import numpy as np

    sys.path.insert(0, os.path.dirname(HERE))
    import flow_core as fc

    def feat(U, V):
        m = np.hypot(U, V)
        water = m > 1e-4
        lg = np.log1p(m)
        return lg, water

    def score(fa, fb):
        (la, wa), (lb, wb) = fa, fb
        if la.shape != lb.shape:
            return (
                0.0,
                0.0,
            )  # different resolution (Overview is 1024x512) -> cannot be the same camera
        iou = (wa & wb).sum() / max((wa | wb).sum(), 1)
        both = wa & wb
        if both.sum() < 100:
            return iou, 0.0
        x = la[both] - la[both].mean()
        y = lb[both] - lb[both].mean()
        c = float((x * y).sum() / np.sqrt((x * x).sum() * (y * y).sum() + 1e-9))
        return iou, c

    orig = {}
    for s in fc.scene_list():
        p = [q for q in fc.vector_files(s) if q.endswith('Vector%04d.exr' % FRAME)]
        if p:
            U, V, _, _ = fc.read_flow(p[0])
            orig[s] = feat(U, V)
    cand = {}
    for d in sorted(glob.glob(os.path.join(PROBE, '*'))):
        p = glob.glob(os.path.join(d, 'vector', 'Vector*.exr'))
        if p:
            U, V, _, _ = fc.read_flow(p[0])
            cand[os.path.basename(d)] = feat(U, V)
    print('%-46s %-32s %6s %6s' % ('scene', 'best camera', 'IoU', 'corr'))
    rows = []
    for s, fs in orig.items():
        best = None
        for c, fcnd in cand.items():
            iou, corr = score(fs, fcnd)
            tot = iou + corr
            if best is None or tot > best[0]:
                best = (tot, c, iou, corr)
        ranked = sorted(
            ((score(fs, fcnd)[0] + score(fs, fcnd)[1], c) for c, fcnd in cand.items()), reverse=True
        )[:3]
        print(
            '%-46s %-32s %6.2f %6.2f   next: %s'
            % (
                s[15:],
                best[1],
                best[2],
                best[3],
                ', '.join('%s %.2f' % (c, t) for t, c in ranked[1:]),
            )
        )
        rows.append((s, best[1], round(best[2], 3), round(best[3], 3)))
    with open(os.path.join(HERE, 'camera_to_scene.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['scene', 'camera', 'water_iou', 'logspeed_corr'])
        w.writerows(rows)
    print('wrote camera_to_scene.csv')
