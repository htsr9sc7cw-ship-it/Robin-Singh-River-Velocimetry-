"""Independent recomputation of the headline numbers of the thesis straight from the result files (own code, not make_tables.py).
Prints one line per claim: the value the thesis states, the value found in the files, OK / DIFF."""
import os, re, glob
import numpy as np, pandas as pd
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'v2_project', 'results')
rd = lambda f: pd.read_csv(os.path.join(R, f))
res = []
def chk(name, claim, found, tol=0.0051):
    ok = abs(claim - found) <= tol; res.append(ok); print('%-4s %-62s thesis %-8s files %-8s' % ('OK' if ok else 'DIFF', name, claim, round(float(found), 3)))
mud = lambda d: d[~d.scene.str.contains('_ts|clear')]
# --- still surface, 28 muddy variants
d = mud(rd('three_way_v2_with_fseed.csv')); d = d.assign(ratio=d.rmse / d.rmse_stay)
g = lambda m: d[d.method == m]
chk('still: scenes (28 muddy)', 28, g('PTV_tuned_ncc').scene.nunique(), 0)
for m, lab, c in [('PIPs++', 'pre-trained', .99), ('PTV_tuned_ncc', 'NCC', .62), ('PTV_tuned_lk', 'LK', .97)]: chk('still: median ratio ' + lab, c, g(m).ratio.median())
chk('still: NCC variants with skill', 23, (g('PTV_tuned_ncc').ratio < 0.8).sum(), 0)
chk('still: NCC direction agreement', 0.93, g('PTV_tuned_ncc').frac_cos08.median())
chk('still: pre-trained speed ratio', 0.04, g('PIPs++').speed_ratio.median())
chk('still: feature-seeded ratio', 0.99, g('PIPs++_fseed').ratio.median())
chk('still: NCC ratio min', 0.09, g('PTV_tuned_ncc').ratio.min()); chk('still: NCC ratio max', 1.20, g('PTV_tuned_ncc').ratio.max())
n = g('PTV_tuned_ncc'); dn = n[n.scene.str.endswith('dense')]; sp = n[n.scene.str.endswith('sparse')]
chk('still: NCC dense median', 0.30, dn.ratio.median()); chk('still: NCC sparse median', 0.73, sp.ratio.median())
chk('still: NCC dense below 0.8', 13, (dn.ratio < .8).sum(), 0); chk('still: NCC sparse below 0.8', 10, (sp.ratio < .8).sum(), 0)
chk('still: PIPs++ sub-steps min (thousands)', 29, g('PIPs++').n.min() / 1000, 0.5); chk('still: PIPs++ sub-steps max (thousands)', 48, g('PIPs++').n.max() / 1000, 0.5); chk('still: NCC sub-steps max (Path2 dense)', 3366, n.n.max(), 0)
# --- moving water, 28 muddy variants
m = rd('surfmove_headline_v3.csv'); m = m[~m.scene.str.contains('clear')]
v = rd('velocity_field_surfmove_v3.csv'); v = v[~v.scene.str.contains('clear')]
spec = {'PIPs++_b2_256': ('pre-trained', .93, 0, .33, .05, .94, -67), 'PIPs++_S6_b2_256': ('S6', .69, 24, .77, .71, .99, -42), 'PTV_tuned_ncc_fd2': ('NCC', .49, 24, .94, 1.00, .56, -10), 'PTV_tuned_lk_fd2': ('LK', .81, 12, .73, .12, .88, -68)}
for k, (lab, ra, sk, di, sr, co, bi) in spec.items():
    x = m[m.method == k]; y = v[v.method == k]
    chk('moving: %s scenes' % lab, 28, x.scene.nunique(), 0)
    chk('moving: %s median ratio15' % lab, ra, x.ratio_h15.median()); chk('moving: %s variants with skill' % lab, sk, (x.ratio_h15 < .8).sum(), 0)
    chk('moving: %s direction' % lab, di, x.frac_cos08.median()); chk('moving: %s speed ratio' % lab, sr, x.speed_ratio.median())
    chk('moving: %s coverage' % lab, co, y.coverage.median()); chk('moving: %s speed bias %%' % lab, bi, y.bias_pct.median(), 0.51)
