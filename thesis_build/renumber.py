"""Swap chapter 3 (Methodology) and chapter 4 (Study Data): renumber headings and every Sect./Chapter reference; verify by heading title."""
import re,glob,sys,os
R='restructure'
def sw(num):
    parts=num.split('.')
    if parts[0]=='3': parts[0]='4'
    elif parts[0]=='4': parts[0]='3'
    return '.'.join(parts)
NUM=r'\d+(?:\.\d+){0,2}'
REF=re.compile(r'(Sects?\.|Sections?|Chapters?)(\s+)('+NUM+r'(?:\s*(?:,|and|–|-|to|&)\s*'+NUM+r')*)')
def fix_ref(m):
    body=m.group(3)
    new=re.sub(NUM,lambda x:sw(x.group(0)),body)
    # keep "3 and 4" order for chapter pairs
    if re.fullmatch(r'4(\s+and\s+)3',new): new='3'+re.search(r'\s+and\s+',new).group(0)+'4'
    return m.group(1)+m.group(2)+new
def heading(m):
    return m.group(1)+sw(m.group(2))+m.group(3)
HEAD=re.compile(r'(?m)^(#{1,4} )(\d+(?:\.\d+){0,2})( .*)$')
def process(text):
    out=[]
    for line in text.split('\n'):
        if HEAD.match(line): line=HEAD.sub(heading,line)
        else: line=REF.sub(fix_ref,line)
        out.append(line)
    return '\n'.join(out)
files=[f'{R}/n{i}_{n}.md' for i,n in [(1,'introduction'),(2,'literature'),(3,'methodology'),(4,'study_data'),(5,'results'),(6,'discussion'),(7,'conclusion')]]
files+= [f'{R}/{x}' for x in ['nA_appendix.md','scripts_table.md','defects_table.md','a8_source_code.md']]
if __name__=='__main__':
    # title index before
    def titles(paths):
        d={}
        for f in paths:
            for m in re.finditer(r'(?m)^#{1,4} (\d+(?:\.\d+){0,2}) (.*)$',open(f).read()): d[m.group(1)]=m.group(2).strip()
        return d
    told=titles(files[:7])
    bad=0
    for f in files:
        t=open(f).read(); n=process(t)
        if f.endswith('scripts_table.md'):   # section column of Table {T:scripts}: last cell of each row
            n='\n'.join((re.sub(r'\| (\d(?:\.\d)?) \|$',lambda m:'| '+sw(m.group(1))+' |',l) if l.startswith('|') else l) for l in n.split('\n'))
        # verify references by title
        for a,b in zip(REF.finditer(t),REF.finditer(n)):
            pass
        open(f,'w').write(n)
    tnew=titles(files[:7])
    # check heading mapping consistent
    for k,v in told.items():
        k2=sw(k)
        if tnew.get(k2)!=v: bad+=1; print('HEADING MISMATCH',k,v,'->',k2,tnew.get(k2))
    print('headings checked',len(told),'bad',bad)
