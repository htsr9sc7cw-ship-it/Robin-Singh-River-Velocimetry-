"""make_results_reinit.py

Thesis section: 5
Inputs: result CSV files
Outputs: result tables and figures

Tables and figures for REINIT-1 (re-initialised PIPs++, matched-cadence FlowVelo) and Study B (fine-tuned).
    /opt/anaconda3/bin/python make_results_reinit.py
Reads results/pips_reinit_pilot.csv, results/three_way_v3_reinit.csv, results/finetune_v3.csv (whichever exist);
writes results/tables/T5_7..T5_9*.csv + TABLES_reinit.md and results/figures/figH_*.png, figI_*.png. Same style as make_results.py.
"""

import os, re, numpy as np, pandas as pd, matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, 'results')
os.makedirs(os.path.join(R, 'tables'), exist_ok=True)
os.makedirs(os.path.join(R, 'figures'), exist_ok=True)
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


def name(m):
    base = {
        'PIPs++': 'PIPs++ untrained, seeded once per 48 frames, 256 px',
        'PIPs++_fseed': 'PIPs++ untrained, feature seeds, 256 px',
        'PTV_tuned_ncc': 'FlowVelo NCC, features every 0.75·FT frames',
        'PTV_tuned_lk': 'FlowVelo LK, features every 0.75·FT frames',
        'PTV_gui_defaults': 'FlowVelo LK, GUI defaults',
    }
    if m in base:
        return base[m]
    g = re.match(r'PIPs\+\+_(?:ft(\d+)_)?r(\d+)_(\d+)$', m)
    if g:
        ft, k, img = g.groups()
        who = 'PIPs++ fine-tuned %s it.' % ft if ft else 'PIPs++ untrained'
        return '%s, %s, %s px' % (
            who,
            (
                'seeded once per 48 frames'
                if k == '48'
                else 're-initialised every %s frame%s' % (k, '' if k == '1' else 's')
            ),
            img,
        )
    g = re.match(r'PTV_(tuned_ncc|tuned_lk)_fd(\d+)$', m)
    if g:
        return 'FlowVelo %s, features every %s frame%s' % (
            g.group(1).split('_')[1].upper(),
            g.group(2),
            '' if g.group(2) == '1' else 's',
        )
    return m


def scene_name(s):
    return (
        s.replace('v2_', '')
        .replace('_dense', ' · dense')
        .replace('_sparse', ' · sparse')
        .replace('_', ' ')
    )


def load(f):
    p = os.path.join(R, f)
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p)
    d['ratio'] = d.rmse / d.rmse_stay
    d['method_name'] = d.method.map(name)
    d['variant'] = d.scene.map(scene_name)
    return d


COL = {
    'PIPs++': '#2a78d6',
    'PTV_tuned_ncc': '#eb6834',
    'PTV_tuned_lk': '#c9a227',
    'PTV_gui_defaults': '#9a9a95',
}


def col(m):
    if m.startswith('PIPs++'):
        return '#2a78d6' if '_ft' not in m else '#6a3d9a'
    return COL.get(re.sub(r'_fd\d+$', '', m), '#555')


md = [
    '# Result tables — re-initialised PIPs++ and matched-cadence FlowVelo (REINIT-1) and fine-tuned PIPs++ (Study B)\n',
    'ratio = RMSE of the tracked displacement / RMSE of the stay-still baseline (1 = no skill, 0 = perfect); direction agreement = fraction of sub-steps within 37° of the true direction; all in native px/frame.\n',
]

