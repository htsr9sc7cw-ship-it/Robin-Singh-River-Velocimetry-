"""make_results.py

Thesis section: see README.md
Inputs: see README.md
Outputs: see README.md

Results tables and figures from results/three_way_v2.csv (corrected scoring, FIXLOG C1-C3).
    /opt/anaconda3/bin/python make_results.py          (base interpreter: pandas + matplotlib)
Writes results/tables/*.csv|md and results/figures/fig_*.png. Every number in the thesis text comes
from these files. Runs from PyCharm unchanged.
"""

import os, numpy as np, pandas as pd, matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, 'results')
os.makedirs(os.path.join(R, 'tables'), exist_ok=True)
os.makedirs(os.path.join(R, 'figures'), exist_ok=True)
d = pd.read_csv(os.path.join(R, 'three_way_v2.csv'))
d = d[
    ~d.scene.str.contains('_ts0_')
].copy()  # the speed-ladder rungs are reported in their own table (T5.6), not pooled
d['ratio'] = d.rmse / d.rmse_stay
d['view'] = d.scene.str.replace('^v2_', '', regex=True).str.replace(
    '_(sparse|dense)$', '', regex=True
)
d['density'] = d.scene.str.extract(r'_(sparse|dense)$')
# GT speed per variant = median |truth| seen by PIPs++ (dense grid over the water, not where PTV found features)
sp = d[d.method == 'PIPs++'].set_index('scene').truth_med
d['gt_speed'] = d.scene.map(sp)
# speed groups from the v3 GT (median |truth| under the PIPs++ grid): the quartile-like edges below are data-driven, members listed from the CSV
bins = [0, 18, 30, 50, 200]
labels = [
    '<18 px/f (Overview)',
    '18-30 px/f (Path 1-7, high angle, Low_1.003)',
    '30-50 px/f (low angle, Low_1, Low_2, Low_1.002)',
    '>50 px/f (Low_1.001)',
]
d['speed_group'] = pd.cut(d.gt_speed, bins, labels=labels)
ORDER = ['PIPs++', 'PTV_tuned_ncc', 'PTV_tuned_lk', 'PTV_gui_defaults']
NAME = {
    'PIPs++': 'PIPs++ (untrained)',
    'PTV_tuned_ncc': 'PTV NCC (tuned)',
    'PTV_tuned_lk': 'PTV LK (tuned)',
    'PTV_gui_defaults': 'PTV LK (GUI defaults)',
}
COL = {
    'PIPs++': '#2a78d6',
    'PTV_tuned_ncc': '#eb6834',
    'PTV_tuned_lk': '#1baf7a',
    'PTV_gui_defaults': '#eda100',
}
MK = {'PIPs++': 'o', 'PTV_tuned_ncc': 's', 'PTV_tuned_lk': '^', 'PTV_gui_defaults': 'v'}
plt.rcParams.update(
    {
        'font.size': 9,
        'font.family': 'DejaVu Sans',
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.grid': True,
        'grid.color': '#e6e6e3',
        'grid.linewidth': 0.6,
        'axes.edgecolor': '#8a8a85',
        'axes.titlesize': 10.5,
        'axes.titleweight': 'bold',
        'axes.titlelocation': 'center',
        'axes.titlepad': 10,
        'axes.labelsize': 9,
        'legend.fontsize': 8,
        'figure.dpi': 200,
        'savefig.dpi': 200,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.15,
        'savefig.facecolor': 'white',
    }
)

