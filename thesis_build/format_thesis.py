"""Layout of THESIS_DRAFT.docx after the model of a high-scoring TU Dresden Hydrosciences master thesis (A4, Palatino 11 pt, Arial headings,
running header with chapter title and page number, booktabs tables, dotted contents lists, nomenclature).
    format_thesis.py RAW.docx OUT.docx          (reads thesis/pagemap.json when it exists)"""
import re, sys, os, json, copy, docx
from docx.shared import Pt, Cm, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
HERE = os.path.dirname(os.path.abspath(__file__))
RAW, OUT = sys.argv[1], sys.argv[2]
PM = json.load(open(os.path.join(HERE, 'pagemap.json'))) if os.path.exists(os.path.join(HERE, 'pagemap.json')) else {}
TITLE = 'Evaluation of AI-Based Particle Tracking Method for Surface Water Velocity Estimation'
SERIF, SANS = 'Palatino', 'Arial'
APP_NATIVE = os.environ.get('APP_NATIVE', '0') == '1'      # appendix tables flow natively with a repeated header row (no hand-cut pieces)
TW = Cm(16)                                   # text width: A4 21 cm - 3 cm - 2 cm
d = docx.Document(os.path.join(HERE, RAW) if not os.path.isabs(RAW) else RAW)
# ---------------------------------------------------------------- page geometry
for s in d.sections:
    s.page_width, s.page_height = Cm(21), Cm(29.7)
    s.left_margin, s.right_margin, s.top_margin, s.bottom_margin = Cm(2.5), Cm(2.5), Cm(2.8), Cm(2.5)
    s.header_distance = Cm(1.3); s.footer_distance = Cm(1.2)
# ---------------------------------------------------------------- styles
def setfont(style, name, size=None, bold=None, italic=None, color='000000'):
    f = style.font; f.name = name
    if size: f.size = Pt(size)
    if bold is not None: f.bold = bold
    if italic is not None: f.italic = italic
    if color: f.color.rgb = RGBColor.from_string(color)
    rpr = style.element.get_or_add_rPr(); rf = rpr.find(qn('w:rFonts'))
    if rf is None: rf = OxmlElement('w:rFonts'); rpr.append(rf)
    for a in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'): rf.set(qn(a), name)
    for a in ('w:asciiTheme', 'w:hAnsiTheme', 'w:cstheme', 'w:eastAsiaTheme'):
        if rf.get(qn(a)) is not None: del rf.attrib[qn(a)]
for n in ('Normal', 'Body Text', 'First Paragraph', 'Compact', 'Block Text', 'Table', 'Caption', 'Image Caption', 'Table Caption'):
    try:
        st = d.styles[n]; setfont(st, SERIF, 11)
        pf = st.paragraph_format; pf.space_before = Pt(0); pf.space_after = Pt(4); pf.line_spacing = 1.2
        if n in ('Normal', 'Body Text', 'First Paragraph', 'Block Text'): pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    except KeyError: pass
for n, sz, sb, sa in (('Title', 22, 0, 10), ('Heading 1', 20, 78, 22), ('Heading 2', 14, 20, 8), ('Heading 3', 12, 14, 6), ('Heading 4', 11, 10, 4)):
    try:
        st = d.styles[n]; setfont(st, SANS, sz, True, False); st.paragraph_format.space_before = Pt(sb); st.paragraph_format.space_after = Pt(sa)
        st.paragraph_format.keep_with_next = True; st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT; st.paragraph_format.line_spacing = 1.0
    except KeyError: pass
for n in ('Verbatim Char', 'Source Code'):
    try: setfont(d.styles[n], 'Courier New', 9.5)
    except KeyError: pass
for p_ in d.paragraphs:                                   # printed source code (Appendix A.8): small, tight, one colour
    if p_.style.name == 'Source Code':
        p_.paragraph_format.space_after = Pt(0); p_.paragraph_format.space_before = Pt(0); p_.paragraph_format.line_spacing = 1.0
        for r_ in p_.runs: r_.font.size = Pt(9 if p_.text.startswith('\\Master Thesis') else 7.5); r_.font.name = 'Courier New'      # folder tree of Appendix A.1: one size larger
from docx.text.paragraph import Paragraph
for p_ in d.paragraphs:                                   # a little air above and below every code excerpt; the lines of one excerpt stay together
    if p_.style.name == 'Source Code':
        _pv, _nx = p_._p.getprevious(), p_._p.getnext()
        _is_sc = lambda e: e is not None and e.tag == qn('w:p') and Paragraph(e, d._body).style.name == 'Source Code'
        if not _is_sc(_pv): p_.paragraph_format.space_before = Pt(7)
        if not _is_sc(_nx): p_.paragraph_format.space_after = Pt(7)
        else: p_.paragraph_format.keep_with_next = True
try: setfont(d.styles['Hyperlink'], SERIF, 11, color='000000')
except KeyError: pass
body = d.element.body
P = lambda: d.paragraphs
APPX_IDX = None
for _p in d.paragraphs:
    if _p.style.name == 'Heading 1' and _p.text.strip().startswith('Appendix A'): APPX_IDX = list(body).index(_p._p)
def after_appx(p): return APPX_IDX is not None and list(body).index(p._p) > APPX_IDX
def find(text, style=None):
    for p in d.paragraphs:
        if p.text.strip() == text and (style is None or p.style.name == style): return p
    return None
# ---------------------------------------------------------------- helpers
def run(p, text, size=None, bold=None, italic=None, font=None, small=False):
    r = p.add_run(text)
    if size: r.font.size = Pt(size)
    if bold is not None: r.font.bold = bold
    if italic is not None: r.font.italic = italic
    if font: r.font.name = font; rf = r._r.get_or_add_rPr().find(qn('w:rFonts')); [rf.set(qn(a), font) for a in ('w:ascii', 'w:hAnsi', 'w:cs')]
    if small: r.font.small_caps = True
    return r
def newp_before(anchor, align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=0, style='Normal'):
    p = anchor.insert_paragraph_before('', style=style); p.alignment = align; p.paragraph_format.space_before = Pt(before); p.paragraph_format.space_after = Pt(after); p.paragraph_format.line_spacing = 1.0; return p
def border(p, side='bottom', sz=6):
    pPr = p._p.get_or_add_pPr(); b = pPr.find(qn('w:pBdr'))
    if b is None: b = OxmlElement('w:pBdr'); pPr.append(b)
    e = OxmlElement('w:' + side); e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), str(sz)); e.set(qn('w:space'), '1'); e.set(qn('w:color'), '000000'); b.append(e)
