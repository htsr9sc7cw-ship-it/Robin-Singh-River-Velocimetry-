"""results_stats.py

Thesis section: 3.5
Inputs: result CSV
Outputs: medians with bootstrap intervals and paired sign tests

Statistics for the headline tables (plan: recommendation 1). Variants are the unit.  For a results CSV with columns
scene, method, <metric>: per method the median with a bootstrap 95 % interval (10 000 resamples of variants), and for every
method pair the paired sign test (two-sided exact binomial on the variants where the two differ) with the number of wins.
usage: python results_stats.py --csv results/strategies_v3.csv --metric ratio_h15 [--methods ...] [--exclude v2_Path2_dense] [--lower-better] --out results/stats_<name>.md
"""

import argparse, csv, itertools, math, numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--csv', required=True)
ap.add_argument('--metric', default='ratio_h15')
ap.add_argument('--methods', nargs='*')
ap.add_argument('--exclude', nargs='*', default=[])
ap.add_argument('--lower-better', action='store_true', default=True)
ap.add_argument('--out', required=True)
ap.add_argument('--seed', type=int, default=0)
a = ap.parse_args()
rng = np.random.default_rng(a.seed)
rows = [
    r
    for r in csv.DictReader(open(a.csv))
    if r['scene'] not in a.exclude and r.get(a.metric, '') not in ('', 'nan')
]
meth = a.methods or sorted({r['method'] for r in rows})
val = {(r['scene'], r['method']): float(r[a.metric]) for r in rows}


def boot_ci(x, n=10000):
    x = np.asarray(x)
    b = np.median(rng.choice(x, (n, len(x)), replace=True), axis=1)
    return np.percentile(b, 2.5), np.percentile(b, 97.5)


def sign_test(w, l):
    n = w + l
    k = min(w, l)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2**n * 2 if n else float('nan')
    return min(p, 1.0)


L = [
    '# %s — %s (variants = %d, excluded %s)'
    % (a.csv, a.metric, len({r['scene'] for r in rows}), a.exclude or 'none'),
    '',
    '| method | n | median | 95 % CI (bootstrap) |',
    '|---|---|---|---|',
]
for m in meth:
    x = [v for (s, mm), v in val.items() if mm == m]
    if x:
        lo, hi = boot_ci(x)
        L.append('| %s | %d | %.3f | [%.3f, %.3f] |' % (m, len(x), np.median(x), lo, hi))
L += ['', '| A | B | A better | B better | ties | sign-test p |', '|---|---|---|---|---|---|']
for m1, m2 in itertools.combinations(meth, 2):
    sc = [s for (s, mm) in val if mm == m1 and (s, m2) in val]
    if not sc:
        continue
    d = np.array([val[(s, m1)] - val[(s, m2)] for s in sc])
    w = int((d < 0).sum()) if a.lower_better else int((d > 0).sum())
    l = int((d > 0).sum()) if a.lower_better else int((d < 0).sum())
    L.append('| %s | %s | %d | %d | %d | %.3f |' % (m1, m2, w, l, len(sc) - w - l, sign_test(w, l)))
open(a.out, 'w').write('\n'.join(L) + '\n')
print('\n'.join(L[:12]))
