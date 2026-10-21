"""train_v3.py

Thesis section: 3.4, 5.6
Inputs: tracer trajectories and frames of the training viewpoints, checkpoint
Outputs: checkpoints and training log

train_v3.py — fine-tune PIPs++ on the Elbersdorf renders (Study B, PREREGISTRATION_finetune.md).

Compact re-implementation of the training loop of pips2 train.py (the original is left untouched): the model, its
sequence loss and the trajectory initialisation are the original ones; the data loader is ours because the labels
are already exact (rerender/out/v2/<view>/tracers_<density>/trajs.npz) and the frames must not be resized.

    /opt/anaconda3/envs/pips2/bin/python train_v3.py --max-iters 3000 --max-hours 8
Environment: FT_VIEWS (comma list, default = the pre-registered training views).
Checkpoints: ckpt/model-<iter>.pth in the layout of the reference checkpoint ({'model_state_dict': ...}).
"""

import os, sys, time, glob, argparse, json
import numpy as np, torch, glob

HERE = os.path.dirname(os.path.abspath(__file__))
XYV = os.path.dirname(HERE)
ORIG = os.path.dirname(XYV)
sys.path.insert(0, ORIG)  # nets/, utils/ of the pipeline (same code as PIP_Execution)
from nets.pips2 import Pips
import imageio.v3 as iio, cv2

TRAIN_VIEWS = [
    'Path1',
    'Path2',
    'Path3',
    'Path5',
    'Path6',
    'Path7',
    'Low_1_002',
    'Low_1_003',
    'Low_2',
]
REND = os.path.join(XYV, 'rerender', 'out', 'v2')


class TracerClips:
    """Random (sequence, start, crop) clips: rgbs S,3,H,W uint8; trajs S,N,2; visibs S,N; valids S,N.
    augs (Study C, PREREGISTRATION_strategies.md): 'scale' (isotropic 0.7-1.3, frames + trajectories), 'photometric'
    (brightness/contrast +-15 %), 'vflip', 'reverse' (temporal reversal), 'movingcrop' (crop window drifts over the clip,
    as in the PIPs++ loader). prefer_persist: sample points valid in >= 80 % of the clip when enough exist (paper: long-lived points).
    """

    def __init__(
        self, views, S=24, N=64, crop=384, seed=0, augs=(), prefer_persist=False, extra=()
    ):
        self.S, self.N, self.crop, self.augs, self.prefer_persist = (
            S,
            N,
            crop,
            set(augs),
            prefer_persist,
        )
        self.rng = np.random.default_rng(seed)
        self.seqs = []
        for v in list(views) + list(extra):
            for dens in ('dense', 'sparse'):
                d = os.path.join(REND, 'v2_' + v)
                a = np.load(os.path.join(d, 'tracers_' + dens, 'trajs.npz'))
                frames = sorted(glob.glob(os.path.join(d, 'images_tracers_' + dens, '*.png')))
                assert len(frames) == a['trajs_2d'].shape[0], (
                    v,
                    dens,
                    len(frames),
                    a['trajs_2d'].shape,
                )
                self.seqs.append(
                    dict(
                        name='v2_%s_%s' % (v, dens),
                        frames=frames,
                        trajs=a['trajs_2d'].astype(np.float32),
                        valids=a['valids'].astype(bool),
                        visibs=a['visibs'].astype(bool),
                    )
                )
        print('training sequences:', [s['name'] for s in self.seqs], flush=True)

    def sample(self):
        for _ in range(50):
            s = self.seqs[self.rng.integers(len(self.seqs))]
            T = len(s['frames'])
            t0 = int(self.rng.integers(0, T - self.S + 1))
            idx = list(range(t0, t0 + self.S))
            if 'reverse' in self.augs and self.rng.random() < 0.5:
                idx = idx[::-1]
            rgbs = np.stack([iio.imread(s['frames'][i])[:, :, :3] for i in idx])
            H, W = rgbs.shape[1:3]
            tr = s['trajs'][idx].copy()
            va = s['valids'][idx].copy()
            vi = s['visibs'][idx].copy()
            sc = 1.0
            if 'scale' in self.augs:
                sc = float(self.rng.uniform(0.7, 1.3))
                Hn, Wn = max(self.crop + 8, int(round(H * sc))), max(
                    self.crop + 8, int(round(W * sc))
                )
                rgbs = np.stack(
                    [cv2.resize(f, (Wn, Hn), interpolation=cv2.INTER_LINEAR) for f in rgbs]
                )
                tr[..., 0] *= Wn / W
                tr[..., 1] *= Hn / H
                H, W = Hn, Wn
            y0 = int(self.rng.integers(0, H - self.crop + 1))
            x0 = int(self.rng.integers(0, W - self.crop + 1))
            if 'movingcrop' in self.augs:  # crop window drifts a little every frame (PIPs++ loader)
                ox = oy = 0
                xs = []
                ys = []
                for k in range(self.S):
                    if k > 0:
                        ox = int(0.8 * ox + self.rng.integers(-6, 7) * 0.2 * 6)
                        oy = int(0.8 * oy + self.rng.integers(-6, 7) * 0.2 * 6)
                    xs.append(int(np.clip(x0 + ox, 0, W - self.crop)))
                    ys.append(int(np.clip(y0 + oy, 0, H - self.crop)))
            else:
                xs = [x0] * self.S
                ys = [y0] * self.S
            out = np.stack(
                [
                    rgbs[k, ys[k] : ys[k] + self.crop, xs[k] : xs[k] + self.crop]
                    for k in range(self.S)
                ]
            )
            tr[..., 0] -= np.array(xs)[:, None]
            tr[..., 1] -= np.array(ys)[:, None]
            inside = (
                (tr[..., 0] >= 1)
                & (tr[..., 0] <= self.crop - 2)
                & (tr[..., 1] >= 1)
                & (tr[..., 1] <= self.crop - 2)
            )
            vi &= inside & va
            ok = vi[0] & vi[1] & (vi.sum(0) >= max(int(np.sqrt(self.S)), 2))
            if self.prefer_persist:
                long_ = ok & (vi.sum(0) >= 0.8 * self.S)
                if long_.sum() >= self.N:
                    ok = long_
            idx_p = np.where(ok)[0]
            if len(idx_p) < self.N:
                continue
            idx_p = self.rng.choice(idx_p, self.N, replace=False)
            tr, va, vi = tr[:, idx_p], va[:, idx_p], vi[:, idx_p]
            tr[~va] = 0
            rgbs = out
            if self.rng.random() < 0.5:
                rgbs = rgbs[:, :, ::-1].copy()
                tr[..., 0] = self.crop - 1 - tr[..., 0]
            if 'vflip' in self.augs and self.rng.random() < 0.5:
                rgbs = rgbs[:, ::-1].copy()
                tr[..., 1] = self.crop - 1 - tr[..., 1]
            if 'photometric' in self.augs:
                a = float(self.rng.uniform(0.85, 1.15))
                b = float(self.rng.uniform(-0.15, 0.15)) * 255
                rgbs = np.clip(rgbs.astype(np.float32) * a + b, 0, 255).astype(np.uint8)
            return dict(
                name=s['name'],
                t0=t0,
                scale=sc,
                rgbs=torch.from_numpy(np.ascontiguousarray(rgbs)).permute(0, 3, 1, 2).contiguous(),
                trajs=torch.from_numpy(np.ascontiguousarray(tr)),
                visibs=torch.from_numpy(vi.astype(np.float32)),
                valids=torch.from_numpy(va.astype(np.float32)),
            )
        raise RuntimeError('no clip with %d good points found' % self.N)


