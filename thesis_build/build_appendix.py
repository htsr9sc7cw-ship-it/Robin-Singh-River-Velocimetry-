import re, glob
old = open('THESIS_DRAFT_rev3_chapters_1-4.m.md').read()
B = open('APPENDIX_B_modifications.m.md').read()
C = open('APPENDIX_C_audit_trail.m.md').read()
def between(s, a, b):
    i = s.index(a); j = s.index(b, i + 1) if b else len(s); return s[i:j]
# defects (old 4.1.3 and 4.2.4) and the per camera view parameter table (old Table 4.2)
d1 = between(old, '### 4.1.3 Defects in the Inherited Driver', '## 4.2 FlowVelo')
d1 = re.sub(r'^### 4\.1\.3 .*\n', '', d1).split('\n---')[0].strip()
d2 = between(old, '### 4.2.4 Defects in the Published', '### 4.2.5')
d2 = re.sub(r'^### 4\.2\.4 .*\n', '', d2).split('\n---')[0].strip()
tp = between(old, '**Table {T:4.2}**', 'The formulas are those of')
tp = tp.strip()
tp_text = between(old, 'The formulas are those of', 'A second, *blind*').strip()
# Appendix B content: drop title + intro, demote headings B.n -> A.3.n
Bi = B.split('\n## B.1', 1)[1]; Bi = '## B.1' + Bi
Bi = re.sub(r'(?m)^## B\.(\d) ', lambda m: '### A.3.%s ' % m.group(1), Bi)
Bi = Bi.replace('B.5', 'A.3.5')
Ci = C.split('\n', 2)[2] if C.startswith('# Appendix C') else C
# result sources
rows = []
for f in ['n3_methodology.md', 'n4_study_data.md', 'n5_results.md', 'n6_discussion.md']:
    for m in re.finditer(r'(?m)^\*\*(Table|Figure) \{([FT]):([^}]+)\}\*\*(.*)$', open(f).read()):
        files = re.findall(r'`((?:results|finetune|fig|ptv|rerender|v2_project|thesis)[^`]*\.(?:csv|txt|png|md|py|pth))`', m.group(4))
        if files: rows.append('| %s {%s:%s} | %s |' % (m.group(1), m.group(2), m.group(3), ', '.join('`%s`' % x for x in files[:3])))
src = '\n'.join(rows)

import json, os, re as _re
_R = os.path.dirname(os.path.abspath(__file__))
try:
    NSCRIPTS = open(os.path.join(_R, 'a8_source_code.md')).read().count('\n**`')
except OSError:
    NSCRIPTS = 62
_dm = json.load(open(os.path.join(_R, '..', 'diagram_map.json')))
_png2script = {p: sc for sc, ps in _dm.items() for p in ps}
_rows = []
for _ch in range(1, 8):
    _fs = [x for x in os.listdir(_R) if x.startswith('n%d_' % _ch)]
    if not _fs: continue
    _k = 0
    for _l in open(os.path.join(_R, _fs[0])).read().split('\n'):
        _m = _re.match(r'^\*\*Figure \{F:([^}]+)\}\*\* (.*)$', _l)
        if _m and _re.search(r'`fig[A-Za-z0-9_]+\.png`', _l):
            _pngs = _re.findall(r'`(fig[A-Za-z0-9_]+\.png)`', _l)
            _title = _re.split(r'[.:(,]', _m.group(2))[0].strip()
            _sc = _png2script.get(_pngs[0], '–')
            _rows.append('| Figure {F:%s} | %s | `%s` | %s |' % (_m.group(1), _title, _sc, ', '.join('`%s`' % p for p in _pngs)))
DIAG_TEXT = ("Every diagram is drawn by its own Python script, which computes every number it draws from the result files. Only Figures {F:1.1}, {F:4.2} and {F:4.3} are schematics of the design of the study. "
  "The scripts are in the folder `Diagram_Scripts` of the digital appendix. The command `python run_all_diagrams.py` draws all diagrams and compares each with the picture in this thesis. On another computer, fonts and library versions can change single pixels, but the numbers drawn are the same. "
  "Table {T:diag} gives the script of each diagram.\n\n**Table {T:diag}** Diagrams and the scripts that draw them.\n\n| Figure | Diagram | Script | Picture |\n|---|---|---|---|\n" + '\n'.join(_rows))
