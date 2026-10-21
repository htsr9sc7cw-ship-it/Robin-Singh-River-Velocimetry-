"""Traces every number of the chapter text (Chapters 1-7 and the abstract) to the result files.
A number counts as TRACED when it appears (at the shown precision) in a result CSV cell, in a median / mean / count
derived from a CSV column, in a generated table, or in an explicit list of settings of the study. All other numbers are
printed with their sentence for a manual look."""
import re, glob, os, json, itertools
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(HERE, '..', 'v2_project', 'results')
pool = set()
def add(x):
    try: x = float(x)
    except Exception: return
    if not np.isfinite(x): return
    for d in (0, 1, 2, 3, 4):
        pool.add(('%.*f' % (d, x)).rstrip('0').rstrip('.') if d else '%d' % round(x))
        pool.add('%.*f' % (d, x)); pool.add('%.*f' % (d, abs(x)))
        pool.add('%.*f' % (d, abs(x) * 100) if abs(x) <= 2.5 else '')
        pool.add('%d' % round(abs(x) * 100) if abs(x) <= 2.5 else '')
for f in glob.glob(os.path.join(RES, '*.csv')) + glob.glob(os.path.join(HERE, '..', 'finetune', 'results_davis', '*.csv')):
    try: df = pd.read_csv(f)
    except Exception: continue
    num = df.select_dtypes('number')
    for c in num.columns:
        col = num[c].dropna()
        for x in col.head(5000): add(x)
        if len(col): add(col.median()); add(col.mean()); add(col.min()); add(col.max()); add(len(col)); add(col.sum())
    for c in num.columns:                                         # medians by method / by group
        for g in [k for k in df.columns if df[k].dtype == object and df[k].nunique() < 60][:4]:
            for _, sub in df.groupby(g)[c]:
                s = sub.dropna()
                if len(s): add(s.median()); add(s.mean()); add(len(s)); add(s.sum())
tables = json.load(open(os.path.join(HERE, 'restructure', 'generated_tables.json')))
alltxt = '\n'.join(tables.values()) + '\n' + '\n'.join(open(f).read() for f in glob.glob(os.path.join(HERE, 'restructure', '*.md')) if '/n' in f.replace('\\', '/') and os.path.basename(f)[0] == 'n' and os.path.basename(f)[1].isdigit())
tabnums = set(re.findall(r'(?<![\w.])\d+(?:[.,]\d+)?', ''.join(l for l in alltxt.split('\n') if l.startswith('|'))))
pool |= {x.replace(',', '.') for x in tabnums}
settings = set('1 2 3 4 5 6 7 8 9 10 11 12 14 15 16 20 24 28 30 32 36 40 44 48 64 120 256 384 512 1024 3000 2.5 0.8 0.5 0.1 0.2 0.05 0.9 37 18 50 80 95 93 99 100'.split())
files = sorted(glob.glob(os.path.join(HERE, 'restructure', 'n[1-7]_*.md'))) + [os.path.join(HERE, '00_abstracts_draft1.md')]
bad = 0; tot = 0
for f in files:
    for ln, para in enumerate(open(f).read().split('\n'), 1):
        if para.startswith(('|', '#', '**Table', '**Figure', '```', '$$')) or not para.strip(): continue
        t = re.sub(r'`[^`]*`', '', para); t = re.sub(r'\{[TF]:[^}]*\}|Sects?\. [\d.–, and]+|Chapters? \d|Eq\. [\d.]+|\(Eltner[^)]*\)|\([A-Z][^)]*\d{4}[a-z]?\)|[A-Z][a-z]+ et al\.,? \(?\d{4}\)?|[A-Z][a-z]+ \(\d{4}\)|Fig\. [\d.]+|Figures? [\d.]+', '', t)
        t = re.sub(r'\b(?:Path|Low|Low_|S|P|F|D|Table|Figure|Overview|ratio)[ _]?\d+[\d._]*', '', t)
        for m in re.finditer(r'(?<![\w.])[−-]?\d[\d ]*(?:[.,]\d+)?', t):
            raw = m.group(0).replace('−', '').replace('-', '').replace(' ', '').replace(',', '.')
            if not raw: continue
            tot += 1
            if raw in pool or raw in settings or raw.lstrip('0') in pool: continue
            bad += 1
            s = para[max(0, para.find(m.group(0).strip()) - 60): para.find(m.group(0).strip()) + 40].replace('\n', ' ')
            print('%s:%d  %-8s ...%s' % (os.path.basename(f)[:6], ln, raw, s))
print('numbers checked:', tot, ' not traced automatically:', bad)