def field(p, instr, size=10):
    r = p.add_run(); r.font.size = Pt(size)
    for t, txt in (('begin', None), (None, instr), ('end', None)):
        if t: e = OxmlElement('w:fldChar'); e.set(qn('w:fldCharType'), t)
        else: e = OxmlElement('w:instrText'); e.set(qn('xml:space'), 'preserve'); e.text = txt
        r._r.append(e)
# ---------------------------------------------------------------- title page
for _p in list(d.paragraphs):
    if _p.style.name == 'Title': _p._p.getparent().remove(_p._p)
tp = find('@@TITLEPAGE@@')
logo = os.path.join(HERE, 'assets', 'tud_logo_2025_de.png')
p = newp_before(tp, WD_ALIGN_PARAGRAPH.LEFT, 0, 0); p.add_run().add_picture(logo, width=Cm(5.4))
p = newp_before(tp, before=48, after=10); run(p, 'Technische Universität Dresden', 15, small=True)
for t in ('Faculty of Environmental Sciences', 'Department of Hydro Sciences', 'Institute of Photogrammetry and Remote Sensing', 'Chair of Geosensor Systems'):
    p = newp_before(tp, after=1); run(p, t, 11, small=True)
p = newp_before(tp, before=70, after=10); run(p, 'Master Thesis', 18)
p = newp_before(tp, after=0); run(p, 'submitted in partial fulfilment of the requirements for the degree of', 10)
p = newp_before(tp, after=0); run(p, 'Master of Science', 10)
p = newp_before(tp, before=34, after=0); run(p, TITLE, 20)
p = newp_before(tp, before=46, after=2); run(p, 'Robin Singh', 18)
p = newp_before(tp, after=0); run(p, '(Mat.-No.: 5056200)', 11)
p = newp_before(tp, WD_ALIGN_PARAGRAPH.LEFT, before=70, after=0); run(p, 'Professor: Prof. Dr. Anette Eltner', 11)
p = newp_before(tp, WD_ALIGN_PARAGRAPH.LEFT, after=0); run(p, 'Supervisor: Dr. Pedro Zamboni', 11)
p = newp_before(tp, WD_ALIGN_PARAGRAPH.LEFT, before=18, after=0); run(p, 'Handout: 1 June 2026 · Submission: 22 October 2026', 11)
tp._p.getparent().remove(tp._p)
# declaration (English)
dc = find('@@DECLARATION@@')
def decl(t, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, before=0, size=11, bold=False):
    p = newp_before(dc, align, before, 6); p.paragraph_format.line_spacing = 1.2; run(p, t, size, bold=bold, italic=italic); return p
decl('Declaration of independent work', bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, size=13)
decl('I hereby declare that I wrote the master thesis submitted today to the Examination Board of the Faculty of Environmental Sciences on the topic above independently, that I used no sources or aids other than those indicated, that all quotations are marked and that the thesis has not been submitted to any other examination authority.')
decl('Dresden, 22 October 2026', before=26, align=WD_ALIGN_PARAGRAPH.LEFT)
decl('Robin Singh', before=34, align=WD_ALIGN_PARAGRAPH.LEFT)
dc._p.getparent().remove(dc._p)
def fix_widths(t, ws):
    tbl = t._tbl; tblPr = tbl.tblPr
    for e in tblPr.findall(qn('w:tblW')) + tblPr.findall(qn('w:tblLayout')): tblPr.remove(e)
    w = OxmlElement('w:tblW'); w.set(qn('w:type'), 'dxa'); w.set(qn('w:w'), str(int(sum(Cm(x).twips for x in ws)))); tblPr.append(w)
    lay = OxmlElement('w:tblLayout'); lay.set(qn('w:type'), 'fixed'); tblPr.append(lay)
    grid = tbl.tblGrid
    for gc in list(grid): grid.remove(gc)
    for x in ws:
        gc = OxmlElement('w:gridCol'); gc.set(qn('w:w'), str(int(Cm(x).twips))); grid.append(gc)
    for row in t.rows:
        for ci, cell in enumerate(row.cells): cell.width = Cm(ws[ci])
# ---------------------------------------------------------------- nomenclature
nm = find('@@NOMENCLATURE@@')
ACR = [('ADCP', 'Acoustic Doppler current profiler'), ('AJ', 'Average Jaccard (TAP-Vid)'), ('DAVIS', 'TAP-Vid-DAVIS benchmark'), ('D1 to D4', 'Deployment modes: re-tracked every 2 frames / re-initialised every 16 frames / long-term, one call per 48 frames / fresh seeds every 2 frames'),
       ('EXR', 'OpenEXR image format (Blender vector pass)'), ('FD / FT', 'FlowVelo feature-detection interval / feature-tracking length (frames)'), ('FLIP', 'Fluid-implicit-particle simulation (Blender Mantaflow)'),
       ('GNSS', 'Global navigation satellite system'), ('GT', 'Ground truth'), ('GUI', 'Graphical user interface'), ('KLT-IV', 'Kanade–Lucas–Tomasi image velocimetry'), ('LK', 'Lucas–Kanade optical flow'), ('LSPIV', 'Large-scale particle image velocimetry'), ('MLP-Mixer', 'Multilayer-perceptron mixer architecture'), ('MPS', 'Metal Performance Shaders (Apple GPU backend of PyTorch)'),
       ('NCC', 'Normalised cross-correlation'), ('OA', 'Occlusion accuracy (TAP-Vid)'), ('PIPs++', 'Persistent Independent Particles (Zheng et al., 2023)'), ('PTV', 'Particle tracking velocimetry'),
       ('RAFT', 'Recurrent all-pairs field transforms (optical flow)'), ('RANSAC', 'Random sample consensus'), ('RMSE', 'Root-mean-square error'), ('SIFT', 'Scale-invariant feature transform'), ('S0 to S6', 'Retraining strategies: pre-trained model (S0), strategies S1 to S5, final model (S6)'), ('STIV', 'Space–time image velocimetry'), ('TAP', 'Tracking any point'), ('TAP-Vid', 'Benchmark for tracking any point in video'), ('UAV', 'Unmanned aerial vehicle')]
SYM = [('ratio', 'RMSE of a tracker divided by the RMSE of a zero-motion reference, all steps', ''), ('ratio₁₅', 'Same, over a 15-frame horizon', ''), ('δ_avg', 'TAP-Vid position accuracy averaged over the thresholds 1, 2, 4, 8 and 16 px', '[%]'),
       ('N', 'Tracked points per training clip', ''), ('k', 'Re-initialisation interval of PIPs++', '[frames]'),
       ('v', 'Mean flow speed in the image', '[px frame⁻¹]'), ('direction agreement', 'Fraction of sub-steps within 37° of the true direction', ''), ('speed ratio', 'Tracked speed divided by true speed', ''),
       ('coverage', 'Fraction of water cells with a velocity estimate', ''), ('speed bias', 'Mean-speed bias in per cent of the true mean speed', '[%]')]
