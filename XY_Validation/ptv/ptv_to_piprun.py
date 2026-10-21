"""Convert a FlowVelo run into the PIP_Run_* folder layout so that the SAME evaluator
(PIP_Evaluation_gt.py) scores PTV and PIPs++ through identical code (Part B, primary path).

    /opt/anaconda3/bin/python ptv_to_piprun.py --run ../out/ptv/<scene>/tuned_lk --project <project root>

The evaluator's contract (import_from_pip): frames/Out_Format.txt = [a blocks, b frames per
block, c particles, 2, h, w]; frames/B<i>/<frame>.txt with c rows "x,y" per frame; a block is a
fresh set of c particles followed for b consecutive frames; blocks tile the sequence.

FlowVelo detects a new batch every FD_everyIthFrame frames and tracks it FT_forNthNberFrames
frames, so with FD == FT its batches tile the sequence exactly like PIPs++ blocks.  Particle
count varies per batch; the evaluator needs a constant c, so every batch is subsampled at
random (fixed seed) to the smallest batch size.  Features that drop out before the end of a
block are frozen at their last position (as PIPs++ does for occluded points) and flagged in
frames/ptv_dropout_mask.npy so they can be excluded downstream.  Positions are corrected by
+1 px in x and y for defect F3 (her metric round trip).  Nothing else is changed.
"""
import os, glob, argparse, datetime
import numpy as np, pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument('--run', required=True)
ap.add_argument('--project', required=True, help='folder with Outputs/ where PIP_Run_* is written')
ap.add_argument('--seed', type=int, default=0)
ap.add_argument('--block-len', type=int, default=0, help='[REINIT-1] frames per block (default 0 = FD, the original behaviour). With a fixed '
                'length, every batch born inside a block joins it as extra particles, masked (dropout mask False) up to and including '
                'its birth frame, so FD < block length (fresh features every 1-2 frames) is scorable in 48-frame blocks like PIPs++.')
ap.add_argument('--max-c', type=int, default=3000, help='[REINIT-1] cap on particles per block (random subsample, fixed seed)')
a = ap.parse_args()

scene = os.path.basename(os.path.dirname(os.path.abspath(a.run)))
trk = glob.glob(os.path.join(a.run, 'Tracking_FT_nbrFrames_*_FD_nbrFrames_*.txt'))[0]
FT = int(os.path.basename(trk).split('nbrFrames_')[1].split('_')[0])
FD = int(os.path.basename(trk).split('nbrFrames_')[2].split('.')[0])
assert FD <= FT, 'batches must start at least every FT frames (got FT=%d FD=%d)' % (FT, FD)
d = pd.read_csv(trk, sep='\t')
d['frame'] = d['frame'].astype(str).str.replace('.png', '', regex=False).astype(int)
d['x'] += 1.0; d['y'] += 1.0                                   # F3
first = d.groupby('id').frame.min()
births = sorted(first.unique())
assert all(b1 - b0 == FD for b0, b1 in zip(births[:-1], births[1:])), 'batches not contiguous every FD frames'
if a.block_len <= 0:
    b = FD                                                     # her batches START every FD frames (span FT+1); using b = FD makes the blocks disjoint and contiguous like PIPs++ blocks (audit D5 #2)
    blocks = births
    per_block = {f0: first[first == f0].index.values for f0 in blocks}
else:                                                          # [REINIT-1] fixed block length; batches born inside a block are its particles
    b = a.block_len
    f_last = int(d.frame.max())
    blocks = [f for f in range(births[0], f_last - b + 2, b)]
    per_block = {f0: first[(first >= f0) & (first < f0 + b)].index.values for f0 in blocks}
c = min(len(v) for v in per_block.values())
c = min(c, a.max_c)
rng = np.random.default_rng(a.seed)
tag = 'PIP_Run_%s_48_%d_%s_p%d' % (scene, c, datetime.datetime.now().strftime('%d_%m_%Y_%H_%M_%S'), os.getpid())   # unique under parallel scoring
out = os.path.join(a.project, 'Outputs', tag, 'frames')
os.makedirs(out, exist_ok=True)
mask = np.ones((len(blocks) * b, c), bool); interp = np.zeros((len(blocks) * b, c), bool)
for bi, f0 in enumerate(blocks):
    ids = rng.choice(per_block[f0], c, replace=False)
    os.makedirs(os.path.join(out, 'B%d' % bi), exist_ok=True)
    sub = d[d.id.isin(ids)]
    # [FIXLOG C7] her TrackEveryNthFrame > 1 leaves frames out of the table inside a tracked pair; they are
    # linearly interpolated (a tracked pair is one straight sub-step) so that every scored step spans ONE frame.
    # Frames after the last observation stay frozen and masked (dropout), as before.
    pos = {i: {} for i in ids}
    for i, g in sub.groupby('id'):
        g = g.sort_values('frame'); fs = g.frame.values; xs = g.x.values; ys = g.y.values
        for fr in range(fs.min(), fs.max() + 1):
            pos[i][fr] = (float(np.interp(fr, fs, xs)), float(np.interp(fr, fs, ys)), fr in set(fs))
    last = {i: None for i in ids}
    birth = {i: min(pos[i]) for i in ids}
    for k in range(b):
        fr = f0 + k
        xy = np.zeros((c, 2))
        for j, i in enumerate(ids):
            if fr <= birth[i] and birth[i] > f0:                # [REINIT-1] born inside the block: frozen at its birth position and
                last[i] = pos[i][birth[i]][:2]                  # masked up to AND including the birth frame (the step into it is not real)
                mask[bi * b + k, j] = False
            elif fr in pos[i]:
                last[i] = pos[i][fr][:2]
                if not pos[i][fr][2]: interp[bi * b + k, j] = True
            else:
                mask[bi * b + k, j] = False
            xy[j] = last[i] if last[i] is not None else (np.nan, np.nan)
        np.savetxt(os.path.join(out, 'B%d' % bi, 'trajs_tensor_B%d_F%d.txt' % (bi, k)), xy, fmt='%.4f', delimiter=',')   # evaluator's ex_num sorts by the 2nd number
# [FIXLOG C3] frame size read from the scene's own PNGs (IHDR), not hard-coded 512x512 (Overview is 1024x512)
png = sorted(glob.glob(os.path.join(a.project, 'Vectors_and_Images', scene, 'images', '*.png')))[0]
with open(png, 'rb') as fh:
    hdr = fh.read(24)
W, H = int.from_bytes(hdr[16:20], 'big'), int.from_bytes(hdr[20:24], 'big')
np.savetxt(os.path.join(out, 'Out_Format.txt'), np.array([[len(blocks), b, c, 2, H, W]]), fmt='%d')
open(os.path.join(out, 'SOURCE_RUN.txt'), 'w').write(os.path.abspath(a.run) + '\n')
np.save(os.path.join(out, 'ptv_dropout_mask.npy'), mask); np.save(os.path.join(out, 'ptv_interpolated_mask.npy'), interp)
print('PTV->PIP_Run', tag, 'blocks', len(blocks), 'frames/block', b, 'FD', FD, 'FT', FT, 'particles', c, 'size %dx%d' % (W, H), 'alive fraction %.3f' % mask.mean(), 'interpolated fraction %.3f' % interp.mean())
