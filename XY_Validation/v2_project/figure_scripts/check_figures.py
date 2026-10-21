"""Checks every figure script: (1) does it run, (2) does the picture look professional, (3) are the numbers in the
picture the numbers of the result tables. No AI tokens are needed; the checker is plain Python.

    python check_figures.py            all figures, short report, exit code 1 if anything FAILS
    python check_figures.py 5_13 6_01  only these figures

How it works: each fig_*.py is run unchanged; the checker hooks matplotlib's savefig and, just before the picture is written,
reads what is drawn (bar lengths, scatter points, heat-map cells, every text). It then
  - recomputes the same numbers independently from results/*.csv and compares them with what is drawn,
  - compares the headline numbers with the values stated in the thesis (Chapter 5),
  - checks the look: no title or "Figure" text inside the picture, no overlapping texts, smallest text still readable at
    print width (6.3 in), only TU-Dresden colours (blues, greys) in the non-photographic figures.
Figures that need the pips2 interpreter (5.9, 5.10, 5.12, 5.17) are run in a child process and get the look checks only.
"""
import colorsys
import glob
import os
import re
import runpy
import subprocess
import sys

import matplotlib

matplotlib.use('Agg')
import matplotlib.figure
import matplotlib.text
import numpy as np
import pandas as pd
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
RES = os.path.join(PROJECT, 'results')
FIG = os.path.join(RES, 'figures')
sys.path.insert(0, HERE)

def pips2_python():
    """interpreter of the pips2 environment: PIPS2_PYTHON, else asked from conda, else None"""
    if os.environ.get('PIPS2_PYTHON'):
        return os.environ['PIPS2_PYTHON']
    try:
        r = subprocess.run(['conda', 'run', '-n', 'pips2', 'python', '-c', 'import sys;print(sys.executable)'], capture_output=True, text=True, shell=(os.name == 'nt'))
        return r.stdout.strip().splitlines()[-1] if r.returncode == 0 and r.stdout.strip() else None
    except OSError:
        return None


PAGE_IN = 6.3                     # text width of the thesis page in inches
PHOTO = ('3_01', '5_09', '5_10', '5_12', '5_17')            # contain rendered photographs: no palette test
PIPS2_ONLY = ('5_09', '5_10', '5_12', '5_17')
CAPTURED = []


# --------------------------------------------------------------------------------------------------------------------
# capture what is drawn, just before the file is written
def _hook(orig):
    def savefig(self, *a, **k):
        CAPTURED.append(snapshot(self, a[0] if a else k.get('fname')))
        return orig(self, *a, **k)
    return savefig


def snapshot(fig, path):
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    texts = []
    ticks = set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            lo, hi = sorted(axis.get_view_interval())
            for tk, loc in zip(axis.get_major_ticks(), axis.get_majorticklocs()):
                for lab in (tk.label1, tk.label2):
                    ticks.add(id(lab))
                    if lo - 1e-9 <= loc <= hi + 1e-9 and lab.get_visible() and lab.get_text().strip():
                        texts.append((lab.get_text().strip(), lab.get_fontsize(), lab.get_window_extent(r), lab.get_rotation()))
    for t in fig.findobj(matplotlib.text.Text):
        s = t.get_text().strip()
        if id(t) in ticks:
            continue
        if s and t.get_visible():
            try:
                bb = t.get_window_extent(r)
            except Exception:
                continue
            texts.append((s, t.get_fontsize(), bb, t.get_rotation()))
    data = []
    for ax in fig.axes:
        d = dict(bars=[(p.get_x(), p.get_y(), p.get_width(), p.get_height()) for p in ax.patches if p.__class__.__name__ == 'Rectangle'],
                 scat=[np.asarray(c.get_offsets()) for c in ax.collections if hasattr(c, 'get_offsets') and len(c.get_offsets())],
                 lines=[(np.asarray(l.get_xdata(), float), np.asarray(l.get_ydata(), float)) for l in ax.lines],
                 images=[np.asarray(i.get_array()) for i in ax.images],
                 title=ax.get_title(loc='left') + ax.get_title(loc='center'))
        data.append(d)
    return dict(path=path, size=fig.get_size_inches(), texts=texts, axes=data, suptitle=fig._suptitle.get_text() if fig._suptitle else '')


