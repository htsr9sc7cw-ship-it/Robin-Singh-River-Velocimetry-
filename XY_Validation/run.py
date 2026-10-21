"""ONE command for every script of the thesis (Mac, Windows, Linux):

    python run.py setup             once per computer: creates the two conda environments and installs the base packages
    python run.py demo              the whole study on one scene, real runs, numbers next to the thesis (about 8 min)
    python run.py list              all names
    python run.py figures           the 25 figure scripts; then  python run.py fig_5_13  draws that figure
    python run.py <name>            runs that script for real on the demo scene (v2_Path4_dense) and prints its result
    python run.py <name> <options>  your own options replace the ready-made ones   (python run.py compare_v2 --help)

Start it from the folder that contains this file or its parent folder:  python run.py demo
Every <name> is a script of the thesis (file name without .py); nothing is simulated or printed from stored files.
Needs: Python 3.8+ and conda (Miniconda or Anaconda) on the PATH.
"""
import glob
import os
import platform
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
WIN = platform.system() == 'Windows'
V2 = os.path.join(HERE, 'v2_project')
SC = 'v2_Path4_dense'
PIPS = dict(PIP_N='256', PIP_SCENE=SC)
D4 = dict(PIP_N='64', PIP_BATCH_LEN='16', PIP_SCENE=SC, PIP_BATCH_EVERY='2', PIP_IMG='256', PIP_RUN_SUFFIX='_S6_b2_256',
          PIP_CKPT_DIR=os.path.join(HERE, 'finetune', 'ckpt_S6'))
H = ['--help']
XYOUT = {'XY_FORMAT_OUT': os.path.join(HERE, 'XY_Format_demo')}
# name: (folder, file, environment, ready-made options, extra environment variables, what it does)
S = {
    'demo': ('.', 'demo.py', 'base', [], {}, 'whole study on one scene: controls, PIPs++, FlowVelo, retrained model, scoring, table against the thesis'),
    'lk_sweep': ('.', 'lk_sweep_demo.py', 'base', [], {}, 'LK pyramid depth 2 to 5 scored next to the thesis (0.92 -> 0.21)'),
    # ground truth and controls
    'convert_uv_to_xy': ('.', 'convert_uv_to_xy.py', 'pips2', ['--dense', '--scene', SC], XYOUT, 'u,v flow files -> x,y track files'),
    'verify_xy_convention': ('.', 'verify_xy_convention.py', 'pips2', ['--scene', SC], XYOUT, 'proves the x,y files follow the Blender convention bit for bit (after convert_uv_to_xy)'),
    'rebuild_xy_seeds': ('.', 'rebuild_xy_seeds.py', 'pips2', ['--scene', SC], {}, 'rebuilds the seed points of the x,y files'),
    'known_answer_eval': ('v2_project', 'known_answer_eval.py', 'base', [SC], {}, 'control: exact tracks must give zero error (PASS)'),
    'field_consistency': ('v2_project', 'field_consistency.py', 'pips2', [SC], {}, 'control: every tracer step against the ground-truth field'),
    # trackers
    'PIP_Execution': ('v2_project', 'PIP_Execution.py', 'pips2', [], PIPS, 'pre-trained PIPs++, 48-frame blocks'),
    'PIP_Evaluation_gt': ('v2_project', 'PIP_Evaluation_gt.py', 'pips2', [], PIPS, 'the one evaluator for all trackers (after PIP_Execution)'),
    'PIP_Execution_batch': ('v2_project', 'PIP_Execution_batch.py', 'pips2', [], D4, 'retrained PIPs++ (S6), fresh seeds every 2 frames'),
    'derive_ptv_params': ('ptv', 'derive_ptv_params.py', 'pips2', [], {'PTV_OUT': os.path.join(V2, 'out_ptv')}, 'FlowVelo parameters from the measured flow speed'),
    'run_flowvelo_ptv': ('ptv', 'run_flowvelo_ptv.py', 'flowvelo', ['--mode', 'tuned_ncc', '--scene', SC], {'PTV_OUT': os.path.join(V2, 'out_ptv')}, 'FlowVelo NCC on the scene'),
    'run_lk_sweep': ('ptv', 'run_lk_sweep.py', 'flowvelo', ['--scene', SC, '--levels', '2', '3', '4', '5', '--templates', 'tuned'], {'PTV_OUT': os.path.join(V2, 'out_ptv_sweep')}, 'FlowVelo LK, pyramid depth 2 to 5 (lk_sweep also scores it)'),
    'corrected_cascade': ('ptv', 'corrected_cascade.py', 'flowvelo', ['../v2_project'], {}, 'FlowVelo direction filters with the corrected angle (after run_flowvelo_ptv)'),
    # retraining
    'train_v3': ('finetune', 'train_v3.py', 'pips2', ['--max-iters', '20', '--S', '12', '--N', '24', '--crop', '256', '--save-every', '20', '--ckpt', 'ckpt_demo'], {'FT_VIEWS': 'Path4'}, 'retrains PIPs++ for 20 steps on the scene (loss falls)'),
    'test_on_tap_mps': ('finetune', 'test_on_tap_mps.py', 'pips2', ['@davis'], {}, 'TAP-Vid-DAVIS test (needs the DAVIS file, 2.5 GB, see the message)'),
    # scoring
    'compare_v2': ('v2_project', 'compare_v2.py', 'base', ['--ptv-eval', '--scenes', SC, '--ptv-root', 'out_ptv', '--modes', 'tuned_ncc', '--out', 'compare_demo.csv'], {}, 'one scorer for all trackers (after demo or the tracker scripts)'),
    'velocity_field_eval': ('v2_project', 'velocity_field_eval.py', 'pips2', ['--scenes', SC, '--methods', 'PIPs++', 'PTV_tuned_ncc', '--out', 'results/velocity_demo.csv'], {}, 'velocity field: bias, error, coverage per tracker'),
    'results_stats': ('v2_project', 'results_stats.py', 'base', ['--csv', 'results/strategies_v3.csv', '--metric', 'ratio_h15', '--exclude', 'v2_Path2_dense', '--out', 'results/stats_demo.md'], {}, 'medians, bootstrap intervals, sign tests of the thesis'),
    # tables and figures
    'make_results_reinit': ('v2_project', 'make_results_reinit.py', 'base', [], {}, 'result tables of the thesis from the stored result files'),
    'run_all_figures': ('v2_project/figure_scripts', 'run_all_figures.py', 'base', [], {}, 'all 25 thesis figures, one script per figure'),
    'check_figures': ('v2_project/figure_scripts', 'check_figures.py', 'base', [], {}, 'checks look and numbers of all figures against the result tables'),
    # Blender
    'bake_and_render': ('rerender', 'bake_and_render.py', 'blender', H, {}, 'Blender fluid bake and render (needs Blender and the .blend scene, see the message)'),
    'rasterise_gt': ('.', 'rasterise_demo.py', 'pips2', [], {}, 'exact ground truth rebuilt from the simulated particles, compared with the thesis ground truth (about 6 min)'),
}
CHAIN = {'make_results_reinit': 'run_all_figures'}      # the table script also writes old-style figures; the thesis figures are drawn after it


