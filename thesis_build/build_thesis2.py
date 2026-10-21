"""Build THESIS_DRAFT.docx in the layout of a TU Dresden Hydrosciences master thesis (see thesis/FORMAT_LEARNINGS_50.md).
    /opt/anaconda3/bin/python build_thesis.py            (uses thesis/pagemap.json for the page numbers of the contents lists if present)
Pipeline: assemble.py -> markdown -> pandoc -> THESIS_RAW.docx -> format_thesis.py -> THESIS_DRAFT.docx
"""
import os, re, subprocess, json, sys
HERE = os.path.dirname(os.path.abspath(__file__)); FIG = os.path.join(os.path.dirname(HERE), 'v2_project', 'results', 'figures')
subprocess.run(['/opt/anaconda3/bin/python', 'assemble2.py'], cwd=HERE, check=True)
TITLE = 'Evaluation of AI-Based Particle Tracking Method for Surface Water Velocity Estimation'
src = open(os.path.join(HERE, 'THESIS_FULL_v4.md')).read()
# ---------------------------------------------------------------- split front matter pieces
ab = open(os.path.join(HERE, '00_abstracts_draft1.md')).read()
def piece(h, nxt):
    i = ab.index('# ' + h + '\n'); j = ab.index('# ' + nxt + '\n', i + 1) if nxt else len(ab)
    return ab[i + len(h) + 3:j].strip()
abs_en = piece('Abstract', None)
i = src.index('# 1 Introduction'); body = src[i:]
# ---------------------------------------------------------------- figure / table captions -> lists
out = []; seen = set(); figs = []; tabs = []
for para in body.split('\n\n'):
    cap = re.match(r'\*\*Figure (\d+\.\d+|[A-Z]\.\d+)\*\*\s*(.*)', para, re.S)
    if cap:
        for f in re.findall(r'`((?:fig|gif)[A-Za-z0-9_\-]+\.png)`', para):
            if os.path.exists(os.path.join(FIG, f)) and f not in seen: seen.add(f); out.append('![](figures/%s){ width=100%% }' % f)
        title = re.sub(r'\s*\(\s*\)', '', re.sub(r'`[^`]*`[,;]?\s*', '', cap.group(2).strip())).strip().rstrip('.')
        short = re.split(r'(?<=[a-z0-9\)%])\.\s', title, 1)[0].rstrip('.:')
        figs.append((cap.group(1), short)); out.append('**Figure %s:** %s' % (cap.group(1), title + ('.' if not title.endswith('.') else '')))
        continue
    tc = re.match(r'\*\*Table (\d+\.\d+b?|[A-Z]\.\d+)\*\*\s*(.*)', para, re.S)
    if tc:
        t = re.sub(r'\s*\([^()]*\)', '', tc.group(2).split('\n')[0].strip()); t = re.sub(r'`[^`]*`[,;]?\s*', '', t)
        t = re.split(r'(?<!et al)(?<!incl)(?<!Sect)(?<!Fig)(?<!vs)\.\s', t, 1)[0].rstrip('.:; ')
        tabs.append((tc.group(1), t))
    out.append(para)
body = '\n\n'.join(out).replace('\n---\n', '\n\n')
key = lambda n: [(ord(x) if x.isalpha() else int(re.sub('b', '', x))) if x[0:1].isalpha() or x[0:1].isdigit() else 0 for x in n.split('.')] + [n.endswith('b')]
# ---------------------------------------------------------------- citations: (Author et al., 2020) -> [Author et al., 2020]
refs_md = open(os.path.join(HERE, '08_references.md')).read()
ref_lines = [l for l in refs_md.split('\n') if re.match(r'^\d+\. ', l)]
def fmt_ref(l):
    l = re.sub(r'^\d+\. ', '', l)
    m = re.match(r'^(.*?)\s*\((\d{4})\)\.\s*(.*)$', l, re.S)
    if not m: return l
    au, yr, rest = m.group(1), m.group(2), m.group(3)
    au = au.replace(' and others', ' et al.').replace(' et al.', ', et al.') if 'et al' in au or 'others' in au else au
    au = au.strip()
    if au.endswith('et al.'): au = au[:-6].rstrip(' ,') + ', et al.'
    parts = [x for x in re.split(r',\s+|\s+and\s+', au) if x]
    names = []; k = 0
    while k < len(parts):
        if parts[k] in ('et al.', 'et al'): names.append('et al.'); k += 1; continue
        if k + 1 < len(parts) and re.match(r'^([A-Z]\.\s?)+$', parts[k + 1].strip()): names.append(parts[k + 1].strip() + ' ' + parts[k]); k += 2
        else: names.append(parts[k]); k += 1
    names = [n_ for n_ in names]
    a = ', '.join(names[:-1]) + (', and ' if len(names) > 2 and names[-1] != 'et al.' else (' and ' if len(names) == 2 and names[-1] != 'et al.' else ', ')) + names[-1] if len(names) > 1 else names[0]
    url = ''; mu = re.search(r'\s(https?://\S+)\s*$', rest)
    if mu: url = mu.group(1); rest = rest[:mu.start()]
    rest = rest.rstrip(' .'); 
    rest = re.sub(r'\*\\url\S+\*\.?', '', rest).strip(' .')
    a = a.rstrip('.') if a.endswith('al.') is False else a
    rest = rest.replace('* ,', '*,')
    if url.startswith('https://doi.org/'): tail = ' doi: %s. URL %s' % (url[len('https://doi.org/'):], url)
    elif url: tail = ' URL %s' % url
    else: tail = ''
    return '%s%s %s, %s.%s' % (a, '' if a.endswith('.') else '.', rest, yr, tail)