ncc = m[m.method == 'PTV_tuned_ncc_fd2'].set_index('scene').ratio_h15; s6 = m[m.method == 'PIPs++_S6_b2_256'].set_index('scene').ratio_h15
chk('moving: S6 better than NCC (variants)', 7, (s6 < ncc).sum(), 0)
chk('moving: S6 water cells within target', 0.30, v[v.method == 'PIPs++_S6_b2_256'].frac_ok.median()); chk('moving: NCC water cells within target', 0.45, v[v.method == 'PTV_tuned_ncc_fd2'].frac_ok.median())
chk('moving: NCC field error %', 29, v[v.method == 'PTV_tuned_ncc_fd2'].rmse_pct.median(), 0.51)
# --- ten held-out variants
ho = ('Path4', 'Low_1_dense', 'Low_1_sparse', 'Low_1_001', 'low_angle', 'Overview')
s = pd.concat([rd('strategies_v3.csv'), rd('s6_heldout_v3.csv')]).drop_duplicates(['scene', 'method'])
s = s[s.scene.str.contains('Path4|Low_1_dense|Low_1_sparse|Low_1_001|low_angle|Overview') & ~s.scene.str.contains('_ts|clear|surfmove|Low_1_00[23]')]
s = s[~s.scene.str.contains('Path4') | s.scene.str.contains('Path4_(dense|sparse)$')]
print('held-out scenes found:', s.scene.nunique())
for k, lab, c in [('PIPs++_r2_256', 'S0 pre-trained (restarted every 2 frames)', .98), ('PIPs++_ft3000_b2_256', 'S1', .72), ('PIPs++_S6_b2_256', 'S6', .69), ('PTV_tuned_ncc_fd2', 'NCC', .62)]:
    x = s[s.method == k]
    if len(x) >= 10: chk('held-out: median ratio15 %s (n=%d)' % (lab, len(x)), c, x.ratio_h15.median()); chk('held-out: %s variants with skill' % lab, {'S6': 8, 'NCC': 7}.get(lab, (x.ratio_h15 < .8).sum()), (x.ratio_h15 < .8).sum(), 0)
    else: print('SKIP held-out %s: only %d rows' % (lab, len(x)))
# --- TAP-Vid-DAVIS
D = os.path.join(R, '..', '..', 'finetune', 'results_davis')
for f, lab, c in [('reference', 'reference weights', 66.4), ('S6', 'S6', 58.7), ('S5', 'S5 from scratch', 11.9)]:
    t = pd.read_csv(os.path.join(D, f + '_S32.csv')); chk('DAVIS: delta_avg ' + lab, c, t.d_avg.mean(), 0.06)
# --- ground-truth control
ka = open(os.path.join(R, 'KNOWN_ANSWER.txt')).read(); last = {}
for l in ka.splitlines():
    mm = re.search(r'KNOWN-ANSWER (\S+) .*-> (PASS_FLOOR|PASS|FAIL|SKIP\w*)', l)
    if mm: last[mm.group(1)] = mm.group(2)
cnt = pd.Series(last).value_counts().to_dict(); print('known-answer final status per variant:', cnt, 'variants', len(last))
print('\n%d of %d checks match' % (sum(res), len(res)))

# ---------------------------------------------------------------- second batch: re-tracking every 2 frames, cascade, fine-tuning
print('\n--- batch 2')
res2 = []
def chk2(name, claim, found, tol=0.0051):
    ok = abs(claim - found) <= tol; res2.append(ok); print('%-4s %-62s thesis %-8s files %-8s' % ('OK' if ok else 'DIFF', name, claim, round(float(found), 3)))
k = mud(rd('three_way_v3_k2.csv')); k = k.assign(ratio=k.rmse / k.rmse_stay)
for mth, lab, c in [('PIPs++_r2_256', 'pre-trained every 2 frames', .97), ('PIPs++_r1_256', 'pre-trained every frame', .93), ('PTV_tuned_ncc_fd2', 'NCC every 2 frames', .64), ('PTV_tuned_lk_fd2', 'LK every 2 frames', .98)]:
    x = k[k.method == mth]; chk2('k2 ratio ' + lab + ' (n=%d)' % len(x), c, x.ratio.median())
