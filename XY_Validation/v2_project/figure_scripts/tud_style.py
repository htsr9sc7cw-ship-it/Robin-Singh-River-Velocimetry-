"""Shared figure style of the thesis, after the corporate design of TU Dresden.

Rules used for every figure: white background, TU Dresden dark blue (HKS 41) for outlines, lines and
emphasis, tints of the same blue and neutral greys for everything else, no figure title inside the
picture (the title is the caption in the thesis), a sans-serif face (Open Sans is the TU Dresden face;
if it is not installed the first available of Arial / Helvetica / DejaVu Sans is used).

Usage in any plotting script::

    import tud_style as tud
    tud.apply()                      # sets fonts, sizes, colours, spines
    ax.plot(x, y, color=tud.TRACKER['S6'], **tud.LINE['S6'])

The hex values are screen approximations of the TU Dresden colours; replace them here (and only here)
if you have the official values of the corporate-design manual.
"""
import matplotlib
from matplotlib import font_manager

# ---- palette ---------------------------------------------------------------------------------------
BLUE = '#002557'        # TU Dresden dark blue (HKS 41): outlines, main lines, emphasis
BLUE_MID = '#0069B4'    # lighter blue for a second series
BLUE_LIGHT = '#8DB4DB'  # light blue for a third series
BLUE_TINT = '#E4ECF5'   # very light tint for bands and highlighted cells
INK = '#1A1A1A'         # text
GREY = '#666666'        # secondary text
GREY_MID = '#9A9A9A'    # reference lines, pre-trained model
GREY_LIGHT = '#D9D9D9'  # grid, separators
WHITE = '#FFFFFF'

# ---- ONE colour + marker + line style per method, used by EVERY figure of the thesis (defined only here) ------------
# keys: S0 pre-trained PIPs++, S1..S5 other retraining strategies, S6 final retrained model, NCC / LK tuned FlowVelo
# (PTV) modes, GUI = FlowVelo LK with GUI default parameters. Blues and greys only (TU Dresden palette); the marker and
# the line style separate similar blues. Never colour a method differently in another figure.
S1_BLUE = '#9DBCE0'; S2_BLUE = '#7FA6D0'; S3_BLUE = '#4F7FB5'; S4_BLUE = '#2B5A94'
LK_BLUE = '#5BA0DA'     # FlowVelo LK: lighter than NCC, clearly visible on white
GUI_GREY = '#555555'    # FlowVelo LK with GUI defaults: dark grey, so it never vanishes next to the light blues
TRACKER = {
    'S0': GREY_MID, 'PRE': GREY_MID,      # pre-trained PIPs++
    'S1': S1_BLUE, 'S2': S2_BLUE, 'S3': S3_BLUE, 'S4': S4_BLUE,
    'S5': INK,                            # trained from scratch
    'S6': BLUE,                           # final retrained model
    'NCC': BLUE_MID, 'LK': LK_BLUE, 'GUI': GUI_GREY,   # FlowVelo modes
}
LINE = {
    'S0': dict(ls='--', marker='o'), 'PRE': dict(ls='--', marker='o'),
    'S1': dict(ls='-', marker='p'), 'S2': dict(ls='-', marker='<'), 'S3': dict(ls='-', marker='>'),
    'S4': dict(ls='-', marker='h'), 'S5': dict(ls=':', marker='*'), 'S6': dict(ls='-', marker='D'),
    'NCC': dict(ls='-', marker='s'), 'LK': dict(ls='-.', marker='^'), 'GUI': dict(ls=':', marker='v'),
}
MARKER = {k: v['marker'] for k, v in LINE.items()}
MIN_PT = 8.2    # smallest text of any figure, in points as printed at the thesis text width (6.3 in)
PAGE_IN = 6.3


def method_key(m):
    """map a run / method name of the result tables to the key of TRACKER (one colour per method everywhere)"""
    if m.startswith('PIPs++'):
        if '_S6' in m: return 'S6'
        for k in ('S2', 'S3', 'S4', 'S5'):
            if '_' + k in m: return k
        return 'S1' if '_ft' in m else 'S0'
    if 'gui' in m: return 'GUI'
    if 'ncc' in m: return 'NCC'
    if 'lk' in m: return 'LK'
    return None


# sequential map for heat maps (white -> TU blue); skill = dark, no skill = light
CMAP = matplotlib.colors.LinearSegmentedColormap.from_list('tud', [BLUE, BLUE_MID, BLUE_LIGHT, BLUE_TINT, WHITE])

_FACES = ['Open Sans', 'Arial', 'Helvetica Neue', 'Helvetica', 'DejaVu Sans']


def font():
    """first installed face of the preferred list"""
    have = {f.name for f in font_manager.fontManager.ttflist}
    return next((f for f in _FACES if f in have), 'DejaVu Sans')


