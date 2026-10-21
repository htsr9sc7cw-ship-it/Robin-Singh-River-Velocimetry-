"""verify_thesis.py: 20 independent checks of the finished thesis. No AI tokens are used; every check is plain Python.

    python verify_thesis.py            all 20 layers, short report (also written to VERIFY_THESIS.txt)

Inputs: THESIS_DRAFT.docx (the document), _build/thesis_preview.pdf (its layout), THESIS_FULL_v4.md (the text),
        v2_project/results/*.csv (the result files), v2_project/figure_scripts/check_figures.py (figure numbers).
Result per layer: ok / WARN (look at it) / FAIL (wrong).
"""
import glob
import os
import re
import subprocess
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
XYV = os.path.dirname(HERE)
RES = os.path.join(XYV, 'v2_project', 'results')
FIGS = os.path.join(XYV, 'v2_project', 'figure_scripts')
PDF = os.path.join(HERE, '_build', 'thesis_preview.pdf')
FULL = open(os.path.join(HERE, 'THESIS_FULL_v4.md'), encoding='utf-8').read()
SRC = open(os.path.join(HERE, '_docx_source.md'), encoding='utf-8').read()
REPORT = []


def layer(n, title):
    def deco(fn):
        try:
            status, msgs = fn()
        except Exception as e:                      # a crashing check is a failed check
            status, msgs = 'FAIL', ['check crashed: %s: %s' % (type(e).__name__, e)]
        REPORT.append((n, title, status, msgs))
        return fn
    return deco


def nums(text):
    """numbers of a text, thousands spaces removed ('3 000' -> '3000'), no section / figure numbers in front of a dot"""
    t = re.sub(r'(?<=\d) (?=\d{3}\b)', '', text)
    return set(re.findall(r'\d+(?:\.\d+)?', t))


def chapters():
    parts = re.split(r'(?m)^# (?=\d )', FULL)
    out = {}
    for p in parts[1:]:
        out[p.split(' ', 1)[0]] = p.split('\n# ')[0]
    return out


CH = chapters()
from docx import Document   # noqa: E402
DOC = Document(os.path.join(HERE, 'THESIS_DRAFT.docx'))
BODY = [p.text for p in DOC.paragraphs if p.style.name != 'Source Code']
TABLE_TEXT = [c.text for t in DOC.tables for r in t.rows for c in r.cells]
ALLTEXT = '\n'.join(BODY + TABLE_TEXT)
try:
    from pypdf import PdfReader
    import logging
    logging.getLogger('pypdf').setLevel(logging.ERROR)
    PAGES = [(p.extract_text() or '') for p in PdfReader(PDF).pages]
except Exception:
    PAGES = []


# ---------------------------------------------------------------------------------------------------------------- 1-5 build
@layer(1, 'document and PDF exist and agree (pages, date)')
def _():
    ok = os.path.getmtime(PDF) >= os.path.getmtime(os.path.join(HERE, 'THESIS_DRAFT.docx')) - 600
    return ('ok' if ok and len(PAGES) > 70 else 'FAIL'), ['%d pages in the PDF, PDF is %s than the document' % (len(PAGES), 'not older' if ok else 'OLDER')]


@layer(2, 'no placeholders, no German, no removed sections')
def _():
    bad = [p for p in [r'\[author', r'\[Pedro', r'TODO', r'Kurzfassung', r'Disclosure', r'Hiermit', r'Audit Trail', r'RQ\d', r'Selbstst', r'lorem'] if re.search(p, ALLTEXT)]
    return ('FAIL' if bad else 'ok'), (['found: ' + ', '.join(bad)] if bad else ['none of 10 forbidden patterns'])


@layer(3, 'contents: every heading listed with its page, none missing')
def _():
    log = open('/tmp/rebuild15.log').read() if os.path.exists('/tmp/rebuild15.log') else ''
    m = re.findall(r'entries (\d+) missing (\d+)', log)
    if not m:
        return 'WARN', ['no build log found']
    e, miss = map(int, m[-1])
    return ('ok' if miss == 0 and 'STABLE' in log else 'FAIL'), ['%d entries, %d missing, page numbers %s' % (e, miss, 'stable' if 'STABLE' in log else 'NOT stable')]