pil = load('pips_reinit_pilot.csv')
if pil is not None:
    order = sorted(pil.method.unique(), key=lambda m: (not m.startswith('PIPs++'), m))
    t = pil.pivot(index='method', columns='variant', values='ratio').loc[order]
    t.index = [name(m) for m in t.index]
    t.to_csv(os.path.join(R, 'tables', 'T5_7_reinit_pilot_ratio.csv'))
    md.append(
        '## Table 5.7  Pilot on four variants: RMSE ratio per method (re-initialisation interval × working resolution; FlowVelo at the same feature cadence)\n\n'
        + t.round(2).to_markdown()
        + '\n'
    )
    t2 = pil.pivot(index='method', columns='variant', values='frac_cos08').loc[order]
    t2.index = [name(m) for m in t2.index]
    t2.to_csv(os.path.join(R, 'tables', 'T5_8_reinit_pilot_direction.csv'))
    md.append(
        '## Table 5.8  Pilot on four variants: direction agreement per method\n\n'
        + t2.round(2).to_markdown()
        + '\n'
    )
    fig, ax = plt.subplots(figsize=(10, 4.6))
    vs = sorted(pil.variant.unique())
    x = np.arange(len(vs))
    w = 0.8 / len(order)
    for i, m in enumerate(order):
        y = [pil[(pil.method == m) & (pil.variant == v)].ratio.mean() for v in vs]
        ax.bar(
            x + (i - len(order) / 2 + 0.5) * w,
            y,
            w,
            color=col(m),
            alpha=0.35 + 0.65 * (i % 2 == 0) if m.startswith('PIPs++') else 0.9,
            edgecolor='white',
            linewidth=0.5,
            label=name(m),
        )
    ax.axhline(1, color='#8a8a85', lw=0.8, ls='--')
    ax.set_xticks(x)
    ax.set_xticklabels(vs)
    ax.set_ylabel('RMSE ratio (tracked / stay-still)')
    ax.set_title(
        'Figure 5.9  Pilot: tracking error ratio per method on four variants (lower is better; 1 = no skill)'
    )
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(R, 'figures', 'figH_reinit_pilot.png'))
    plt.close(fig)

full = load('three_way_v3_k2.csv')
if full is not None:
    full['density'] = np.where(full.scene.str.endswith('dense'), 'dense', 'sparse')
    nv = full.groupby('method').scene.count()
    full = full[
        full.method.isin(nv[nv == nv.max()].index)
    ]  # methods run on all 28 (pilot-only settings: Table 5.7)
    g = (
        full.groupby(['method', 'density'])[['ratio', 'frac_cos08', 'speed_ratio', 'n']]
        .median()
        .unstack('density')
        .round(3)
    )
    g.columns = [
        '%s, %s'
        % ({'ratio': 'ratio', 'frac_cos08': 'direction', 'speed_ratio': 'speed', 'n': 'n'}[a], b)
        for a, b in g.columns
    ]
    g.index = [name(m) for m in g.index]
    g.to_csv(os.path.join(R, 'tables', 'T5_9_reinit_full_medians.csv'))
    md.append(
        '## Table 5.9  All 28 muddy variants, both trackers re-tracked every 2 frames: median RMSE ratio, direction agreement and speed ratio per method and tracer density\n\n'
        + g.to_markdown()
        + '\n'
    )
    better = (
        full.groupby('method')
        .ratio.apply(lambda r: int((r < 0.8).sum()))
        .rename('variants with ratio < 0.8')
    )
    better.index = [name(m) for m in better.index]
    md.append(
        '## Table 5.10  Variants (of 28) on which each method beats the break-point rule (ratio < 0.8)\n\n'
        + better.to_frame().to_markdown()
        + '\n'
    )
    tw = full.pivot(index='variant', columns='method', values='ratio')
    tw.columns = [name(m) for m in tw.columns]
    tw.to_csv(os.path.join(R, 'tables', 'T5_11_reinit_full_per_variant.csv'))
    md.append(
        '## Table 5.11  RMSE ratio per variant and method, all 28 muddy variants\n\n'
        + tw.round(2).to_markdown()
        + '\n'
    )
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for m in sorted(full.method.unique(), key=lambda m: (not m.startswith('PIPs++'), m)):
        s = full[full.method == m]
        ax.scatter(
            s.truth_med,
            s.ratio,
            s=22,
            color=col(m),
            marker='o' if s.method.str.contains('_r').any() or m.startswith('PTV') else 'x',
            alpha=0.85,
            label=name(m),
            edgecolor='white',
            linewidth=0.4,
        )
    ax.axhline(1, color='#8a8a85', lw=0.8, ls='--')
    ax.axhline(0.8, color='#c9a227', lw=0.8, ls=':')
    ax.set_xlabel('median true displacement (px/frame)')
    ax.set_ylabel('RMSE ratio (tracked / stay-still)')
    ax.set_title(
        'Figure 5.10  Tracking error ratio against flow speed, all 28 muddy variants, both trackers re-tracked every 2 frames'
    )
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(R, 'figures', 'figI_reinit_full_vs_speed.png'))
    plt.close(fig)