CROP = 256


class PodClips:
    """Rehearsal clips from the PointOdyssey sample (published layout <root>/<seq>/rgbs/rgb_%05d.jpg + anno.npz): same output
    format as TracerClips. Frames resized so the shorter side >= crop, then random crop."""

    def __init__(self, root, S, N, crop, seed=1):
        self.S, self.N, self.crop, self.rng = S, N, crop, np.random.default_rng(seed)
        self.seqs = [
            d
            for d in sorted(glob.glob(os.path.join(root, '*')))
            if os.path.isfile(os.path.join(d, 'anno.npz'))
        ]
        assert self.seqs, 'no PointOdyssey sequences under ' + root
        self.cache = {}
        print('PointOdyssey rehearsal sequences:', len(self.seqs), flush=True)

    def anno(self, d):
        if d not in self.cache:
            a = np.load(os.path.join(d, 'anno.npz'), allow_pickle=True)
            self.cache[d] = (
                a['trajs_2d'].astype(np.float32),
                a['visibs'].astype(bool),
                a['valids'].astype(bool),
            )
        return self.cache[d]

    def sample(self):
        for _ in range(50):
            d = self.seqs[self.rng.integers(len(self.seqs))]
            tr_all, vi_all, va_all = self.anno(d)
            T = tr_all.shape[0]
            frames = sorted(glob.glob(os.path.join(d, 'rgbs', 'rgb_*.jpg')))
            if len(frames) < self.S or T < self.S:
                continue
            t0 = int(self.rng.integers(0, min(T, len(frames)) - self.S + 1))
            idx = range(t0, t0 + self.S)
            rgbs = np.stack([iio.imread(frames[i])[:, :, :3] for i in idx])
            H, W = rgbs.shape[1:3]
            sc = max(self.crop / H, self.crop / W, 0.5)
            Hn, Wn = max(self.crop, int(round(H * sc))), max(self.crop, int(round(W * sc)))
            rgbs = np.stack([cv2.resize(f, (Wn, Hn)) for f in rgbs])
            tr = tr_all[t0 : t0 + self.S].copy()
            tr[..., 0] *= Wn / W
            tr[..., 1] *= Hn / H
            va = va_all[t0 : t0 + self.S].copy()
            vi = vi_all[t0 : t0 + self.S].copy()
            bad = ~np.isfinite(tr).all(-1)
            tr[bad] = 0
            va &= ~bad
            vi &= ~bad
            y0 = int(self.rng.integers(0, Hn - self.crop + 1))
            x0 = int(self.rng.integers(0, Wn - self.crop + 1))
            rgbs = rgbs[:, y0 : y0 + self.crop, x0 : x0 + self.crop]
            tr[..., 0] -= x0
            tr[..., 1] -= y0
            inside = (
                (tr[..., 0] >= 1)
                & (tr[..., 0] <= self.crop - 2)
                & (tr[..., 1] >= 1)
                & (tr[..., 1] <= self.crop - 2)
            )
            vi &= inside & va
            ok = vi[0] & vi[1] & (vi.sum(0) >= max(int(np.sqrt(self.S)), 2))
            idx_p = np.where(ok)[0]
            if len(idx_p) < self.N:
                continue
            idx_p = self.rng.choice(idx_p, self.N, replace=False)
            tr, va, vi = tr[:, idx_p], va[:, idx_p], vi[:, idx_p]
            tr[~va] = 0
            return dict(
                name='pod:' + os.path.basename(d),
                t0=t0,
                scale=sc,
                rgbs=torch.from_numpy(np.ascontiguousarray(rgbs)).permute(0, 3, 1, 2).contiguous(),
                trajs=torch.from_numpy(np.ascontiguousarray(tr)),
                visibs=torch.from_numpy(vi.astype(np.float32)),
                valids=torch.from_numpy(va.astype(np.float32)),
            )
        raise RuntimeError('no PointOdyssey clip with %d good points' % self.N)