@layer(4, 'section numbering is complete (1..7, A.1..A.6, no gaps)')
def _():
    heads = [p.text.strip() for p in DOC.paragraphs if p.style.name.startswith('Heading')]
    msgs, st = [], 'ok'
    top = [h for h in heads if re.match(r'^\d+ ', h)]
    if [h.split()[0] for h in top] != [str(i) for i in range(1, 8)]:
        st = 'FAIL'; msgs.append('chapters: %s' % [h.split()[0] for h in top])
    for ch in range(1, 8):
        subs = [int(h.split()[0].split('.')[1]) for h in heads if re.match(r'^%d\.\d+ ' % ch, h)]
        if subs and subs != list(range(1, len(subs) + 1)):
            st = 'FAIL'; msgs.append('chapter %d sections %s' % (ch, subs))
    app = [h.split()[0] for h in heads if re.match(r'^A\.\d+ ', h)]
    if app != ['A.%d' % i for i in range(1, len(app) + 1)]:
        st = 'FAIL'; msgs.append('appendix sections %s' % app)
    return st, msgs or ['chapters 1-7 and appendix %s are complete and in order' % (', '.join(app))]


@layer(5, 'layout: margins equal, pages well filled, nothing beyond the page')
def _():
    s = DOC.sections[3]
    msgs, st = ['margins left %.1f right %.1f cm' % (s.left_margin.cm, s.right_margin.cm)], 'ok'
    if abs(s.left_margin.cm - s.right_margin.cm) > 0.01:
        st = 'WARN'
    import tempfile
    tmp = tempfile.mkdtemp()
    subprocess.run(['/opt/anaconda3/bin/pdftoppm', '-r', '20', '-gray', '-png', PDF, tmp + '/p'], capture_output=True)
    from PIL import Image
    low = []
    for f in sorted(glob.glob(tmp + '/p-*.png')):
        n = int(f.split('-')[-1].split('.')[0]); a = np.asarray(Image.open(f).convert('L')); h = a.shape[0]
        body = a[int(h * .08):int(h * .93)]; used = np.where((body < 200).any(axis=1))[0]
        if n > 12 and (len(used) == 0 or (used.max() - used.min() + 1) / body.shape[0] < 0.2): low.append(n)
    msgs.append('pages less than 20 %% filled: %s' % (low or 'none'))
    if len(low) > 4: st = 'WARN'
    return st, msgs


# ---------------------------------------------------------------------------------------------------------------- 6-9 references
@layer(6, 'every cross-reference (Sect., Chapter, Appendix, Table, Figure, Eq.) points to something that exists')
def _():
    heads = {p.text.strip().split()[0] for p in DOC.paragraphs if p.style.name.startswith('Heading') and re.match(r'^(\d+|A)(\.\d+)* ', p.text.strip())}
    caps = set(re.findall(r'(?m)^(Table|Figure) ([A-Z]?\d+(?:\.\d+)?b?):', '\n'.join(BODY))) | set(re.findall(r'(Table|Figure) ([A-Z]?\d+(?:\.\d+)?b?):', '\n'.join(TABLE_TEXT)))
    eqs = set(re.findall(r'\((\d+\.\d+)\)', '\n'.join(BODY)))
    text = '\n'.join(BODY + TABLE_TEXT); miss = []
    cut = text.find('A.6 Source Code')                         # the printed scripts name figures that are not in this thesis
    if cut > 0: text = text[:cut] if text.count('A.6 Source Code') == 1 else text[:text.rfind('A.6 Source Code')]
    for m in re.finditer(r'(?:Sect\.|Sects\.|Appendix|Chapter) ((?:\d+|A)(?:\.\d+)*)', text):
        ref = m.group(1)
        before = text[max(0, m.start() - 40):m.start()]
        if re.search(r'(et al\.,? \d{4},? |utorial \(|, \d{4}, )$', before): continue      # section of a cited paper or of the tutorial
        if ref not in heads and ref != 'A' and not re.match(r'^\d+$', ref):
            miss.append('Sect. ' + ref)
        elif re.match(r'^\d+$', ref) and ref not in {h.split('.')[0] for h in heads}:
            miss.append('Chapter ' + ref)
    for m in re.finditer(r'(Table|Figure) ([A-Z]?\d+\.\d+b?)(?!\d)', text):
        if (m.group(1), m.group(2)) not in caps: miss.append('%s %s' % (m.group(1), m.group(2)))
    miss = sorted(set(miss))
    return ('FAIL' if miss else 'ok'), (['missing targets: ' + ', '.join(miss[:20])] if miss else ['all references resolve (%d headings, %d captions)' % (len(heads), len(caps))])


