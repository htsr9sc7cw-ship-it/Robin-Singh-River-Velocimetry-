"""Build thesis_code/: every script that the thesis refers to, cleaned, in the folder layout of the project.

Run:  python make_code_package.py
The layout (v2_project/, ptv/, finetune/, rerender/, root helpers) is the same as in XY_Validation/, because the
scripts find each other relative to their own location.  Cleaning = uniform header + black (line length 100).  The
code is not changed (verify_code_package.py checks the AST).  Third-party code is copied unchanged.
"""
import ast, os, shutil, subprocess, sys
from make_digital_appendix import MANIFEST, header, ROOT, PY, HERE

PKG = os.path.join(HERE, '..', 'thesis_code')
SHARED = [  # (source relative to XY_Validation, destination relative to the package, vendored?)
    ('flow_core.py', 'flow_core.py', False), ('rebuild_xy_seeds.py', 'rebuild_xy_seeds.py', False),
    ('verify_xy_convention.py', 'verify_xy_convention.py', False), ('../convert_uv_to_xy.py', 'convert_uv_to_xy.py', False),
    ('v2_project/scene_config.py', 'v2_project/scene_config.py', False), ('v2_project/PIP_Execution.py', 'v2_project/PIP_Execution.py', False),
    ('v2_project/PIP_Execution_reinit.py', 'v2_project/PIP_Execution_reinit.py', False), ('v2_project/make_results.py', 'v2_project/make_results.py', False),
    ('v2_project/tapvid_eval.py', 'v2_project/tapvid_eval.py', False), ('v2_project/make_tapnet_video.py', 'v2_project/make_tapnet_video.py', False),
    ('v2_project/saverloader.py', 'v2_project/saverloader.py', False),
    ('v2_project/tapvid_metrics.py', 'v2_project/tapvid_metrics.py', True), ('v2_project/tapnet_viz.py', 'v2_project/tapnet_viz.py', True),
    ('v2_project/tapnet_viz_utils_upstream.py', 'v2_project/tapnet_viz_utils_upstream.py', True),
    ('ptv/ptv_to_piprun.py', 'ptv/ptv_to_piprun.py', False), ('rerender/gt_from_particles.py', 'rerender/gt_from_particles.py', False),
    ('rerender/accept_consistency.py', 'rerender/accept_consistency.py', False), ('rerender/synth_tracers.py', 'rerender/synth_tracers.py', False),
    ('rerender/flow_trials.py', 'rerender/flow_trials.py', False), ('rerender/make_ts_variant.py', 'rerender/make_ts_variant.py', False),
    ('rerender/moving_surface_control.py', 'rerender/moving_surface_control.py', False), ('finetune/mem_probe.py', 'finetune/mem_probe.py', False),
    ('thesis/table_3_2.py', 'thesis/table_3_2.py', False),
    ('finetune/after_S6.sh', 'finetune/after_S6.sh', False), ('finetune/run_S6.sh', 'finetune/run_S6.sh', False), ('finetune/run_davis.sh', 'finetune/run_davis.sh', False),
    ('finetune/run_finetune.sh', 'finetune/run_finetune.sh', False), ('finetune/run_strategies.sh', 'finetune/run_strategies.sh', False),
    ('v2_project/finish_surfmove.sh', 'v2_project/finish_surfmove.sh', False), ('v2_project/render_in_gap.sh', 'v2_project/render_in_gap.sh', False),
    ('v2_project/render_videos_S6.sh', 'v2_project/render_videos_S6.sh', False), ('v2_project/run_on_drive.sh', 'v2_project/run_on_drive.sh', False),
    ('v2_project/run_pips_batch.sh', 'v2_project/run_pips_batch.sh', False), ('v2_project/run_pips_v2.sh', 'v2_project/run_pips_v2.sh', False),
    ('v2_project/run_reinit_all.sh', 'v2_project/run_reinit_all.sh', False), ('rerender/rerender_clear.sh', 'rerender/rerender_clear.sh', False),
    ('rerender/run_surfmove_all.sh', 'rerender/run_surfmove_all.sh', False), ('rerender/speed_ladder.sh', 'rerender/speed_ladder.sh', False),
]

def main():
    if os.path.isdir(PKG): shutil.rmtree(PKG)
    done = []
    items = [(rel, rel, False) for rel, *_ in MANIFEST] + SHARED
    for src_rel, dst_rel, vendored in items:
        src = os.path.join(ROOT, src_rel)
        if not os.path.exists(src): print('MISSING', src_rel); continue
        dst = os.path.join(PKG, dst_rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
        if vendored or not dst_rel.endswith('.py'):
            shutil.copy(src, dst)
        else:
            code = open(src).read(); tree = ast.parse(code); old = ast.get_docstring(tree, clean=False)
            m = {r: (s, i, o) for r, s, i, o in MANIFEST}.get(src_rel)
            sec, inp, outp = m if m else ('see README.md', 'see README.md', 'see README.md')
            has = tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(getattr(tree.body[0], 'value', None), ast.Constant) and isinstance(tree.body[0].value.value, str)
            doc = '"""' + header(os.path.basename(dst_rel), sec, inp, outp, old).replace('"""', "'''") + '"""\n'
            lines = code.split('\n')
            if has:
                n0 = tree.body[0]; body = '\n'.join(lines[:n0.lineno - 1]) + ('\n' if n0.lineno > 1 else '') + doc + '\n'.join(lines[n0.end_lineno:])
            else:
                k = 0
                while k < len(lines) and (lines[k].startswith('#!') or lines[k].startswith('# -*-')): k += 1
                body = '\n'.join(lines[:k]) + ('\n' if k else '') + doc + '\n'.join(lines[k:])
            open(dst, 'w').write(body); subprocess.run([PY, '-m', 'black', '-q', '-l', '100', '-S', dst], check=True)
        done.append(dst_rel)
    for sub, files in [('registers', [('v2_project', 'PREREGISTRATION_v2.md'), ('v2_project', 'PREREGISTRATION_v2_sweep.md'), ('v2_project', 'PREREGISTRATION_v2_reinit.md'), ('finetune', 'PREREGISTRATION_finetune.md'), ('finetune', 'PREREGISTRATION_strategies.md'), ('ptv', 'PTV_PREREGISTRATION.md')])]:
        d = os.path.join(PKG, sub); os.makedirs(d, exist_ok=True)
        for folder, f in files:
            p = os.path.join(ROOT, folder, f)
            if os.path.exists(p): shutil.copy(p, d)
    shutil.copy(os.path.join(ROOT, 'thesis', 'REPRODUCE.md'), PKG)
    print(len(done), 'files in', os.path.abspath(PKG))

if __name__ == '__main__':
    main()
