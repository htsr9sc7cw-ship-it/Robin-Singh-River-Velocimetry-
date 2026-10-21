"""Build the digital appendix: cleaned copies of the thesis scripts (originals are never modified).

Run:  python make_digital_appendix.py            (from thesis/digital_appendix)
For every script: add a uniform header to the module docstring (purpose, thesis section, inputs, outputs),
format with black (line length 100), and copy it to scripts/.  The AST of the code is not changed, which
verify_digital_appendix.py proves.  Registers, logs and REPRODUCE.md are copied next to the scripts.
"""
import ast, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))          # XY_Validation
PY = sys.executable

MANIFEST = [
    # path, thesis section, inputs, outputs
    ('rerender/bake_and_render.py', '4.2, 4.3', 'Blender file with the fluid scene, camera name, frame range', 'fluid cache, rendered frames, motion-vector pass'),
    ('rerender/match_cameras.py', '4.3', 'rendered candidate cameras, original scene frames', 'camera_to_scene.csv and SIFT evidence'),
    ('rerender/rasterise_gt.py', '4.4', 'projected FLIP particles of one viewpoint', 'per-pixel backward ground-truth field (EXR)'),
    ('v2_project/known_answer_eval.py', '3.5, 5.1', 'tracers/trajs.npz of a variant, ground-truth field', 'known-answer verdict (PASS, PASS_FLOOR, FAIL) per variant'),
    ('v2_project/field_consistency.py', '3.5, 5.1', 'tracer trajectories and ground-truth EXR of a variant', 'one line per variant in results/FIELD_CONSISTENCY.txt'),
    ('v2_project/PIP_Execution_batch.py', '3.5 (mode D4)', 'frames of a variant, PIPs++ checkpoint', 'PIPs++ run folder with tracks and dropout mask'),
    ('v2_project/PIP_Evaluation_gt.py', '3.5', 'tracker run folder in the PIPs++ layout, ground-truth field', 'per-step tables Trajs_F*.txt and evaluation summary'),
    ('ptv/derive_ptv_params.py', '3.3', 'frames and ground-truth fields of every variant', 'ptv_params.csv'),
    ('ptv/run_flowvelo_ptv.py', '3.3', 'frames, parameter file, FlowVeloTool source', 'FlowVelo tracks, filtered tracks and filter counts'),
    ('ptv/run_lk_sweep.py', '3.3, 5.3.2', 'a variant, parameter file', 'LK tracks for pyramid depths 2 to 5'),
    ('ptv/corrected_cascade.py', '5.3.1', 'FlowVelo track files and logs', 'results/cascade_corrected.csv'),
    ('finetune/train_v3.py', '3.4, 5.6', 'tracer trajectories and frames of the training viewpoints, checkpoint', 'checkpoints and training log'),
    ('finetune/test_on_tap_mps.py', '3.5, 5.8', 'TAP-Vid-DAVIS pickle, checkpoint', 'delta_avg, survival and median error per checkpoint'),
    ('v2_project/compare_v2.py', '3.5', 'evaluation folders of all trackers', 'result CSV with ratio, direction, speed, coverage and TAP-Vid metrics'),
    ('v2_project/velocity_field_eval.py', '3.5, 5.7', 'evaluation tables of a tracker', 'bias, field RMSE and coverage per variant'),
    ('v2_project/results_stats.py', '3.5', 'result CSV', 'medians with bootstrap intervals and paired sign tests'),
    ('v2_project/make_results_reinit.py', '5', 'result CSV files', 'result tables and figures'),
    ('v2_project/make_thesis_figures.py', '5, 6', 'result CSV files', 'overview figures K to S'),
    ('v2_project/make_strategy_figures.py', '1, 3, 5', 'verified numbers of Chapter 5, gallery images', 'route map, methodology figure, results at a glance'),
]
EXTRA = ['finetune/run_strategies.sh', 'finetune/run_S6.sh', 'finetune/run_davis.sh', 'v2_project/run_pips_batch.sh', 'v2_project/run_ptv_fd.sh']

def header(name, section, inputs, outputs, old):
    first = (old or '').strip().split('\n')[0].strip()
    return ('%s\n\nThesis section: %s\nInputs: %s\nOutputs: %s\n\n%s\n' % (name, section, inputs, outputs, (old or '').strip()))

def main():
    out = os.path.join(HERE, 'scripts'); os.makedirs(out, exist_ok=True)
    for rel, sec, inp, outp in MANIFEST:
        src = os.path.join(ROOT, rel); code = open(src).read(); tree = ast.parse(code)
        old = ast.get_docstring(tree, clean=False)
        # locate module docstring node
        has = tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(getattr(tree.body[0], 'value', None), ast.Constant) and isinstance(tree.body[0].value.value, str)
        new_doc = '"""' + header(os.path.basename(rel), sec, inp, outp, old).replace('"""', "'''") + '"""\n'
        lines = code.split('\n')
        if has:
            n0 = tree.body[0]; start, end = n0.lineno - 1, n0.end_lineno
            body = '\n'.join(lines[:start]) + ('\n' if start else '') + new_doc + '\n'.join(lines[end:])
        else:
            # keep a shebang or __future__ import first
            k = 0
            while k < len(lines) and (lines[k].startswith('#!') or lines[k].startswith('# -*-')): k += 1
            body = '\n'.join(lines[:k]) + ('\n' if k else '') + new_doc + '\n'.join(lines[k:])
        dst = os.path.join(out, os.path.basename(rel)); open(dst, 'w').write(body)
        subprocess.run([PY, '-m', 'black', '-q', '-l', '100', '-S', dst], check=True)
    for rel in EXTRA:
        if os.path.exists(os.path.join(ROOT, rel)): shutil.copy(os.path.join(ROOT, rel), os.path.join(out, os.path.basename(rel)))
    for sub, files in [('registers', [('v2_project', 'PREREGISTRATION_v2.md'), ('v2_project', 'PREREGISTRATION_v2_sweep.md'), ('v2_project', 'PREREGISTRATION_v2_reinit.md'), ('finetune', 'PREREGISTRATION_finetune.md'), ('finetune', 'PREREGISTRATION_strategies.md'), ('ptv', 'PTV_PREREGISTRATION.md')]),
                       ('logs', [('.', 'FIXLOG.md'), ('.', 'CHANGE_REGISTER.md'), ('.', 'STATE.md')])]:
        d = os.path.join(HERE, sub); os.makedirs(d, exist_ok=True)
        for folder, f in files:
            p = os.path.join(ROOT, folder, f)
            if os.path.exists(p): shutil.copy(p, d)
    ad = os.path.join(HERE, 'logs', 'audit'); os.makedirs(ad, exist_ok=True)
    for f in os.listdir(os.path.join(ROOT, 'audit')):
        if f.endswith('.md'): shutil.copy(os.path.join(ROOT, 'audit', f), ad)
    shutil.copy(os.path.join(ROOT, 'thesis', 'REPRODUCE.md'), HERE)
    print('scripts:', len(os.listdir(out)))

if __name__ == '__main__':
    main()
