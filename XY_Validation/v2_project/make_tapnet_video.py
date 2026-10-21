"""make_tapnet_video.py

Thesis section: see README.md
Inputs: see README.md
Outputs: see README.md

Videos rendered with DeepMind's own tapnet visualiser (tapnet_viz.plot_tracks_tails / paint_point_track, vendored):
rainbow points sorted by height with tails, occluded points hidden — the look of the TAP-Vid / TAPIR demo videos — for our
trackers on our scenes: PIPs++ (run suffix) and FlowVelo PTV, over the whole 192-frame sequence, side by side.
    XYV_DATA=<v2_project>/Vectors_and_Images python make_tapnet_video.py v2_Path4_dense [scene ...]
    env PIP_TAP_SUFFIX (default ft3000_b2_256 -> fallbacks), PIP_TAP_PTV (tuned_ncc_fd2), PIP_TAP_MAXPTS (400 per method), PIP_TAP_FPS (16)
Tracks: every PIPs++ point of every block (and every FlowVelo track) is one track over the full sequence, occluded outside
its life and when its true position has left the water/image (TAP-Vid convention). Output results/videos_tapnet/<scene>_*.mp4
"""

import os
import shutil, sys, glob, re, csv, numpy as np, cv2, torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
os.environ.setdefault('XYV_DATA', os.path.join(HERE, 'Vectors_and_Images'))
import flow_core as fc, tapnet_viz as tv

R = os.path.join(HERE, 'results', 'videos_tapnet')
os.makedirs(R, exist_ok=True)
SUF = os.environ.get('PIP_TAP_SUFFIX', 'ft3000_b2_256')
PTV_MODE = os.environ.get('PIP_TAP_PTV', 'tuned_ncc_fd2')
MAXPTS = int(os.environ.get('PIP_TAP_MAXPTS', '400'))
MAXPTV = int(os.environ.get('PIP_TAP_MAXPTV', '3000'))
FPS = int(os.environ.get('PIP_TAP_FPS', '16'))
dev = fc.pick_device('cpu')
rng = np.random.default_rng(0)


def gt_advect(P0, f_start, nfr, vec, W, H):
    gx = torch.tensor(P0[:, 0], dtype=torch.float32)
    gy = torch.tensor(P0[:, 1], dtype=torch.float32)
    out = [np.stack([gx.numpy(), gy.numpy()], -1)]
    for k in range(1, nfr):
        fr = f_start + k
        if fr not in vec:
            out.append(out[-1])
            continue
        U, V, _, _ = fc.read_flow(vec[fr])
        gx, gy = fc.step_forward(gx, gy, fc.to_field(U, dev), fc.to_field(V, dev), H, W)
        out.append(np.stack([gx.numpy(), gy.numpy()], -1))
    G = np.stack(out)
    return G, (G[..., 0] >= 0) & (G[..., 0] <= W - 1) & (G[..., 1] >= 0) & (G[..., 1] <= H - 1)


def pips_tracks(scene, W, H, T, f0, vec):
    """-> points [N,T,2], occluded [N,T] over the whole sequence, label"""
    for s in (SUF, 'ft3000_r2_256', 'r2_256'):
        runs = sorted(
            [
                r
                for r in glob.glob(os.path.join(HERE, 'Outputs', 'PIP_Run_%s_%s_48_*' % (scene, s)))
                if os.path.isdir(os.path.join(r, 'frames', 'B0'))
            ],
            key=os.path.getmtime,
        )
        if not runs:
            continue
        run = runs[-1]
        fmt = np.loadtxt(os.path.join(run, 'frames', 'Out_Format.txt')).astype(int)
        nb, b, c, _, h, w = fmt[:6]
        P = np.stack(
            [
                np.stack(
                    [
                        np.loadtxt(
                            os.path.join(
                                run, 'frames', 'B%d' % i, 'trajs_tensor_B%d_F%d.txt' % (i, k)
                            ),
                            delimiter=',',
                        )
                        for k in range(b)
                    ]
                )
                for i in range(nb)
            ]
        )
        P[..., 0] *= W / w
        P[..., 1] *= H / h
        m = os.path.join(run, 'frames', 'ptv_dropout_mask.npy')
        mask = np.load(m).reshape(nb, b, c) if os.path.exists(m) else np.ones((nb, b, c), bool)
        pts = np.zeros((nb * c, T, 2), np.float32)
        occ = np.ones((nb * c, T), bool)
        gpts = np.zeros_like(pts)  # [GT panel] same seeds advected through the exact GT field
        for i in range(nb):
            birth = np.array(
                [int(np.argmax(mask[i][:, j])) if mask[i][:, j].any() else 0 for j in range(c)]
            )
            for bf in np.unique(birth):
                sel = np.where(birth == bf)[0]
                G, inview = gt_advect(P[i, bf, sel], f0 + i * b + bf, b - bf, vec, W, H)
                t0 = i * b + bf
                span = min(b - bf, T - t0)
                pts[i * c + sel, t0 : t0 + span] = P[i, bf : bf + span, sel]
                occ[i * c + sel, t0 : t0 + span] = ~(
                    inview[:span].T & mask[i][bf : bf + span, sel].T
                )
                gpts[i * c + sel, t0 : t0 + span] = G[:span].transpose(1, 0, 2)
        global GTP
        GTP = gpts
        return pts, occ, s
    return None, None, None