def conda_python(env):
    """interpreter of a conda environment, found through conda"""
    key = {'pips2': 'PIPS2_PYTHON', 'flowvelo': 'FLOWVELO_PYTHON'}.get(env)
    if key and os.environ.get(key):
        return os.environ[key]
    r = subprocess.run(['conda', 'run', '-n', env, 'python', '-c', 'import sys;print(sys.executable)'], capture_output=True, text=True, shell=WIN)
    if r.returncode or not r.stdout.strip():
        sys.exit('conda environment "%s" is missing. Create it once with:  python run.py setup' % env)
    return r.stdout.strip().splitlines()[-1]


def figure_scripts(start=''):
    """names of the figure scripts (fig_<chapter>_<number>_<name>.py) that start with `start`"""
    d = os.path.join(V2, 'figure_scripts')
    return sorted(f for f in os.listdir(d) if re.match(r'fig_\d_\d\d_.*\.py$', f) and f.startswith(start)) if os.path.isdir(d) else []


def blender_exe():
    found = shutil.which('Blender') or shutil.which('blender')
    cand = {'Darwin': ['/Applications/Blender.app/Contents/MacOS/Blender'],
            'Windows': sorted(glob.glob(r'C:\Program Files\Blender Foundation\Blender *\blender.exe'), reverse=True)}.get(platform.system(), ['/usr/bin/blender', '/snap/bin/blender'])
    return found or next((c for c in cand if os.path.exists(c)), None)


