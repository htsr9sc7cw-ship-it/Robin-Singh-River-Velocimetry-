"""lk_sweep_demo.py: Lucas-Kanade pyramid depth 2 to 5 on the demo scene, scored, next to the thesis values (Sect. 5.3, Fig. 5.6 text).

    python run.py lk_sweep          (about 4 min)

Runs ptv/run_lk_sweep.py (FlowVelo with the LK pyramid depth overridden, her source untouched), scores every depth with
compare_v2.py and prints the ratio next to the value stored in results/lk_sweep_v2.csv.
"""
import os
import subprocess
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.join(HERE, 'v2_project')
SCENE = 'v2_Path4_dense'
LEVELS = [2, 3, 4, 5]
sys.argv.append('--quick')            # reuse the interpreter lookup of demo.py without running its steps
import demo                           # noqa: E402

env = dict(demo.ENV, PTV_OUT=os.path.join(V2, 'out_ptv_sweep'))
print('LK sweep on %s' % SCENE)
r = subprocess.run([demo.PY['flowvelo'], '-W', 'ignore', 'run_lk_sweep.py', '--scene', SCENE, '--levels'] + [str(l) for l in LEVELS] + ['--templates', 'tuned'],
                   cwd=os.path.join(HERE, 'ptv'), env=env, capture_output=True, text=True)
print('  FlowVelo LK, pyramid depth %s: %s' % (LEVELS, 'ok' if r.returncode == 0 else 'FAILED'))
if r.returncode:
    sys.exit(r.stderr[-800:])
modes = ['lk_L%d_Ttuned' % l for l in LEVELS]
r = subprocess.run([demo.PY['base'], 'compare_v2.py', '--ptv-eval', '--scenes', SCENE, '--ptv-root', 'out_ptv_sweep', '--modes'] + modes + ['--no-pips', '--out', 'demo_lk_sweep.csv'],
                   cwd=V2, env=env, capture_output=True, text=True)
print('  scoring: %s' % ('ok' if r.returncode == 0 else 'FAILED'))
if r.returncode:
    sys.exit(r.stderr[-800:])
d = pd.read_csv(os.path.join(V2, 'results', 'demo_lk_sweep.csv')); d['ratio'] = d.rmse / d.rmse_stay
t = pd.read_csv(os.path.join(V2, 'results', 'lk_sweep_v2.csv')); t = t[t.scene == SCENE]; t['ratio'] = t.rmse / t.rmse_stay
print('\n  %-26s %9s %9s' % ('LK pyramid depth', 'this run', 'thesis'))
ok = True
for l in LEVELS:
    m = 'PTV_lk_L%d_Ttuned' % l
    a, b = float(d[d.method == m].ratio.iloc[0]), float(t[t.method == m].ratio.iloc[0]); ok &= abs(a - b) < 0.02
    print('  %-26s %9.3f %9.3f   %s' % ('maxLevel %d' % l, a, b, 'PASS' if abs(a - b) < 0.02 else 'DIFFERENT'))
print('\n  one more pyramid level brings LK from no skill to the level of NCC (thesis Sect. 5.3)')
print('ALL NUMBERS MATCH THE THESIS' if ok else 'SOME NUMBERS DIFFER')
