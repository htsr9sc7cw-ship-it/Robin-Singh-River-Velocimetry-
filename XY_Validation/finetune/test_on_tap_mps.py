"""test_on_tap_mps.py

Thesis section: 3.5, 5.8
Inputs: TAP-Vid-DAVIS pickle, checkpoint
Outputs: delta_avg, survival and median error per checkpoint

test_on_tap_mps.py — the PIPs++ repository's TAP-Vid-DAVIS test (test_on_tap.py) with a device and checkpoint argument;
the tracking loop and the metric code are the repo's, verbatim except for .cuda() -> .to(device) and the removal of the
tensorboard image summaries. Protocol as in the README: S = 128-frame windows with the query-frame features carried
(feat_init), iters 16, image_size 512 x 896, points visible in frame 0 tracked to the end; metrics d_1..d_16, d_avg,
survival (16 px on the 256-scale), median_l2. README reference for model-000200000.pth: d_avg 70.6, survival 89.3, median_l2 6.9.
    PYTORCH_ENABLE_MPS_FALLBACK=1 python test_on_tap_mps.py --ckpt <dir or .pth> --device mps|cpu --out results/tapvid_davis_<tag>.csv [--S 128] [--max-videos 30]
"""

import os, sys, time, argparse, csv, numpy as np, torch, torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
ORIG = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ORIG)
from nets.pips2 import Pips
import utils.basic
from datasets.tapviddataset_fullseq import TapVidDavis


def test_on_fullseq(model, d, device, iters=16, S_max=128, image_size=(512, 896)):
    metrics = {}
    rgbs = d['rgbs'].to(device).float()
    trajs_g = d['trajs'].to(device).float()
    valids = d['valids'].to(device).float()
    B, S, C, H, W = rgbs.shape
    B, S, N, D = trajs_g.shape
    assert D == 2 and B == 1
    rgbs_ = rgbs.reshape(B * S, C, H, W)
    H_, W_ = image_size
    sy = H_ / H
    sx = W_ / W
    rgbs_ = F.interpolate(rgbs_, (H_, W_), mode='bilinear')
    rgbs = rgbs_.reshape(B, S, 3, H_, W_)
    trajs_g[:, :, :, 0] *= sx
    trajs_g[:, :, :, 1] *= sy
    H, W = H_, W_
    trajs_e = trajs_g[:, 0].repeat(1, S, 1, 1)
    cur_frame = 0
    done = False
    feat_init = None
    while not done:
        end_frame = cur_frame + S_max
        if end_frame > S:
            diff = end_frame - S
            end_frame = end_frame - diff
            cur_frame = max(cur_frame - diff, 0)
        traj_seq = trajs_e[:, cur_frame:end_frame]
        rgb_seq = rgbs[:, cur_frame:end_frame]
        S_local = rgb_seq.shape[1]
        if feat_init is not None:
            feat_init = [fi[:, :S_local] for fi in feat_init]
        preds, preds_anim, feat_init, _ = model(traj_seq, rgb_seq, iters=iters, feat_init=feat_init)
        trajs_e[:, cur_frame:end_frame] = preds[-1][:, :S_local]
        trajs_e[:, end_frame:] = trajs_e[:, end_frame - 1 : end_frame]
        if end_frame >= S:
            done = True
        else:
            cur_frame = cur_frame + S_max - 1
    d_sum = 0.0
    thrs = [1, 2, 4, 8, 16]
    sc_pt = torch.tensor([W / 256.0, H / 256.0], device=device).view(1, 1, 2)
    for thr in thrs:
        d_ = (torch.norm(trajs_e[:, 1:] / sc_pt - trajs_g[:, 1:] / sc_pt, dim=-1) < thr).float()
        d_ = utils.basic.reduce_masked_mean(d_, valids[:, 1:]).item() * 100.0
        d_sum += d_
        metrics['d_%d' % thr] = d_
    metrics['d_avg'] = d_sum / len(thrs)
    dists = torch.norm(trajs_e / sc_pt - trajs_g / sc_pt, dim=-1)
    dist_ok = 1 - (dists > 16).float() * valids
    metrics['survival'] = torch.mean(torch.cumprod(dist_ok, dim=1)).item() * 100.0
    dists_ = dists.permute(0, 2, 1).reshape(B * N, S)
    valids_ = valids.permute(0, 2, 1).reshape(B * N, S)
    metrics['median_l2'] = (
        utils.basic.reduce_masked_median(dists_, valids_, keep_batch=True).mean().item()
    )
    metrics['n_points'] = N
    metrics['n_frames'] = S
    return metrics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--device', default='mps')
    ap.add_argument('--out', required=True)
    ap.add_argument('--S', type=int, default=128)
    ap.add_argument('--iters', type=int, default=16)
    ap.add_argument('--H', type=int, default=512)
    ap.add_argument('--W', type=int, default=896)
    ap.add_argument('--max-videos', type=int, default=30)
    ap.add_argument('--data', default=os.path.join(HERE, 'tapvid_davis', 'tapvid_davis'))
    a = ap.parse_args()
    dev = a.device if (a.device == 'cpu' or torch.backends.mps.is_available()) else 'cpu'
    ck = (
        a.ckpt
        if a.ckpt.endswith('.pth')
        else next(os.path.join(a.ckpt, f) for f in sorted(os.listdir(a.ckpt)) if f.endswith('.pth'))
    )
    model = Pips(stride=8).to(dev)
    model.load_state_dict(
        torch.load(ck, map_location='cpu', weights_only=False)['model_state_dict'], strict=False
    )
    model.eval()
    ds = TapVidDavis(a.data)
    rows = []
    t0 = time.time()
    with torch.no_grad():
        for i in range(min(a.max_videos, len(ds))):
            s = ds[i]
            d = {k: v.unsqueeze(0) for k, v in s.items()}
            m = test_on_fullseq(model, d, dev, iters=a.iters, S_max=a.S, image_size=(a.H, a.W))
            m['video'] = i
            rows.append(m)
            print(
                'video %2d  frames %3d  points %3d  d_avg %.1f  survival %.1f  median_l2 %.1f  (%.0f s)'
                % (
                    i,
                    m['n_frames'],
                    m['n_points'],
                    m['d_avg'],
                    m['survival'],
                    m['median_l2'],
                    time.time() - t0,
                ),
                flush=True,
            )
            if dev == 'mps':
                torch.mps.empty_cache()
    keys = [
        'video',
        'n_frames',
        'n_points',
        'd_1',
        'd_2',
        'd_4',
        'd_8',
        'd_16',
        'd_avg',
        'survival',
        'median_l2',
    ]
    with open(a.out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        [w.writerow({k: r[k] for k in keys}) for r in rows]
    print(
        'MEAN over %d videos: d_avg %.1f  survival %.1f  median_l2 %.1f  | ckpt %s  S %d  size %dx%d  device %s'
        % (
            len(rows),
            np.mean([r['d_avg'] for r in rows]),
            np.mean([r['survival'] for r in rows]),
            np.mean([r['median_l2'] for r in rows]),
            ck,
            a.S,
            a.H,
            a.W,
            dev,
        ),
        flush=True,
    )


if __name__ == '__main__':
    main()
