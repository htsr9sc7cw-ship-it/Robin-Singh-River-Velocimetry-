"""demo.py: the whole study on one scene, start to finish, with real runs (no stored results are used).

    python run.py demo            about 8 min on a laptop GPU (Apple M-series), longer on a CPU
    python run.py demo --quick    controls, pre-trained PIPs++ and FlowVelo only (about 3 min)

Scene: v2_Path4_dense (Blender FLIP river, 512 x 512 px, 201 frames, exact ground truth from the simulated tracers).
Steps (the scripts of the thesis, unchanged):
  1  known_answer_eval.py      the exact tracks through the evaluator must give zero error          (Sect. 4.5)
  2  field_consistency.py      every tracer step against the ground-truth velocity field            (Sect. 4.4)
  3  PIP_Execution.py + PIP_Evaluation_gt.py    pre-trained PIPs++, 48-frame blocks, 256 px         (Sect. 3.2)
  4  derive_ptv_params.py + run_flowvelo_ptv.py FlowVelo NCC, parameters derived from the data       (Sect. 3.3)
  5  PIP_Execution_batch.py + PIP_Evaluation_gt.py  retrained PIPs++ (S6), fresh seeds every 2 frames (Sect. 3.4)
  6  compare_v2.py             one scorer for all trackers: ratio = RMSE / RMSE of a tracker that stands still (Sect. 3.5)
The table at the end puts every number next to the value printed in the thesis (Table 5.1 and the held-out table).
"""
import csv
import glob
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCENE = 'v2_Path4_dense'
V2 = os.path.join(HERE, 'v2_project')
WIN = os.name == 'nt'
QUICK = '--quick' in sys.argv


def conda_python(env):
    """interpreter of a conda environment (found through conda), or None"""
    key = {'pips2': 'PIPS2_PYTHON', 'flowvelo': 'FLOWVELO_PYTHON'}.get(env)
    if key and os.environ.get(key):
        return os.environ[key]
    try:
        r = subprocess.run(['conda', 'run', '-n', env, 'python', '-c', 'import sys;print(sys.executable)'], capture_output=True, text=True, shell=WIN)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip().splitlines()[-1]
    except OSError:
        pass
    return None


if not os.path.isdir(os.path.join(V2, 'Vectors_and_Images', SCENE, 'images')):
    sys.exit('The demo scene is not here. It is part of the full thesis kit (thesis_kit, about 2 GB, on the project drive); the e-mail package contains only the code.')
PY = {'base': sys.executable, 'pips2': conda_python('pips2'), 'flowvelo': conda_python('flowvelo')}
for env, py in PY.items():
    if not py:
        sys.exit('conda environment "%s" not found. Create the environments once with:  python run.py setup' % env)
ENV = dict(os.environ, XYV_DATA=os.path.join(V2, 'Vectors_and_Images'), PIPS2_PYTHON=PY['pips2'], BASE_PYTHON=PY['base'],
           FLOWVELO_PYTHON=PY['flowvelo'], PYTORCH_ENABLE_MPS_FALLBACK='1', PYTHONIOENCODING='utf-8', PIP_PROJECT=V2,
           PIP_FIX_SIGN='1', PIP_FIX_TRANSPOSE='1', PIP_MP='0', PIP_NO_PLOTS='1')