# ---- Table 5.1: per variant, RMSE / stay-still and direction agreement -----------------------
d['GT speed (px/frame)'] = d.gt_speed.round(1)
d['variant'] = d.scene.str.replace('^v2_', '', regex=True).str.replace('_', ' ')
t1 = (
    d.pivot_table(index=['variant', 'GT speed (px/frame)'], columns='method', values='ratio')
    .reindex(columns=ORDER)
    .round(2)
    .sort_index(level='GT speed (px/frame)')
)
t1.to_csv(os.path.join(R, 'tables', 'T5_1_rmse_ratio_per_variant.csv'))
t2 = (
    d.pivot_table(index=['variant', 'GT speed (px/frame)'], columns='method', values='frac_cos08')
    .reindex(columns=ORDER)
    .round(2)
    .sort_index(level='GT speed (px/frame)')
)
t2.to_csv(os.path.join(R, 'tables', 'T5_2_frac_cos08_per_variant.csv'))
# ---- Table 5.3: per speed group and method: medians of the headline metrics -----------------
g = (
    d.groupby(['speed_group', 'method'], observed=True)[
        [
            'n',
            'rmse',
            'rmse_stay',
            'ratio',
            'err_med',
            'cos_med',
            'frac_cos08',
            'speed_ratio',
            'frac_zero',
            'd4',
            'd8',
            'd16',
        ]
    ]
    .median()
    .round(3)
)
g.to_csv(os.path.join(R, 'tables', 'T5_3_by_speed_group.csv'))
# ---- Table 5.4: PTV filter cascade (her logfile) per mode, summed over variants -------------
casc_cols = [
    'raw',
    'after_mindist',
    'after_maxdist',
    'after_mincount',
    'after_steady',
    'after_range',
    'final',
]
t4 = d[d.method != 'PIPs++'].groupby('method')[casc_cols].agg(['sum', 'median']).round(0)
t4.to_csv(os.path.join(R, 'tables', 'T5_4_filter_cascade.csv'))
# ---- Table 5.5: overall medians ---------------------------------------------------------------
t5 = (
    d.groupby('method')[
        [
            'n',
            'rmse',
            'rmse_stay',
            'ratio',
            'cos_med',
            'frac_cos08',
            'speed_ratio',
            'frac_zero',
            'd8',
        ]
    ]
    .median()
    .reindex(ORDER)
    .round(3)
)
t5['variants_better_than_stay'] = (
    d[d.ratio < 0.8].groupby('method').size().reindex(ORDER).fillna(0).astype(int)
)
t5.to_csv(os.path.join(R, 'tables', 'T5_5_overall.csv'))
NAMES = {
    'PIPs++': 'PIPs++ (untrained, grid seeds)',
    'PIPs++_fseed': 'PIPs++ (untrained, feature seeds)',
    'PTV_tuned_ncc': 'FlowVelo NCC (tuned)',
    'PTV_tuned_lk': 'FlowVelo LK (tuned, maxLevel 2)',
    'PTV_gui_defaults': 'FlowVelo LK (GUI defaults)',
}


def pretty(t):
    t = t.copy()
    if isinstance(t.index, pd.MultiIndex):
        t.index = pd.MultiIndex.from_tuples(
            [tuple(NAMES.get(x, x) if isinstance(x, str) else x for x in i) for i in t.index],
            names=t.index.names,
        )
    else:
        t.index = [NAMES.get(x, x) if isinstance(x, str) else x for x in t.index]
    t.columns = [NAMES.get(c, c) if isinstance(c, str) else c for c in t.columns]
    if isinstance(t.index, pd.MultiIndex):
        t = t.reset_index()  # tuple row labels -> plain columns
    return t.round(2)


with open(os.path.join(R, 'tables', 'TABLES.md'), 'w') as f:
    f.write(
        '# Result tables (dataset v3; all displacements in native px/frame; ratio = RMSE of tracked displacement / RMSE of the stay-still baseline)\n\n'
    )
    for name, t in (
        (
            'Table 5.1  RMSE ratio per variant and method (below 1 = better than assuming no motion)',
            t1,
        ),
        (
            'Table 5.2  Fraction of sub-steps within 37° of the true direction, per variant and method',
            t2,
        ),
        ('Table 5.3  Median metrics per flow-speed group and method', g),
        (
            'Table 5.4  FlowVelo filter cascade: tracks remaining after each filter (sum and median over variants)',
            t4,
        ),
        ('Table 5.5  Overall medians over the 28 muddy variants', t5),
    ):
        f.write(
            '## %s\n\n%s\n\n'
            % (name, pretty(t).to_markdown(index=not isinstance(t.index, pd.MultiIndex)))
        )

# ---- Fig A: RMSE ratio vs GT speed ------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.0, 4.4))
ax.axhline(1.0, color='#8a8a85', lw=1, ls='--')
ax.text(
    118,
    1.02,
    'stay-still baseline (ratio = 1)',
    color='#52514e',
    ha='right',
    va='bottom',
    fontsize=8,
)
for m in ORDER:
    s = d[d.method == m]
    ax.scatter(
        s.gt_speed,
        s.ratio,
        s=28,
        marker=MK[m],
        color=COL[m],
        label=NAME[m],
        alpha=0.9,
        edgecolor='white',
        linewidth=0.6,
    )
ax.set_xlabel('Ground-truth surface speed, median over the view (px/frame)')
ax.set_ylabel('RMSE ratio (tracked / stay-still)')
ax.set_ylim(0, 1.5)
ax.set_xlim(0, 120)
ax.legend(frameon=False, loc='lower right', fontsize=8)
ax.set_title(
    'Figure 5.1  Tracking error relative to the stay-still baseline versus ground-truth flow speed (28 variants)'
)
fig.tight_layout()
fig.savefig(os.path.join(R, 'figures', 'figA_rmse_ratio_vs_speed.png'))
plt.close(fig)