def nom_table(rows, head):
    """Nomenclature as tabbed paragraphs (no table), so the heading and the list stay on one page."""
    p = newp_before(nm, WD_ALIGN_PARAGRAPH.LEFT, before=6, after=3); run(p, head, 11, bold=True, font=SERIF); p.paragraph_format.keep_with_next = True
    for a, b, c in rows:
        p = newp_before(nm, WD_ALIGN_PARAGRAPH.LEFT, after=1.5)
        pf = p.paragraph_format; pf.left_indent = Cm(3.4); pf.first_line_indent = Cm(-3.4); pf.line_spacing = 1.05
        pf.tab_stops.add_tab_stop(Cm(3.4)); pf.tab_stops.add_tab_stop(TW, WD_TAB_ALIGNMENT.RIGHT)
        run(p, a, 10, bold=True); run(p, '\t' + b, 10)
        if c: run(p, '\t' + c, 10)
nom_table([(a, b, '') for a, b in ACR], 'Acronyms'); nom_table(SYM, 'Symbols'); nm._p.getparent().remove(nm._p)
# ---------------------------------------------------------------- section breaks and running headers
def sect_copy():
    base = body.find(qn('w:sectPr')); s = copy.deepcopy(base)
    for e in list(s):
        if e.tag in (qn('w:headerReference'), qn('w:footerReference'), qn('w:type'), qn('w:pgNumType')): s.remove(e)
    t = OxmlElement('w:type'); t.set(qn('w:val'), 'nextPage'); s.insert(0, t); return s
h1 = [p for p in d.paragraphs if p.style.name == 'Heading 1']
starts = []       # (paragraph, header title)
for p in h1:
    t = p.text.strip()
    if t == 'Contents': starts.append((p, ''))
    elif re.match(r'^\d+ ', t): starts.append((p, re.sub(r'^(\d+) ', r'\1. ', t).upper()))
    elif t == 'Bibliography': starts.append((p, 'BIBLIOGRAPHY'))
    elif t.startswith('Appendix'): starts.append((p, t.split(' ', 2)[0].upper() + ' ' + t.split(' ', 2)[1]))
startset = {id(p._p) for p, _ in starts}
for p in h1:
    p.paragraph_format.page_break_before = (id(p._p) not in startset)
for p, _ in starts:
    br = OxmlElement('w:p'); pPr = OxmlElement('w:pPr'); pPr.append(sect_copy()); br.append(pPr); p._p.addprevious(br)
bs = body.find(qn('w:sectPr')); t = OxmlElement('w:type'); t.set(qn('w:val'), 'nextPage'); bs.insert(0, t)
titles = [None] + [t for _, t in starts]
secs = d.sections
assert len(secs) == len(titles), (len(secs), len(titles))
for k, (sec, title) in enumerate(zip(secs, titles)):
    sec.header.is_linked_to_previous = False
    hp = sec.header.paragraphs[0]; hp.text = ''; hp.paragraph_format.tab_stops.add_tab_stop(TW, WD_TAB_ALIGNMENT.RIGHT); hp.paragraph_format.space_after = Pt(0)
    border(hp, 'bottom', 6)
    if k == 0:
        run(hp, ' ', 10, font=SANS); sec.different_first_page_header_footer = True; sec.first_page_header.is_linked_to_previous = False; sec.first_page_header.paragraphs[0].text = ''
    else:
        if title: run(hp, title, 10, font=SERIF)
        run(hp, '\t', 10); field(hp, ' PAGE ', 10)
    sec.footer.is_linked_to_previous = False
    if k == 1:
        pg = OxmlElement('w:pgNumType'); pg.set(qn('w:start'), '1'); sec._sectPr.append(pg)
# ---------------------------------------------------------------- contents lists with dotted leaders
def toc_par(p, kind, text):
    page = str(PM.get(text, '·'))
    for r in list(p.runs): r._r.getparent().remove(r._r)
    pf = p.paragraph_format; pf.line_spacing = 1.15; pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.tab_stops.add_tab_stop(TW, WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
    lv = {'T0': 0, 'T1': 1, 'T2': 2, 'T3': 3, 'F': 0}[kind]
    ind = [0, 0.6, 1.4, 2.4][lv] if kind != 'F' else 0
    pf.left_indent = Cm(ind + 1.0); pf.first_line_indent = Cm(-1.0); pf.right_indent = Cm(0.9)
    pf.space_before = Pt(8 if kind == 'T0' else 0); pf.space_after = Pt(1)
    if kind == 'T0': run(p, text, 10.5, bold=True, font=SANS)
    else: run(p, text, 10.5)
    run(p, '\t' + page, 10.5, bold=(kind == 'T0'), font=SANS if kind == 'T0' else None)
    # allow the page number to sit in the right indent
    ppr = p._p.get_or_add_pPr(); ind_e = ppr.find(qn('w:ind'))
    if ind_e is not None and ind_e.get(qn('w:right')) is not None: del ind_e.attrib[qn('w:right')]
for p in d.paragraphs:
    m = re.match(r'^@@(T\d|F)@@(.*)$', p.text)
    if m: toc_par(p, m.group(1), m.group(2).strip())
# ---------------------------------------------------------------- tables: booktabs
def cell_border(cell, **kw):
    tcPr = cell._tc.get_or_add_tcPr(); b = tcPr.find(qn('w:tcBorders'))
    if b is None: b = OxmlElement('w:tcBorders'); tcPr.append(b)
    for side, sz in kw.items():
        e = b.find(qn('w:' + side))
        if e is None: e = OxmlElement('w:' + side); b.append(e)
        e.set(qn('w:val'), 'single' if sz else 'nil'); e.set(qn('w:sz'), str(sz)); e.set(qn('w:space'), '0'); e.set(qn('w:color'), '000000')
def auto_widths(t, size, total=16.0, wordy=False):
    """column widths from the content: no word is ever broken, the label column gets the room that is left"""
    ncol = len(t.columns); cw = 0.021 * size; minw = []; pref = []
    for ci in range(ncol):
        cells = [row.cells[ci].text.strip() for row in t.rows]
        longest = 1
        for ri_, c in enumerate(cells):
            for w in re.split(r'[\s/–-]+', c):
                if w: longest = max(longest, len(w) * (1.12 if ri_ == 0 else 1.0))
        maxlen = max([len(c) for c in cells] + [1])
        minw.append(longest * cw + 0.3); pref.append(max(minw[-1], min(maxlen, 36 if (ci == 0 or wordy) else 12) * cw + 0.3))
    if sum(pref) <= total:
        k = max(1.0, 0.8 * total / sum(pref)); return [p * k for p in pref]
    if sum(minw) >= total:
        k = total / sum(minw); return [m * k for m in minw]
    extra = total - sum(minw); want = [p - m for p, m in zip(pref, minw)]; k = min(1.0, extra / max(sum(want), 1e-9))
    ws = [m + w * k for m, w in zip(minw, want)]
    ws[0] += total - sum(ws)
    return ws
def cell_line(cell, side, sz, color):
    tcPr = cell._tc.get_or_add_tcPr(); b = tcPr.find(qn('w:tcBorders'))
    if b is None: b = OxmlElement('w:tcBorders'); tcPr.append(b)
    e = b.find(qn('w:' + side))
    if e is None: e = OxmlElement('w:' + side); b.append(e)
    e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), str(sz)); e.set(qn('w:space'), '0'); e.set(qn('w:color'), color)
