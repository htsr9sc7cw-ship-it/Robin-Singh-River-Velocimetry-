"""tapvid_eval.py

Thesis section: see README.md
Inputs: see README.md
Outputs: see README.md

TAP-Vid / PIPs++-repo metrics for every evaluation folder (plan 18 Sep; PREREGISTRATION_strategies.md).
    /opt/anaconda3/envs/pips2/bin/python tapvid_eval.py --scenes ... --methods PIPs++ PIPs++_S2_r2_256 PTV_tuned_ncc_fd2 ... --out tapvid_v3.csv
For each block of a run: the query points are the block's first positions (PTV: each batch's birth frame, query_mode 'first'),
the ground-truth trajectory is the query point advected through the ground-truth fields (flow_core.step_forward, the same
advection as the GIFs and the known-answer control), gt_occluded = advected point off the image or off the water (|flow| < 1e-3),
pred_occluded = predicted point off the image (PIPs++ has no visibility output; PTV: dropout mask). Coordinates on the
TAP-Vid 256 x 256 evaluation scale (native / (W/256, H/256)). Also survival_16 (fraction of tracks whose error stays < 16 px
at every evaluated visible frame), survival_32, and median_l2 (median over tracks of the mean error), as in the PIPs++ repo.
Untrained/inherited and FlowVelo rows are computed the same way so that the columns are comparable.
"""

import os, sys, glob, re, argparse, csv as _csv, numpy as np, torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
os.environ.setdefault('XYV_DATA', os.path.join(HERE, 'Vectors_and_Images'))
import flow_core as fc, tapvid_metrics as tm

ap = argparse.ArgumentParser()
ap.add_argument('--scenes', nargs='+', required=True)
ap.add_argument('--methods', nargs='+', required=True)
ap.add_argument('--out', default='tapvid_v3.csv')
a = ap.parse_args()
dev = fc.pick_device('mps')


def eval_dir(scene, method):
    if method == 'PIPs++':
        ev = sorted(
            glob.glob(os.path.join(HERE, 'Outputs', 'PIP_Eval_%s_48_256_*' % scene)),
            key=os.path.getmtime,
        )
        return ev[-1] if ev else None
    if method.startswith('PIPs++_'):
        d = os.path.join(HERE, 'Outputs', 'PIP_Eval_%s_%s' % (scene, method[7:]))
        return d if os.path.isdir(d) else None
    if method.startswith('PTV_'):
        d = os.path.join(HERE, 'Outputs', 'PTV_Eval_%s_%s' % (scene, method[4:]))
        return d if os.path.isdir(d) else None


def run_of(ev):
    f = os.path.join(ev, 'SOURCE_RUN.txt')
    r = open(f).read().strip() if os.path.exists(f) else None
    if r and not os.path.isdir(r):
        r = os.path.join(HERE, 'Outputs', os.path.basename(r))
    if r is None:  # inherited grid run: newest PIP_Run_<scene>_48_256_* with block files
        scene = os.path.basename(ev).replace('PIP_Eval_', '').split('_48_256')[0]
        c = sorted(
            [
                x
                for x in glob.glob(os.path.join(HERE, 'Outputs', 'PIP_Run_%s_48_256_*' % scene))
                if '_fseed_' not in x and os.path.isdir(os.path.join(x, 'frames', 'B0'))
            ],
            key=os.path.getmtime,
        )
        r = c[-1] if c else None
    return r


def load_run(run):
    fmt = np.loadtxt(os.path.join(run, 'frames', 'Out_Format.txt')).astype(int)
    nb, b, c, _, h, w = fmt[:6]
    P = np.stack(
        [
            np.stack(
                [
                    np.loadtxt(
                        os.path.join(run, 'frames', 'B%d' % i, 'trajs_tensor_B%d_F%d.txt' % (i, k)),
                        delimiter=',',
                    )
                    for k in range(b)
                ]
            )
            for i in range(nb)
        ]
    )  # nb,b,c,2
    mask = (
        np.load(os.path.join(run, 'frames', 'ptv_dropout_mask.npy'))
        if os.path.exists(os.path.join(run, 'frames', 'ptv_dropout_mask.npy'))
        else None
    )
    return P, (h, w), (mask.reshape(nb, b, c) if mask is not None else None)