# ---- Fig B: delta-accuracy curves per speed group ----------------------------------------------
fig, axes = plt.subplots(1, 4, figsize=(12, 4.2), sharey=True)
th = [1, 2, 4, 8, 16]
for ax, grp in zip(axes, labels):
    for m in ORDER:
        s = d[(d.method == m) & (d.speed_group == grp)]
        if len(s) == 0:
            continue
        y = [s['d%d' % t].median() for t in th]
        ax.plot(th, y, marker=MK[m], ms=4, lw=1.8, color=COL[m], label=NAME[m])
    ax.set_xscale('log', base=2)
    ax.set_xticks(th)
    ax.set_xticklabels(th)
    ax.set_title(
        grp.split(' (')[0] + '\n(' + grp.split(' (')[1] if ' (' in grp else grp,
        fontsize=8.5,
        fontweight='normal',
        pad=6,
    )
    ax.set_xlabel('Endpoint error threshold (px)')
    ax.set_ylim(0, 1)
axes[0].set_ylabel('Fraction of sub-steps below threshold', labelpad=8)
h, l = next((ax.get_legend_handles_labels() for ax in axes if ax.lines), ([], []))
fig.legend(h, l, loc='lower center', ncol=4, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.02))
fig.suptitle(
    'Figure 5.2  Fraction of sub-steps within an error threshold, by flow-speed group (median over variants)',
    fontsize=10.5,
    fontweight='bold',
)
fig.tight_layout(rect=(0, 0.06, 1, 0.9))
fig.savefig(os.path.join(R, 'figures', 'figB_delta_accuracy_by_speed.png'))
plt.close(fig)

# ---- Fig C: direction agreement and speed ratio vs GT speed ------------------------------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.6))
for m in ORDER:
    s = d[d.method == m]
    a1.scatter(
        s.gt_speed,
        s.frac_cos08,
        s=26,
        marker=MK[m],
        color=COL[m],
        label=NAME[m],
        edgecolor='white',
        linewidth=0.6,
    )
    a2.scatter(
        s.gt_speed,
        s.speed_ratio,
        s=26,
        marker=MK[m],
        color=COL[m],
        edgecolor='white',
        linewidth=0.6,
    )
a1.set_ylim(0, 1.05)
a1.set_ylabel('Fraction of sub-steps within 37° of the true direction')
a1.set_xlabel('Ground-truth speed (px/frame)')
h, l = a1.get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=4, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.02))
a2.axhline(1, color='#8a8a85', lw=1, ls='--')
a2.set_ylim(0, 1.6)
a2.set_ylabel('Median measured / true displacement')
a2.set_xlabel('Ground-truth speed (px/frame)')
a1.set_title('(a) Direction agreement', fontweight='normal', pad=6)
a2.set_title('(b) Speed ratio (1 = correct magnitude)', fontweight='normal', pad=6)
fig.suptitle(
    'Figure 5.3  Direction and magnitude of the tracked displacement relative to the ground truth',
    fontsize=10.5,
    fontweight='bold',
)
fig.tight_layout(rect=(0, 0.07, 1, 0.92))
fig.savefig(os.path.join(R, 'figures', 'figC_direction_and_speed_ratio.png'))
plt.close(fig)

# ---- Fig D: PTV filter cascade --------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7.2, 3.6))
stages = [
    'raw',
    'after_mindist',
    'after_maxdist',
    'after_mincount',
    'after_steady',
    'after_range',
    'final',
]
snames = [
    'Detected and\ntracked',
    'Minimum\ndistance',
    'Maximum\ndistance',
    'Minimum\ncount',
    'Steadiness',
    'Angle\nrange',
    'Main-flow\ndirection',
]
x = np.arange(len(stages))
w = 0.27
for i, m in enumerate(ORDER[1:]):
    s = d[d.method == m][stages].sum()
    ax.bar(x + (i - 1) * w, s.values, w * 0.92, color=COL[m], label=NAME[m])
    ax.text(
        x[-1] + (i - 1) * w,
        s.values[-1] + 300,
        '%d' % s.values[-1],
        ha='center',
        fontsize=7.5,
        color='#52514e',
    )
ax.set_xticks(x)
ax.set_xticklabels(snames, fontsize=8)
ax.set_ylabel('Tracks remaining (log scale)')
ax.set_yscale('log')
ax.legend(frameon=False, fontsize=8)
ax.set_title(
    'Figure 5.5  Number of FlowVelo tracks remaining after each filter of the published cascade (sum over 28 variants)'
)
fig.tight_layout()
fig.savefig(os.path.join(R, 'figures', 'figD_filter_cascade.png'))
plt.close(fig)