def cell_fill(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    for e in tcPr.findall(qn('w:shd')): tcPr.remove(e)
    sh = OxmlElement('w:shd'); sh.set(qn('w:val'), 'clear'); sh.set(qn('w:color'), 'auto'); sh.set(qn('w:fill'), fill); tcPr.append(sh)
nom_ids = {id(t._tbl) for t in d.tables if t.rows and t.rows[0].cells[0].text.strip() in ('Acronyms', 'Symbols')}
for t in d.tables:
    if id(t._tbl) in nom_ids: continue
    in_app0 = (APPX_IDX is not None and list(body).index(t._tbl) > APPX_IDX)
    ncol = len(t.columns); size = 11 if ncol <= 5 else 10 if ncol <= 8 else 8.5 if ncol <= 12 else 7.5
    if APPX_IDX is not None and list(body).index(t._tbl) > APPX_IDX and len(t.rows) > 12: size = min(size, 9)      # long appendix tables: smaller type so that caption and table fit one page
    hdr_txt = [c.text.strip().lower() for c in t.rows[0].cells]
    wordy = 'what it tests' in hdr_txt                # text-heavy table: smaller type, left-aligned
    if wordy: size = 8.5
    t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False
    tblPr = t._tbl.tblPr
    for e in tblPr.findall(qn('w:tblBorders')): tblPr.remove(e)
    for e in tblPr.findall(qn('w:tblStyle')): tblPr.remove(e)
    mar = OxmlElement('w:tblCellMar')
    for k, v in (('top', 40), ('left', 60), ('bottom', 40), ('right', 60)):
        e = OxmlElement('w:' + k); e.set(qn('w:w'), str(v)); e.set(qn('w:type'), 'dxa'); mar.append(e)
    tblPr.append(mar)
    ws = auto_widths(t, size, wordy=wordy) if ncol > 1 else [16.0]
    nrows = len(t.rows)
    group_tbl = any(not r.cells[0].text.strip() for r in t.rows[1:]) and nrows > 4        # tables with grouped rows (first cell empty): a thin rule between groups
    if APPX_IDX is not None and list(body).index(t._tbl) > APPX_IDX and nrows > 12:       # wide text columns for long appendix tables: fewer lines per row
        if ncol == 4: ws = [3.0, 4.8, 6.2, 2.0]
        elif ncol == 6: ws = [1.0, 4.6, 2.6, 4.2, 2.6, 1.0]
    if in_app0 and hdr_txt[:1] == ['id'] and ncol == 5: ws = [1.25, 4.5, 2.9, 2.6, 4.75]                      # A.3.2, A.3.3: ids such as A10 on one line, 'comparability' unbroken
    if in_app0 and hdr_txt[:1] == ['camera view'] and ncol == 11: ws = [2.3, 1.1, 1.1, 1.7, 1.8, 1.5, 1.2, 0.8, 0.8, 1.9, 1.8]; size = 7.5      # A.4: headers FT, FD, min. count unbroken
    if in_app0 and hdr_txt[:1] == ['variant'] and hdr_txt[-1] == 'ptv lk' and ncol == 6: ws = [2.8, 2.6, 2.6, 2.6, 2.7, 2.7]        # A.9: 'PTV LK' on one line
    if in_app0 and hdr_txt[:1] == ['step'] and ncol == 4: ws = [3.5, 4.6, 5.9, 2.0]                     # A.1: 'Pre-trained PIPs++' on one line
    if in_app0 and hdr_txt[:1] in (['measure'], ['checkpoint']) and ncol <= 5: size = 7.5      # A.11, A.12: same small type as A.9, A.10
    if in_app0 and hdr_txt == ['item', 'state', 'proof']: size = 9                                       # A.3.1: same type as the change registers
    if in_app0 and hdr_txt == ['item', 'state', 'proof']: ws = [3.9, 4.3, 7.8]                         # A.3.1: first column wide enough for tool names
    if in_app0 and hdr_txt[:1] == ['figure'] and hdr_txt[-1] == 'picture' and ncol == 4:
        ws = [1.8, 2.2, 5.5, 6.5]; size = 7.5                       # A.13: wide Figure column; every picture file name on one line, one name per line, no comma
        for _r in t.rows[1:]:
            _c = _r.cells[3]; _p0 = _c.paragraphs[0]
            if ', ' in _p0.text and _p0.runs:
                _names = [x.strip() for x in _p0.text.split(', ')]
                for _x in _p0.runs[1:]: _x._r.getparent().remove(_x._r)
                _p0.runs[0].text = _names[0]
                for _n in _names[1:]:
                    _p0.runs[0].add_break(); _rn = _p0.add_run(_n); _rn.font.name = _p0.runs[0].font.name   # A.13: picture file names on one line
    if hdr_txt and hdr_txt[-1] == 'what it gives' and ncol == 4: ws = [2.4, 4.8, 3.4, 5.4]; size = min(size, 8) if in_app0 else size; ws = [2.3, 5.6, 3.0, 5.1] if in_app0 else ws            # script table of the appendix: wide last column
    if hdr_txt and hdr_txt[0] == 'metric' and ncol == 3 and not in_app0: ws = [3.4, 7.2, 5.4]; size = 9.5       # Table 4.3: wide columns, fewer wrapped lines
    if hdr_txt and hdr_txt[0] == 'condition' and ncol == 4: ws = [3.9, 2.8, 5.2, 4.1]; size = 9.5   # Table 6.1
    if ncol >= 5 and hdr_txt and hdr_txt[0] in ('variant', 'measure', 'checkpoint', 'method') and ws[0] < 2.6:      # first column must not break words letter by letter
        need = 2.6 - ws[0]; rest = sum(ws[1:]); ws = [2.6] + [w * (rest - need) / rest for w in ws[1:]]
    if in_app0: size = 9          # one size for every appendix table
    fix_widths(t, ws)
    in_app = (list(body).index(t._tbl) > APPX_IDX) if APPX_IDX is not None else False
    _num = re.compile(r'^[\s\-+\u2212\u00b1<>\u2265\u2264~]*\d[\d\s.,/\u2013\u2009%\u00b0px()e\-]*$')
    _textcol = []
    for _ci in range(ncol):
        _cells = [r_.cells[_ci].text.strip() for r_ in t.rows[1:] if r_.cells[_ci].text.strip()]
        _textcol.append(bool(_cells) and sum(1 for c_ in _cells if _num.match(c_)) / len(_cells) < 0.5)
    for ri, row in enumerate(t.rows):
        trPr = row._tr.get_or_add_trPr()
        if in_app and False:
            for e in trPr.findall(qn('w:tblHeader')): trPr.remove(e)          # appendix tables: no repeated header row
        if nrows <= 30 or in_app: trPr.append(OxmlElement('w:cantSplit'))      # long tables may break between rows and inside rows
        if ri == 0 and ((nrows <= 30 and not in_app) or (in_app and nrows > 3)):
            if not trPr.findall(qn('w:tblHeader')): trPr.append(OxmlElement('w:tblHeader'))
        for ci, cell in enumerate(row.cells):
            cell.width = Cm(ws[ci])
            tcPr = cell._tc.get_or_add_tcPr()
            for e in tcPr.findall(qn('w:shd')): tcPr.remove(e)
            if ri == 0: cell_border(cell, top=12, bottom=6)
            elif ri < nrows - 1: cell_line(cell, 'bottom', 2, 'BFBFBF')          # light hairline between rows (booktabs: no heavy grid)
            if group_tbl and ri > 1 and row.cells[0].text.strip(): cell_line(cell, 'top', 4, '000000')
            if ri == nrows - 1: cell_border(cell, bottom=12)
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(0); p.paragraph_format.space_before = Pt(0); p.paragraph_format.line_spacing = 1.05
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT if (ci == 0 or wordy or _textcol[ci]) else WD_ALIGN_PARAGRAPH.CENTER      # text columns left, numbers centred
                for r in p.runs:
                    r.font.size = Pt(size); r.font.name = SERIF; r.font.color.rgb = RGBColor(0, 0, 0)
                    if ri == 0: r.font.bold = True
from docx.text.paragraph import Paragraph
# long appendix tables: the caption flows with the first rows instead of being left alone on the previous page
for t in d.tables:
    if APPX_IDX is not None and list(body).index(t._tbl) > APPX_IDX and len(t.rows) > 12:
        pv = t._tbl.getprevious()
        if pv is not None and pv.tag == qn('w:p'): Paragraph(pv, d._body).paragraph_format.keep_with_next = False
# ---------------------------------------------------------------- appendix: tall tables are cut into page-sized pieces
# Pages never starts a table on a partly filled page unless the whole table fits there (it ignores keep-with-next and cantSplit rows), so a tall table
# leaves its heading or caption alone at the foot of the previous page. Each piece below fits one page; the header row is repeated in every piece.
import copy as _copy
APP_PAGE_CM = 23.0                      # real body height of an appendix page is about 24 cm (measured in the Pages export)
EST_F = 1.0                            # the estimate below is about 7 % too low (measured against the Pages export)
PAGE_END_CM = 26.5                      # lowest usable table edge on a page (cm from the top)
_split_i = -1
_prev_end = None
def _est_table_rows(t):
    grid = [int(g.get(qn('w:w'))) / 567.0 for g in t._tbl.find(qn('w:tblGrid')).findall(qn('w:gridCol'))]
    out = []
    for tr in t._tbl.findall(qn('w:tr')):
        mx = 1; size = 10
        for ci, tc in enumerate(tr.findall(qn('w:tc'))):
            sz = tc.find('.//' + qn('w:sz')); size = int(sz.get(qn('w:val'))) / 2 if sz is not None else size
            cpl = max(3, int((grid[ci] - 0.25) / (size * 0.0185)))
            lines = 0
            for p_ in tc.findall(qn('w:p')):
                txt = ''.join(x.text or '' for x in p_.iter(qn('w:t')))
                words = txt.split(); n = 1; cur = 0
                for w_ in words:
                    if cur and cur + 1 + len(w_) > cpl: n += 1; cur = len(w_)
                    else: cur += (1 if cur else 0) + len(w_)
                    while cur > cpl: n += 1; cur -= cpl
                lines += n
            mx = max(mx, lines)
        out.append((mx * size * 0.0445 + 0.2) * EST_F)
    return out
# measured in the Pages export: cm from the top of the page to the header row of each cut or kept-together table (first body cell -> (position, mode));
# ('chain', gap) = gap below the end of the previous cut table; mode 'together' = the table is never split by a page break
HDR_CFG = {'A2': (16.0, 'split'), 'B2': (('chain', 2.4), 'split'), 'C-a': (('chain', 2.4), 'split'), 'errors reported': (('chain', 2.4), 'split'), '1': (('chain', 4.0), 'split'),
           'Low_1.001': (('chain', 5.3), 'split'), 'Table 2.1': (('chain', 8.6), 'split'), 'PIPs++ pre-trained': (23.0, 'together'), 'P1': (14.0, 'split'), 'reference weights (S0)': (20.8, 'together'), 'Figure 1.1': (10.5, 'split')}
def _is_p(el): return el is not None and el.tag == qn('w:p')
def _cfg_for(t):
    pv_ = t._tbl.getprevious()
    if _is_p(pv_):
        ct = ''.join(pv_.itertext()).strip()
        for key, v in HDR_CFG.items():
            if key.startswith('cap:') and ct.startswith(key[4:]): return v
    k = t.rows[1].cells[0].text.strip()
    for key, v in HDR_CFG.items():
        if k == key or (len(key) > 6 and k.startswith(key)): return v
    return None
def _walk_back(el):
    """first element of the block (headings and lead-in text) that belongs to the table: a page break goes in front of it"""
    cur = el; extra = 0.0; seen_h = False
    for _ in range(6):
        pr = cur.getprevious()
        while pr is not None and pr.tag in (qn('w:bookmarkStart'), qn('w:bookmarkEnd')): pr = pr.getprevious()
        if not _is_p(pr): break
        P_ = Paragraph(pr, d._body); tx = P_.text.strip()
        if P_.style.name.startswith('Heading'): cur = pr; extra += 1.3; seen_h = True; continue
        if seen_h or not tx or tx.startswith('Note.'): break
        pp2 = pr.getprevious()
        while pp2 is not None and pp2.tag in (qn('w:bookmarkStart'), qn('w:bookmarkEnd')): pp2 = pp2.getprevious()
        if not (_is_p(pp2) and Paragraph(pp2, d._body).style.name.startswith('Heading')): break      # lead-in text that explains the previous table stays where it is
        cur = pr; extra += 2.2
    return cur, extra
for t in list(d.tables):
    if APP_NATIVE or APPX_IDX is None or list(body).index(t._tbl) <= APPX_IDX or len(t.rows) < 3 or t.rows[0].cells[0].text.strip() == 'Group': continue
    cfg = _cfg_for(t)
    if cfg is None: continue
    hs = _est_table_rows(t)
    pv = t._tbl.getprevious()
    lead = 1.6 if (_is_p(pv) and ''.join(pv.itertext()).strip().startswith('Table A.')) else 0.0
    total = sum(hs)
    _h, _mode = cfg
    if isinstance(_h, tuple): _h = (_prev_end + _h[1]) if _prev_end is not None else 3.3 + 2.2
    _ran_past = _h > PAGE_END_CM
    if _ran_past: _h -= (PAGE_END_CM - 3.3)               # (the chain ran past the page end: the heading would be stranded at the foot, so heading and table start the next page)
    budget_first = PAGE_END_CM - 0.8 - _h                      # (0.8 cm safety: Pages moves a table that does not fit as a whole)
    first, extra = _walk_back(pv if _is_p(pv) else t._tbl)
    _force_break = False
    if (_mode == 'together' and total > budget_first) or budget_first < 4.0 or _ran_past:         # no room: headings and table start the next page together
        _force_break = True; budget_first = APP_PAGE_CM - lead - (extra if not lead else extra)
        _h = 3.3 + extra + lead
    if _mode == 'together' and total <= APP_PAGE_CM:
        if _force_break:
            sp0 = OxmlElement('w:p'); pPr0 = OxmlElement('w:pPr'); sc0 = OxmlElement('w:spacing')
            sc0.set(qn('w:before'), '0'); sc0.set(qn('w:after'), '0'); sc0.set(qn('w:line'), '20'); sc0.set(qn('w:lineRule'), 'exact'); pPr0.append(sc0); sp0.append(pPr0)
            _r0 = OxmlElement('w:r'); _b0 = OxmlElement('w:br'); _b0.set(qn('w:type'), 'page'); _r0.append(_b0); sp0.append(_r0)
            first.addprevious(sp0)
        print('APPENDIX KEEP', t.rows[1].cells[0].text[:20], 'est %.1f cm' % total, 'break' if _force_break else 'no break')
        _prev_end = None
        continue
    def _cut(budget):
        ch, cur, acc = [], [], hs[0]; lim = budget
        for ri in range(1, len(hs)):
            if cur and acc + hs[ri] > lim: ch.append(cur); cur, acc = [], hs[0]; lim = APP_PAGE_CM
            cur.append(ri); acc += hs[ri]
        ch.append(cur); return ch
    chunks = _cut(budget_first)
    if len(chunks) > 1 and not _force_break and len(chunks[0]) < 3:          # a heading with only one or two rows below it at the page foot: heading and table start the next page
        _force_break = True; budget_first = APP_PAGE_CM - lead - extra; _h = 3.3 + extra + lead; chunks = _cut(budget_first)
    print('APPENDIX SPLIT', t.rows[1].cells[0].text[:20], 'rows', len(hs), 'est %.1f cm' % total, 'pieces', len(chunks), [round(sum(hs[r] for r in c) + hs[0], 1) for c in chunks], 'force' if _force_break else '')
    _prev_end = (_h if len(chunks) == 1 else 3.3) + sum(hs[r] for r in chunks[-1]) + hs[0]
    if _force_break:
        sp0 = OxmlElement('w:p'); pPr0 = OxmlElement('w:pPr'); sc0 = OxmlElement('w:spacing')
        sc0.set(qn('w:before'), '0'); sc0.set(qn('w:after'), '0'); sc0.set(qn('w:line'), '20'); sc0.set(qn('w:lineRule'), 'exact'); pPr0.append(sc0); sp0.append(pPr0)
        _r0 = OxmlElement('w:r'); _b0 = OxmlElement('w:br'); _b0.set(qn('w:type'), 'page'); _r0.append(_b0); sp0.append(_r0)
        first.addprevious(sp0)
    if len(chunks) < 2: continue
    orig = t._tbl; anchor = orig
    for c in chunks[1:]:
        nt = _copy.deepcopy(orig)
        for ri, tr in enumerate(nt.findall(qn('w:tr'))):
            if ri != 0 and ri not in c: nt.remove(tr)
        sp = OxmlElement('w:p'); pPr_ = OxmlElement('w:pPr'); sc_ = OxmlElement('w:spacing')
        sc_.set(qn('w:before'), '0'); sc_.set(qn('w:after'), '0'); sc_.set(qn('w:line'), '20'); sc_.set(qn('w:lineRule'), 'exact'); pPr_.append(sc_); sp.append(pPr_)
        anchor.addnext(sp); sp.addnext(nt); anchor = nt
        _r = OxmlElement('w:r'); _b = OxmlElement('w:br'); _b.set(qn('w:type'), 'page'); _r.append(_b); sp.append(_r)      # a piece always starts on a fresh page: the cuts are real page boundaries
    keep = set([0] + chunks[0])
    for ri, tr in enumerate(orig.findall(qn('w:tr'))):
        if ri not in keep: orig.remove(tr)
# ---------------------------------------------------------------- tables never break across pages
import copy
LIMIT_CM = 1e9                                    # usable height for a table block (page 29.7 cm minus margins, header, caption)
def est_row_cm(row, widths, size):
    mx = 1
    for ci, cell in enumerate(row.cells):
        cpl = max(4, int(widths[ci] * 4.0 * 9.5 / size))
        lines = sum(max(1, -(-len(par.text) // cpl)) for par in cell.paragraphs)
        mx = max(mx, lines)
    return mx * size * 0.0425 + 0.16
for t in list(d.tables):
    if id(t._tbl) in nom_ids or len(t.rows) < 3: continue
    ncol = len(t.columns); size = 11 if ncol <= 5 else 10 if ncol <= 8 else 8.5 if ncol <= 12 else 7.5
    fw = 2.8 if ncol > 12 else (3.2 if ncol > 8 else (4.2 if ncol > 5 else 3.6)); ws = [fw] + [(16.0 - fw) / max(ncol - 1, 1)] * (ncol - 1) if ncol > 1 else [16.0]
    hs = [est_row_cm(r, ws, size) for r in t.rows]
    if sum(hs) <= LIMIT_CM:
        chunks = [list(range(len(t.rows)))]

    else:                                         # balanced split into equal parts; the header row is repeated in every part
        import math
        nparts = math.ceil(sum(hs) / LIMIT_CM); target = (sum(hs) - hs[0] * nparts) / nparts + 1e-6
        chunks, cur, acc = [], [], 0.0
        for ri in range(1, len(t.rows)):
            if cur and acc + hs[ri] > target * 1.15 and len(chunks) < nparts - 1: chunks.append(cur); cur, acc = [], 0.0
            cur.append(ri); acc += hs[ri]
        chunks.append(cur); chunks = [[0] + c for c in chunks]
    if len(chunks) > 1:
        print('SPLIT table (%d rows, est %.1f cm) into %d parts; first cell: %r' % (len(t.rows), sum(hs), len(chunks), t.rows[0].cells[0].text[:30]))
        orig = t._tbl; anchor = orig
        for k, c in enumerate(chunks[1:], 1):
            nt = copy.deepcopy(orig)
            rows = nt.findall(qn('w:tr'))
            for ri, tr in enumerate(rows):
                if ri not in c: nt.remove(tr)
            cont = d.add_paragraph(); cont.paragraph_format.space_before = Pt(0); cont.paragraph_format.space_after = Pt(4); cont.paragraph_format.keep_with_next = True; cont.paragraph_format.page_break_before = True
            r_ = cont.add_run('(table continued)'); r_.italic = True; r_.font.size = Pt(9); r_.font.name = SERIF
            cont._p.getparent().remove(cont._p); anchor.addnext(cont._p); anchor = cont._p
            anchor.addnext(nt); anchor = nt
        for ri, tr in enumerate(orig.findall(qn('w:tr'))):
            if ri not in chunks[0]: orig.remove(tr)

# ---------------------------------------------------------------- captions, figures
MAXH = int(Cm(15.0))
FIG_SCALE = {'Figure 4.4': 0.72, 'Figure 4.5': 0.8}
capre = re.compile(r'^(Figure|Table) (\d+\.\d+b?|[A-Z]\.\d+)(:?)(\s|$)')
cur_h1 = ''
for p in d.paragraphs:
    txt = p.text.strip()
    if p.style.name == 'Heading 1': cur_h1 = txt
    if p._p.xpath('.//w:drawing') and p is not d.paragraphs[0]:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.keep_with_next = True; p.paragraph_format.space_before = Pt(8); p.paragraph_format.line_spacing = 1.0
        for e in p._p.xpath('.//wp:extent'):
            cx, cy = int(e.get('cx')), int(e.get('cy')); mx = int(Cm(13.6 if cur_h1.endswith('Introduction') else 15.5))
            if cx > mx: e.set('cx', str(mx)); e.set('cy', str(int(cy * mx / cx))); cx, cy = mx, int(cy * mx / cx)
            if cy > MAXH: e.set('cx', str(int(cx * MAXH / cy))); e.set('cy', str(MAXH))
        for e in p._p.xpath('.//a:ext'):
            if e.get('cx') and int(e.get('cx')) > int(Cm(15.5)): cx, cy = int(e.get('cx')), int(e.get('cy')); e.set('cx', str(int(Cm(15.5)))); e.set('cy', str(int(cy * int(Cm(15.5)) / cx)))
            if e.get('cx') and int(e.get('cy')) > MAXH: cx, cy = int(e.get('cx')), int(e.get('cy')); e.set('cx', str(int(cx * MAXH / cy))); e.set('cy', str(MAXH))
        _nx = p._p.getnext(); _ct = ''.join(_nx.itertext()).strip() if _nx is not None else ''
        _fm = re.match(r'(Figure \d+\.\d+)', _ct)
        if _fm and _fm.group(1) in FIG_SCALE:                      # print layout: shrink single figures a little so that they fill the page gap
            _sc = FIG_SCALE[_fm.group(1)]
            for e in p._p.xpath('.//wp:extent') + p._p.xpath('.//a:ext'):
                if e.get('cx') and e.get('cy'): e.set('cx', str(int(int(e.get('cx')) * _sc))); e.set('cy', str(int(int(e.get('cy')) * _sc)))
    m = capre.match(txt)
    if m and len(txt) > 14 and not txt.startswith('@@') and p.runs and p.runs[0].bold:        # captions start with a bold label; sentences that merely start with "Table 5.1 shows ..." stay normal text
        if not m.group(3) and p.runs:
            r0 = p.runs[0]; r0.text = r0.text.replace(m.group(2), m.group(2) + ':', 1) if m.group(2) in r0.text else r0.text
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.line_spacing = 1.1; p.paragraph_format.space_after = Pt(10 if m.group(1) == 'Figure' else 5)
        p.paragraph_format.left_indent = Cm(1.8); p.paragraph_format.first_line_indent = Cm(-1.8) if False else None
        if m.group(1) == 'Table': p.paragraph_format.keep_with_next = True; p.paragraph_format.space_before = Pt(10)
        for r in p.runs: r.font.size = Pt(10); r.font.bold = False; r.font.color.rgb = RGBColor(0, 0, 0); r.font.name = SERIF
        p.paragraph_format.left_indent = Cm(0)
# ---------------------------------------------------------------- table captions become the first row of their table
from docx.text.paragraph import Paragraph
def caption_into_table(t):
    """caption and table form one object: a page break can never separate them (Pages ignores keep-with-next for tables)"""
    pv = t._tbl.getprevious()
    if pv is None or pv.tag != qn('w:p'): return
    txt = ''.join(pv.itertext()).strip()
    if not re.match(r'^Table ([A-Z]\.)?\d', txt): return
    if not re.match(r'^Table [A-Z]\.\d+:', txt) or len(txt) > 200: return       # appendix tables only (the main chapters stay as they are)
    ncol = len(t.columns)
    tr = copy.deepcopy(t.rows[0]._tr)
    cells = tr.findall(qn('w:tc'))
    for tc_ in cells[1:]: tr.remove(tc_)
    tc = cells[0]; tcPr = tc.get_or_add_tcPr()
    for tag in ('w:tcBorders', 'w:gridSpan', 'w:shd'):
        for e in tcPr.findall(qn(tag)): tcPr.remove(e)
    gs = OxmlElement('w:gridSpan'); gs.set(qn('w:val'), str(ncol)); tcPr.append(gs)
    for e in tcPr.findall(qn('w:tcW')): e.set(qn('w:w'), '9071'); e.set(qn('w:type'), 'dxa')
    for p_ in tc.findall(qn('w:p')): tc.remove(p_)
    tc.append(pv)                                   # moves the caption paragraph into the cell
    t._tbl.insert(list(t._tbl).index(t.rows[0]._tr), tr)
    cp = Paragraph(pv, t._parent)
    cp.paragraph_format.keep_with_next = True; cp.paragraph_format.space_before = Pt(2); cp.paragraph_format.space_after = Pt(5)
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER                 # centred like the reference thesis
for t in list(d.tables):
    if id(t._tbl) in nom_ids: continue
    caption_into_table(t)
# appendix: tables that follow a heading directly get a hair-thin first row (like the caption row of the other tables): Pages then keeps heading and table together
for t in d.tables:
    if APPX_IDX is None or list(body).index(t._tbl) <= APPX_IDX or len(t.rows) < 6: continue
    pv = t._tbl.getprevious()
    if pv is None or pv.tag != qn('w:p') or not Paragraph(pv, d._body).style.name.startswith('Heading'): continue
    ncol_ = len(t.columns); tr = _copy.deepcopy(t.rows[0]._tr); cells_ = tr.findall(qn('w:tc'))
    for tc_ in cells_[1:]: tr.remove(tc_)
    tc = cells_[0]; tcPr = tc.get_or_add_tcPr()
    for tag in ('w:tcBorders', 'w:gridSpan', 'w:shd'):
        for e in tcPr.findall(qn(tag)): tcPr.remove(e)
    gs = OxmlElement('w:gridSpan'); gs.set(qn('w:val'), str(ncol_)); tcPr.append(gs)
    for e in tcPr.findall(qn('w:tcW')): e.set(qn('w:w'), '9071'); e.set(qn('w:type'), 'dxa')
    for p_ in tc.findall(qn('w:p')): tc.remove(p_)
    p_ = OxmlElement('w:p'); pPr_ = OxmlElement('w:pPr'); pPr_.append(OxmlElement('w:keepNext'))
    sc_ = OxmlElement('w:spacing'); sc_.set(qn('w:before'), '0'); sc_.set(qn('w:after'), '0'); sc_.set(qn('w:line'), '20'); sc_.set(qn('w:lineRule'), 'exact'); pPr_.append(sc_); p_.append(pPr_)
    tc.append(p_)
    t._tbl.insert(list(t._tbl).index(t.rows[0]._tr), tr)
# (no row-level keep-with-next: Pages answers it by moving tables to pages of their own)
# ---------------------------------------------------------------- tables that would run over a page break start on a fresh page
import json
BR = os.path.join(HERE, 'table_breaks.json')
if os.path.exists(BR):
    brk = set(json.load(open(BR)))
    for ti, t in enumerate(d.tables):
        if ti in brk:
            pv = t._tbl.getprevious()
            if pv is not None and pv.tag == qn('w:p'):
                tgt = Paragraph(pv, d._body)
                while True:                                   # a heading in front of the paragraph moves with it (Pages leaves headings alone otherwise)
                    pp = tgt._p.getprevious()
                    if pp is not None and pp.tag == qn('w:p') and Paragraph(pp, d._body).style.name.startswith('Heading'): tgt = Paragraph(pp, d._body)
                    else: break
                tgt.paragraph_format.page_break_before = True
# ---------------------------------------------------------------- notes under tables
for p in d.paragraphs:
    if p.text.startswith('Note. '):
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT; p.paragraph_format.space_before = Pt(4); p.paragraph_format.space_after = Pt(8); p.paragraph_format.line_spacing = 1.05
        for r in p.runs: r.font.size = Pt(9); r.font.name = SERIF
# ---------------------------------------------------------------- bibliography entries: hanging indent, ragged right
inbib = False
for p in d.paragraphs:
    if p.style.name == 'Heading 1': inbib = (p.text.strip() == 'Bibliography')
    elif inbib:
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT; p.paragraph_format.left_indent = Cm(0.9); p.paragraph_format.first_line_indent = Cm(-0.9); p.paragraph_format.space_after = Pt(7); p.paragraph_format.line_spacing = 1.1
        for r in p.runs: r.font.size = Pt(10.5)
# ---------------------------------------------------------------- numbered equations as native Word equations (Office Math)
import omml
EQ_RE = re.compile(r'\(Eq\. ([A-Z]?[0-9.]+)\)\s*$')
n_eq = 0
for p_ in list(d.paragraphs):
    m_ = EQ_RE.search(p_.text.strip())
    if not m_ or m_.group(1) not in omml.EQUATIONS or len(p_.text) > 260: continue
    label = m_.group(1)
    t_ = d.add_table(rows=1, cols=3)
    t_.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = t_._tbl.tblPr
    lay = OxmlElement('w:tblLayout'); lay.set(qn('w:type'), 'fixed'); tblPr.append(lay)
    widths = [Cm(1.4), Cm(13.2), Cm(1.4)]
    for c_, w_ in zip(t_.rows[0].cells, widths):
        c_.width = w_
        vA = OxmlElement('w:vAlign'); vA.set(qn('w:val'), 'center'); c_._tc.get_or_add_tcPr().append(vA)
        mid = t_.rows[0].cells[1].paragraphs[0]
    mid.paragraph_format.space_before = Pt(6); mid.paragraph_format.space_after = Pt(6)
    t_.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))      # an equation is never cut by a page break
    mid._p.append(omml.omath_para(omml.EQUATIONS[label]))
    num = t_.rows[0].cells[2].paragraphs[0]
    num.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    rr = num.add_run('(%s)' % label); rr.font.name = SERIF; rr.font.size = Pt(11)
    prev = p_._p.getprevious()
    if prev is not None and prev.tag == qn('w:p'):                       # keep the sentence that introduces the equation on the same page
        pPr = prev.get_or_add_pPr(); kn = OxmlElement('w:keepNext'); pPr.append(kn)
    p_._p.addprevious(t_._tbl)
    p_._p.getparent().remove(p_._p)
    n_eq += 1
print('equations converted:', n_eq)
d.core_properties.title = TITLE; d.core_properties.author = 'Robin Singh'
d.save(os.path.join(HERE, OUT) if not os.path.isabs(OUT) else OUT)
print('formatted:', len(d.sections), 'sections,', len(d.tables), 'tables')
