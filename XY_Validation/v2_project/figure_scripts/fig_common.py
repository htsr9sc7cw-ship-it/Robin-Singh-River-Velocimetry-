"""Shared helpers for the figure scripts: paths, saving, the result tables and the method styles.

Every figure script of this folder imports this file and tud_style.py; nothing else is shared. Each figure
script runs on its own (PyCharm: right-click > Run) and writes one picture to ../results/figures/.
Interpreter: the base Python with pandas + matplotlib (the three worked-example scripts and Fig. 5.17 need the
pips2 environment, see their headers).
"""
import os
import re

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import tud_style as tud

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)                      # .../v2_project
RES = os.path.join(PROJECT, 'results')
FIG = os.path.join(RES, 'figures')
os.makedirs(FIG, exist_ok=True)
tud.apply()

# --- the four original methods (Chapter 5.2 to 5.6): one blue / grey and one marker each ------------------------
ORDER = ['PIPs++', 'PTV_tuned_ncc', 'PTV_tuned_lk', 'PTV_gui_defaults']
NAME = {'PIPs++': 'PIPs++ (pre-trained)', 'PTV_tuned_ncc': 'PTV NCC',
        'PTV_tuned_lk': 'PTV LK', 'PTV_gui_defaults': 'PTV LK (GUI defaults)'}
KEY = {'PIPs++': 'S0', 'PTV_tuned_ncc': 'NCC', 'PTV_tuned_lk': 'LK', 'PTV_gui_defaults': 'GUI'}
COL = {m: tud.TRACKER[k] for m, k in KEY.items()}          # the one colour per method of tud_style.TRACKER
MK = {m: tud.MARKER[k] for m, k in KEY.items()}
# where several methods give nearly the same value the markers overlap: large pale marker at the back, small dark one in front
SZ = {'PIPs++': 70, 'PTV_gui_defaults': 50, 'PTV_tuned_lk': 40, 'PTV_tuned_ncc': 34}
ZO = {'PIPs++': 2, 'PTV_gui_defaults': 3, 'PTV_tuned_lk': 4, 'PTV_tuned_ncc': 5}


def save(fig, name, **kw):
    """write results/figures/<name> (no title inside the picture: the title is the thesis caption)"""
    kw.setdefault('bbox_inches', 'tight')
    kw.setdefault('pad_inches', 0.12)
    path = os.path.join(FIG, name)
    fig.savefig(path, dpi=200, facecolor='white', **kw)
    plt.close(fig)
    print('wrote', path)


def load_main():
    """the 28 muddy variants of Sect. 5.2 with ratio, view, density, ground-truth speed and speed group"""
    d = pd.read_csv(os.path.join(RES, 'three_way_v2.csv'))
    d = d[~d.scene.str.contains('_ts0_|clear')].copy()   # speed-ladder rungs and the clear-water views are reported separately: 28 muddy variants
    d['ratio'] = d.rmse / d.rmse_stay
    d['view'] = d.scene.str.replace('^v2_', '', regex=True).str.replace('_(sparse|dense)$', '', regex=True)
    d['density'] = d.scene.str.extract(r'_(sparse|dense)$')
    d['gt_speed'] = d.scene.map(d[d.method == 'PIPs++'].set_index('scene').truth_med)
    labels = ['<18 px/f (Overview)', '18-30 px/f (Path 1-7, high angle, Low_1.003)',
              '30-50 px/f (low angle, Low_1, Low_2, Low_1.002)', '>50 px/f (Low_1.001)']
    d['speed_group'] = pd.cut(d.gt_speed, [0, 18, 30, 50, 200], labels=labels)
    return d, labels


def ci(x, n=10000, seed=0):
    """95 % bootstrap interval of the median"""
    rng = np.random.default_rng(seed)
    x = np.asarray(x)
    b = np.median(rng.choice(x, (n, len(x))), 1)
    return np.percentile(b, 2.5), np.percentile(b, 97.5)


# --- names of the restarted / fine-tuned runs (Sect. 5.3 to 5.6) -----------------------------------------------
def run_name(m):
    base = {'PIPs++': 'PIPs++ pre-trained, started once per 48 frames', 'PIPs++_fseed': 'PIPs++ pre-trained, feature seeds',
            'PTV_tuned_ncc': 'PTV NCC, features every 0.75 FT frames',
            'PTV_tuned_lk': 'PTV LK, features every 0.75 FT frames', 'PTV_gui_defaults': 'PTV LK, GUI defaults'}
    if m in base:
        return base[m]
    g = re.match(r'PIPs\+\+_(?:ft(\d+)_)?r(\d+)_(\d+)$', m)
    if g:
        ft, k, img = g.groups()
        who = 'PIPs++ fine-tuned %s it.' % ft if ft else 'PIPs++ pre-trained'
        return '%s, %s, %s px' % (who, 'started once per 48 frames' if k == '48' else 'restarted every %s frame%s' % (k, '' if k == '1' else 's'), img)
    g = re.match(r'PTV_(tuned_ncc|tuned_lk)_fd(\d+)$', m)
    if g:
        return 'FlowVelo %s, features every %s frame%s' % (g.group(1).split('_')[1].upper(), g.group(2), '' if g.group(2) == '1' else 's')
    return m


def scene_label(s):
    return s.replace('v2_', '').replace('_dense', ' · dense').replace('_sparse', ' · sparse').replace('_', ' ')


def load_run_table(csv_name):
    p = os.path.join(RES, csv_name)
    d = pd.read_csv(p)
    d['ratio'] = d.rmse / d.rmse_stay
    d['method_name'] = d.method.map(run_name)
    d['variant'] = d.scene.map(scene_label)
    return d


def run_colour(m):
    """colour of a run: the one colour of its method (tud_style.TRACKER): pre-trained S0, fine-tuned S1, PTV NCC / LK / GUI"""
    k = tud.method_key(m)
    return tud.TRACKER[k] if k else tud.INK
