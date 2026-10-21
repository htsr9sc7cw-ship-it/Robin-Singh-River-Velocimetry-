"""Regroup Chapter 5 into 5.1 simulation, 5.2 PTV, 5.3 PIPs++, 5.4 comparison, 5.5 predictions. Maps references first (old->new), then reassembles n5 from its own blocks."""
import re
R='restructure'
M={'5.1':'5.1','5.2':'5.4','5.2.1':'5.4.1','5.2.2':'5.4.2','5.2.3':'5.4.3','5.2.4':'5.4.4','5.3':'5.2',
   '5.4':'5.3','5.4.1':'5.3.1','5.4.2':'5.3.2','5.4.3':'5.3.3','5.5':'5.3','5.5.1':'5.3.4','5.5.2':'5.3.5','5.5.3':'5.3.6',
   '5.6':'5.4.5','5.7':'5.3.7','5.8':'5.5'}
NUM=r'\d+(?:\.\d+){0,2}'
REF=re.compile(r'(Sects?\.|Sections?)(\s+)('+NUM+r'(?:\s*(?:,|and|–|-|to|&)\s*'+NUM+r')*)')
def mp(n):
    return M.get(n,n) if n.startswith('5.') else n
fix=lambda m:m.group(1)+m.group(2)+re.sub(NUM,lambda x:mp(x.group(0)),m.group(3))
files=[f'{R}/{x}' for x in ['n1_introduction.md','n2_literature.md','n3_methodology.md','n4_study_data.md','n5_results.md','n6_discussion.md','n7_conclusion.md','scripts_table.md','defects_table.md','appendix_post.py','build_appendix.py','nA_appendix.md','moved_tables.json']]
for f in files:
    L=open(f).read().split('\n')
    out=[l if re.match(r'#{1,4} \d',l) else REF.sub(fix,l) for l in L]
    open(f,'w').write('\n'.join(out))
# reassemble n5
p=f'{R}/n5_results.md'; t=open(p).read()
parts=re.split(r'(?m)^(?=#{2,3} 5\.\d)',t)
pre=parts[0]; B={}
for b in parts[1:]:
    k=re.match(r'#{2,3} (5(?:\.\d){1,2}) ',b).group(1); B[k]=b
def body(k): return B[k].split('\n',1)[1].strip('\n')+'\n\n'
def sec(h,k): return h+'\n\n'+body(k)
new=pre.rstrip('\n')+'\n\n'
new+=sec('## 5.1 Simulation and Ground Truth','5.1')
new+=sec('## 5.2 Particle Tracking Velocimetry','5.3')
new+='## 5.3 PIPs++\n\n@@INTRO53@@\n\n'
new+=sec('### 5.3.1 Seeding and Surface','5.4.1')+sec('### 5.3.2 Re-Tracking','5.4.2')+sec('### 5.3.3 Worked Examples','5.4.3')
new+=sec('### 5.3.4 Fine-Tuning','5.5.1')+sec('### 5.3.5 Strategies','5.5.2')+sec('### 5.3.6 Final Model','5.5.3')
new+=sec('### 5.3.7 Retention','5.7')
new+='## 5.4 Comparison of the Methods\n\n@@INTRO54@@\n\n'
new+=sec('### 5.4.1 Overall','5.2.1')+sec('### 5.4.2 Speed Groups','5.2.2')+sec('### 5.4.3 Tracer Density','5.2.3')+sec('### 5.4.4 Clear Water','5.2.4')
new+=sec('### 5.4.5 Moving Water','5.6')
new+=sec('## 5.5 Predictions','5.8')
# keep intro text of old 5.2, 5.4, 5.5 for the hand edit
import json
json.dump({'old52':body('5.2'),'old54':body('5.4'),'old55':body('5.5')},open('/tmp/old_intros.json','w'))
open(p,'w').write(new.rstrip('\n')+'\n')
print('ok',len(new.split()))
