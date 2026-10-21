"""Writes every result table of the thesis from the result files (v2_project/results/*.csv, finetune/results_davis/*.csv).
Output: restructure/generated_tables.json  {key: markdown table}.  assemble2.py puts the tables in the text (marker @@TABLE:key@@).
Rounding is half-up to two decimals; counts use a space as thousands separator."""
import glob, json, os, re
from decimal import Decimal, ROUND_HALF_UP
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
XY = os.path.dirname(HERE)
RES = os.path.join(XY, 'v2_project', 'results')
DAVIS = os.path.join(XY, 'finetune', 'results_davis')
csv = lambda f: pd.read_csv(os.path.join(RES, f))

def r(x, d=2):
    if x is None or (isinstance(x, float) and np.isnan(x)): return '–'
    q = Decimal(1).scaleb(-d)
    s = str(Decimal(repr(round(float(x), 8))).quantize(q, rounding=ROUND_HALF_UP))
    return s.replace('-', '−') if s.startswith('-') else s
def n(x): return '{:,}'.format(int(round(float(x)))).replace(',', ' ')
def md(header, rows): return '\n'.join(['| ' + ' | '.join(header) + ' |', '|' + '---|' * len(header)] + ['| ' + ' | '.join(str(c) for c in row) + ' |' for row in rows])
def bold(s): return '**%s**' % s

# ---------------------------------------------------------------- data sets
def ratio(d): return d.rmse / d.rmse_stay
A = csv('three_way_v2_with_fseed.csv'); A = A[~A.scene.str.contains('_ts0_|clear')].copy(); A['ratio'] = ratio(A)         # the 28 muddy variants, still surface
SPEED = A[A.method == 'PIPs++'].set_index('scene').truth_med
A['gs'] = A.scene.map(SPEED)
A['dens'] = A.scene.str.extract(r'_(sparse|dense)$')[0]
NAME = {'PIPs++': 'PIPs++ pre-trained', 'PIPs++_fseed': 'PIPs++ pre-trained, feature seeds', 'PTV_tuned_ncc': 'PTV NCC (tuned)', 'PTV_tuned_lk': 'PTV LK (tuned)', 'PTV_gui_defaults': 'PTV LK (GUI defaults)'}
MAIN4 = ['PIPs++', 'PTV_tuned_ncc', 'PTV_tuned_lk', 'PTV_gui_defaults']
def med(d, m, col): return d[d.method == m][col].median()
OUT = {}

# ---------------------------------------------------------------- Table: four methods (still surface)
def four_methods():
    full, simple = [], []
    for m in ['PIPs++', 'PIPs++_fseed', 'PTV_tuned_ncc', 'PTV_tuned_lk', 'PTV_gui_defaults']:
        x = A[A.method == m]
        full.append([NAME[m], n(x.n.median()), r(x.ratio.median()), r(x.frac_cos08.median()), r(x.speed_ratio.median()), r(x.d8.median()), r(x.frac_tracks_follow.median()), int((x.ratio < 0.8).sum())])
        if m != 'PIPs++_fseed': simple.append([NAME[m], r(x.ratio.median()), r(x.frac_cos08.median()), r(x.speed_ratio.median()), int((x.ratio < 0.8).sum())])
    OUT['f52'] = md(['method', 'steps scored', 'ratio', 'direction', 'speed ratio', 'within 8 px', 'tracks that follow', 'variants with skill'], full)
    OUT['5.2'] = md(['method', 'ratio', 'direction', 'speed ratio', 'variants with skill (of 28)'], simple)
four_methods()

# ---------------------------------------------------------------- Table: speed groups
GR = ['<18', '18-30', '30-50', '>50']
A['grp'] = pd.cut(A.gs, [0, 18, 30, 50, 200], labels=GR)
GLAB = {'<18': 'below 18', '18-30': '18 to 30', '30-50': '30 to 50', '>50': 'above 50'}
def groups():
    cnt = A[A.method == 'PIPs++'].groupby('grp', observed=True).size()
    members = {'<18': 'Overview', '18-30': 'Path 1–7, Low_1.003', '30-50': 'low angle, Low_1, Low_2, Low_1.002', '>50': 'Low_1.001'}
    simple = []
    for m in MAIN4:
        simple.append([NAME[m]] + [r(A[(A.method == m) & (A.grp == g)].ratio.median()) for g in GR])
    OUT['5.3'] = md(['median ratio'] + ['%s px/frame (%d variants)' % (GLAB[g], cnt[g]) for g in GR], simple)
    rows = []
    for g in GR:
        for i, m in enumerate(MAIN4):
            x = A[(A.method == m) & (A.grp == g)]
            rows.append([('%s px/frame' % GLAB[g]) if i == 0 else '', members[g] if i == 0 else '', NAME[m], r(x.ratio.median()), r(x.frac_cos08.median()), r(x.speed_ratio.median()), r(x.d8.median())])
    OUT['f53'] = md(['speed group', 'members', 'method', 'ratio', 'direction', 'speed ratio', 'within 8 px'], rows)
