"""Read the Pages PDF export and write pagemap.json: contents / list entry -> printed page number (Contents page = 1)."""
import re, json, os, sys, logging, pypdf
logging.disable(logging.CRITICAL)
HERE = os.path.dirname(os.path.abspath(__file__))
pdf = os.path.join(HERE, '_build', 'thesis_preview.pdf')
r = pypdf.PdfReader(pdf); pages = [[re.sub(r'\s+', ' ', l).strip() for l in (p.extract_text() or '').split('\n')] for p in r.pages]
c0 = next(i for i, L in enumerate(pages) if 'Contents' in L and any('Introduction' in x and '.....' in x for x in L))
ch1 = next(i for i, L in enumerate(pages) if i > c0 and any(x.startswith('1. INTRODUCTION') for x in L[:3]))
src = open(os.path.join(HERE, '_docx_source.md')).read()
entries = re.findall(r'^@@(T\d|F)@@(.*)$', src, re.M)
pm = {}; miss = []
for kind, text in entries:
    text = text.strip(); key = text
    if kind == 'F': pref = re.match(r'^((?:Figure|Table) (?:\d+\.\d+b?|[A-Z]\.\d+):)', text).group(1)
    else: pref = re.sub(r'\s+', ' ', text)[:30]
    found = None
    for i in range(c0 + 1 if text in ('List of Figures', 'List of Tables', 'Nomenclature') else ch1, len(pages)):
        for l in pages[i]:
            if (l.startswith(pref) if kind == 'F' else (l.startswith(pref) and (len(text) > 30 or l == text or l.startswith(text)))):
                found = i; break
        if found is not None: break
    if found is None: miss.append(text[:50]); continue
    pm[key] = found - c0 + 1
json.dump(pm, open(os.path.join(HERE, 'pagemap.json'), 'w'), indent=1, ensure_ascii=False)
print('contents page idx', c0 + 1, 'chapter 1 pdf page', ch1 + 1, 'entries', len(pm), 'missing', len(miss), miss[:8])
