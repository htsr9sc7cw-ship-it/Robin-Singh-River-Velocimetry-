"""compare_v2.py

Thesis section: 3.5
Inputs: evaluation folders of all trackers
Outputs: result CSV with ratio, direction, speed, coverage and TAP-Vid metrics

Three-way comparison on dataset v2, both trackers through the SAME evaluator.

    /opt/anaconda3/envs/pips2/bin/python compare_v2.py [--ptv-eval]

Step 1 (--ptv-eval): for every variant and PTV mode, convert the FlowVelo run to the PIP_Run layout
(ptv/ptv_to_piprun.py, +1 px for F3, blocks every FD frames) and score it with PIP_Evaluation_gt.py
(PIP_FIX_SIGN=1). Step 2: read every PIP_Eval Tables/Trajs_F*.txt (columns: id,x,y,dx,dy,|d|,dU,dV,dUV;
truth = measured - dU), compute per variant and method: RMSE, median endpoint error, stay-still and
mean-flow baselines from the same truth samples, direction agreement (circular), speed ratio, and
the PTV filter cascade from logfileImgSpace.txt. Writes results/three_way_v2.csv.
"""

import os, sys, glob, re, subprocess, argparse, ast


def _py(env, default):
    """interpreter for a sub-process: environment variable, else the project default if it exists, else this one"""
    return os.environ.get(env) or (default if os.path.exists(default) else sys.executable)


import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
XYV = os.path.dirname(HERE)
ap = argparse.ArgumentParser()
ap.add_argument('--ptv-eval', action='store_true')
ap.add_argument('--scenes', nargs='*', default=None)
ap.add_argument(
    '--ptv-root',
    default='out_ptv',
    help='folder under v2_project with <scene>/<mode>/ FlowVelo runs',
)
ap.add_argument('--modes', nargs='*', default=['tuned_lk', 'tuned_ncc', 'gui_defaults'])
ap.add_argument('--out', default='three_way_v2.csv')
ap.add_argument('--no-pips', action='store_true')
ap.add_argument('--workers', type=int, default=4)
ap.add_argument(
    '--method-suffix', default='', help="e.g. '_blind' for runs from an image-derived parameter set"
)
ap.add_argument(
    '--pips-suffixes',
    nargs='*',
    default=[],
    help="[REINIT-1] extra PIPs++ runs scored as rows PIPs++_<suffix>: Outputs/PIP_Eval_<scene>_<suffix>",
)
ap.add_argument(
    '--ptv-block-len',
    type=int,
    default=0,
    help='[REINIT-1] ptv_to_piprun.py --block-len (0 = FD, original)',
)
a = ap.parse_args()
scenes = sorted(
    os.path.basename(p) for p in glob.glob(os.path.join(HERE, 'Vectors_and_Images', 'v2_*'))
)
if a.scenes:
    scenes = [x for x in scenes if x in a.scenes]
env = dict(
    os.environ, PIP_PROJECT=HERE, PIP_FIX_SIGN='1', PIP_FIX_TRANSPOSE='1', PIP_MP='0'
)  # [FIXLOG C4]
os.makedirs(os.path.join(HERE, 'results'), exist_ok=True)


def newest_run(scene, n):
    r = sorted(
        glob.glob(os.path.join(HERE, 'Outputs', 'PIP_Run_%s_48_%d_*' % (scene, n))),
        key=os.path.getmtime,
    )
    return r[-1] if r else None


