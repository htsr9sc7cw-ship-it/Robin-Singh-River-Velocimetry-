"""Figure 5.6  Speed ladder: Error ratio as the same simulation is replayed at 1/4, 1/2 and full speed.
Output: results/figures/figG_speed_ladder.png      Run:  python fig_5_06_speed_ladder.py"""
from fig_common import *

d, _ = load_main()
L = pd.read_csv(os.path.join(RES, 'speed_ladder_v2.csv'))
L['ratio'] = L.rmse / L.rmse_stay
base = d[d.scene.str.match(r'v2_Low_1(_001)?_(sparse|dense)$')].copy()
A = pd.concat([base, L])
A['gt_speed'] = A.scene.map(A[A.method == 'PIPs++'].set_index('scene').truth_med)
A = A[A.method != 'PIPs++_fseed']
fig, ax = plt.subplots(figsize=(6.6, 3.9))
for m in ORDER:
    s = A[A.method == m].groupby('scene').agg(gt=('gt_speed', 'median'), r=('ratio', 'median')).dropna()
    ax.scatter(s['gt'].values, s['r'].values, s=SZ[m], zorder=ZO[m], alpha=0.9, marker=MK[m], color=COL[m], label=NAME[m], edgecolor='white', linewidth=0.5)
ax.axhline(1.0, color=tud.GREY, lw=1, ls='--'); ax.axhline(0.8, color=tud.GREY, lw=0.8, ls=':')
ax.text(70, 0.815, 'skill limit (0.8)', fontsize=7.5, color=tud.GREY, ha='right', va='bottom')
ax.set_xlabel('True surface speed (px/frame)'); ax.set_ylabel('Error ratio (1 = no gain)')
ax.set_ylim(0, 1.5); ax.legend()
save(fig, 'figG_speed_ladder.png')