def save_debug(d, path):
    import matplotlib

    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    r = d['rgbs'].permute(0, 2, 3, 1).numpy()
    t = d['trajs'].numpy()
    v = d['visibs'].numpy() > 0
    fig, ax = plt.subplots(1, 2, figsize=(9, 4.5))
    for a_, k in zip(ax, (0, r.shape[0] - 1)):
        a_.imshow(r[k])
        a_.scatter(t[k, v[k], 0], t[k, v[k], 1], s=8, c='#eb6834')
        a_.set_title(
            '%s  frame %d of clip (scale %.2f)' % (d['name'], k, d.get('scale', 1)), fontsize=8
        )
        a_.axis('off')
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    print('debug clip saved', path, flush=True)


def init_trajs(trajs_g, rng):
    """pips2 train.py run_model: random / ground-truth mix, zero-velocity for half, frame 0 exact."""
    B, S, N, _ = trajs_g.shape
    dev = trajs_g.device
    x = torch.rand(B, S, N, 1, device=dev) * 0
    y = x.clone()
    rnd = torch.rand(B, S, N, 2, device=dev) * torch.tensor(
        [float(CROP - 1), float(CROP - 1)], device=dev
    )
    coeff = torch.rand(B, 1, N, 1, device=dev)
    e0 = rnd * coeff + trajs_g * (1 - coeff)
    z = trajs_g[:, 0:1].repeat(1, S, 1, 1)
    m = (torch.rand(B, 1, N, 1, device=dev) > 0.5).float()
    e0 = e0 * m + z * (1 - m)
    e0[:, 0:1] = trajs_g[:, 0:1]
    return e0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--max-iters', type=int, default=3000)
    ap.add_argument('--max-hours', type=float, default=8)
    ap.add_argument('--S', type=int, default=24)
    ap.add_argument('--N', type=int, default=64)
    ap.add_argument('--crop', type=int, default=384)
    ap.add_argument('--lr', type=float, default=1e-4)
    ap.add_argument('--iters', type=int, default=6)
    ap.add_argument('--save-every', type=int, default=500)
    ap.add_argument('--init', default=os.path.join(ORIG, 'reference_model', 'model-000200000.pth'))
    ap.add_argument('--ckpt', default=os.path.join(HERE, 'ckpt'))
    ap.add_argument('--resume', action='store_true')
    ap.add_argument(
        '--augs', default='', help='comma list: scale,photometric,vflip,reverse,movingcrop'
    )
    ap.add_argument('--persist', action='store_true')
    ap.add_argument(
        '--onecycle',
        action='store_true',
        help='one-cycle lr schedule (peak = --lr) over --max-iters, as in pips2 train.py',
    )
    ap.add_argument(
        '--extra',
        default='',
        help='comma list of extra training views, e.g. Path3_clear,high_angle_clear',
    )
    ap.add_argument(
        '--mix-pod',
        default='',
        help='PointOdyssey dataset root (extracted sample tar) for rehearsal',
    )
    ap.add_argument('--mix-frac', type=float, default=0.5)
    ap.add_argument(
        '--debug-png',
        default='',
        help='save one augmented clip (frame 0 and last) with points overlaid',
    )
    a = ap.parse_args()
    global CROP
    CROP = a.crop
    dev = 'mps' if torch.backends.mps.is_available() else 'cpu'
    views = os.environ.get('FT_VIEWS', ','.join(TRAIN_VIEWS)).split(',')
    data = TracerClips(
        views,
        a.S,
        a.N,
        a.crop,
        augs=[x for x in a.augs.split(',') if x],
        prefer_persist=a.persist,
        extra=[x for x in a.extra.split(',') if x],
    )
    pod = PodClips(a.mix_pod, a.S, a.N, a.crop) if a.mix_pod else None
    model = Pips(stride=8).to(dev)
    if a.init and a.init != 'none':
        ck = torch.load(a.init, map_location='cpu', weights_only=False)
        model.load_state_dict(ck['model_state_dict'], strict=False)
        print('init from', a.init, flush=True)
    else:
        print('init: RANDOM (from scratch)', flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-6, eps=1e-8)
    sched = (
        torch.optim.lr_scheduler.OneCycleLR(
            opt,
            a.lr,
            a.max_iters + 100,
            pct_start=0.1,
            cycle_momentum=False,
            anneal_strategy='linear',
        )
        if a.onecycle
        else None
    )
    step = 0
    os.makedirs(a.ckpt, exist_ok=True)
    if a.resume:
        prev = sorted(glob.glob(os.path.join(a.ckpt, 'model-*.pth')))
        if prev:
            ck = torch.load(prev[-1], map_location='cpu', weights_only=False)
            model.load_state_dict(ck['model_state_dict'])
            opt.load_state_dict(ck['optimizer_state_dict'])
            step = ck['step']
            print('resumed from', prev[-1], 'step', step, flush=True)
    model.train()
    log = open(os.path.join(a.ckpt, 'train_log.csv'), 'a')
    t_start = time.time()
    rng = np.random.default_rng(step)
    print('config', vars(a), 'device', dev, flush=True)
    while step < a.max_iters and (time.time() - t_start) < a.max_hours * 3600:
        step += 1
        t0 = time.time()
        d = pod.sample() if (pod is not None and rng.random() < a.mix_frac) else data.sample()
        if a.debug_png and step == 1:
            save_debug(d, a.debug_png)
        rgbs = d['rgbs'].unsqueeze(0).float().to(dev)
        trajs_g = d['trajs'].unsqueeze(0).to(dev)
        vis_g = d['visibs'].unsqueeze(0).to(dev)
        valids = d['valids'].unsqueeze(0).to(dev)
        e0 = init_trajs(trajs_g, rng)
        preds, _, _, loss = model(
            e0, rgbs, iters=a.iters, trajs_g=trajs_g, vis_g=vis_g, valids=valids, is_train=True
        )
        if torch.isnan(loss):
            print('nan loss at step', step, '- stopping', flush=True)
            break
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if sched is not None:
            sched.step()
        with torch.no_grad():
            err = torch.norm(preds[-1] - trajs_g, dim=-1)
            ate = (err * valids).sum() / valids.sum().clamp(min=1)
        log.write(
            '%d,%.4f,%.3f,%s,%d,%.2f,%.3g\n'
            % (
                step,
                loss.item(),
                ate.item(),
                d['name'],
                d['t0'],
                time.time() - t0,
                opt.param_groups[0]['lr'],
            )
        )
        log.flush()
        if step % 10 == 0 or step <= 5:
            print(
                'step %d loss %.4f ate %.2f px  %s  %.2f s/it'
                % (step, loss.item(), ate.item(), d['name'], time.time() - t0),
                flush=True,
            )
        if step % a.save_every == 0 or step == a.max_iters:
            torch.save(
                dict(
                    model_state_dict=model.state_dict(),
                    optimizer_state_dict=opt.state_dict(),
                    step=step,
                ),
                os.path.join(a.ckpt, 'model-%06d.pth' % step),
            )
            print('saved', step, flush=True)
    torch.save(
        dict(model_state_dict=model.state_dict(), optimizer_state_dict=opt.state_dict(), step=step),
        os.path.join(a.ckpt, 'model-%06d.pth' % step),
    )
    print('TRAIN_DONE step', step, '%.1f h' % ((time.time() - t_start) / 3600), flush=True)


if __name__ == '__main__':
    main()
