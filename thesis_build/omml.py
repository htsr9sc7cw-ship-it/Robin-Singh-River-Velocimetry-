"""Office Math (OMML) builders for the numbered equations of the thesis.
Each equation is built from small helpers and inserted as a native Word equation (Insert > Equation), centred, with its number at the right margin."""
import copy
from lxml import etree

M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = 'xmlns:m="%s" xmlns:w="%s"' % (M, W)
FONT = '<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/><w:sz w:val="23"/><w:szCs w:val="23"/></w:rPr>'


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def r(t, plain=False, bold=False):
    """math run; variables are italic by default, plain=True for operator names and digits"""
    sty = ''
    if plain and bold: sty = '<m:sty m:val="b"/>'
    elif plain: sty = '<m:sty m:val="p"/>'
    elif bold: sty = '<m:sty m:val="bi"/>'
    return '<m:r><m:rPr>%s</m:rPr>%s<m:t xml:space="preserve">%s</m:t></m:r>' % (sty, FONT, esc(t))


def p(t):
    return r(t, plain=True)


def sub(base, s):
    return '<m:sSub><m:e>%s</m:e><m:sub>%s</m:sub></m:sSub>' % (base, s)


def sup(base, s):
    return '<m:sSup><m:e>%s</m:e><m:sup>%s</m:sup></m:sSup>' % (base, s)


def frac(n, d):
    return '<m:f><m:num>%s</m:num><m:den>%s</m:den></m:f>' % (n, d)


def sqrt(x):
    return '<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>%s</m:e></m:rad>' % x


def bar(x):
    return '<m:bar><m:barPr><m:pos m:val="top"/></m:barPr><m:e>%s</m:e></m:bar>' % x


def delim(x, beg='(', end=')'):
    return '<m:d><m:dPr><m:begChr m:val="%s"/><m:endChr m:val="%s"/></m:dPr><m:e>%s</m:e></m:d>' % (beg, end, x)


def nary(chr_, lower, upper, body, hide_upper=False, side=False):
    sup_hide = '<m:supHide m:val="1"/>' if hide_upper else ''
    loc = 'subSup' if side else 'undOvr'
    return ('<m:nary><m:naryPr><m:chr m:val="%s"/><m:limLoc m:val="%s"/>%s</m:naryPr>'
            '<m:sub>%s</m:sub><m:sup>%s</m:sup><m:e>%s</m:e></m:nary>') % (chr_, loc, sup_hide, lower, upper, body)


def vec(letter):
    return r(letter, bold=True)


# ---------------------------------------------------------------------------------------------------- the equations
def nor(t):
    """words and operators as normal text; this encoding is sized consistently by Pages and Word"""
    return '<m:r><m:rPr><m:nor/></m:rPr>%s<m:t xml:space="preserve">%s</m:t></m:r>' % (FONT, esc(t))


def build():
    E = {}
    # (2.1)  min(l1, l2) > l_t   (plain-style runs render at the common size for this short form)
    E['2.1'] = p('min') + delim(sub(r('λ'), p('1')) + p(', ') + sub(r('λ'), p('2'))) + p(' > ') + sub(r('λ'), r('t'))
    # (2.2)  normalised cross-correlation coefficient (Fujita et al., 1998); alpha = a - mean(a), beta = b - mean(b)
    E['2.2'] = (sub(r('R'), r('ab')) + nor(' = ') +
                frac(nary('∑', '', '', r('α') + r('β'), hide_upper=True, side=True),
                     sqrt(nary('∑', '', '', sup(r('α'), nor('2')), hide_upper=True, side=True) + nary('∑', '', '', sup(r('β'), nor('2')), hide_upper=True, side=True))))
    # (2.3)  dissimilarity of the Lucas-Kanade method (Shi and Tomasi, 1994, Eq. 3, weighting function 1)
    E['2.3'] = (r('ε') + delim(vec('d')) + nor(' = ') +
                nary('∫', r('W'), '', sup(delim(r('J') + delim(vec('x') + nor(' + ') + vec('d')) + nor(' − ') + r('I') + delim(vec('x')), '[', ']'), nor('2')) + r('d') + vec('x'), hide_upper=True))
    # (4.1)  ratio
    E['4.1'] = nor('ratio = ') + frac(sub(nor('RMSE'), nor('tracker')), sub(nor('RMSE'), nor('reference')))
    # (4.2)  direction agreement
    E['4.2'] = r('A') + nor(' = ') + frac(r('N') + delim(nor('cos ') + r('θ') + nor(' > 0.8')), r('N'))
    # (4.3)  speed ratio
    E['4.3'] = r('q') + nor(' = median') + delim(frac(nor('|') + vec('d') + nor('|'), nor('|') + vec('t') + nor('|')))
    # (4.4)  coverage
    E['4.4'] = r('C') + nor(' = ') + frac(sub(r('N'), nor('est')), sub(r('N'), nor('water')))
    # (4.5)  speed bias; the bars denote means over the cells with an estimate
    E['4.5'] = (r('B') + nor(' = 100 ⋅ ') + frac(bar(sub(r('v'), nor('tracked'))) + nor(' − ') + bar(sub(r('v'), nor('true'))), bar(sub(r('v'), nor('true')))))
    # (A.1)  ratio from the step errors
    di = sub(vec('d'), r('i')); ti = sub(vec('t'), r('i'))
    E['A.1'] = (nor('ratio = ') +
                sqrt(frac(nary('∑', '', '', nor('|') + di + nor(' − ') + ti + nor('|²'), hide_upper=True),
                          nary('∑', '', '', nor('|') + ti + nor('|²'), hide_upper=True))))
    return E


def omath_para(inner):
    xml = '<m:oMathPara %s><m:oMathParaPr><m:jc m:val="center"/></m:oMathParaPr><m:oMath>%s</m:oMath></m:oMathPara>' % (NS, inner)
    return etree.fromstring(xml)


EQUATIONS = build()