ft = load('finetune_v3.csv')
if ft is not None:
    ft['held_out'] = ~ft.scene.eq('v2_Path2_dense')
    keep = ft[
        ft.held_out
        & ft.method.isin(
            [
                'PIPs++',
                'PIPs++_r2_256',
                'PIPs++_ft3000_r2_256',
                'PTV_tuned_ncc_fd2',
                'PTV_tuned_lk_fd2',
            ]
        )
    ]
    t = keep.pivot(index='method', columns='variant', values='ratio_h15').loc[
        ['PIPs++', 'PIPs++_r2_256', 'PIPs++_ft3000_r2_256', 'PTV_tuned_ncc_fd2', 'PTV_tuned_lk_fd2']
    ]
    t.index = [name(m) for m in t.index]
    t.to_csv(os.path.join(R, 'tables', 'T5_12_finetune_heldout.csv'))
    md.append(
        '## Table 5.12  Held-out viewpoints: RMSE ratio over a 15-frame horizon (ratio_h15, Sect. 4.3.2) of untrained and fine-tuned PIPs++ (re-tracked every 2 frames) and FlowVelo (features every 2 frames)\n\n'
        + t.round(2).to_markdown()
        + '\n'
    )
    g2 = (
        keep.groupby('method')
        .agg(
            **{
                'ratio (all steps)': ('ratio', 'median'),
                'ratio (15-frame horizon)': ('ratio_h15', 'median'),
                'direction': ('frac_cos08', 'median'),
                'within 8 px': ('d8', 'median'),
                'tracks following': ('frac_tracks_follow', 'median'),
                'speed ratio': ('speed_ratio', 'median'),
                'n (all steps)': ('n', 'median'),
                'n (15-frame)': ('n_h15', 'median'),
                'variants < 0.8 (h15)': ('ratio_h15', lambda r: int((r < 0.8).sum())),
            }
        )
        .loc[
            [
                'PIPs++',
                'PIPs++_r2_256',
                'PIPs++_ft3000_r2_256',
                'PTV_tuned_ncc_fd2',
                'PTV_tuned_lk_fd2',
            ]
        ]
        .round(2)
    )
    g2.index = [name(m) for m in g2.index]
    g2.to_csv(os.path.join(R, 'tables', 'T5_12b_finetune_heldout_medians.csv'))
    md.append(
        '## Table 5.12b  Held-out viewpoints: medians over the 10 variants\n\n'
        + g2.to_markdown()
        + '\n'
    )
    lc = ft[
        ft.scene.isin(['v2_Path4_dense', 'v2_Low_1_dense'])
        & ft.method.str.match(r'PIPs\+\+_(ft\d+_)?r2_256$')
    ].pivot(index='method', columns='variant', values='ratio_h15')
    lc.index = [name(m) for m in lc.index]
    md.append(
        '## Table 5.12c  Learning curve: ratio (15-frame horizon) after 0, 1 000, 2 000 and 3 000 fine-tuning steps\n\n'
        + lc.round(2).to_markdown()
        + '\n'
    )
    c = ft[
        ~ft.held_out
        & ft.method.isin(['PIPs++', 'PIPs++_r2_256', 'PIPs++_ft3000_r2_256', 'PTV_tuned_ncc_fd2'])
    ][['method_name', 'ratio', 'ratio_h15', 'frac_cos08']].set_index('method_name')
    md.append(
        '## Table 5.13  Leakage control: training viewpoint Path2 dense (not part of the held-out table)\n\n'
        + c.round(3).to_markdown()
        + '\n'
    )
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    ms = sorted(keep.method.unique(), key=lambda m: (not m.startswith('PIPs++'), m))
    vs = sorted(keep.variant.unique())
    x = np.arange(len(vs))
    w = 0.8 / len(ms)
    for i, m in enumerate(ms):
        ax.bar(
            x + (i - len(ms) / 2 + 0.5) * w,
            [keep[(keep.method == m) & (keep.variant == v)].ratio_h15.mean() for v in vs],
            w,
            color=col(m),
            edgecolor='white',
            linewidth=0.5,
            label=name(m),
        )
    ax.axhline(1, color='#8a8a85', lw=0.8, ls='--')
    ax.set_xticks(x)
    ax.set_xticklabels(vs, rotation=30, ha='right')
    ax.set_ylabel('RMSE ratio, 15-frame horizon')
    ax.set_title(
        'Figure 5.11  Held-out viewpoints: error ratio over a 15-frame horizon, untrained vs fine-tuned PIPs++ and FlowVelo'
    )
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.3), ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(R, 'figures', 'figJ_finetune_heldout.png'))
    plt.close(fig)
open(os.path.join(R, 'tables', 'TABLES_reinit.md'), 'w').write('\n'.join(md))
print('wrote', [f for f, d in (('pilot', pil), ('full', full), ('finetune', ft)) if d is not None])
