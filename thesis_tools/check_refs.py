"""Check every 'Sect. x.y' / 'Chapter n' / 'Appendix A.x' reference of THESIS_FULL_v4.md against the headings."""
import re
t = open('THESIS_FULL_v4.md').read()
heads = set(re.findall(r'(?m)^#{1,4} ((?:\d+|A)(?:\.\d+)*)\b', t))
chap = set(re.findall(r'(?m)^# (\d+) ', t))
pat = re.compile(r'(Sects?\.|Sections?)\s+(\d+(?:\.\d+){0,2}|A\.\d+(?:\.\d+)*)((?:\s*(?:,|and|–|-)\s*(?:\d+(?:\.\d+){0,2}|A\.\d+(?:\.\d+)*))*)')
bad = []
for m in pat.finditer(t):
    pre = t[max(0, m.start() - 45):m.start()]
    if re.search(r'et al\.?,?\s*\(?\d{4}[a-z]?,?\s*$|\d{4},\s*$|Eltner|Zheng|Doersch|paper|tutorial', pre): continue
    toks = re.findall(r'\d+(?:\.\d+){0,2}|A\.\d+(?:\.\d+)*', m.group(2) + m.group(3))
    for k in toks:
        if k not in heads and k not in chap: bad.append((k, t[max(0, m.start() - 50):m.end() + 20].replace('\n', ' ')))
for m in re.finditer(r'Chapters?\s+(\d+)', t):
    if m.group(1) not in chap: bad.append(('Chapter ' + m.group(1), t[max(0, m.start() - 40):m.end() + 20].replace('\n', ' ')))
print(len(bad), 'dangling references')
for b in bad: print(b)