groups()

# ---------------------------------------------------------------- Table: density
def density():
    simple, full = [], []
    for m in ['PIPs++', 'PTV_tuned_ncc', 'PTV_tuned_lk', 'PTV_gui_defaults']:
        s, dn = A[(A.method == m) & (A.dens == 'sparse')], A[(A.method == m) & (A.dens == 'dense')]
        simple.append([NAME[m], r(s.ratio.median()), r(dn.ratio.median())])
    for m in ['PIPs++', 'PIPs++_fseed', 'PTV_tuned_ncc', 'PTV_tuned_lk', 'PTV_gui_defaults']:
        s, dn = A[(A.method == m) & (A.dens == 'sparse')], A[(A.method == m) & (A.dens == 'dense')]
        full.append([NAME[m], r(s.ratio.median()), r(dn.ratio.median()), r(s.frac_cos08.median()), r(dn.frac_cos08.median())])
    OUT['5.4'] = md(['median ratio', 'sparse tracers', 'dense tracers'], simple)
    OUT['f54'] = md(['method', 'ratio, sparse', 'ratio, dense', 'direction, sparse', 'direction, dense'], full)
density()

# ---------------------------------------------------------------- Table: clear against muddy water
def clear():
    C = csv('three_way_v2.csv'); C = C[~C.scene.str.contains('_ts0_')].copy(); C['ratio'] = ratio(C)
    g = lambda sc, m: r(C[(C.scene == sc) & (C.method == m)].ratio.iloc[0])
    rows = [[NAME[m]] + [g(sc, m) for sc in ('v2_Path3_dense', 'v2_Path3_clear_dense', 'v2_Path3_sparse', 'v2_Path3_clear_sparse')] for m in ['PIPs++', 'PTV_tuned_ncc', 'PTV_tuned_lk']]
    OUT['clear'] = md(['ratio on Path3', 'dense, muddy', 'dense, clear', 'sparse, muddy', 'sparse, clear'], rows)
    full = [[NAME[m]] + [g(sc, m) for sc in ('v2_Path3_dense', 'v2_Path3_clear_dense', 'v2_Path3_sparse', 'v2_Path3_clear_sparse', 'v2_high_angle_clear_dense', 'v2_high_angle_clear_sparse')] for m in MAIN4]
    OUT['fclear'] = md(['ratio', 'Path3 dense, muddy', 'Path3 dense, clear', 'Path3 sparse, muddy', 'Path3 sparse, clear', 'high angle dense, clear', 'high angle sparse, clear'], full)
clear()

# ---------------------------------------------------------------- Table: filter cascade
def cascade():
    C = csv('three_way_v2.csv'); C = C[~C.scene.str.contains('_ts0_|clear')]
    cc = csv('cascade_corrected.csv'); cc = cc[~cc.scene.str.contains('_ts0_|clear')]
    st = ['raw', 'after_mindist', 'after_maxdist', 'after_mincount', 'after_steady', 'after_range', 'final']
    lab = ['Detected and tracked', 'After the minimum-distance filter', 'After the maximum-distance filter', 'After the minimum-count filter', 'After the steadiness filter', 'After the angle-range filter', 'After the main-flow filter (final tracks)']
    modes = [('PTV_tuned_ncc', 'tuned_ncc', 'PTV NCC (tuned)'), ('PTV_tuned_lk', 'tuned_lk', 'PTV LK (tuned)'), ('PTV_gui_defaults', 'gui_defaults', 'GUI defaults (LK)')]
    sums = {m: C[C.method == m][st].sum() for m, _, _ in modes}
    rows = [[lab[i]] + [n(sums[m][st[i]]) for m, _, _ in modes] for i in range(len(st))]
    corr = []
    for m, mode, _ in modes:
        x = cc[cc['mode'] == mode]; corr.append('%s of %s' % (n(x.corrected_steady_range.sum()), n(x.n_after_mincount.sum())))
    rows.append(['Corrected steadiness and range pass (a)'] + corr)
    OUT['5.5'] = md(['filter stage'] + [t for _, _, t in modes], rows)