rows = []
for scene in a.scenes:
    vec = fc.vector_files(scene)
    fnum = lambda p: int(re.findall(r'(\d{4})\.exr', p)[0])
    byf = {fnum(p): p for p in vec}
    U0, V0, H, W = fc.read_flow(vec[0])
    f_first = min(byf)
    sx, sy = 256.0 / W, 256.0 / H
    fields = {}

    def field(fr):
        if fr not in fields:
            U, V, _, _ = fc.read_flow(byf[fr])
            fields[fr] = (fc.to_field(U, dev), fc.to_field(V, dev), np.hypot(U, V))
        return fields[fr]

    for method in a.methods:
        ev = eval_dir(scene, method)
        if not ev:
            continue
        run = run_of(ev)
        if not run or not os.path.exists(os.path.join(run, 'frames', 'Out_Format.txt')):
            continue
        P, (h, w), mask = load_run(run)
        nb, b, c = P.shape[:3]
        gx_scale, gy_scale = W / w, H / h  # run units -> native
        qs, gto, gtt, pro, prt = [], [], [], [], []
        for i in range(nb):
            f0 = f_first + i * b
            pred = P[i].copy()
            pred[..., 0] *= gx_scale
            pred[..., 1] *= gy_scale  # b,c,2 native
            alive = mask[i] if mask is not None else np.ones((b, c), bool)
            birth = np.array(
                [int(np.argmax(alive[:, j])) if alive[:, j].any() else 0 for j in range(c)]
            )
            # ground truth: advect each point from its query frame through the GT fields
            gt = np.full((b, c, 2), np.nan, np.float32)
            occ = np.ones((b, c), bool)
            px = torch.tensor(pred[birth, np.arange(c), 0], dtype=torch.float32, device=dev)
            py = torch.tensor(pred[birth, np.arange(c), 1], dtype=torch.float32, device=dev)
            cur = np.stack([px.cpu().numpy(), py.cpu().numpy()], -1)
            for k in range(b):
                started = birth <= k
                gt[k, started] = cur[started]
                inside = (
                    (cur[:, 0] >= 0)
                    & (cur[:, 0] <= W - 1)
                    & (cur[:, 1] >= 0)
                    & (cur[:, 1] <= H - 1)
                )
                fr = f0 + k
                mag = field(fr)[2] if fr in byf else None
                onwater = np.zeros(c, bool)
                if mag is not None:
                    ix = np.clip(np.round(cur[:, 0]).astype(int), 0, W - 1)
                    iy = np.clip(np.round(cur[:, 1]).astype(int), 0, H - 1)
                    onwater = mag[iy, ix] > 1e-3
                occ[k] = ~(started & inside & onwater)
                if k < b - 1 and (fr + 1) in byf:
                    Uf, Vf, _ = field(fr + 1)
                    qx, qy = fc.step_forward(
                        torch.tensor(cur[:, 0], device=dev),
                        torch.tensor(cur[:, 1], device=dev),
                        Uf,
                        Vf,
                        H,
                        W,
                    )
                    nxt = np.stack([qx.cpu().numpy(), qy.cpu().numpy()], -1)
                    nxt[~started] = (
                        pred[np.minimum(birth, b - 1), np.arange(c)][~started]
                        if False
                        else nxt[~started]
                    )
                    # points not yet born stay at their birth position until they start
                    nb_ = ~(birth <= k + 1)
                    nxt[nb_] = pred[birth[nb_], np.where(nb_)[0]]
                    cur = nxt
            pin = (
                (pred[..., 0] >= 0)
                & (pred[..., 0] <= W - 1)
                & (pred[..., 1] >= 0)
                & (pred[..., 1] <= H - 1)
            )
            pocc = ~(pin & alive)
            qs.append(
                np.stack(
                    [birth, pred[birth, np.arange(c), 1] * sy, pred[birth, np.arange(c), 0] * sx],
                    -1,
                )
            )
            gtt.append(np.transpose(np.nan_to_num(gt) * np.array([sx, sy]), (1, 0, 2)))
            gto.append(occ.T)
            prt.append(np.transpose(pred * np.array([sx, sy]), (1, 0, 2)))
            pro.append(pocc.T)
        Q = np.concatenate(qs)[None]
        GO = np.concatenate(gto)[None]
        GT = np.concatenate(gtt)[None]
        PO = np.concatenate(pro)[None]
        PT = np.concatenate(prt)[None]
        m = tm.compute_tapvid_metrics(Q, GO, GT, PO, PT, 'first')
        # survival / median_l2 (repo style), per track, on evaluated visible frames
        eye = np.eye(b, dtype=np.int32)
        evalf = (np.cumsum(eye, 1) - eye)[Q[0, :, 0].astype(int)] > 0
        err = np.sqrt(((PT[0] - GT[0]) ** 2).sum(-1))
        vis = ~GO[0] & evalf
        with np.errstate(invalid='ignore'):
            surv16 = np.array(
                [
                    np.all(err[j][vis[j]] < 16) if vis[j].any() else np.nan
                    for j in range(err.shape[0])
                ]
            )
            surv32 = np.array(
                [
                    np.all(err[j][vis[j]] < 32) if vis[j].any() else np.nan
                    for j in range(err.shape[0])
                ]
            )
            mean_err = np.array(
                [err[j][vis[j]].mean() if vis[j].any() else np.nan for j in range(err.shape[0])]
            )
            va = vis & ~PO[0]  # 'alive' variants: only frames where the method reports a position
            surv16a = np.array(
                [np.all(err[j][va[j]] < 16) if va[j].any() else np.nan for j in range(err.shape[0])]
            )
            mean_err_a = np.array(
                [err[j][va[j]].mean() if va[j].any() else np.nan for j in range(err.shape[0])]
            )
            alive_frac = float(va.sum() / max(vis.sum(), 1))
        rows.append(
            dict(
                scene=scene,
                method=method,
                n_tracks=int(np.isfinite(mean_err).sum()),
                delta_avg=float(m['average_pts_within_thresh'][0]),
                OA=float(m['occlusion_accuracy'][0]),
                AJ=float(m['average_jaccard'][0]),
                pts_within_1=float(m['pts_within_1'][0]),
                pts_within_4=float(m['pts_within_4'][0]),
                pts_within_16=float(m['pts_within_16'][0]),
                survival_16=float(np.nanmean(surv16)),
                survival_32=float(np.nanmean(surv32)),
                median_l2=float(np.nanmedian(mean_err)),
                survival_16_alive=float(np.nanmean(surv16a)),
                median_l2_alive=float(np.nanmedian(mean_err_a)),
                alive_frac=alive_frac,
                source_run=os.path.basename(run),
            )
        )
        print(
            '%-24s %-28s delta_avg %.3f AJ %.3f OA %.3f surv16 %.2f med_l2 %.1f | alive: surv16 %.2f med_l2 %.1f (%.0f%% of visible frames)'
            % (
                scene,
                method,
                rows[-1]['delta_avg'],
                rows[-1]['AJ'],
                rows[-1]['OA'],
                rows[-1]['survival_16'],
                rows[-1]['median_l2'],
                rows[-1]['survival_16_alive'],
                rows[-1]['median_l2_alive'],
                100 * alive_frac,
            ),
            flush=True,
        )
    fields.clear()
with open(os.path.join(HERE, 'results', a.out), 'w', newline='') as fh:
    wr = _csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ['scene'])
    wr.writeheader()
    [wr.writerow(r) for r in rows]
print('wrote', a.out, len(rows), 'rows')