SCALE = 1.25   # all text of the diagrams is drawn 25 % larger than the original sizes


def _scale_explicit_sizes():
    """explicit fontsize=... values in the scripts are scaled by SCALE as well"""
    from matplotlib import text as _t
    if getattr(_t.Text, '_tud_scaled', False): return
    _orig = _t.Text.set_fontsize
    def set_fontsize(self, fontsize):
        if isinstance(fontsize, (int, float)): fontsize = fontsize * SCALE
        return _orig(self, fontsize)
    _t.Text.set_fontsize = set_fontsize; _t.Text._tud_scaled = True


def fs_min(width_in):
    """explicit fontsize=... argument that already satisfies MIN_PT for a picture of this width (layouts can use it)"""
    return MIN_PT / min(1.0, PAGE_IN / width_in) / SCALE


def _enforce_min_size(fig):
    """no text of the picture is smaller than MIN_PT points at print width (axis, tick, legend, annotation, panel title)"""
    from matplotlib import text as _t
    w = fig.get_size_inches()[0]
    lo = MIN_PT / min(1.0, PAGE_IN / w)
    for ax in fig.axes:
        for axis, name in ((ax.xaxis, 'x'), (ax.yaxis, 'y')):
            labs = axis.get_ticklabels()
            if labs and labs[0].get_fontsize() < lo - 1e-6:
                ax.tick_params(axis=name, which='both', labelsize=lo)
    for t in fig.findobj(_t.Text):
        if t.get_text().strip() and t.get_fontsize() < lo - 1e-6:
            t._fontproperties.set_size(lo); t.stale = True


def _hook_savefig():
    from matplotlib import figure as _f
    if getattr(_f.Figure, '_tud_min', False): return
    _orig = _f.Figure.savefig
    def savefig(self, *a, **k):
        _enforce_min_size(self)
        return _orig(self, *a, **k)
    _f.Figure.savefig = savefig; _f.Figure._tud_min = True


def apply():
    """set the thesis style for every figure drawn afterwards"""
    _scale_explicit_sizes(); _hook_savefig()
    matplotlib.rcParams.update({
        'font.family': font(), 'mathtext.fontset': 'custom', 'mathtext.rm': font(), 'mathtext.it': font() + ':italic', 'mathtext.bf': font() + ':bold', 'mathtext.default': 'regular', 'font.size': 9 * SCALE, 'text.color': INK,
        'axes.labelsize': 9 * SCALE, 'axes.titlesize': 10 * SCALE, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left',
        'axes.edgecolor': BLUE, 'axes.labelcolor': INK, 'axes.linewidth': 0.9,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.grid': True, 'grid.color': GREY_LIGHT, 'grid.linewidth': 0.6, 'axes.axisbelow': True,
        'xtick.color': INK, 'ytick.color': INK, 'xtick.labelsize': 8.5 * SCALE, 'ytick.labelsize': 8.5 * SCALE,
        'legend.frameon': True, 'legend.framealpha': 1.0, 'legend.facecolor': WHITE, 'legend.edgecolor': 'none', 'legend.fontsize': 8.5 * SCALE,
        'figure.facecolor': WHITE, 'axes.facecolor': WHITE, 'savefig.facecolor': WHITE, 'savefig.dpi': 200,
        'axes.prop_cycle': matplotlib.cycler(color=[BLUE, BLUE_MID, BLUE_LIGHT, GREY_MID, INK]),
    })


def box(ax, x, y, w, h, title='', sub='', sect='', lw=1.4, fc=WHITE, ec=BLUE, ls='-', size=(9.2, 7.6), tcolor=INK):
    """white rounded box with a TU-blue outline; title in bold, sub text below, section tag bottom right"""
    from matplotlib.patches import FancyBboxPatch
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=1.0', fc=fc, ec=ec, lw=lw, ls=ls, zorder=2))
    if title:
        ax.text(x + 1.4, y + h - 1.5, title, ha='left', va='top', fontsize=size[0], fontweight='bold', color=ec if ec != GREY_MID else GREY, zorder=3)
    if sub:
        ax.text(x + 1.4, y + h - 5.6, sub, ha='left', va='top', fontsize=size[1], color=tcolor, linespacing=1.35, zorder=3)
    if sect:
        ax.text(x + w - 1.0, y + 1.0, sect, ha='right', va='bottom', fontsize=7.4, color=GREY, zorder=3)


def arrow(ax, x0, y0, x1, y1, lw=1.3, color=BLUE):
    """thin blue arrow"""
    ax.annotate('', xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle='-|>', color=color, lw=lw, shrinkA=0, shrinkB=0), zorder=1)