cascade()

# ---------------------------------------------------------------- Table: pyramid depth
def pyramid():
    L = csv('lk_sweep_v2.csv'); L['ratio'] = ratio(L)
    sc = [('v2_Overview_dense', 'Overview dense'), ('v2_Path2_dense', 'Path2 dense'), ('v2_Path4_dense', 'Path4 dense'), ('v2_Low_1_dense', 'Low_1 dense')]
    def cell(s, lv, what):
        x = L[(L.scene == s) & (L.method == 'PTV_lk_L%d_Ttuned' % lv)]
        return r(x.ratio.iloc[0]) if what == 'ratio' else r(x.frac_cos08.iloc[0])
    sp = {s: r(SPEED[s], 0) for s, _ in sc}
    OUT['5.6'] = md(['ratio of LK', 'true speed (px/frame)', 'depth 2 (as published)', 'depth 3', 'depth 4'], [[nm, sp[s]] + [cell(s, lv, 'ratio') for lv in (2, 3, 4)] for s, nm in sc])
    OUT['f56'] = md(['ratio (direction agreement)', 'true speed (px/frame)', 'depth 2 (as published)', 'depth 3', 'depth 4 (= depth 5)'], [[nm, sp[s]] + ['%s (%s)' % (cell(s, lv, 'ratio'), cell(s, lv, 'dir')) for lv in (2, 3, 4)] for s, nm in sc])
pyramid()


# ---------------------------------------------------------------- Table: speed ladder
def ladder():
    L = csv('speed_ladder_v2.csv'); L['ratio'] = ratio(L)
    B = csv('three_way_v2.csv'); B = B[B.scene.str.match(r'v2_Low_1(_001)?_dense$')].copy(); B['ratio'] = ratio(B)
    D = pd.concat([B, L]); D = D[D.scene.str.contains('dense')]
    sp = D[D.method == 'PIPs++'].set_index('scene').truth_med
    D['gs'] = D.scene.map(sp); D['cam'] = D.scene.str.extract(r'(v2_Low_1(?:_001)?)')[0]
    col = lambda g: 0 if g < 15 else 1 if g < 30 else 2 if g < 60 else 3
    heads = ['8 px/frame', '21–22 px/frame', '46–48 px/frame', '83 px/frame']
    spec = [('PTV_tuned_ncc', 'v2_Low_1', 'PTV NCC, Low_1'), ('PTV_tuned_ncc', 'v2_Low_1_001', 'PTV NCC, Low_1.001'), ('PTV_tuned_lk', 'v2_Low_1', 'PTV LK, Low_1'), ('PTV_tuned_lk', 'v2_Low_1_001', 'PTV LK, Low_1.001'),
            ('PTV_gui_defaults', 'v2_Low_1', 'PTV LK (GUI defaults), Low_1'), ('PIPs++', 'v2_Low_1', 'PIPs++ pre-trained, Low_1'), ('PIPs++', 'v2_Low_1_001', 'PIPs++ pre-trained, Low_1.001')]
    simple, full = [], []
    for m, cam, lab in spec:
        x = D[(D.method == m) & (D.cam == cam)]
        rs = ['–'] * 4; fs = ['–'] * 4
        for _, row in x.iterrows():
            c = col(row.gs); rs[c] = r(row.ratio); fs[c] = '%s (%s)' % (r(row.ratio), r(row.frac_cos08))
        simple.append([lab] + rs); full.append([lab] + fs)
    OUT['5.7'] = md(['ratio of the method on the camera'] + heads, simple)
    OUT['f57'] = md(['ratio (direction agreement)'] + heads, full)
ladder()