matplotlib.figure.Figure.savefig = _hook(matplotlib.figure.Figure.savefig)


# --------------------------------------------------------------------------------------------------------------------
# independent recomputation of the numbers from the result files
def csv(name):
    return pd.read_csv(os.path.join(RES, name))


def main_table():
    d = csv('three_way_v2.csv'); d = d[~d.scene.str.contains('_ts0_|clear')].copy(); d['ratio'] = d.rmse / d.rmse_stay
    return d


def moving_water():
    m = csv('surfmove_headline_v3.csv'); m = m[~m.scene.str.contains('clear')]
    v = csv('velocity_field_surfmove_v3.csv'); v = v[~v.scene.str.contains('clear')]
    return m, v


def heldout():
    d = pd.concat([csv('strategies_v3.csv'), csv('s6_heldout_v3.csv')]).drop_duplicates(['scene', 'method'])
    return d[d.scene != 'v2_Path2_dense']


def davis():
    f = os.path.join(os.path.dirname(PROJECT), 'finetune', 'results_davis')
    return {k: pd.read_csv(os.path.join(f, '%s_S32.csv' % k)).d_avg.mean() for k in ('reference', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6')}


M_ALL = {'S0': 'PIPs++_b2_256', 'S6': 'PIPs++_S6_b2_256', 'NCC': 'PTV_tuned_ncc_fd2', 'LK': 'PTV_tuned_lk_fd2'}
# headline values as printed in the thesis (Chapter 5): the picture must show exactly these
THESIS = dict(ratio={'S0': 0.93, 'S6': 0.69, 'NCC': 0.49, 'LK': 0.81}, skill={'S0': 0, 'S6': 24, 'NCC': 24, 'LK': 12},
              speed={'S6': 0.71, 'NCC': 1.00}, coverage={'S6': 0.99, 'NCC': 0.56},
              heldout={'S1': 0.72, 'S2': 0.71, 'S3': 0.69, 'S4': 0.71, 'S5': 1.04, 'S6': 0.69, 'NCC': 0.62, 'LK': 0.99},
              davis={'reference': 66.4, 'S1': 55.0, 'S2': 49.5, 'S3': 59.6, 'S4': 55.1, 'S5': 11.9, 'S6': 58.7})


class Rep:
    def __init__(self, tag):
        self.tag, self.items = tag, []

    def ok(self, msg): self.items.append(('ok', msg))
    def warn(self, msg): self.items.append(('WARN', msg))
    def fail(self, msg): self.items.append(('FAIL', msg))

    def eq(self, what, drawn, expected, tol=0.006):
        (self.ok if abs(drawn - expected) <= tol else self.fail)('%s: drawn %.3f, table %.3f' % (what, drawn, expected))

    def has(self, what, texts, s):
        (self.ok if any(s in t for t in texts) else self.fail)('%s: "%s" %s in the picture' % (what, s, 'is' if any(s in t for t in texts) else 'is NOT'))

    def status(self):
        st = [i[0] for i in self.items]
        return 'FAIL' if 'FAIL' in st else 'WARN' if 'WARN' in st else 'ok'


# --------------------------------------------------------------------------------------------------------------------
# look checks, valid for every figure
def look(rep, cap, png, photo):
    w, h = cap['size']
    texts = [t[0] for t in cap['texts']]
    if cap['suptitle']:
        rep.fail('picture has a figure title: "%s"' % cap['suptitle'][:50])
    if any(re.match(r'^(Figure|Fig\.)\s*\d', t) for t in texts):
        rep.fail('a text inside the picture starts with "Figure n"')
    if len(cap['axes']) == 1 and cap['axes'][0]['title']:
        rep.fail('single-panel picture has a title: "%s"' % cap['axes'][0]['title'][:50])
    if w > 7.6:
        rep.warn('picture is %.1f in wide; text shrinks by %.0f %% on the page' % (w, 100 * (1 - PAGE_IN / w)))
    small = min((fs for s, fs, _, _ in cap['texts'] if len(s) > 1), default=9) * min(1.0, PAGE_IN / w)
    (rep.ok if small >= 5.5 else rep.warn)('smallest text at print size: %.1f pt' % small)
    n = 0; bbs = [(s, bb) for s, _, bb, rot in cap['texts'] if bb.width > 1 and rot % 90 == 0]
    for i in range(len(bbs)):
        for j in range(i + 1, len(bbs)):
            a, b = bbs[i][1], bbs[j][1]
            ix = min(a.x1, b.x1) - max(a.x0, b.x0); iy = min(a.y1, b.y1) - max(a.y0, b.y0)
            if ix > 1 and iy > 1 and ix * iy > 0.25 * min(a.width * a.height, b.width * b.height):
                n += 1
                if n <= 2:
                    rep.warn('texts overlap: "%s" / "%s"' % (bbs[i][0][:18], bbs[j][0][:18]))
    if n == 0:
        rep.ok('no overlapping texts')
    elif n > 2:
        rep.warn('%d overlapping text pairs in total' % n)
    if os.path.exists(png):
        im = Image.open(png).convert('RGB'); a = np.asarray(im, float) / 255
        if not photo:
            mx, mn = a.max(2), a.min(2); sat = (mx - mn) / np.maximum(mx, 1e-6)
            sel = (sat > 0.35) & (mx > 0.3)
            hue = np.array([colorsys.rgb_to_hsv(*p)[0] * 360 for p in a[sel][::7]]) if sel.any() else np.array([])
            off = ((hue < 185) | (hue > 265)).mean() * sel.mean() if len(hue) else 0.0
            (rep.ok if off < 0.004 else rep.fail)('colours: %.2f %% of the pixels are outside blue / grey' % (100 * off))
        white = (a.min(2) > 0.97).mean()
        (rep.ok if white < 0.97 else rep.warn)('%.0f %% of the picture is empty white' % (100 * white))


# --------------------------------------------------------------------------------------------------------------------
# number checks, one function per figure (the key is the number of the figure)
def n_1_01(rep, cap):
    t = [x[0] for x in cap['texts']]; m, _ = moving_water()
    for k, v in THESIS['ratio'].items():
        rep.eq('median ratio %s (CSV vs thesis)' % k, round(m[m.method == M_ALL[k]].ratio_h15.median(), 2), v, 0.0051)
    for s in ('0.93', '0.69', '0.49', '0.81', '28 test variants'):
        rep.has('route map', t, s)


def n_3_01(rep, cap):
    t = [x[0] for x in cap['texts']]
    for s in ('16 camera views', '201 frames', '14 m x 8 m', 'below 0.8'):
        rep.has('methodology', t, s)


def n_3_02(rep, cap):
    t = [x[0] for x in cap['texts']]; d = heldout(); dv = davis()
    for key, m in (('S1', 'PIPs++_ft3000_b2_256'), ('S2', 'PIPs++_S2_b2_256'), ('S4', 'PIPs++_S4_b2_256'), ('S5', 'PIPs++_S5_b2_256'), ('S6', 'PIPs++_S6_b2_256'),
                   ('NCC', 'PTV_tuned_ncc_fd2'), ('LK', 'PTV_tuned_lk_fd2')):
        v = round(d[d.method == m].ratio_h15.median(), 2)
        rep.eq('held-out ratio %s (CSV vs thesis)' % key, v, THESIS['heldout'][key], 0.0051)
        rep.has('tree %s' % key, t, '%.2f' % THESIS['heldout'][key])
    for key, v in dv.items():
        rep.eq('DAVIS %s (CSV vs thesis)' % key, round(v, 1), THESIS['davis'][key], 0.051)
        rep.has('tree DAVIS %s' % key, t, '%.1f' % THESIS['davis'][key])


def n_5_01(rep, cap):
    t1 = pd.read_csv(os.path.join(RES, 'tables', 'T5_1_rmse_ratio_per_variant.csv'))
    sc = cap['axes'][0]['scat']
    for pts, col in zip(sc, ['PIPs++', 'PTV_tuned_ncc', 'PTV_tuned_lk', 'PTV_gui_defaults']):
        drawn = np.sort(pts[:, 1]); tab = np.sort(t1[col].values)
        rep.eq('%s: %d points, max difference to Table 5.1' % (col, len(drawn)), float(np.abs(drawn - tab).max()) if len(drawn) == len(tab) else 9.9, 0.0, 0.0051)


def n_5_03(rep, cap):
    t2 = pd.read_csv(os.path.join(RES, 'tables', 'T5_2_frac_cos08_per_variant.csv'))
    for pts, col in zip(cap['axes'][0]['scat'], ['PIPs++', 'PTV_tuned_ncc', 'PTV_tuned_lk', 'PTV_gui_defaults']):
        drawn = np.sort(pts[:, 1]); tab = np.sort(t2[col].values)
        rep.eq('%s direction agreement vs Table 5.2' % col, float(np.abs(drawn - tab).max()) if len(drawn) == len(tab) else 9.9, 0.0, 0.0051)


def n_5_05(rep, cap):
    d = main_table(); st = ['raw', 'after_mindist', 'after_maxdist', 'after_mincount', 'after_steady', 'after_range', 'final']
    bars = [b for b in cap['axes'][0]['bars'] if b[3] > 0]
    for i, m in enumerate(['PTV_tuned_ncc', 'PTV_tuned_lk', 'PTV_gui_defaults']):
        exp = d[d.method == m][st].sum().values; got = np.array([b[3] for b in bars])[i * 7:(i + 1) * 7]
        rep.eq('%s: tracks after each filter, max difference' % m, float(np.abs(got - exp).max()) if len(got) == len(exp) else 9e9, 0.0, 0.5)


def n_5_08(rep, cap):
    full = csv('three_way_v3_k2.csv'); full['ratio'] = full.rmse / full.rmse_stay
    nv = full.groupby('method').scene.count(); full = full[full.method.isin(nv[nv == nv.max()].index)]
    drawn = np.sort(np.concatenate([p[:, 1] for p in cap['axes'][0]['scat']])); tab = np.sort(full.ratio.values)
    rep.eq('all %d points of the re-tracking figure vs CSV, max difference' % len(drawn), float(np.abs(drawn - tab).max()) if len(drawn) == len(tab) else 9.9, 0.0, 0.0001)


def n_5_11(rep, cap):
    ft = csv('finetune_v3.csv'); ft = ft[~ft.scene.eq('v2_Path2_dense')]
    ms = ['PIPs++', 'PIPs++_r2_256', 'PIPs++_ft3000_r2_256', 'PTV_tuned_ncc_fd2', 'PTV_tuned_lk_fd2']
    drawn = np.sort([b[3] for b in cap['axes'][0]['bars'] if b[3] > 0]); exp = np.sort(ft[ft.method.isin(ms)].groupby(['method', 'scene']).ratio_h15.mean().values)
    rep.eq('%d bars vs ratio_h15 of finetune_v3.csv, max difference' % len(drawn), float(np.abs(drawn - exp).max()) if len(drawn) == len(exp) else 9.9, 0.0, 0.0001)


def n_5_13(rep, cap):
    t = [x[0] for x in cap['texts']]; d = heldout()
    rows = ['PIPs++_b2_256', 'PIPs++_ft3000_b2_256', 'PIPs++_S2_b2_256', 'PIPs++_S3_r48_256', 'PIPs++_S4_b2_256', 'PIPs++_S5_b2_256', 'PIPs++_S6_b2_256', 'PTV_tuned_ncc_fd2', 'PTV_tuned_lk_fd2']
    widths = [b[2] for b in cap['axes'][0]['bars'] if b[2] > 0.05][:9]
    for m, w in zip(rows, widths):
        rep.eq('%s median ratio_h15 (bar vs CSV)' % m, w, float(d[d.method == m].ratio_h15.median()), 0.0001)
    for m in rows:
        rep.has(m, t, '%.2f' % d[d.method == m].ratio_h15.median())


def n_5_15(rep, cap):
    t = [x[0] for x in cap['texts']]; m, v = moving_water()
    for k, mm in M_ALL.items():
        r = m[m.method == mm].ratio_h15
        rep.eq('%s median ratio (CSV vs thesis)' % k, round(float(r.median()), 2), THESIS['ratio'][k], 0.0051)
        rep.eq('%s variants with skill (CSV vs thesis)' % k, int((r < 0.8).sum()), THESIS['skill'][k], 0)
        rep.has('headline %s' % k, t, '%.2f' % THESIS['ratio'][k])
    for k in ('S6', 'NCC'):
        rep.eq('%s speed ratio (CSV vs thesis)' % k, round(float(m[m.method == M_ALL[k]].speed_ratio.median()), 2), THESIS['speed'][k], 0.0051)
        rep.eq('%s coverage (CSV vs thesis)' % k, round(float(v[v.method == M_ALL[k]].coverage.median()), 2), THESIS['coverage'][k], 0.0051)


def n_5_16(rep, cap):
    m, _ = moving_water(); im = cap['axes'][0]['images'][0]
    sp = pd.read_csv(os.path.join(PROJECT, 'ptv_params_v2.csv')).set_index('scene').speed_mean_px
    sc = sorted(m.scene.unique(), key=lambda s: sp.get(s, 0)); worst = 0.0
    for i, mm in enumerate(['PIPs++_b2_256', 'PIPs++_S6_b2_256', 'PTV_tuned_ncc_fd2', 'PTV_tuned_lk_fd2']):
        for j, s in enumerate(sc):
            worst = max(worst, abs(im[j, i] - m[(m.scene == s) & (m.method == mm)].ratio_h15.values[0]))
    rep.eq('%d x %d heat-map cells vs CSV, max difference' % im.shape[::-1], worst, 0.0, 0.0001)


def n_5_18(rep, cap):
    dv = davis(); keys = ['reference', 'S3', 'S6', 'S4', 'S1', 'S2', 'S5']
    widths = [b[2] for b in cap['axes'][0]['bars'] if b[2] > 1]
    for k, w in zip(keys, widths):
        rep.eq('DAVIS %s bar (vs results_davis CSV)' % k, w, dv[k], 0.001)
        rep.eq('DAVIS %s (CSV vs thesis)' % k, round(dv[k], 1), THESIS['davis'][k], 0.051)


def n_5_19(rep, cap):
    t = [x[0] for x in cap['texts']]; m, v = moving_water(); d = heldout()
    for k in ('S0', 'LK', 'S6', 'NCC'):
        rep.has('panel A ratio %s' % k, t, '%.2f' % THESIS['ratio'][k])
    for s in ('12', '24'):
        rep.has('panel B', t, s)
    rep.eq('panel C: S6 coverage (CSV)', round(100 * float(v[v.method == M_ALL['S6']].coverage.median())), 99, 0.5)
    rep.eq('panel C: S6 speed (CSV)', round(100 * float(m[m.method == M_ALL['S6']].speed_ratio.median())), 71, 0.5)
    rep.eq('panel C: NCC coverage (CSV)', round(100 * float(v[v.method == M_ALL['NCC']].coverage.median())), 56, 0.5)
    for s in ('99 %', '71 %', '56 %', '100 %', '1.04', 'NCC 0.62', '66.4 to 58.7'):
        rep.has('panel C/D/E', t, s)
    for k, mm in (('S1', 'PIPs++_ft3000_b2_256'), ('S2', 'PIPs++_S2_b2_256'), ('S4', 'PIPs++_S4_b2_256'), ('S5', 'PIPs++_S5_b2_256'), ('S6', 'PIPs++_S6_b2_256')):
        rep.eq('panel D %s (CSV vs thesis)' % k, round(float(d[d.method == mm].ratio_h15.median()), 2), THESIS['heldout'][k], 0.0051)


def n_6_01(rep, cap):
    _, v = moving_water()
    for pts, k in zip(cap['axes'][0]['scat'], ('S0', 'S6', 'NCC', 'LK')):
        x = v[v.method == M_ALL[k]]
        rep.eq('%s: %d points (coverage, bias) vs CSV, max difference' % (k, len(pts)),
               float(max(np.abs(np.sort(pts[:, 0]) - np.sort(x.coverage.values)).max(), np.abs(np.sort(pts[:, 1]) - np.sort(x.bias_pct.values)).max())) if len(pts) == len(x) else 9.9, 0.0, 0.0001)


NUMBERS = {k[2:]: f for k, f in globals().items() if re.match(r'n_\d_\d\d$', k)}


# --------------------------------------------------------------------------------------------------------------------
def tag_of(path):
    m = re.match(r'fig_(\d)_(\d\d)_', os.path.basename(path))
    return '%s_%s' % m.groups()


def main():
    want = sys.argv[1:]
    scripts = sorted(glob.glob(os.path.join(HERE, 'fig_[1-9]_*.py')))
    reports = []
    for sp in scripts:
        tag = tag_of(sp)
        if want and tag not in want:
            continue
        rep = Rep(tag)
        reports.append(rep)
        base = os.path.basename(sp)
        if tag in PIPS2_ONLY:
            py = pips2_python()
            if not py:
                rep.warn('needs the pips2 interpreter: set PIPS2_PYTHON to test it (look checks skipped)')
                continue
            r = subprocess.run([py, '-W', 'ignore', sp], cwd=HERE, capture_output=True, text=True)
            if r.returncode and any(k in r.stderr for k in ('No such file', 'out of range', 'empty sequence')):
                rep.warn('skipped: the stored tracker runs of the thesis are not in this kit')
                continue
            (rep.ok if r.returncode == 0 else rep.fail)('script runs (pips2)' if r.returncode == 0 else 'script failed: ' + (r.stderr.strip().splitlines() or [''])[-1][:100])
            out = re.findall(r'wrote (.+\.png)', r.stdout)
            for p in out:
                im = Image.open(p)
                (rep.ok if im.width >= 1200 else rep.warn)('%s: %d x %d px' % (os.path.basename(p), im.width, im.height))
            continue
        CAPTURED.clear()
        try:
            runpy.run_path(sp, run_name='__main__')
        except SystemExit:
            pass
        except Exception as e:
            rep.fail('script failed: %s: %s' % (type(e).__name__, str(e)[:100]))
            continue
        if not CAPTURED:
            rep.fail('script wrote no picture')
            continue
        rep.ok('script runs and writes %d picture(s)' % len(CAPTURED))
        cap = CAPTURED[-1] if len(CAPTURED) == 1 else max(CAPTURED, key=lambda c: len(c['texts']))
        look(rep, cap, cap['path'], tag in PHOTO)
        if tag in NUMBERS:
            NUMBERS[tag](rep, cap)
        else:
            rep.ok('(no numbers to cross-check beyond the data source)')
    lines = []
    for rep in reports:
        bad = [i for i in rep.items if i[0] != 'ok']
        lines.append('%-4s fig_%s   %d checks, %d ok%s' % (rep.status(), rep.tag, len(rep.items), sum(1 for i in rep.items if i[0] == 'ok'), '' if not bad else '  <- ' + ' | '.join('%s %s' % i for i in bad[:3])))
    nfail = sum(r.status() == 'FAIL' for r in reports); nwarn = sum(r.status() == 'WARN' for r in reports)
    lines.append('')
    lines.append('%d figures checked: %d ok, %d warnings, %d failed; %d individual checks' % (len(reports), len(reports) - nfail - nwarn, nwarn, nfail, sum(len(r.items) for r in reports)))
    text = '\n'.join(lines)
    print(text)
    if not want:
        open(os.path.join(HERE, 'FIGURE_CHECK.txt'), 'w').write(text + '\n')
    sys.exit(1 if nfail else 0)


if __name__ == '__main__':
    main()
