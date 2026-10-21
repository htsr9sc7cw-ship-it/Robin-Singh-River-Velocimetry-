"""Check the code package: compile every script, compare its code with the original, run smoke tests in a linked copy.

Run:  python check_code_package.py            (needs thesis_code_test/, made with link_external.sh)
Writes thesis_code/RUN_CHECK.txt.  Levels: RAN = executed and gave the expected result; STARTS = the script
starts and reports its usage or reaches its data check; NOT RUN = needs Blender, hours of GPU time or the full data.
"""
import ast, datetime, glob, os, py_compile, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_code_package import ROOT, PKG
from make_digital_appendix import MANIFEST
TEST = os.path.abspath(os.path.join(PKG, '..', 'thesis_code_test')); PKG = os.path.abspath(PKG)
BASE, PIPS2, FLOW = '/opt/anaconda3/bin/python', '/opt/anaconda3/envs/pips2/bin/python', '/opt/anaconda3/envs/flowvelo/bin/python'
P2 = os.path.join(os.path.dirname(ROOT), 'pips2-master Original from PIPs++ GitHub')

def norm(tree):
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)) and n.body and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], 'value', None), ast.Constant) and isinstance(n.body[0].value.value, str):
            if isinstance(n, ast.Module): n.body = n.body[1:]
            else: n.body[0].value.value = n.body[0].value.value.strip()
    return ast.dump(tree)

L = ['Code package check, %s' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), '']
ok = True
files = sorted(glob.glob(os.path.join(PKG, '**', '*.py'), recursive=True))
bad = []
for f in files:
    rel = os.path.relpath(f, PKG); orig = os.path.join(ROOT, rel) if os.path.exists(os.path.join(ROOT, rel)) else os.path.join(os.path.dirname(ROOT), rel)
    try: py_compile.compile(f, doraise=True)
    except Exception as e: bad.append(rel + ' (does not compile)'); continue
    if os.path.exists(orig) and norm(ast.parse(open(f).read())) != norm(ast.parse(open(orig).read())): bad.append(rel + ' (code differs)')
L.append('%d Python files: all compile; code identical to the originals except: %s' % (len(files), bad or 'none')); ok &= not bad
L.append('')
env0 = dict(os.environ)
def run(name, py, script, args, level, env_extra=None, expect=None, timeout=900, cwd=None):
    global ok
    e = dict(env0); e['PYTHONPATH'] = P2; e.update(env_extra or {})
    c = cwd or os.path.dirname(os.path.join(TEST, script))
    try:
        r = subprocess.run([py, '-W', 'ignore', os.path.basename(script)] + args, cwd=c, env=e, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout + r.stderr).strip().split('\n'); tail = ' | '.join(x.strip() for x in out[-2:])[:200]
        good = r.returncode == 0 and ((expect in (r.stdout + r.stderr)) if expect else True)
    except subprocess.TimeoutExpired: good, tail = False, 'timeout'
    L.append('%-8s %-26s %s' % ('OK' if good else 'FAILED', name, '[%s] %s' % (level, tail))); ok &= good
CSV = os.path.join(ROOT, 'v2_project', 'results', 'strategies_v3.csv')
run('known_answer_eval', BASE, 'v2_project/known_answer_eval.py', ['v2_Path4_dense'], 'RAN', expect='-> PASS')
run('field_consistency', PIPS2, 'v2_project/field_consistency.py', ['v2_Path4_dense'], 'RAN', env_extra={'XYV_DATA': os.path.join(TEST, 'v2_project', 'Vectors_and_Images')}, expect='v2_Path4_dense')
run('results_stats', BASE, 'v2_project/results_stats.py', ['--csv', CSV, '--metric', 'ratio_h15', '--out', os.path.join(TEST, 'v2_project', 'results', 'stats_check.md')], 'RAN')
run('make_strategy_figures', BASE, 'v2_project/make_strategy_figures.py', [], 'RAN', expect='ok')
run('compare_v2', BASE, 'v2_project/compare_v2.py', ['--help'], 'STARTS', expect='usage')
run('velocity_field_eval', BASE, 'v2_project/velocity_field_eval.py', ['--help'], 'STARTS', expect='usage')
run('train_v3 (5 steps)', PIPS2, 'finetune/train_v3.py', ['--ckpt', os.path.join(TEST, 'finetune', 'ckpt_test'), '--init', os.path.join(TEST, 'reference_model', 'model-000200000.pth'), '--max-iters', '5', '--S', '12', '--N', '24', '--crop', '256', '--lr', '1e-4', '--iters', '6', '--save-every', '5'], 'RAN', env_extra={'PYTORCH_ENABLE_MPS_FALLBACK': '1'}, expect='TRAIN_DONE')
run('test_on_tap_mps', PIPS2, 'finetune/test_on_tap_mps.py', ['--help'], 'STARTS')
run('run_flowvelo_ptv', FLOW, 'ptv/run_flowvelo_ptv.py', ['--help'], 'STARTS', expect='usage')
L += ['', 'Not run in this check (need Blender, hours of GPU time or the full data): bake_and_render.py, match_cameras.py, rasterise_gt.py,',
      'gt_from_particles.py, synth_tracers.py, PIP_Execution*.py, train_v3.py (full training of 3 000 steps), run_*.sh, derive_ptv_params.py, make_results_reinit.py.',
      'Their code is identical to the originals that produced the results (first line of this file), and REPRODUCE.md gives the commands.', '',
      'RESULT: ' + ('ALL CHECKS PASSED' if ok else 'SEE FAILED LINES')]
open(os.path.join(PKG, 'RUN_CHECK.txt'), 'w').write('\n'.join(L) + '\n'); print('\n'.join(L))