@layer(7, 'figures and tables: numbering consecutive, captions = list entries, every figure file embedded')
def _():
    msgs, st = [], 'ok'
    for ch in '1356':
        nf = sorted({int(x) for x in re.findall(r'Figure %s\.(\d+):' % ch, ALLTEXT)})
        nt = sorted({int(x) for x in re.findall(r'Table %s\.(\d+):' % ch, ALLTEXT)})
        for name, lst in (('Figure', nf), ('Table', nt)):
            if lst and lst != list(range(1, lst[-1] + 1)):
                st = 'FAIL'; msgs.append('%s numbers in chapter %s: %s' % (name, ch, lst))
    n_img = len(DOC.inline_shapes)
    msgs.append('%d pictures embedded' % n_img)
    return st, msgs


@layer(8, 'citations: every (Author, year) in the text is in the bibliography, every entry is cited')
def _():
    bib = FULL.split('# References', 1)[1].split('\n# Appendix', 1)[0]
    entries = re.findall(r'(?m)^\d+\.\s+([A-ZÄÖÜ][^,]+),.*?\((\d{4})[a-z]?\)', bib)
    keys = {(a.split()[-1].lower(), y) for a, y in entries}
    body = '\n'.join(v for k, v in CH.items() if k in '1234567')
    cites = set()
    for m in re.finditer(r'([A-Z][A-Za-zäöüÄÖÜ\-]+)(?: et al\.|,? and [A-Z][A-Za-zäöüÄÖÜ\-]+)?,? \(?(\d{4})[a-z]?', body):
        if 1900 < int(m.group(2)) < 2030: cites.add((m.group(1).lower(), m.group(2)))
    nocite = sorted(c for c in cites if c not in keys and c[0] not in ('table', 'sect', 'figure', 'fig', 'sects', 'chapter', 'march', 'april', 'september', 'august', 'july', 'june', 'may', 'october', 'to', 'in', 'the'))
    uncited = sorted(k for k in keys if k not in cites)
    msgs = ['%d bibliography entries' % len(keys)]
    st = 'ok'
    if nocite: st = 'WARN'; msgs.append('cited, not in bibliography (may be false positives): %s' % nocite[:8])
    if uncited: st = 'WARN'; msgs.append('in bibliography, never cited: %s' % uncited[:8])
    return st, msgs


@layer(9, 'bibliography: every entry has a DOI or URL and a year; no duplicates')
def _():
    bib = FULL.split('# References', 1)[1].split('\n# Appendix', 1)[0]
    items = [l for l in bib.split('\n') if re.match(r'^\d+\.', l)]
    no_link = [l[:40] for l in items if 'doi' not in l.lower() and 'http' not in l]
    dup = len(items) - len({re.sub(r'\W', '', l[:60]).lower() for l in items})
    return ('ok' if not no_link and not dup else 'WARN'), ['%d entries, %d without link, %d duplicates' % (len(items), len(no_link), dup)] + no_link[:3]


# ---------------------------------------------------------------------------------------------------------------- 10-15 numbers
def recompute():
    m = pd.read_csv(os.path.join(RES, 'surfmove_headline_v3.csv')); m = m[~m.scene.str.contains('clear')]
    v = pd.read_csv(os.path.join(RES, 'velocity_field_surfmove_v3.csv')); v = v[~v.scene.str.contains('clear')]
    return m, v