def run(title, env, script, args=(), cwd=V2, extra=None, quiet=True):
    """run one script of the thesis; show its last line"""
    t0 = time.time()
    e = dict(ENV, **(extra or {}))
    r = subprocess.run([PY[env], '-W', 'ignore', script] + list(args), cwd=cwd, env=e, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip().splitlines()
    last = next((l for l in reversed(out) if l.strip() and 'Warning' not in l and not l.startswith('  ')), '')
    print('  %-52s %s  (%.0f s)' % (title, 'ok' if r.returncode == 0 else 'FAILED', time.time() - t0), flush=True)
    if r.returncode != 0:
        print('\n'.join(out[-12:]))
        sys.exit('stopped: %s failed' % script)
    return r.stdout + r.stderr, last


def newest(pattern):
    hits = sorted(glob.glob(os.path.join(V2, pattern)), key=os.path.getmtime)
    return hits[-1] if hits else None


def reference():
    """the numbers printed in the thesis for this scene, read from the stored result files of the thesis"""
    ref = {}
    with open(os.path.join(V2, 'results', 'tables', 'T5_1_rmse_ratio_per_variant.csv')) as f:
        for row in csv.DictReader(f):
            if row['variant'] == 'Path4 dense':
                ref['PIPs++'] = float(row['PIPs++']); ref['PTV_tuned_ncc'] = float(row['PTV_tuned_ncc'])
    with open(os.path.join(V2, 'results', 's6_heldout_v3.csv')) as f:
        for row in csv.DictReader(f):
            if row['scene'] == SCENE and row['method'] == 'PIPs++_S6_b2_256':
                ref['S6_h15'] = float(row['ratio_h15']); ref['S6_speed'] = float(row['speed_ratio'])
    return ref


def main():
    t_all = time.time()
    print('Thesis demo on %s   (python: %s)' % (SCENE, sys.version.split()[0]))
    print('\n[1/6] controls')
    _, l = run('known-answer control', 'base', 'known_answer_eval.py', [SCENE]); print('       ', l[:150])
    _, l = run('field consistency', 'pips2', 'field_consistency.py', [SCENE]); print('       ', l[:150])
    print('\n[2/6] pre-trained PIPs++ (published weights)')
    pe = dict(PIP_N='256', PIP_SCENE=SCENE)
    run('PIPs++ tracking, 4 blocks of 48 frames', 'pips2', 'PIP_Execution.py', extra=pe)
    run('evaluation against the exact ground truth', 'pips2', 'PIP_Evaluation_gt.py', extra=pe)
    print('\n[3/6] FlowVelo (reference tool, NCC)')
    ptv = os.path.join(HERE, 'ptv')
    fe = dict(PTV_OUT=os.path.join(V2, 'out_ptv'))
    run('parameters derived from the measured flow speed', 'pips2', 'derive_ptv_params.py', cwd=ptv, extra=fe)
    run('FlowVelo NCC tracking and filtering', 'flowvelo', 'run_flowvelo_ptv.py', ['--mode', 'tuned_ncc', '--scene', SCENE], cwd=ptv, extra=fe)
    suffix = ''
    if not QUICK:
        print('\n[4/6] retrained PIPs++ (final model S6, fresh seeds every 2 frames)')
        be = dict(PIP_N='64', PIP_BATCH_LEN='16', PIP_SCENE=SCENE, PIP_BATCH_EVERY='2', PIP_IMG='256', PIP_RUN_SUFFIX='_S6_b2_256',
                  PIP_CKPT_DIR=os.path.join(HERE, 'finetune', 'ckpt_S6'))
        out, _ = run('S6 tracking', 'pips2', 'PIP_Execution_batch.py', extra=be)
        run_dir = [l for l in out.splitlines() if l.startswith('DONE ')][-1][5:].strip()
        run_dir = os.path.normpath(os.path.join(V2, run_dir))
        npts = open(os.path.join(run_dir, 'frames', 'Out_Format.txt')).read().split()[2]
        ev = os.path.join(V2, 'Outputs', 'PIP_Eval_%s_S6_b2_256' % SCENE)
        run('S6 evaluation', 'pips2', 'PIP_Evaluation_gt.py', extra=dict(PIP_SCENE=SCENE, PIP_N=npts, PIP_RUN_DIR=run_dir, PIP_EVAL_OUT=ev))
        open(os.path.join(ev, 'SOURCE_RUN.txt'), 'w').write(run_dir + '\n')
        suffix = 'S6_b2_256'
    print('\n[5/6] one scorer for all trackers')
    args = ['--ptv-eval', '--scenes', SCENE, '--ptv-root', 'out_ptv', '--modes', 'tuned_ncc', '--out', 'demo_result.csv']
    if suffix:
        args += ['--pips-suffixes', suffix]
    run('compare_v2.py', 'base', 'compare_v2.py', args)
    print('\n[6/6] result against the thesis')
    import pandas as pd
    d = pd.read_csv(os.path.join(V2, 'results', 'demo_result.csv'))
    d['ratio'] = d.rmse / d.rmse_stay
    ref = reference()
    rows = [('PIPs++ pre-trained', 'PIPs++', 'ratio', 'PIPs++', 0.01), ('FlowVelo NCC', 'PTV_tuned_ncc', 'ratio', 'PTV_tuned_ncc', 0.01)]
    if suffix:
        rows.append(('PIPs++ retrained (S6)', 'PIPs++_S6_b2_256', 'ratio_h15', 'S6_h15', 0.02))
    print('\n  %-24s %-10s %9s %9s   %s' % ('method', 'measure', 'this run', 'thesis', ''))
    ok = True
    for label, m, col, rk, tol in rows:
        v = float(d[d.method == m][col].iloc[0]); t = ref[rk]; good = abs(v - t) <= tol; ok &= good
        print('  %-24s %-10s %9.3f %9.3f   %s' % (label, col, v, t, 'PASS' if good else 'DIFFERENT (tolerance %.2f)' % tol))
    print('\n  ratio = RMSE of the tracker / RMSE of a tracker that stands still; below 0.8 counts as skill (thesis Sect. 3.5)')
    print('  result file: %s' % os.path.join(V2, 'results', 'demo_result.csv'))
    print('\n%s   (%.1f min)' % ('ALL NUMBERS MATCH THE THESIS' if ok else 'SOME NUMBERS DIFFER (small differences can come from the GPU / CPU used)', (time.time() - t_all) / 60))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
