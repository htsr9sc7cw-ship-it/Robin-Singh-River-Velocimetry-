"""rasterise_demo.py: exact ground truth from the simulated particles, rebuilt and compared with the ground truth of the thesis (Sect. 4.4).

    python run.py rasterise_gt        (about 6 min)

Runs rerender/rasterise_gt.py on the particles of the demo scene (201 frames, 300 000 surface particles per frame): every frame gives a
smooth forward field and from it the backward field Vector####.exr. The new files are then compared pixel by pixel with the
Vector####.exr files that every result of the thesis is scored against.
"""
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv.append('--quick')
import demo  # noqa: E402  (interpreter lookup)

scene_out = os.path.join('out', 'v2', 'v2_Path4')
print('rasterising the particles of v2_Path4 ...', flush=True)
r = subprocess.run([demo.PY['pips2'], '-W', 'ignore', 'rasterise_gt.py', scene_out], cwd=os.path.join(HERE, 'rerender'), env=demo.ENV, capture_output=True, text=True)
if r.returncode:
    sys.exit(r.stderr[-800:])
print('  ' + [l for l in r.stdout.splitlines() if l.startswith('Forward')][-1][:120])
sys.path.insert(0, HERE)
os.environ['XYV_DATA'] = os.path.join(HERE, 'v2_project', 'Vectors_and_Images')
import flow_core as fc  # noqa: E402

new = sorted(os.listdir(os.path.join(HERE, 'rerender', scene_out, 'vector')))
worst, n = 0.0, 0
for f in new:
    if not f.endswith('.exr'):
        continue
    a = fc.read_flow(os.path.join(HERE, 'rerender', scene_out, 'vector', f))[:2]
    b = fc.read_flow(os.path.join(HERE, 'v2_project', 'Vectors_and_Images', 'v2_Path4_dense', 'vector', f))[:2]
    worst = max(worst, max(float(np.abs(a[0] - b[0]).max()), float(np.abs(a[1] - b[1]).max()))); n += 1
print('\n  %d ground-truth frames rebuilt from the particles; largest difference to the ground truth of the thesis: %.2e px' % (n, worst))
print('IDENTICAL TO THE GROUND TRUTH OF THE THESIS' if worst < 1e-3 else 'DIFFERENT (check the rasterise_gt.py version)')
sys.exit(0 if worst < 1e-3 else 1)
