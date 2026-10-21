"""Writes restructure/a8_source_code.md: the complete source of every Python script made for the thesis (Appendix A.6).
Source: thesis_kit/XY_Validation (the scripts as they run). Upstream code (PIPs++, FlowVeloTool, DeepMind tapvid_metrics / tapnet_viz) is not included."""
import ast
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
K = os.path.join(HERE, 'thesis_kit', 'XY_Validation')
GROUPS = [
    ('A.6.1 Data and Ground Truth', ['rerender/gt_from_particles.py', 'rerender/rasterise_gt.py', 'rerender/synth_tracers.py', 'v2_project/known_answer_eval.py']),
    ('A.6.2 PTV Implementation', ['ptv/derive_ptv_params.py', 'ptv/run_flowvelo_ptv.py', 'ptv/run_lk_sweep.py', 'ptv/corrected_cascade.py', 'ptv/ptv_to_piprun.py']),
    ('A.6.3 PIPs++ and Retraining', ['v2_project/PIP_Execution_batch.py', 'finetune/train_v3.py']),
    ('A.6.4 Scoring', ['v2_project/compare_v2.py', 'v2_project/velocity_field_eval.py', 'v2_project/results_stats.py']),
    ('A.6.5 Diagrams', ['Diagram_Scripts/run_all_diagrams.py']),
]


from print_clean import clean


def compiles(src):
    try:
        compile(src, 'x', 'exec'); return True
    except SyntaxError:
        return False


PURPOSE = {
 'run.py': 'One command that starts every script (python run.py <name>) in the right environment.',
 'demo.py': 'The whole study on one scene with real runs; prints the thesis numbers next to the measured ones.',
 'lk_sweep_demo.py': 'LK pyramid depth 2 to 5 on the demo scene, scored next to the thesis values.',
 'rasterise_demo.py': 'Rebuilds the exact ground truth from the particles and compares it with the ground truth of the thesis.',
 'bake_and_render.py': 'Bakes the FLIP fluid simulation in Blender and renders the camera views.',
 'match_cameras.py': 'Finds which camera made which original scene by matching SIFT features.',
 'gt_from_particles.py': 'Projects the simulated particles through the camera into image displacements.',
 'rasterise_gt.py': 'Turns the projected particles into the per-pixel backward ground-truth field (EXR).',
 'synth_tracers.py': 'Adds the tracers to the frames and moves them through the ground-truth field.',
 'make_ts_variant.py': 'Makes the Blender copies for the speed ladder (time scale 0.5 and 0.25).',
 'moving_surface_control.py': 'Builds the moving-surface control by warping the surface frames with the ground truth.',
 'flow_trials.py': 'Trial bakes at low resolution that calibrate the speed of the particle velocity.',
 'accept_consistency.py': 'Image-level consistency test of the rendered tracers against the ground truth.',
 'flow_core.py': 'Shared helpers: reading the EXR flow, moving points through the field, device choice.',
 'convert_uv_to_xy.py': 'Converts the u,v flow files into x,y track files in the PointOdyssey format.',
 'verify_xy_convention.py': 'Proves that the x,y files follow the Blender convention bit for bit.',
 'rebuild_xy_seeds.py': 'Re-seeds a denser grid of points through the x,y files (for pictures).',
 'scene_config.py': 'Shared settings of the PIPs++ scripts: scene, number of points, device.',
 'known_answer_eval.py': 'Known-answer control: the exact tracer tracks through the evaluator must give zero error.',
 'field_consistency.py': 'Checks every tracer step against the ground-truth velocity field.',
 'PIP_Execution.py': 'Runs the pre-trained PIPs++ in 48-frame blocks on a scene.',
 'PIP_Execution_reinit.py': 'PIPs++ with re-initialisation every k frames, and with other checkpoints.',
 'PIP_Execution_batch.py': 'PIPs++ with fresh seed points every 2 frames, each followed for 16 frames (mode D4).',
 'PIP_Evaluation_gt.py': 'The one evaluator for all trackers: compares tracked and true displacement per step.',
 'derive_ptv_params.py': 'Sets the FlowVelo parameters of every scene from the measured flow speed.',
 'run_flowvelo_ptv.py': 'Runs FlowVeloTool without its graphical interface (NCC, LK or GUI defaults).',
 'run_lk_sweep.py': 'Repeats the LK mode with pyramid depth 2 to 5 and two template sizes.',
 'corrected_cascade.py': 'Repeats the FlowVelo direction filters with the corrected angle computation.',
 'ptv_to_piprun.py': 'Converts FlowVelo tracks into the PIPs++ output layout, so that one evaluator scores both.',
 'train_v3.py': 'Retrains PIPs++ on the river scenes (strategies S1 to S6).',
 'test_on_tap_mps.py': 'Tests a checkpoint on TAP-Vid-DAVIS.',
 'mem_probe.py': 'Measures the memory use of one training step.',
 'compare_v2.py': 'Scores all trackers with the same code (ratio, direction, speed, coverage).',
 'velocity_field_eval.py': 'Grids the tracks into a velocity field: bias, error and coverage per variant.',
 'results_stats.py': 'Medians with bootstrap intervals and paired sign tests over the variants.',
 'tapvid_eval.py': 'Scores the tracks with the TAP-Vid metrics.',
 'make_results.py': 'Result tables and figures of the first comparison (Sects. 5.2 and 5.3).',
 'make_results_reinit.py': 'Result tables of the re-tracking and fine-tuning experiments (Sects. 5.4 and 5.6).',
 'make_tapnet_video.py': 'Draws the track videos with the DeepMind plotting code.',
 'fig_common.py': 'Shared helpers of the figure scripts: paths, saving, result tables, method styles.',
 'tud_style.py': 'The TU Dresden figure style: colours, fonts and box helpers.',
 'worked_example.py': 'Helper of the worked-example diagrams: tracks of the trackers drawn on a frame.',
 'run_all_diagrams.py': 'One command: draws every diagram of the thesis from the result files of the experiments and compares it with the thesis picture.',
  'check_figures.py': 'Checks every figure: look, and the numbers drawn against the result tables.',
}