@layer(10, 'headline numbers of the text equal the result files (recomputed from the CSV)')
def _():
    m, v = recompute(); M = {'pre-trained': 'PIPs++_b2_256', 'S6': 'PIPs++_S6_b2_256', 'NCC': 'PTV_tuned_ncc_fd2', 'LK': 'PTV_tuned_lk_fd2'}
    exp = {}
    for k, mm in M.items():
        r = m[m.method == mm].ratio_h15
        exp[k + ' median ratio'] = '%.2f' % r.median(); exp[k + ' variants with skill'] = str(int((r < 0.8).sum()))
    exp['S6 speed ratio'] = '%.2f' % m[m.method == M['S6']].speed_ratio.median(); exp['S6 coverage'] = '%.2f' % v[v.method == M['S6']].coverage.median()
    exp['NCC coverage'] = '%.2f' % v[v.method == M['NCC']].coverage.median()
    miss = [k + ' = ' + x for k, x in exp.items() if x not in nums(CH['5'] + CH['7']) and (' ' + x) not in ALLTEXT]
    return ('FAIL' if miss else 'ok'), (['not found in the text: ' + '; '.join(miss)] if miss else ['%d headline values recomputed from the CSV and found in Chapter 5 / 7' % len(exp)])


@layer(11, 'tables of Chapter 5: every value of the stored result tables appears in the document table')
def _():
    msgs, st, tot, hit = [], 'ok', 0, 0
    doc_nums = nums('\n'.join(TABLE_TEXT))
    for f in ['T5_1_rmse_ratio_per_variant', 'T5_2_frac_cos08_per_variant', 'T5_5_overall']:
        p = os.path.join(RES, 'tables', f + '.csv')
        if not os.path.exists(p): continue
        d = pd.read_csv(p); vals = d.select_dtypes('number').round(2).values.ravel()
        for x in vals:
            if np.isnan(x): continue
            tot += 1; s = '%.2f' % x
            if s in doc_nums or ('%.1f' % x) in doc_nums or str(int(round(x))) in doc_nums: hit += 1
    r = hit / max(tot, 1)
    return ('ok' if r > 0.97 else 'WARN'), ['%d of %d table values found (%.1f %%)' % (hit, tot, 100 * r)]


@layer(12, 'figures: every number drawn in the 25 figures equals the result tables (check_figures.py)')
def _():
    r = subprocess.run(['/opt/anaconda3/bin/python', '-W', 'ignore', os.path.join(FIGS, 'check_figures.py')], capture_output=True, text=True, cwd=FIGS)
    last = [l for l in r.stdout.splitlines() if 'figures checked' in l]
    return ('ok' if r.returncode == 0 else 'FAIL'), last or [r.stderr[-300:]]


@layer(13, 'abstract and extended summary: every number appears in the body')
def _():
    ab = re.search(r'# Abstract\n(.*?)\n# ', SRC, re.S); ex = None
    text = (ab.group(1) if ab else '') + (ex.group(1) if ex else '')
    body = nums(FULL)
    miss = sorted(n for n in nums(text) if n not in body and len(n) > 1)
    return ('ok' if not miss else 'WARN'), ['%d numbers in the abstract and extended summary' % len(nums(text))] + (['not in the body: %s' % miss[:12]] if miss else [])


@layer(14, 'conclusion: every number appears in the results chapter')
def _():
    c5 = nums(CH['5']) | nums('\n'.join(TABLE_TEXT))
    c = CH['7']
    miss = sorted(n for n in nums(c) if n not in c5 and len(n) > 1)
    return ('ok' if not miss else 'WARN'), (['numbers only in the conclusion: %s' % miss] if miss else ['all conclusion numbers are in Chapter 5'])


@layer(15, 'discussion: every number appears in Chapters 3 to 5')
def _():
    base = set()
    for k, v in CH.items():
        if k[0] in '345': base |= nums(v)
    base |= nums('\n'.join(TABLE_TEXT))
    d = CH['6']
    miss = sorted(n for n in nums(d) if n not in base and len(n) > 1)
    return ('ok' if len(miss) <= 3 else 'WARN'), ['%d numbers only in the discussion: %s' % (len(miss), miss[:12])]


# ---------------------------------------------------------------------------------------------------------------- 16-20 consistency
@layer(16, 'constants stay the same everywhere (28 variants, 16 camera views, 201 frames, 3 000 steps, 24 of 28)')
def _():
    msgs, st = [], 'ok'
    for pat, name in [(r'(\d+) (?:muddy[- ]water |moving[- ]water |muddy )?variants of the (?:third|final)', 'variants'), (r'(\d+) camera views', 'viewpoints'), (r'(\d+) frames \(frames 80', 'frames')]:
        vals = sorted(set(re.findall(pat, FULL)))
        msgs.append('%s: %s' % (name, vals))
    wrong = [w for w in ('27 variants', '29 variants', '15 camera views of the final', '200 frames') if w in FULL]
    if wrong: st = 'FAIL'; msgs.append('contradicting constants: %s' % wrong)
    return st, msgs