refs_list = [fmt_ref(l) for l in ref_lines]
refs_block = '# Bibliography\n\n' + '\n\n'.join(refs_list)
body = re.sub(r'# References\n.*?(?=\n# Appendix A)', lambda m: refs_block + '\n', body, flags=re.S)
SURN = ['Ansari', 'Blender Foundation', 'Dixon and Mood', 'Doersch', 'Efron and Tibshirani', 'Eltner', 'Farnebäck', 'Fischler and Bolles', 'Fujita', 'Harley', 'Hauet', 'Hendrickx', 'Karaev', 'Lowe', 'Lucas and Kanade', 'Muste', 'Perks', 'Shi and Tomasi', 'Tauro', 'Teed and Deng', 'Thuerey', 'Welber', 'Zheng', 'Zhu and Bridson']
auth = r'(?:' + '|'.join(re.escape(s) for s in SURN) + r')(?:\s+et\s+al\.?)?(?:\s+and\s+[A-Z][a-z]+)?'
item = auth + r',?\s+(?:19|20)\d{2}[a-z]?(?:,[^;()]*)?'
def _norm(x):
    """'Author et al. 2020' / 'Author et al., 2020' -> 'Author et al., 2020' (Harvard)."""
    x = re.sub(r'\s+', ' ', x.strip())
    return re.sub(r'^(' + auth + r'),?\s+((?:19|20)\d{2}[a-z]?)', r'\1, \2', x)
def group(m):
    g = re.sub(r'\s+', ' ', m.group(1)); items = [x.strip() for x in g.split(';')]
    if all(re.fullmatch(item, x) for x in items): return '(' + '; '.join(_norm(x) for x in items) + ')'
    return m.group(0)
def conv(t):
    """ONE citation scheme (Harvard, round brackets): parenthetical (Eltner et al., 2020; Muste et al., 2008), narrative Eltner et al. (2020).
    Square-bracket forms in the sources are converted to the same scheme."""
    t = re.sub(r'\(([^()]*(?:19|20)\d{2}[^()]*)\)', group, t)
    t = re.sub(r'\[([^\[\]]*(?:19|20)\d{2}[^\[\]]*)\]', group, t)
    t = re.sub(r'\b(' + auth + r')\s+\[((?:19|20)\d{2}[a-z]?(?:,[^\[\]]*)?)\]', lambda m: re.sub(r'\s+', ' ', m.group(1)) + ' (' + re.sub(r'\s+', ' ', m.group(2)) + ')', t)
    return t
body = conv(body)
abs_en = conv(abs_en)
# (no Disclosure section: removed on request)
# ---------------------------------------------------------------- contents, lists
def lvl_of(t):
    if re.match(r'^(\d+|Appendix [A-Z]) ', t) and not re.match(r'^\d+\.\d', t): return 0
    n = re.match(r'^((?:\d+|A)(?:\.\d+)*)\s', t).group(1)
    return n.count('.')
toc_lines = ['@@T0@@List of Figures', '@@T0@@List of Tables', '@@T0@@Nomenclature']
for m in re.finditer(r'^#{1,3}\s+(((?:\d+|A)(?:\.\d+)*\s+|Appendix [A-Z]\s+|Disclosure$|Bibliography$)[^\n]*)$', body, re.M):
    t = m.group(1).strip(); lv = lvl_of(t) if t not in ('Disclosure', 'Bibliography') else 0
    if t.startswith('A.') and lv > 1: continue
    toc_lines.append('@@T%d@@%s' % (lv, t))
