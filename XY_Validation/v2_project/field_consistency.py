"""field_consistency.py

Thesis section: 3.5, 5.1
Inputs: tracer trajectories and ground-truth EXR of a variant
Outputs: one line per variant in results/FIELD_CONSISTENCY.txt

Whole-field consistency (AUD21-5 A-2): ALL tracer steps of a variant (not only whole-block, in-frame tracers as in
known_answer_eval.py) against the backward EXR at the END position, nearest pixel (the evaluator's sampling) and bilinear.
    XYV_DATA=<Vectors_and_Images> /opt/anaconda3/envs/pips2/bin/python field_consistency.py <scene> [<scene> ...]
Appends one line per variant to results/FIELD_CONSISTENCY.txt: n, median, RMSE, p99, frac>1, frac>3 for both samplings.
"""

import os, sys, datetime, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import flow_core as fc


def bil(F, x, y):
    H, W = F.shape
    x = np.clip(x, 0, W - 1.001)
    y = np.clip(y, 0, H - 1.001)
    x0 = np.floor(x).astype(int)
    y0 = np.floor(y).astype(int)
    fx = x - x0
    fy = y - y0
    return (
        F[y0, x0] * (1 - fx) * (1 - fy)
        + F[y0, x0 + 1] * fx * (1 - fy)
        + F[y0 + 1, x0] * (1 - fx) * fy
        + F[y0 + 1, x0 + 1] * fx * fy
    )


for scene in sys.argv[1:]:
    d = os.path.join(os.environ['XYV_DATA'], scene)
    z = np.load(os.path.join(d, 'tracers', 'trajs.npz'))
    T, val, frames = z['trajs_2d'], z['valids'], z['frames']
    vec = {int(os.path.basename(p)[6:10]): p for p in fc.vector_files(scene)}
    eb, en = [], []
    for i in range(1, len(frames)):
        U, V, H, W = fc.read_flow(vec[frames[i]])
        ok = val[i] & val[i - 1]
        x1, y1 = T[i, ok, 0], T[i, ok, 1]
        dx, dy = x1 - T[i - 1, ok, 0], y1 - T[i - 1, ok, 1]
        eb.append(np.hypot(dx + bil(U, x1, y1), dy + bil(V, x1, y1)))
        xi = np.clip(np.floor(x1).astype(int), 0, W - 1)
        yi = np.clip(np.floor(y1).astype(int), 0, H - 1)
        en.append(np.hypot(dx + U[yi, xi], dy + V[yi, xi]))
    out = []
    for n, e in (('bilinear', np.concatenate(eb)), ('nearest', np.concatenate(en))):
        out.append(
            '%s n %d median %.3f rmse %.3f p99 %.2f frac>1 %.4f frac>3 %.4f'
            % (
                n,
                len(e),
                np.median(e),
                np.sqrt((e**2).mean()),
                np.percentile(e, 99),
                (e > 1).mean(),
                (e > 3).mean(),
            )
        )
    line = 'FIELD %s: ' % scene + ' | '.join(out)
    print(line, flush=True)
    open(os.path.join(HERE, 'results', 'FIELD_CONSISTENCY.txt'), 'a').write(
        datetime.datetime.now().isoformat() + ' ' + line + '\n'
    )