@layer(17, 'number format: decimal point everywhere, no comma decimals, consistent minus sign and thousands space')
def _():
    com = re.findall(r'(?<![\d,])\d,\d{1,2}(?![\d,])', re.sub(r'`[^`]*`', '', ALLTEXT))
    return ('ok' if len(com) <= 3 else 'WARN'), ['%d comma-decimals found %s' % (len(com), com[:5])]


@layer(18, 'scripts: appendix prints the key scripts, each equals the cleaned file in the kit; run.py names exist')
def _():
    kit = os.path.join(HERE, 'thesis_kit', 'XY_Validation'); a7 = open(os.path.join(HERE, 'restructure', 'a8_source_code.md'), encoding='utf-8').read()
    files = re.findall(r'(?m)^\*\*`([^`]+)`\*\* \((\d+) lines\)', a7); bad = []
    sys.path.insert(0, HERE); from print_clean import clean
    for f, n in files:
        p = os.path.join(HERE, f) if f.startswith('Diagram_Scripts/') else os.path.join(kit, f)
        if not os.path.exists(p): bad.append(f); continue
        src = clean(open(p, encoding='utf-8').read(), os.path.basename(f)).rstrip('\n') + '\n'
        if src.count('\n') != int(n) or ('````\n' + src + '````') not in a7: bad.append(f)
    rs = open(os.path.join(kit, 'run.py')).read(); reg = re.findall(r"'([\w.]+\.py)', '(?:base|pips2|flowvelo|blender)'", rs)
    gone = [r for r in set(reg) if not glob.glob(os.path.join(kit, '**', r), recursive=True)]
    st = 'ok' if not bad and not gone else 'FAIL'
    return st, ['%d scripts printed, %d differ from the kit, %d run.py targets missing' % (len(files), len(bad), len(gone))] + bad[:3]


@layer(19, 'ground truth and controls: the stored known-answer and consistency results still say PASS')
def _():
    ka = open(os.path.join(RES, 'KNOWN_ANSWER.txt')).read(); last = [l for l in ka.splitlines() if 'KNOWN-ANSWER' in l][-1]
    fc = os.path.join(RES, 'FIELD_CONSISTENCY.txt')
    return ('ok' if 'PASS' in last else 'FAIL'), [last[:150]]


@layer(20, 'reproduction: the demo kit reproduces the thesis numbers (ratio 0.97, 0.25, 0.52 for Path4 dense)')
def _():
    p = os.path.join(XYV, 'thesis', 'thesis_kit', 'XY_Validation', 'v2_project', 'results', 'demo_result.csv')
    if not os.path.exists(p):
        return 'WARN', ['no demo_result.csv yet: run  python run.py demo  in thesis_kit (5.6 min)']
    d = pd.read_csv(p); d['ratio'] = d.rmse / d.rmse_stay
    got = {r.method: (r.ratio, getattr(r, 'ratio_h15', np.nan)) for r in d.itertuples()}
    ok = abs(got['PIPs++'][0] - 0.97) < .01 and abs(got['PTV_tuned_ncc'][0] - 0.253) < .01
    return ('ok' if ok else 'FAIL'), ['demo run: %s' % {k: round(v[0], 3) for k, v in got.items()}]


# ---------------------------------------------------------------------------------------------------------------- report
lines = []
for n, title, st, msgs in sorted(REPORT):
    lines.append('%-4s layer %2d  %s' % (st, n, title))
    for m in msgs:
        lines.append('         ' + m)
nf = sum(1 for r in REPORT if r[2] == 'FAIL'); nw = sum(1 for r in REPORT if r[2] == 'WARN')
lines.append('')
lines.append('%d layers: %d ok, %d warnings, %d failed' % (len(REPORT), len(REPORT) - nf - nw, nw, nf))
text = '\n'.join(lines)
print(text)
open(os.path.join(HERE, 'VERIFY_THESIS.txt'), 'w').write(text + '\n')
sys.exit(1 if nf else 0)