# ---- Fig E: sparse vs dense tracers -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7.6, 5.0))
pv = d.pivot_table(index=['view', 'method'], columns='density', values='ratio').reset_index()
for m in ORDER:
    s = pv[pv.method == m]
    ax.scatter(
        s['sparse'],
        s['dense'],
        s=28,
        marker=MK[m],
        color=COL[m],
        label=NAME[m],
        edgecolor='white',
        linewidth=0.6,
    )
ax.plot([0, 1.5], [0, 1.5], color='#8a8a85', lw=1, ls='--')
ax.set_xlim(0, 1.5)
ax.set_ylim(0, 1.5)
ax.set_xlabel('RMSE ratio, sparse tracers (0.0006 per water pixel)')
ax.set_ylabel('RMSE ratio, dense tracers (0.0025 per water pixel)', labelpad=8)
ax.legend(frameon=False, fontsize=8)
ax.set_title(
    'Figure 5.4  Tracking error ratio with sparse versus dense tracers,\nper viewpoint and method',
    pad=12,
)
fig.tight_layout()
fig.savefig(os.path.join(R, 'figures', 'figE_sparse_vs_dense.png'))
plt.close(fig)
d.to_csv(os.path.join(R, 'three_way_v2_annotated.csv'), index=False)
# ---- Table 5.6 / Fig G: speed ladder (same simulation at time_scale 1, 0.5, 0.25) ------------------
lp = os.path.join(R, 'speed_ladder_v2.csv')
if os.path.exists(lp):
    L = pd.read_csv(lp)
    L['ratio'] = L.rmse / L.rmse_stay
    base = d[d.scene.str.match(r'v2_Low_1(_001)?_(sparse|dense)$')].copy()
    base['ts'] = 1.0
    L['ts'] = L.scene.str.extract(r'_ts0_(\d+)_')[0].map({'5': 0.5, '25': 0.25})
    A = pd.concat([base, L])
    A['camera'] = A.scene.str.extract(r'(v2_Low_1(?:_001)?)')[0]
    A['density'] = A.scene.str.extract(r'_(sparse|dense)$')[0]
    A['gt_speed'] = A.scene.map(
        A[A.method == 'PIPs++'].set_index('scene').truth_med
    )  # same definition as figA/T5.1 (PIPs++ grid truth)
    A = A[A.method != 'PIPs++_fseed']
    A['camera'] = A.camera.str.replace('v2_', '').str.replace('_', ' ')
    A['playback'] = A.ts
    t6 = A.pivot_table(
        index=['camera', 'density', 'playback'], columns='method', values=['ratio', 'frac_cos08']
    ).round(2)
    t6.columns = [
        '%s — %s'
        % ({'ratio': 'RMSE ratio', 'frac_cos08': 'direction agreement'}[a], NAMES.get(b, b))
        for a, b in t6.columns
    ]
    t6.insert(
        0,
        'GT speed (px/frame)',
        A.groupby(['camera', 'density', 'playback']).gt_speed.median().round(1),
    )
    t6.to_csv(os.path.join(R, 'tables', 'T5_6_speed_ladder.csv'))
    with open(os.path.join(R, 'tables', 'TABLES.md'), 'a') as f:
        f.write(
            '## Table 5.6  Speed ladder: ground-truth speed, RMSE ratio and direction agreement per camera, density and playback speed\n\n%s\n\n'
            % pretty(t6).to_markdown(index=False)
        )
    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    for m in ORDER:
        s_ = (
            A[A.method == m]
            .groupby('scene')
            .agg(gt=('gt_speed', 'median'), r=('ratio', 'median'))
            .dropna()
        )
        ax.scatter(
            s_['gt'].values,
            s_['r'].values,
            s=30,
            marker=MK[m],
            color=COL[m],
            label=NAME[m],
            edgecolor='white',
            linewidth=0.6,
        )
    ax.axhline(1.0, color='#8a8a85', lw=1, ls='--')
    ax.axhline(0.8, color='#8a8a85', lw=0.8, ls=':')
    ax.text(
        84,
        0.815,
        'break-point threshold (0.8)',
        fontsize=7.5,
        color='#52514e',
        ha='right',
        va='bottom',
    )
    ax.set_xlabel('Ground-truth surface speed (px/frame)')
    ax.set_ylabel('RMSE ratio (tracked / stay-still)')
    ax.set_ylim(0, 1.5)
    ax.legend(frameon=False, fontsize=8)
    ax.set_title(
        'Figure 5.7  Tracking error ratio along the speed ladder (two cameras, playback 1, 0.5 and 0.25)'
    )
    fig.tight_layout()
    fig.savefig(os.path.join(R, 'figures', 'figG_speed_ladder.png'))
    plt.close(fig)
print(t5.to_string())
print('\nwrote', os.listdir(os.path.join(R, 'figures')))