A = '''# Appendix A Supplementary Material

This appendix lists what is delivered with the thesis and how the results can be reproduced. Sect. A.1 gives the structure of the digital appendix, Sect. A.2 the scripts. Sect. A.3 lists every change to a published implementation together with the observations made on them. Sect. A.4 names the result file behind every table and figure, Sect. A.5 gives the script of every diagram and the command that draws them all, and Sect. A.6 points to the source code.

## A.1 Digital Appendix

The folder `thesis_kit` holds all scripts together with the data of one scene, the weights and the third-party code. The command `python run.py demo` runs the whole study there and prints the thesis numbers next to the numbers it measures. Every folder has a README with further description. The scripts in `scripts/` are cleaned copies of the scripts that produced the results, and the originals are untouched.

```
\\Master Thesis
    \\thesis              sources, figures, build scripts
    \\digital_appendix
        \\scripts         cleaned scripts (Sect. A.2)
        \\registers       pre-registrations (Sect. 4.6)
        \\logs            FIXLOG, change register, audits
    \\rerender            Blender copies, render and GT scripts
    \\v2_project          PIPs++ drivers, evaluator, results
        \\results         tables and figures (Sect. A.4)
    \\finetune            training scripts, checkpoints
    \\ptv                 FlowVelo driver and parameters
    \\audit               audit reports AUD10, AUD21, D2-D5
    \\reference_model     pre-trained PIPs++ checkpoint
```

## A.2 Scripts

@@SCRIPTS@@

### A.2.3 Derivation of the Ratio

For a scored step *i*, let **d**_*i* be the tracked step and **t**_*i* the true step (px/frame). The error is **e**_*i* = **d**_*i* − **t**_*i*, and the root-mean-square error of a tracker over *N* steps is RMSE = sqrt( (1/*N*) Σ |**e**_*i*|² ). A reference tracker that reports no movement has **d**_*i* = 0, so that its error is −**t**_*i* and its RMSE is the root-mean-square true step. The ratio of Eq. 4.1 is therefore

*ratio* = sqrt( Σ |**d**_*i* − **t**_*i*|² / Σ |**t**_*i*|² )  (Eq. A.1)

A tracker that reports no movement has the ratio 1. A tracker that follows the true direction but moves at a fraction *c* of the true speed (**d**_*i* = *c* **t**_*i*) has the ratio |1 − *c*|, so that a ratio below 0.8 requires *c* between 0.2 and 1.8 for this simple case. The ratio is a normalised root-mean-square error, which makes views of different flow speed comparable. It is a formulation made for this study, and no published source is claimed for it. The code is `compare_v2.py` (Table {T:scripts}).


## A.3 Modifications

The following table lists every point at which the software used in this thesis departs from the two published implementations it evaluates, the PIPs++ model and inference code of Zheng et al. (2023) and FlowVeloTool of Eltner et al. (2020), and from the pre-registered plan. The table documents in one place what was run, what was left unchanged and why each change was made. Each row names the file, the finding that motivated the change (FIXLOG identifier) and the section of the thesis that uses it.

**Software versions.** The pre-trained model is the checkpoint `model-000200000.pth` (SHA-256 `74dd05ba…de3d1`) of the released PIPs++ code (https://github.com/aharley/pips2, commit 8b5bd9e; Zheng et al., 2023). The PTV implementation is FlowVeloTool (https://github.com/AnetteEltner/FlowVeloTool, commit 7f40008; Eltner et al., 2020). Both were used without modification.

''' + Bi.strip() + '''

### A.3.6 Observations on the Existing Code

''' + open('defects_table.md').read().strip() + '''

### A.3.7 FlowVelo Parameters per Camera View

''' + tp + '\n\n' + tp_text + '''

## A.4 Result Sources

The file behind every table and figure of the thesis is listed in Table {T:src}. The scripts that produce the files are listed in Table {T:scripts}, and `thesis/REPRODUCE.md` gives the command for each table.

**Table {T:src}** Result file behind each table and figure.

| Table or figure | File |
|---|---|
''' + src + '''

## A.5 Diagram Scripts

''' + DIAG_TEXT + '''

@@SHEETS@@
'''
import appendix_post
A = appendix_post.apply(A)
open('nA_appendix.md', 'w').write(A)
print(len(A.split()), 'words;', len(rows), 'source rows')