def eval_job(s, mode):
    """Convert one FlowVelo run to the PIP_Run layout and score it; returns a log line. Safe to run in parallel:
    the evaluator is told the exact run folder (PIP_RUN_DIR), so concurrent jobs of one scene cannot cross-talk.
    """
    run = os.path.join(HERE, a.ptv_root, s, mode)
    outdir = os.path.join(HERE, 'Outputs', 'PTV_Eval_%s_%s%s' % (s, mode, a.method_suffix))
    if os.path.exists(os.path.join(outdir, 'Tables', 'SUMMARY.txt')) or not glob.glob(
        os.path.join(run, 'Tracking_FT_*.txt')
    ):
        return 'skip %s %s' % (s, mode)
    p = subprocess.run(
        [
            _py('BASE_PYTHON', '/opt/anaconda3/bin/python'),
            os.path.join(XYV, 'ptv', 'ptv_to_piprun.py'),
            '--run',
            run,
            '--project',
            HERE,
            '--block-len',
            str(a.ptv_block_len),
        ],
        capture_output=True,
        text=True,
    )
    m = re.search(r'PTV->PIP_Run (\S+) .*particles (\d+)', p.stdout)
    if not m:
        return 'PTV->PIP failed %s %s %s %s' % (s, mode, p.stdout[-300:], p.stderr[-300:])
    tag, c = m.group(1), int(m.group(2))
    e = dict(
        env,
        PIP_SCENE=s,
        PIP_N=str(c),
        PIP_EVAL_OUT=outdir,
        PIP_RUN_DIR=os.path.join(HERE, 'Outputs', tag),
        PIP_NO_PLOTS='1',
    )
    r = subprocess.run(
        [
            _py('PIPS2_PYTHON', '/opt/anaconda3/envs/pips2/bin/python'),
            '-W',
            'ignore',
            os.path.join(HERE, 'PIP_Evaluation_gt.py'),
        ],
        env=e,
        capture_output=True,
        text=True,
    )
    rm = re.search(r'RMSE \(endpoint error\)\s*:\s*([\d.]+)', r.stdout)
    used = re.search(r'Using PIPs output: (.*)', r.stdout)
    if used:
        open(os.path.join(outdir, 'SOURCE_RUN.txt'), 'w').write(used.group(1).strip() + '\n')
    return 'PTV eval %s %s c=%d RMSE %s' % (
        s,
        mode,
        c,
        rm.group(1) if rm else 'FAIL ' + r.stderr[-200:],
    )


if a.ptv_eval:
    from concurrent.futures import ThreadPoolExecutor

    jobs = [(s, mode) for s in scenes for mode in a.modes]
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for line in ex.map(lambda j: eval_job(*j), jobs):
            print(line, flush=True)


def frame_size(scene):
    png = sorted(glob.glob(os.path.join(HERE, 'Vectors_and_Images', scene, 'images', '*.png')))[0]
    hdr = open(png, 'rb').read(24)
    return int.from_bytes(hdr[16:20], 'big'), int.from_bytes(hdr[20:24], 'big')  # W, H


def find_source_run(eval_dir, scene, A):
    """The PIP_Run the evaluator scored: SOURCE_RUN.txt if recorded, else the run whose block-0
    positions equal the evaluator's table (mtime alone is ambiguous when two runs share c)."""
    f = os.path.join(eval_dir, 'SOURCE_RUN.txt')
    if os.path.exists(f):
        return open(f).read().strip()
    for r in sorted(
        glob.glob(os.path.join(HERE, 'Outputs', 'PIP_Run_%s_48_*' % scene)),
        key=os.path.getmtime,
        reverse=True,
    ):
        if not os.path.exists(os.path.join(r, 'frames', 'Out_Format.txt')):
            continue  # incomplete run folder
        fmt = np.loadtxt(os.path.join(r, 'frames', 'Out_Format.txt'))
        if int(fmt[2]) != A.shape[1]:
            continue
        b1 = np.loadtxt(os.path.join(r, 'frames', 'B0', 'trajs_tensor_B0_F1.txt'), delimiter=',')
        dif = np.abs(b1 - A[1, :, 1:3])
        dif = dif[np.isfinite(dif)]
        if (
            dif.size and (dif < 2e-3).mean() > 0.9
        ):  # evaluator rounds to 3 dp and clips off-image points
            return r
    raise RuntimeError('no PIP_Run matches %s' % eval_dir)


