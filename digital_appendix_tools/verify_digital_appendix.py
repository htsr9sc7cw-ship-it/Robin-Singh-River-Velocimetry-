"""Verify the cleaned scripts of the digital appendix against the originals and write VERIFICATION.txt.

Checks per script: (1) it compiles; (2) its code is identical to the original after formatting, i.e. the abstract
syntax trees are equal when the module docstring is ignored, so no result can change; (3) the header fields
(Thesis section, Inputs, Outputs) are present; (4) ruff finds no undefined names (F821) that the original lacks.
Check 5 runs the known-answer control of the original evaluator on one variant.
"""
import ast, datetime, os, py_compile, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_digital_appendix import MANIFEST, ROOT, HERE, PY

def norm_docs(tree):
    """docstrings are compared after strip(); black only changes their trailing whitespace"""
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], 'value', None), ast.Constant) and isinstance(n.body[0].value.value, str):
            n.body[0].value.value = n.body[0].value.value.strip()
    return tree

def strip_doc(tree):
    tree = norm_docs(tree)
    if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(getattr(tree.body[0], 'value', None), ast.Constant) and isinstance(tree.body[0].value.value, str):
        tree.body = tree.body[1:]
    return ast.dump(tree)

def f821(path):
    r = subprocess.run([PY, '-m', 'ruff', 'check', '--select', 'F821,E9', '--output-format', 'concise', path], capture_output=True, text=True)
    return len([l for l in r.stdout.split('\n') if ': F821' in l or ': E9' in l])

lines = ['Verification of the digital appendix, %s' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), '']
ok_all = True
for rel, *_ in MANIFEST:
    name = os.path.basename(rel); new = os.path.join(HERE, 'scripts', name); old = os.path.join(ROOT, rel)
    res = []
    try: py_compile.compile(new, doraise=True); res.append('compiles')
    except Exception as e: res.append('COMPILE FAIL'); ok_all = False
    same = strip_doc(ast.parse(open(old).read())) == strip_doc(ast.parse(open(new).read()))
    res.append('code identical to original' if same else 'CODE DIFFERS'); ok_all &= same
    doc = ast.get_docstring(ast.parse(open(new).read())) or ''
    hdr = all(k in doc for k in ('Thesis section:', 'Inputs:', 'Outputs:')); res.append('header ok' if hdr else 'HEADER MISSING'); ok_all &= hdr
    a, b = f821(old), f821(new); res.append('undefined names %d (original %d)' % (b, a)); ok_all &= (b <= a)
    lines.append('%-28s %s' % (name, '; '.join(res)))
# known-answer control through the original evaluator
r = subprocess.run(['/opt/anaconda3/bin/python', 'known_answer_eval.py', 'v2_Path4_dense'], cwd=os.path.join(ROOT, 'v2_project'), capture_output=True, text=True, timeout=1800)
tail = [l for l in (r.stdout + r.stderr).strip().split('\n') if l.strip()][-3:]
lines += ['', 'Known-answer control (known_answer_eval.py v2_Path4_dense, original evaluator):'] + ['  ' + l for l in tail]
lines += ['', 'RESULT: ' + ('ALL CHECKS PASSED' if ok_all and r.returncode == 0 else 'CHECK FAILED')]
open(os.path.join(HERE, 'VERIFICATION.txt'), 'w').write('\n'.join(lines) + '\n'); print('\n'.join(lines))