def setup():
    """create the two conda environments (once) and install the base packages into the python that runs this file"""
    envs = subprocess.run(['conda', 'env', 'list'], capture_output=True, text=True, shell=WIN).stdout
    for name in ('pips2', 'flowvelo'):
        if any(l.split() and l.split()[0] == name for l in envs.splitlines()):
            print('environment %-9s already exists' % name)
            continue
        print('creating environment %s (a few minutes) ...' % name, flush=True)
        r = subprocess.run(['conda', 'env', 'create', '-f', os.path.join(KIT, 'environment', name + '.yml')], shell=WIN)
        if r.returncode:
            sys.exit('could not create %s' % name)
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r', os.path.join(KIT, 'environment', 'base.txt')])
    print('setup done. Next:  python run.py demo')


def main():
    a = sys.argv[1:]
    dry = '--dry' in a
    a = [x for x in a if x != '--dry']
    if not a or a[0] in ('list', '-h', '--help'):
        print(__doc__)
        for k, v in S.items():
            print('  python run.py %-22s %s   [%s]' % (k, v[5], v[2]))
        print('\nFigures: python run.py figures   (one command per figure, e.g.  python run.py fig_1_01)')
        return
    if a[0] == 'setup':
        return setup()
    if a[0] == 'figures':
        for f in figure_scripts():
            print('  python run.py %-8s draws %s' % (f[:8], f[9:-3]))
        return
    if a[0] not in S and figure_scripts(a[0]):
        f = figure_scripts(a[0])[0]
        env = 'pips2' if f[4:10] in ('5_09_w', '5_10_w', '5_12_w', '5_17_v') else 'base'
        S[a[0]] = ('v2_project/figure_scripts', f, env, [], {}, 'figure')
    if a[0] not in S:
        sys.exit('unknown name "%s". Type:  python run.py list' % a[0])
    folder, fname, env, default, extra, _ = S[a[0]]
    cwd = os.path.join(HERE, folder)
    opts = a[1:] or default
    if opts == ['@davis']:
        pkl = os.path.join(HERE, 'finetune', 'tapvid_davis', 'tapvid_davis.pkl')
        if not os.path.exists(pkl):
            print('The TAP-Vid-DAVIS benchmark file (2.5 GB, DeepMind, https://github.com/google-deepmind/tapnet) is not part of this kit.\n'
                  'Put tapvid_davis.pkl into finetune/tapvid_davis/ and run:\n'
                  '   python run.py test_on_tap_mps\n'
                  'The thesis results (reference weights 66.4, final model S6 58.7) are in finetune/results_davis/*_S32.csv.')
            return
        opts = ['--data', pkl, '--S', '32', '--max-videos', '2']
    if env == 'blender':
        if not os.path.exists(os.path.join(HERE, 'rerender', 'Basefile_a_TRACERS.blend')):
            sys.exit('This step needs Blender 5.x, the Blender scene file Basefile_a_TRACERS.blend and the baked fluid cache (about 100 GB).\nThey are on the project drive, not in the kit. The script itself is rerender/%s; python run.py bake_and_render --help is not available without Blender.' % fname)
        exe = blender_exe()
        if not exe:
            sys.exit('Blender 5.x is needed for this script (https://www.blender.org). It is not part of the kit, nor is the .blend scene file.')
        cmd = [exe, '--background', '--python', fname, '--'] + opts
    else:
        cmd = [sys.executable if env == 'base' else conda_python(env), '-W', 'ignore', fname] + opts
    environ = dict(os.environ, XYV_DATA=os.path.join(V2, 'Vectors_and_Images'), PYTORCH_ENABLE_MPS_FALLBACK='1', PYTHONIOENCODING='utf-8',
                   PIP_PROJECT=V2, PIP_FIX_SIGN='1', PIP_FIX_TRANSPOSE='1', PIP_MP='0', PIP_NO_PLOTS='1', BASE_PYTHON=sys.executable, **extra)
    if env != 'blender' and a[0] in ('compare_v2', 'run_all_figures', 'check_figures', 'make_results_reinit'):
        environ['PIPS2_PYTHON'] = conda_python('pips2')          # the scorer and the figure scripts start the pips2 scripts themselves
    print('>>', folder, '|', os.path.basename(cmd[0]), ' '.join(cmd[1:]), flush=True)
    if dry:
        return
    rc = subprocess.call(cmd, cwd=cwd, env=environ)
    if rc == 0 and a[0] in CHAIN:
        sys.argv = [sys.argv[0], CHAIN[a[0]]]
        return main()
    sys.exit(rc)


if __name__ == '__main__':
    main()
