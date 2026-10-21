import re,glob,sys
pats={
 'we+verb':r"\b[Ww]e (put|cut|ran|got|look|find out|used|chose|take|took|keep|kept|leave|left|test|tested|add|added|set|made|make|built|wrote|show|call|tried|do not|did not|never|also|then|can|could|need|know|see|saw|use|run|count|draw|feed|give|repair|repaired|handle|handled|train|trained|score|scored|report|compare|compared|place|read|check|checked)\b",
 'published weights/model':r"published (PIPs\+\+|weights|model|checkpoint)",
 'repo/commit/ckpt':r"github\.com|commit [0-9a-f]{6,}|\.pth|model-0002|SHA-256",
 'everyday':r"\b(cheap(er)?|a lot|stuff|big|nice|good|bad|right speed|the right|works?|gets?|got|turns? |tool made|one of them|simple|easy|just|really|very|huge|tiny|a bit|kind of)\b",
 'meta/files':r"result files|file behind every|program of Sect|scored by the program",
 'contraction':r"\b\w+n't\b|\b\w+'(s|re|ve|ll)\b",
}
tot=0
for f in sorted(glob.glob('restructure/n[1-7]_*.md'))+['00_abstracts_draft1.md']:
    t=open(f).read()
    sents=re.split(r'(?<=[.!?])\s+',t)
    hits={}
    for s in sents:
        for k,p in pats.items():
            if re.search(p,s): hits.setdefault(k,[]).append(s.strip().replace('\n',' ')[:140])
    n=sum(len(v) for v in hits.values()); tot+=n
    print(f"== {f}: {n}  "+', '.join(f"{k}:{len(v)}" for k,v in hits.items()))
    if '-v' in sys.argv:
        for k,v in hits.items():
            for s in v: print(f"   [{k}] {s}")
print('total',tot)
