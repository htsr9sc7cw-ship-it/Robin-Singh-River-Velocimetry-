"""Figure 5.14  Training error of all runs: position error per training clip, smoothed, logarithmic axis.
Reads the training logs finetune/ckpt*/train_log.csv (columns: step, loss, ate_px, ...).
Output: results/figures/figR1_training_curves.png      Run:  python fig_5_14_training_curves.py"""
from fig_common import *

FT = os.path.join(os.path.dirname(PROJECT), 'finetune')
RUNS = [('ckpt', 'S1 short clips', 'S1'), ('ckpt_S2', 'S2 + data, augmentation', 'S2'), ('ckpt_S3', 'S3 long clips', 'S3'),
        ('ckpt_S4', 'S4 rehearsal', 'S4'), ('ckpt_S5', 'S5 from scratch', 'S5'), ('ckpt_S6', 'S6 final model', 'S6')]
fig, ax = plt.subplots(figsize=(6.8, 3.7))
for folder, label, key in RUNS:
    d = pd.read_csv(os.path.join(FT, folder, 'train_log.csv'), header=None, comment='#')
    d = d[pd.to_numeric(d[0], errors='coerce').notna()]
    d = d[~d[3].astype(str).str.startswith('pod:')]            # S4 rehearsal clips from PointOdyssey are not river clips
    step, ate = d[0].astype(float).values, d[2].astype(float)
    ax.plot(step, ate.rolling(100, min_periods=1).median(), color=tud.TRACKER[key], lw=2.0 if key == 'S6' else 1.4, ls=tud.LINE[key]['ls'], label=label)
ax.set_yscale('log'); ax.set_xlabel('training step'); ax.set_ylabel('Error per clip (px, log scale)')
ax.legend(ncol=2, loc='upper right', fontsize=7.8)
save(fig, 'figR1_training_curves.png')