def metrics(eval_dir, scene, method):
    """All methods in NATIVE pixel units of the scene [FIXLOG C2]; frame k=0 of every block excluded
    (the evaluator's displacement there is 0 by construction); PTV points frozen after dropout
    excluded through ptv_dropout_mask.npy [FIXLOG C1]."""
    T = sorted(
        glob.glob(os.path.join(eval_dir, 'Tables', 'Trajs_F*.txt')),
        key=lambda p: int(re.findall(r'F(\d+)', p)[0]),
    )
    if not T:
        return None
    A = np.stack([np.loadtxt(p, delimiter=',') for p in T])  # (F, P, 9)
    run = find_source_run(eval_dir, scene, A)
    fmt = np.loadtxt(os.path.join(run, 'frames', 'Out_Format.txt')).astype(int)
    b, h, w = fmt[1], fmt[4], fmt[5]
    W, H = frame_size(scene)
    sx, sy = W / w, H / h  # 1 for PTV (native), 2 / 4 for PIPs++ (256-px run)
    keep = np.ones(A.shape[:2], bool)
    keep[0::b] = False
    # [FIXLOG D-5.1] positions on the frame border (evaluator clips off-image points there): exclude the step
    # if its start or end lies on the border, for every method, in the run's own units
    px_, py_ = A[..., 1], A[..., 2]
    onb = (px_ <= 0) | (px_ >= w - 1) | (py_ <= 0) | (py_ >= h - 1)
    onb_step = onb.copy()
    onb_step[1:] |= onb[:-1]
    n_border = int((keep & onb_step).sum())
    keep &= ~onb_step
    has_mask = os.path.exists(
        os.path.join(run, 'frames', 'ptv_dropout_mask.npy')
    )  # PTV runs, and PIPs++ batch mode (D4)
    if method.startswith('PTV') or has_mask:
        mask = np.load(os.path.join(run, 'frames', 'ptv_dropout_mask.npy'))
        assert mask.shape == keep.shape, (mask.shape, keep.shape)
        keep &= mask
        if method.startswith('PTV'):
            assert (h, w) == (H, W), 'PTV run not at native size: %s' % run
        n_expected = int(mask.sum() - mask[0::b].sum())
    dx, dy, dU, dV = A[..., 3] * sx, A[..., 4] * sy, A[..., 6] * sx, A[..., 7] * sy
    tx, ty = dx - dU, dy - dV  # truth (forward) at the tracked points
    keep &= np.isfinite(dx) & np.isfinite(tx) & (np.hypot(tx, ty) > 1e-3)
    extra = {}
    if method.startswith('PTV') or has_mask:
        # alive points off the water (GT flow 0: banks in Overview/Path1/Path7) are excluded like everywhere else; counted
        n_offwater = (
            int((mask & ~keep)[1:].sum() - (~np.isfinite(dx) & mask)[1:].sum())
            if False
            else int(n_expected - keep.sum())
        )
        assert 0 < mask.mean() < 1 and keep.sum() <= n_expected, (
            'mask not applied?',
            keep.sum(),
            n_expected,
        )
        ip = os.path.join(run, 'frames', 'ptv_interpolated_mask.npy')
        extra = dict(
            n_alive=int(n_expected),
            n_offwater=n_offwater,
            frac_interpolated=float(np.load(ip)[keep].mean()) if os.path.exists(ip) else np.nan,
        )
    # per-track view (before flattening): a track 'follows' the flow if, over its kept sub-steps, the
    # summed measured displacement is 0.5-1.5x the summed true displacement and within 37 deg of it
    # Windows of HW frames inside each block (PIPs++ 48 -> 3 windows of 15; PTV blocks = FD frames,
    # 4-15 depending on scene speed -> one window of FD frames); horizon recorded in track_horizon.
    HW = min(15, b)
    F, P = keep.shape
    nb = F // b
    nw = b // HW  # horizon = block length, capped at 15 (recorded per row)

    def win(a):
        a = a.reshape(nb, b, P)[:, : nw * HW].reshape(nb * nw, HW, P)
        return a

    kb = win(keep)
    sx_ = win(np.where(keep, dx, 0)).sum(1)
    sy_ = win(np.where(keep, dy, 0)).sum(1)
    tx_ = win(np.where(keep, tx, 0)).sum(1)
    ty_ = win(np.where(keep, ty, 0)).sum(1)
    nk = kb.sum(1)
    ok = nk >= 3
    mr = np.hypot(sx_, sy_) / (np.hypot(tx_, ty_) + 1e-6)
    cs = (sx_ * tx_ + sy_ * ty_) / (np.hypot(sx_, sy_) * np.hypot(tx_, ty_) + 1e-6)
    follow = ok & (mr > 0.5) & (mr < 1.5) & (cs > 0.8)
    still = ok & (mr < 0.2)
    trk = dict(
        track_horizon=int(HW),
        n_tracks=int(ok.sum()),
        frac_tracks_follow=float(follow.sum() / max(ok.sum(), 1)),
        frac_tracks_still=float(still.sum() / max(ok.sum(), 1)),
    )
    # [FIXLOG E-1] equal-horizon variant: steps 1..15 of every block only (the PTV batches live FT = 20 frames; a PIPs++ point
    # that follows a 23 px/frame flow leaves the frame within ~20 of its 47 steps and the border rule then keeps mostly the
    # points that did NOT move). ratio_h15 = RMSE / stay-still RMSE over those steps, for every method alike.
    kidx = (np.arange(F) % b)[:, None]
    k15 = keep & (kidx >= 1) & (kidx <= 15)
    e15 = np.hypot(dx[k15] - tx[k15], dy[k15] - ty[k15])
    t15 = np.hypot(tx[k15], ty[k15])
    h15 = dict(
        n_h15=int(k15.sum()),
        rmse_h15=float(np.sqrt(np.mean(e15**2))) if k15.any() else np.nan,
        rmse_stay_h15=float(np.sqrt(np.mean(t15**2))) if k15.any() else np.nan,
    )
    h15['ratio_h15'] = h15['rmse_h15'] / h15['rmse_stay_h15'] if k15.any() else np.nan
    dx, dy, tx, ty = dx[keep], dy[keep], tx[keep], ty[keep]
    err = np.hypot(dx - tx, dy - ty)
    tm = np.hypot(tx, ty)
    mm = np.hypot(dx, dy)
    cos = (dx * tx + dy * ty) / (mm * tm + 1e-6)
    mfx, mfy = tx.mean(), ty.mean()
    return dict(
        n=int(keep.sum()),
        n_border_excluded=n_border,
        **extra,
        **trk,
        source_run=os.path.basename(run),
        unit_scale_x=sx,
        unit_scale_y=sy,
        rmse=float(np.sqrt(np.mean(err**2))),
        err_med=float(np.median(err)),
        rmse_stay=float(np.sqrt(np.mean(tm**2))),
        rmse_meanflow=float(np.sqrt(np.mean((tx - mfx) ** 2 + (ty - mfy) ** 2))),
        cos_med=float(np.median(cos[mm > 0.5])) if (mm > 0.5).any() else np.nan,
        frac_cos08=float((cos[mm > 0.5] > 0.8).mean()) if (mm > 0.5).any() else np.nan,
        frac_zero=float((mm < 0.01).mean()),
        speed_ratio=float(np.median(mm / (tm + 1e-6))),
        truth_med=float(np.median(tm)),
        d1=float((err < 1).mean()),
        d2=float((err < 2).mean()),
        d4=float((err < 4).mean()),
        d8=float((err < 8).mean()),
        d16=float((err < 16).mean()),
        **h15
    )