def purpose(src, name):
    if name in PURPOSE:
        return PURPOSE[name]
    doc = ast.get_docstring(ast.parse(src)) or ''
    first = doc.split('\n')[0].strip()
    return re.sub(r'\s+', ' ', first).rstrip('.') + '.'


def purpose_old(src, name):
    doc = ast.get_docstring(ast.parse(src)) or ''
    lines = [l.strip() for l in doc.split('\n')]
    lines = [l for l in lines if l and not re.match(r'^(Thesis section|Inputs|Outputs)\s*:', l, re.I) and l != name]
    text = ' '.join(lines[:3]) if lines else ''
    text = re.sub(r'^[\w./]+\.py\s*[:—-]+\s*', '', text)
    m = re.match(r'(.{20,220}?[.!?])(\s|$)', text)
    return (m.group(1) if m else text[:200]).strip()


out = []
n = 0
total_lines = 0
for title, files in GROUPS:
    out.append('### %s\n' % title)
    for f in files:
        p = os.path.join(HERE, f) if f.startswith('Diagram_Scripts/') else os.path.join(K, f)
        src = clean(open(p, encoding='utf-8').read(), os.path.basename(f)).rstrip('\n') + '\n'
        n += 1
        if not compiles(src): print('SYNTAX PROBLEM after clean-up:', f)
        total_lines += src.count('\n')
        pur = purpose(src, os.path.basename(f))
        out.append('**`%s`** (%d lines). %s\n' % (f, src.count('\n'), pur))
        out.append('````\n' + src + '````\n')
head = ("## A.6 Source Code\n\nThis section prints the %d key Python scripts of the study (%s lines): the ground truth and its control, the PTV implementation and its parameters, the PIPs++ driver and the training loop, the scoring, and the script that draws all diagrams. "
        'All other scripts (98 in total, listed with their job and run command in Table A.1 and in the file `CODE_GUIDE.md`), among them the helpers and the individual diagram scripts, are in the digital appendix and in the code package `thesis_kit`. '
        'The PIPs++ code of the original repository (Harley et al., 2022; Zheng et al., 2023), FlowVeloTool (Eltner et al., 2020) and the two DeepMind files `tapvid_metrics.py` and `tapnet_viz.py` are third-party code, used as released except for the changes listed in Sect. A.3, and are not printed. '
        'The print removes placeholder headers, dates, personal references and the path of the Python installation, and nothing else. '
        'The command `python run.py <name>` runs a script, and `python run.py demo` runs the study on one scene and prints the thesis numbers next to the numbers measured (Sect. A.1).\n') % (n, format(total_lines, ',').replace(',', ' '))
open(os.path.join(HERE, 'restructure', 'a8_source_code.md'), 'w').write(head + '\n' + '\n'.join(out))