def ptv_tracks(scene, T, f0):
    fs = glob.glob(os.path.join(HERE, 'out_ptv', scene, PTV_MODE, 'Tracking_FT_*.txt'))
    tr = {}
    for r in csv.DictReader(open(fs[0]), delimiter='\t'):
        tr.setdefault(int(float(r['id'])), []).append(
            (int(r['frame'][:4]), float(r['x']) + 1, float(r['y']) + 1)
        )
    ids = sorted(tr)
    pts = np.zeros((len(ids), T, 2), np.float32)
    occ = np.ones((len(ids), T), bool)
    for n, i in enumerate(ids):
        for fr, x, y in tr[i]:
            k = fr - f0
            if 0 <= k < T:
                pts[n, k] = (x, y)
                occ[n, k] = False
    return pts, occ


def subsample_sorted(pts, occ, n):
    alive = (~occ).any(1)
    idx = np.where(alive)[0]
    if len(idx) > n:
        idx = rng.choice(idx, n, replace=False)
    first = np.array([np.argmax(~occ[i]) for i in idx])
    y0 = pts[idx, first, 1]
    order = idx[np.argsort(y0)]  # sorted by height -> rainbow, as in the demo
    global LAST_ORDER
    LAST_ORDER = order
    return pts[order], occ[order]