x = k[k.method == 'PIPs++_r2_256'].set_index('scene').ratio; y = d[d.method == 'PIPs++'].set_index('scene').ratio
chk2('k2: scenes where re-tracking lowers PIPs++ ratio', 26, (x.reindex(y.index) < y).sum(), 0)
chk2('k2: pre-trained direction', 0.38, k[k.method == 'PIPs++_r2_256'].frac_cos08.median()); chk2('k2: pre-trained speed ratio', 0.09, k[k.method == 'PIPs++_r2_256'].speed_ratio.median())
chk2('k2: NCC variants with skill', 22, (k[k.method == 'PTV_tuned_ncc_fd2'].ratio < .8).sum(), 0)
# cascade of the three FlowVelo modes (28 muddy variants, summed)
for mth, lab in [('PTV_tuned_ncc', 'NCC'), ('PTV_tuned_lk', 'LK'), ('PTV_gui_defaults', 'GUI')]:
    x = g(mth); raw, mc, fin = x.raw.sum(), x.after_mincount.sum(), x.final.sum()
    print('     cascade %-4s raw %d  after min-count %d (%.1f %% removed)  final %d (%.1f %% kept)' % (lab, raw, mc, 100 * (1 - mc / raw), fin, 100 * fin / raw))
cc = rd('cascade_corrected.csv'); cc = cc[~cc.scene.str.contains('_ts|clear')]
print('     corrected cascade columns:', list(cc.columns)); print(cc.groupby('mode')[['n_after_mincount', 'her_final', 'corrected_steady_range']].sum().to_string())
print('\nbatch 2: %d of %d checks match' % (sum(res2), len(res2)))

# ---------------------------------------------------------------- batch 3: retraining strategies on the ten held-out variants
print('\n--- batch 3')
res3 = []
def chk3(name, claim, found, tol=0.0051):
    ok = abs(claim - found) <= tol; res3.append(ok); print('%-4s %-62s thesis %-8s files %-8s' % ('OK' if ok else 'DIFF', name, claim, round(float(found), 3)))
A = pd.concat([rd('strategies_v3.csv'), rd('s6_heldout_v3.csv')]).drop_duplicates(['scene', 'method'])
A = A[A.scene.str.contains('Path4_(?:dense|sparse)$|Low_1_dense|Low_1_sparse|Low_1_001|low_angle|Overview') & ~A.scene.str.contains('_ts|clear|surfmove|Low_1_00[23]')]
P = lambda mth: A[A.method == mth].set_index('scene')
for mth, lab, c in [('PIPs++_S2_b2_256', 'S2', .71), ('PIPs++_S3_b2_256', 'S3 fresh seeds', .75), ('PIPs++_S3_r48_256', 'S3 long-term', .69), ('PIPs++_S4_b2_256', 'S4', .71), ('PIPs++_S5_b2_256', 'S5 from scratch', 1.04), ('PIPs++_S6_r48_256', 'S6 long-term', .72), ('PIPs++_S6_b2_512', 'S6 native 512 px', .72)]:
    x = P(mth)
    if len(x) == 10: chk3('held-out median ratio15 ' + lab, c, x.ratio_h15.median())
    else: print('SKIP', lab, len(x))
s6, nc = P('PIPs++_S6_b2_256'), P('PTV_tuned_ncc_fd2')
chk3('S6 direction agreement', 0.82, s6.frac_cos08.median()); chk3('S6 speed ratio (256 px)', 0.76, s6.speed_ratio.median())
x5 = P('PIPs++_S6_b2_512'); chk3('S6 speed ratio (512 px)', 0.90, x5.speed_ratio.median()) if len(x5) == 10 else None
chk3('S6 wins against NCC (of 10)', 3, (s6.ratio_h15 < nc.reindex(s6.index).ratio_h15).sum(), 0)
s2, s5 = P('PIPs++_S2_b2_256'), P('PIPs++_S5_b2_256')
chk3('S5 loses to S2 on (of 10)', 10, (s5.ratio_h15 > s2.reindex(s5.index).ratio_h15).sum(), 0)
print('\nbatch 3: %d of %d checks match' % (sum(res3), len(res3)))