rows = []
for s in scenes:
    # PIPs++
    ev = sorted(
        glob.glob(os.path.join(HERE, 'Outputs', 'PIP_Eval_%s_48_256_*' % s)), key=os.path.getmtime
    )
    if ev and not a.no_pips:
        m = metrics(ev[-1], s, 'PIPs++')
        if m:
            rows.append(dict(scene=s, method='PIPs++', **m))
    evf = os.path.join(
        HERE, 'Outputs', 'PIP_Eval_%s_fseed' % s
    )  # feature-seeded PIPs++ (AUD21-1 item 1), if run
    if os.path.isdir(evf) and not a.no_pips:
        m = metrics(evf, s, 'PIPs++_fseed')
        if m:
            rows.append(dict(scene=s, method='PIPs++_fseed', **m))
    for suf in a.pips_suffixes:  # [REINIT-1] re-initialised / fine-tuned PIPs++ variants
        evs = os.path.join(HERE, 'Outputs', 'PIP_Eval_%s_%s' % (s, suf))
        if os.path.isdir(evs) and not a.no_pips:
            m = metrics(evs, s, 'PIPs++_' + suf)
            if m:
                rows.append(dict(scene=s, method='PIPs++_' + suf, **m))
    for mode in a.modes:
        ev = os.path.join(HERE, 'Outputs', 'PTV_Eval_%s_%s%s' % (s, mode, a.method_suffix))
        run = os.path.join(HERE, a.ptv_root, s, mode)
        m = metrics(ev, s, 'PTV_' + mode + a.method_suffix) if os.path.isdir(ev) else None
        casc = {}
        lf = os.path.join(run, 'logfileImgSpace.txt')
        if os.path.exists(lf):
            txt = open(lf).read()
            g = re.search(r"filter cascade.*?', (\[.*?\])", txt)
            if g:
                try:
                    c = ast.literal_eval(g.group(1).replace('nan', 'None'))
                    casc = dict(
                        raw=c[0],
                        after_mindist=c[1],
                        after_maxdist=c[2],
                        after_mincount=c[3],
                        after_steady=c[5],
                        after_range=c[7],
                        final=c[9],
                    )
                except Exception:
                    pass
            nf = re.search(r"n_final_tracks: ', (\d+)", txt)
            casc['final'] = int(nf.group(1)) if nf else casc.get('final')
        rows.append(dict(scene=s, method='PTV_' + mode + a.method_suffix, **(m or {}), **casc))
df = pd.DataFrame(rows)
df.to_csv(os.path.join(HERE, 'results', a.out), index=False)
pd.set_option('display.width', 250)
print(
    df[
        [
            'scene',
            'method',
            'n',
            'rmse',
            'rmse_stay',
            'err_med',
            'cos_med',
            'speed_ratio',
            'frac_zero',
            'final',
        ]
    ].to_string(index=False)
)
