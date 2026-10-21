"""Compare the chapter sources with the saved copies: numbers, {T:}/{F:} keys, Sect. refs, `paths` and (Author, year) citations must be identical."""
import re, glob, collections
def facts(s):
    return {'numbers': collections.Counter(re.findall(r'\d+(?:[.,]\d+)?', re.sub(r'\bIn short, ','',s))),
            'keys': collections.Counter(re.findall(r'\{[TF]:[^}]+\}', s)),
            'sect': collections.Counter(re.findall(r'Sects?\. [\d.–]+', s)),
            'paths': collections.Counter(re.findall(r'`[^`]+`', s)),
            'cites': collections.Counter(re.findall(r'\(?[A-Z][A-Za-z\-]+(?: et al\.| and [A-Z][a-z]+)?,? \(?\d{4}[a-z]?\)?', s))}
bad = 0
for f in sorted(glob.glob('restructure/n[1-7]_*.md')):
    a = open('Versions/restructure_before_simplify/' + f.split('/')[-1]).read(); b = open(f).read()
    fa, fb = facts(a), facts(b)
    for k in fa:
        d = (fa[k] - fb[k]) + (fb[k] - fa[k])
        if d: bad += 1; print(f.split('/')[-1], k, dict(list(d.items())[:12]))
print('DIFFERENCES:', bad)