toc_lines += ['@@T1@@A.6 Source Code']
contents = '# Contents\n\n' + '\n\n'.join(toc_lines)
def shorten(t, n=105):
    t = re.sub(r'\s*\([^()]*\)\s*', ' ', t).strip()
    parts = re.split(r'\s*[:;]\s+|\s—\s|(?<=[a-z0-9\)%])\.\s', t)
    out_ = parts[0]
    k = 1
    while len(out_) < 14 and k < len(parts): out_ += ': ' + parts[k]; k += 1
    return out_.rstrip(' .:;')
figs = [(n, shorten(t)) for n, t in figs]; tabs = [(n, shorten(t)) for n, t in tabs]
lof = '# List of Figures\n\n' + '\n\n'.join('@@F@@Figure %s: %s' % (n, t) for n, t in sorted(figs, key=lambda x: key(x[0])))
lot = '# List of Tables\n\n' + '\n\n'.join('@@F@@Table %s: %s' % (n, t) for n, t in sorted(tabs, key=lambda x: key(x[0])))
nomen = '# Nomenclature\n\n@@NOMENCLATURE@@'
front = f'''@@TITLEPAGE@@

# Assignment

**Evaluation of AI-Based Particle Tracking Method for Surface Water Velocity Estimation**

Measuring river discharge is a major task in hydrology and hydrometry. It's a key variable to understand river system dynamics, as well as catchment behavior. A common approach to estimate the discharge is the velocity-area method, which uses flow velocity information and wetted river cross-section area. Several methods can be used to estimate river flow velocity, such as current meters, acoustic devices (i.e. acoustic Doppler current profilers), and surface velocity radars. Nevertheless, these methods can be costly and labor-intensive. Therefore, there is a need for more flexible and less costly alternatives.

Image-based approaches have gained attention as a remote sensing and low-cost alternative in several hydrometry applications. Various algorithms can be used to estimate surface flow velocity from images, with emphasis on particle image velocimetry (PIV) and particle tracking velocimetry (PTV). Both algorithms contain a set of parameters to be set, depending mostly on surface velocity to be measured. Consequently, accurate results cannot be achieved using a "one-size-fits-all" configuration, as each river presents unique lighting conditions, surface roughness, and flow speeds.

Recently, AI-based particle tracking has emerged as an alternative to traditional image velocimetry; however, these models were not yet, or poorly, evaluated in environmental problems. Among the AI-based particle tracking, PIPs++ has shown promising results in glacier movement using RGB images. Yet, it remains untested and not evaluated in water surface velocity.

The aim of this master thesis is to systematically evaluate and enhance the application of the PIPs++ deep learning model for particle tracking-based surface water velocity estimation, utilizing a synthetic river surface dataset generated from real image sequences under varying flow and illumination conditions.

The specific objectives of this study are:

1. To evaluate the performance of the pre-trained PIPs++ particle tracking model for estimating surface water velocity from river image sequences.
2. To assess strategies for training or re-training the PIPs++ model using a synthetic river surface particle tracking dataset.
3. To compare the velocity estimation accuracy and robustness of the pre-trained versus re-trained PIPs++ models under diverse environmental conditions.

# Declaration of independent work

@@DECLARATION@@

# Acknowledgments

I express my sincere gratitude to Prof. Dr. Anette Eltner for the opportunity to carry out this research and for her pioneering work on image-based river velocimetry, which forms the scientific foundation of this thesis.

I express my sincere gratitude to Dr. Pedro Zamboni for supervising this research and for his constructive support to the structure and scientific presentation of the thesis.

Above all, I thank my mother, Kalpana Singh. Her love, her patience and her unshakeable belief in me carried me through every stage of my studies, and without her unconditional support and encouragement this thesis would not exist. I dedicate this work to her.

# Abstract

{abs_en}

'''
appE = ''
a8 = open(os.path.join(HERE, 'restructure', 'a8_source_code.md')).read()
md = front + contents + '\n\n' + lof + '\n\n' + lot + '\n\n' + nomen + '\n\n' + body.rstrip() + '\n' + appE + '\n' + a8
open(os.path.join(HERE, '_docx_source.md'), 'w').write(md)
subprocess.run(['/opt/anaconda3/bin/pandoc', '_docx_source.md', '-o', '_build/THESIS_RAW.docx', '--from', 'markdown+pipe_tables', '--metadata', 'title=' + TITLE], cwd=HERE, check=True)
subprocess.run(['/opt/anaconda3/bin/python', 'format_thesis.py', '_build/THESIS_RAW.docx', 'THESIS_DRAFT.docx'], cwd=HERE, check=True)
print('built;', len(seen), 'figures,', len(figs), 'figure captions,', len(tabs), 'table captions,', len(refs_list), 'references')