# ---------------------------------------------------------------- Table: re-tracking (28 variants)
def retrack():
    K = csv('three_way_v3_k2.csv'); K['ratio'] = ratio(K); nv = K.groupby('method').scene.count(); K = K[K.method.isin(nv[nv == nv.max()].index)]
    spec = [('PIPs++', 'PIPs++ pre-trained, once per 48 frames'), ('PIPs++_r2_256', 'PIPs++ pre-trained, every 2 frames'), ('PIPs++_r1_256', 'PIPs++ pre-trained, every frame'),
            ('PTV_tuned_ncc', 'PTV NCC, derived rhythm'), ('PTV_tuned_ncc_fd2', 'PTV NCC, every 2 frames'), ('PTV_tuned_lk', 'PTV LK, derived rhythm'), ('PTV_tuned_lk_fd2', 'PTV LK, every 2 frames')]
    rows, full = [], []
    for m, lab in spec:
        x = K[K.method == m]
        rows.append([lab, r(x.ratio.median()), r(x.frac_cos08.median()), r(x.speed_ratio.median()), int((x.ratio < 0.8).sum())])
        xd, xs = x[x.scene.str.endswith('dense')], x[x.scene.str.endswith('sparse')]
        full.append([lab, r(xd.ratio.median()), r(xs.ratio.median()), r(xd.frac_cos08.median()), r(xs.frac_cos08.median()), r(xd.speed_ratio.median()), r(xs.speed_ratio.median()), n(x.n.median()), int((x.ratio < 0.8).sum())])
    OUT['5.10'] = md(['method', 'ratio', 'direction', 'speed ratio', 'variants with skill (of 28)'], rows)
    OUT['f510'] = md(['method', 'ratio, dense', 'ratio, sparse', 'direction, dense', 'direction, sparse', 'speed ratio, dense', 'speed ratio, sparse', 'steps scored', 'variants with skill'], full)
retrack()

# ---------------------------------------------------------------- held-out variants: fine-tuned model, strategies
HELD = ['Path4_dense', 'Path4_sparse', 'Low_1_dense', 'Low_1_sparse', 'Low_1_001_dense', 'Low_1_001_sparse', 'low_angle_dense', 'low_angle_sparse', 'Overview_dense', 'Overview_sparse']
import re as _re_cv
def cv_name(t):
    """camera-view names as written in the text: Low_1, Low_1.003, Low_2"""
    t = _re_cv.sub(r'Low[ _]1[ _](00\d)', r'Low_1.\1', t)
    t = _re_cv.sub(r'Low[ ]([12])\b', r'Low_\1', t)
    return t
HLAB = {h: cv_name(h.replace('_001', ' 001').replace('_', ' ').replace('Low 1 ', 'Low 1 ').replace(' dense', ' dense').replace(' sparse', ' sparse')) for h in HELD}
def held_methods():
    F = csv('finetune_v3.csv'); F['ratio'] = ratio(F); F = F[F.scene != 'v2_Path2_dense']
    spec = [('PIPs++', 'Pre-trained, once per block'), ('PIPs++_r2_256', 'Pre-trained, every 2 frames'), ('PIPs++_ft3000_r2_256', 'Fine-tuned, every 2 frames'), ('PTV_tuned_ncc_fd2', 'PTV NCC'), ('PTV_tuned_lk_fd2', 'PTV LK')]
    piv = {m: F[F.method == m].set_index('scene').ratio_h15 for m, _ in spec}
    rows = [[HLAB[h]] + [r(piv[m]['v2_' + h]) for m, _ in spec] for h in HELD]
    rows.append(['Median'] + [r(piv[m].median()) for m, _ in spec]); rows.append(['Variants with skill (ratio < 0.8)'] + [int((piv[m] < 0.8).sum()) for m, _ in spec])
    OUT['f511'] = md(['variant'] + [t for _, t in spec], rows)
    rows2 = []
    for m, t in spec:
        x = F[F.method == m]
        rows2.append([t, r(x.ratio.median()), r(x.ratio_h15.median()), r(x.frac_cos08.median()), r(x.d8.median()), r(x.frac_tracks_follow.median()), r(x.speed_ratio.median()), n(x.n.median()), n(x.n_h15.median())])
    OUT['f512'] = md(['method', 'ratio (all steps)', 'ratio (15 frames)', 'direction', 'within 8 px', 'tracks that follow', 'speed ratio', 'steps scored', 'steps scored (15 frames)'], rows2)
held_methods()

