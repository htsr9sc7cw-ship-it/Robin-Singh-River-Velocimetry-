"""Symbolic figure/table keys: symbolize() turns 'Figure 5.3' into 'Figure {F:5.3}', resolve() renumbers by position."""
import re
CAP = re.compile(r'^\*\*(Figure|Table) (\d+\.\d+|[A-Z]\.\d+)\*\*', re.M)
def symbolize(t):
    def cap(m): return '**%s {%s:%s}**' % (m.group(1), m.group(1)[0], m.group(2))
    t = CAP.sub(cap, t)
    def ref(m):
        k = m.group(1)[0]; body = m.group(2)
        return m.group(1) + ' ' + re.sub(r'\d+\.\d+', lambda x: '{%s:%s}' % (k, x.group(0)), body)
    return re.sub(r'(Figures?|Figs?\.|Tables?)\s+(\d+\.\d+(?:\s*(?:[–,-]|and)\s*\d+\.\d+)*)', ref, t)
def resolve(t):
    chap = None; counts = {}; table = {}
    for line in t.split('\n'):
        h = re.match(r'^# (\d+|Appendix [A-Z])\b', line)
        if h: chap = h.group(1).replace('Appendix ', ''); continue
        m = re.match(r'^\*\*(Figure|Table) \{([FT]):([^}]+)\}\*\*', line)
        if m:
            k = m.group(2); counts[(chap, k)] = counts.get((chap, k), 0) + 1
            table[(k, m.group(3))] = '%s.%d' % (chap, counts[(chap, k)])
    missing = set()
    def sub(m):
        v = table.get((m.group(1), m.group(2)))
        if v is None: missing.add(m.group(0)); return m.group(0)
        return v
    out = re.sub(r'\{([FT]):([^}]+)\}', sub, t)
    return out, missing
if __name__ == '__main__':
    import sys
    for f in sys.argv[1:]:
        t = open(f).read(); open(f, 'w').write(symbolize(t)); print('symbolized', f)