for scene in sys.argv[1:]:
    imgs = sorted(glob.glob(os.path.join(HERE, 'Vectors_and_Images', scene, 'images', '*.png')))
    by_f = {int(os.path.basename(p)[:4]): p for p in imgs}
    if not imgs:
        print('skip', scene)
        continue
    frames_idx = sorted(by_f)
    f0 = frames_idx[0]
    T = min(192, len(frames_idx))
    rgb = np.stack([cv2.cvtColor(cv2.imread(by_f[f]), cv2.COLOR_BGR2RGB) for f in frames_idx[:T]])
    H, W = rgb.shape[1:3]
    vec = {int(re.findall(r'(\d{4})\.exr', p)[0]): p for p in fc.vector_files(scene)}
    pp, po, used = pips_tracks(scene, W, H, T, f0, vec)
    vp, vo = ptv_tracks(scene, T, f0)
    if pp is None:
        print('no PIPs++ run', scene)
        continue

    def water_only(
        pts, occ, gts=None
    ):  # [thesis] drop off-water seeds: GT displacement over the first alive step < 0.5 px
        keep = []
        for n in range(pts.shape[0]):
            a = np.where(~occ[n])[0]
            if len(a) < 2:
                continue
            g, _ = gt_advect(pts[n : n + 1, a[0]], f0 + a[0], 2, vec, W, H)
            keep.append(n) if np.hypot(*(g[1, 0] - g[0, 0])) > 0.5 else None
        keep = np.array(keep, int)
        return (pts[keep], occ[keep]) if gts is None else (pts[keep], occ[keep], gts[keep])

    pp, po, gp_all = water_only(pp, po, GTP)
    vp, vo = water_only(vp, vo)
    pp, po = subsample_sorted(pp, po, MAXPTS)
    gp = gp_all[LAST_ORDER]
    go = po.copy()
    vp, vo = subsample_sorted(vp, vo, MAXPTV)
    eye = np.eye(3)[None].repeat(T, 0)
    import gc  # [OPS-5] keep frames uint8 and free between panels (Overview render reached 17 GB swap)

    vid_p = np.ascontiguousarray(
        tv.plot_tracks_tails(
            rgb,
            pp,
            po.astype(np.float32),
            eye,
            point_size=int(os.environ.get('PIP_TAP_PTSIZE', '22')),
            linewidth=1.6,
            tail=int(os.environ.get('PIP_TAP_TAIL', '6')),
        ),
        dtype=np.uint8,
    )
    gc.collect()
    vid_v = np.ascontiguousarray(
        tv.plot_tracks_tails(
            rgb,
            vp,
            vo.astype(np.float32),
            eye,
            point_size=int(os.environ.get('PIP_TAP_PTSIZE', '22')),
            linewidth=1.6,
            tail=int(os.environ.get('PIP_TAP_TAIL', '6')),
        ),
        dtype=np.uint8,
    )
    gc.collect()
    vid_g = np.ascontiguousarray(
        tv.plot_tracks_tails(
            rgb,
            gp,
            go.astype(np.float32),
            eye,
            point_size=int(os.environ.get('PIP_TAP_PTSIZE', '22')),
            linewidth=1.6,
            tail=int(os.environ.get('PIP_TAP_TAIL', '6')),
        ),
        dtype=np.uint8,
    )
    gc.collect()
    label = {
        'S6_b2_256': 'RETRAINED PIPs++ S6 (new points every 2 frames)',
        'b2_256': 'PRE-TRAINED PIPs++ (new points every 2 frames)',
        'ft3000_b2_256': 'Retrained PIPs++ FT-1 (new points every 2 frames)',
        'ft3000_r48_256': 'Retrained PIPs++ (long-term)',
        'ft3000_r2_256': 'Retrained PIPs++ (re-tracked every 2 frames)',
        'r2_256': 'Untrained PIPs++',
        'b2_256': 'Untrained PIPs++ (new points every 2 frames)',
    }.get(used, used)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    h_, w_ = vid_p.shape[1:3]
    for name, vid in (
        ('%s_%s_pips' % (scene, used), vid_p),
        ('%s_ptv_%s' % (scene, PTV_MODE), vid_v),
        ('%s_groundtruth' % scene, vid_g),
    ):
        wr = cv2.VideoWriter(os.path.join(R, name + '.mp4'), fourcc, FPS, (w_, h_))
        [wr.write(cv2.cvtColor(f, cv2.COLOR_RGB2BGR)) for f in vid]
        wr.release()
    wr = cv2.VideoWriter(
        os.path.join(R, '%s_%s_side_by_side.mp4' % (scene, used)),
        fourcc,
        FPS,
        (3 * w_ + 16, h_ + 36),
    )
    for k in range(T):
        canvas = np.full((h_ + 36, 3 * w_ + 16, 3), 255, np.uint8)
        canvas[36:, :w_] = cv2.cvtColor(vid_g[k], cv2.COLOR_RGB2BGR)
        canvas[36:, w_ + 8 : 2 * w_ + 8] = cv2.cvtColor(vid_p[k], cv2.COLOR_RGB2BGR)
        canvas[36:, 2 * w_ + 16 :] = cv2.cvtColor(vid_v[k], cv2.COLOR_RGB2BGR)
        for tx, x0 in (
            ('GROUND TRUTH (Blender), same seeds   frame %d' % (f0 + k), 8),
            (label, w_ + 16),
            ('FlowVelo PTV (NCC, new features every 2 frames)', 2 * w_ + 24),
        ):
            cv2.putText(
                canvas, tx, (x0, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 2, cv2.LINE_AA
            )
        wr.write(canvas)
    del vid_p, vid_v, vid_g, rgb
    gc.collect()
    wr.release()
    import subprocess

    sb = os.path.join(R, '%s_%s_side_by_side.mp4' % (scene, used))
    os.makedirs(os.path.join(R, 'h264'), exist_ok=True)
    os.makedirs(os.path.join(R, 'gif'), exist_ok=True)  # [OPS-6] mp4v does not play in most viewers
    subprocess.run(
        [
            shutil.which('ffmpeg') or '/opt/anaconda3/bin/ffmpeg',
            '-y',
            '-loglevel',
            'error',
            '-i',
            sb,
            '-c:v',
            'libx264',
            '-pix_fmt',
            'yuv420p',
            '-crf',
            '22',
            '-vf',
            'scale=trunc(iw/2)*2:trunc(ih/2)*2',
            '-movflags',
            '+faststart',
            os.path.join(R, 'h264', os.path.basename(sb)),
        ]
    )
    subprocess.run(
        [
            shutil.which('ffmpeg') or '/opt/anaconda3/bin/ffmpeg',
            '-y',
            '-loglevel',
            'error',
            '-i',
            sb,
            '-vf',
            'fps=8,scale=1536:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer',
            os.path.join(R, 'gif', os.path.basename(sb)[:-4] + '.gif'),
        ]
    )
    print(
        'tapnet video',
        scene,
        used,
        T,
        'frames',
        pp.shape[0],
        'pips tracks',
        vp.shape[0],
        'ptv tracks',
        flush=True,
    )