STRAT = [('PIPs++_b2_256', 'S0'), ('PIPs++_ft3000_b2_256', 'S1'), ('PIPs++_S2_b2_256', 'S2'), ('PIPs++_S3_b2_256', 'S3'), ('PIPs++_S3_r48_256', 'S3 long-term'), ('PIPs++_S4_b2_256', 'S4'), ('PIPs++_S5_b2_256', 'S5'), ('PIPs++_S6_b2_256', 'S6'), ('PTV_tuned_ncc_fd2', 'NCC'), ('PTV_tuned_lk_fd2', 'LK')]
def strategies():
    D = pd.concat([csv('strategies_v3.csv'), csv('s6_heldout_v3.csv')]).drop_duplicates(['scene', 'method']); D = D[D.scene != 'v2_Path2_dense']
    piv = {m: D[D.method == m].set_index('scene').ratio_h15 for m, _ in STRAT}
    ncc = piv['PTV_tuned_ncc_fd2']
    dv = {k: pd.read_csv(os.path.join(DAVIS, '%s_S32.csv' % k)).d_avg.mean() for k in ('reference', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6')}
    dmap = {'S0': 'reference', 'S1': 'S1', 'S2': 'S2', 'S3': 'S3', 'S3 long-term': 'S3', 'S4': 'S4', 'S5': 'S5', 'S6': 'S6'}
    simple = []
    for m, lab in STRAT:
        p = piv[m]; better = '–' if lab == 'NCC' else int((p < ncc).sum())
        simple.append([lab, r(p.median()), int((p < 0.8).sum()), better, r(dv[dmap[lab]], 1) if lab in dmap else '–'])
    OUT['5.13'] = md(['strategy', 'median ratio', 'variants with skill (of 10)', 'variants better than NCC', 'DAVIS accuracy (δ~avg~)'], simple)
    rows = [[HLAB[h]] + [r(piv[m]['v2_' + h]) for m, _ in STRAT] for h in HELD]
    rows.append(['Median'] + [r(piv[m].median()) for m, _ in STRAT]); rows.append(['Variants with skill (ratio < 0.8)'] + [int((piv[m] < 0.8).sum()) for m, _ in STRAT]); rows.append(['Variants better than NCC'] + [('–' if l == 'NCC' else int((piv[m] < ncc).sum())) for m, l in STRAT])
    OUT['f513'] = md(['variant'] + [l for _, l in STRAT], rows)
    # DAVIS full
    rows = []
    for key, lab in [('reference', 'reference weights (S0)'), ('S3', 'S3 long clips'), ('S6', 'S6 final'), ('S4', 'S4 rehearsal (50 % PointOdyssey)'), ('S1', 'S1 short clips'), ('S2', 'S2 data + augmentation'), ('S5', 'S5 from scratch')]:
        x = pd.read_csv(os.path.join(DAVIS, '%s_S32.csv' % key)); rows.append([lab, r(x.d_avg.mean(), 1), r(x.survival.mean(), 1), r(x.median_l2.mean(), 1)])
    OUT['f515'] = md(['checkpoint', 'δ~avg~', 'survival (16 px)', 'median error (px)'], rows)
    # per-track and field metrics (held-out)
    V = csv('velocity_field_heldout_v3.csv'); V = V[V.scene != 'v2_Path2_dense']
    extra = os.path.join(RES, 'velocity_field_strategies_v3.csv')
    if os.path.exists(extra) and os.path.getsize(extra) > 10: V = pd.concat([V, pd.read_csv(extra)]).drop_duplicates(['scene', 'method'])
    rows = []
    for m, lab in STRAT:
        x = D[D.method == m]; v = V[V.method == m]
        if len(v) < 10: rows.append([lab, r(x.ratio_h15.median()), r(x.frac_cos08.median()), r(x.frac_tracks_follow.median()), r(x.speed_ratio.median()), 'not computed', '', '', '']); continue
        rows.append([lab, r(x.ratio_h15.median()), r(x.frac_cos08.median()), r(x.frac_tracks_follow.median()), r(x.speed_ratio.median()), r(v.bias_pct.median(), 0), r(v.rmse_pct.median(), 0), r(v.coverage.median()), r(v.frac_ok.median())])
    OUT['f514'] = md(['strategy', 'ratio (15 frames)', 'direction', 'tracks that follow', 'speed ratio', 'speed bias (%)', 'field error (%)', 'water covered', 'cells within target'], rows)
strategies()

# ---------------------------------------------------------------- headline, moving water
def headline():
    M = csv('surfmove_headline_v3.csv'); M = M[~M.scene.str.contains('clear')]; V = csv('velocity_field_surfmove_v3.csv'); V = V[~V.scene.str.contains('clear')]; T = csv('tapvid_surfmove_v3.csv'); T = T[~T.scene.str.contains('clear')]
    spec = [('PIPs++_b2_256', 'PIPs++ pre-trained'), ('PIPs++_S6_b2_256', 'PIPs++ retrained (S6)'), ('PTV_tuned_ncc_fd2', 'PTV NCC'), ('PTV_tuned_lk_fd2', 'PTV LK')]
    ncc = M[M.method == 'PTV_tuned_ncc_fd2'].set_index('scene').ratio_h15
    cols = {}
    for m, lab in spec:
        x = M[M.method == m]; p = x.set_index('scene').ratio_h15; v = V[V.method == m]; t = T[T.method == m]
        cols[lab] = dict(ratio=r(x.ratio_h15.median()), skill=int((p < 0.8).sum()), better=int((p < ncc).sum()) if m != 'PTV_tuned_ncc_fd2' else 0, dirn=r(x.frac_cos08.median()), follow=r(x.frac_tracks_follow.median()), speed=r(x.speed_ratio.median()),
                         davis=r(t.delta_avg.median()), surv=r(t.survival_16.median()), l2=r(t.median_l2.median(), 1), bias=r(v.bias_pct.median(), 0), rmse=r(v.rmse_pct.median(), 0), cov=r(v.coverage.median()), ok=r(v.frac_ok.median()))
    labs = [l for _, l in spec]
    def build(rows): return md(['measure'] + labs, [[nm] + [cols[l][k] for l in labs] for nm, k in rows])
    # 'in short' row: verbal verdict per method (formerly the separate results-at-a-glance table)
    verdict = {'PIPs++ pre-trained': 'No skill on any variant', 'PIPs++ retrained (S6)': 'Follows the water, but underestimates the speed', 'PTV NCC': 'Most accurate, but measures only about half of the water', 'PTV LK': 'Follows the water on 12 variants only'}
    for l in labs: cols[l]['short'] = verdict[l]
    OUT['5.15'] = build([('Ratio (15-frame horizon)', 'ratio'), ('Variants with skill (of 28)', 'skill'), ('Direction agreement', 'dirn'), ('Speed ratio', 'speed'), ('Coverage (water cells with an estimate)', 'cov'), ('Speed bias (%)', 'bias'), ('Field error (% of mean speed)', 'rmse'), ('Water cells within the target', 'ok'), ('In short', 'short')])
    OUT['f516'] = build([('Ratio (15-frame horizon)', 'ratio'), ('Variants with skill (of 28)', 'skill'), ('Variants better than NCC (of 28)', 'better'), ('Direction agreement', 'dirn'), ('Tracks following the flow', 'follow'), ('Speed ratio', 'speed'), ('δ~avg~ (TAP-Vid)', 'davis'), ('Survival (16 px)', 'surv'),
                         ('Median error (px)', 'l2'), ('Speed bias (%)', 'bias'), ('Field error (% of mean speed)', 'rmse'), ('Coverage (water cells with an estimate)', 'cov'), ('Water cells within the target', 'ok')])
def heat():
    """error ratio of every method on every moving-water variant (replaces the heat-map figure); values below 0.8 in bold"""
    M = csv('surfmove_headline_v3.csv'); M = M[~M.scene.str.contains('clear')]; V = csv('velocity_field_surfmove_v3.csv'); V = V[~V.scene.str.contains('clear')]
    sp = V.groupby('scene').true_mean_px.first()
    cols = [('PIPs++_b2_256', 'PIPs++ pre-trained'), ('PIPs++_S6_b2_256', 'PIPs++ retrained (S6)'), ('PTV_tuned_ncc_fd2', 'PTV NCC'), ('PTV_tuned_lk_fd2', 'PTV LK')]
    P = {k: M[M.method == k].set_index('scene').ratio_h15 for k, _ in cols}
    def label(sc):
        t = sc.replace('v2_', '').replace('_surfmove', ''); name, dens = t.rsplit('_', 1); return cv_name(name.replace('_', ' ') + ' ' + dens)
    rows = []
    for sc in sp.sort_values().index:
        rows.append([label(sc), int(round(sp[sc]))] + [bold(r(P[k][sc])) if P[k][sc] < 0.8 else r(P[k][sc]) for k, _ in cols])
    OUT['heat'] = md(['variant', 'flow speed (px/frame)'] + [l for _, l in cols], rows)
    print('heat: skill counts', {l: int((P[k] < 0.8).sum()) for k, l in cols}, '| S6 highest skill speed', int(round(max(sp[sc] for sc in P['PIPs++_S6_b2_256'].index if P['PIPs++_S6_b2_256'][sc] < 0.8))), '| NCC without skill', [label(sc) for sc in P['PTV_tuned_ncc_fd2'].index if P['PTV_tuned_ncc_fd2'][sc] >= 0.8])


headline()
heat()

json.dump(OUT, open(os.path.join(HERE, 'restructure', 'generated_tables.json'), 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for k, v in OUT.items(): print('==', k); print(v)
