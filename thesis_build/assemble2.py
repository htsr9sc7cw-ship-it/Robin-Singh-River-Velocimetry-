"""Assemble the thesis text from the restructured chapter files and resolve figure/table keys. Output: THESIS_FULL_v4.md"""
import re, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from capkeys import resolve
R = os.path.join(HERE, 'restructure')
rd = lambda p: open(p).read().strip()
parts = [rd(os.path.join(R, f)) for f in ['n1_introduction.md', 'n2_literature.md', 'n4_study_data.md', 'n3_methodology.md', 'n5_results.md', 'n6_discussion.md', 'n7_conclusion.md']]
parts.append(rd(os.path.join(HERE, '08_references.md')))
app = rd(os.path.join(R, 'nA_appendix.md'))
app = app.replace('@@SCRIPTS@@', rd(os.path.join(R, 'scripts_table.md'))).replace('@@SHEETS@@', rd(os.path.join(R, 'sheets.md')))
parts.append(app)
full = '\n\n---\n\n'.join(parts)
import subprocess, json
subprocess.run([sys.executable, os.path.join(HERE, 'make_tables.py')], check=True, stdout=subprocess.DEVNULL)
GEN = json.load(open(os.path.join(R, 'generated_tables.json')))
full = re.sub(r'@@TABLE:([\w.]+)@@', lambda m: GEN[m.group(1)], full)
full = re.sub(r'(?m)^(\*\*(?:Table|Figure) [^\n]*)\n(\|)', r'\1\n\n\2', full)      # a table needs a blank line after its caption
full = re.sub(r'(\|[^\n]*\|)\n\n(\| (?:A\d+|B\d+|C-[a-z]) \|)', r'\1\n\2', full)   # no blank line inside a table
full, missing = resolve(full)
open(os.path.join(HERE, 'THESIS_FULL_v4.md'), 'w').write(full)
print(len(full.split()), 'words; unresolved keys:', sorted(missing))
