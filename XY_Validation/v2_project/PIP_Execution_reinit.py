"""PIP_Execution_reinit.py

Thesis section: see README.md
Inputs: see README.md
Outputs: see README.md

PIP_Execution_reinit.py — PIPs++ with RE-INITIALISED tracking (Study A, PREREGISTRATION_v2_reinit.md).

Copy of PIP_Execution.py (kept untouched) with one change in the inference loop: inside every 48-frame block the tracker
is re-initialised at its own tracked positions every PIP_REINIT_K frames (features re-sampled at the current frame,
model window PIP_WIN frames) and the steps are chained.  the supervisor's request 2026-09-16: "track once per frame / once per
2 frames instead of once per 48".  With PIP_REINIT_K >= 47 this is exactly the original single call per block.

Environment (in addition to PIP_SCENE, PIP_N, PIP_SEEDS... of the original):
  PIP_REINIT_K   re-initialisation interval in frames (1, 2, ... ; 48 = original behaviour)      default 1
  PIP_WIN        frames the model sees per call (>= K+1)                                          default 8
  PIP_IMG        working resolution: 256 = resize to 256x256 as all runs so far; 512 = native size  default 256
  PIP_CKPT_DIR   checkpoint folder (Study B fine-tuned weights)                                    default ./reference_model
  PIP_RUN_SUFFIX appended to the run name, e.g. _r1_512
Output layout identical to PIP_Execution.py (Outputs/PIP_Run_<scene><suffix>_48_<N>_<date>_p<pid>/frames/B<i>/...,
Out_Format.txt = [blocks, 48, N, 2, H, W]) so PIP_Evaluation_gt.py and compare_v2.py score it unchanged.
"""

import time, os, datetime, torch, math, imageio
import utils.improc, saverloader
import numpy as np
import scene_config

device = scene_config.DEVICE
import torch.nn.functional as F
import fnmatch as fm
from nets.pips2 import Pips

K_REINIT = int(os.environ.get('PIP_REINIT_K', '1'))
WIN = int(os.environ.get('PIP_WIN', '8'))
IMG = int(os.environ.get('PIP_IMG', '256'))
_REF = './reference_model' if os.path.isdir('./reference_model') else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'reference_model')
CKPT_DIR = os.environ.get('PIP_CKPT_DIR', _REF)


def read_images(fn, fheader, ftype):
    frames = []
    for ifile in sorted(os.listdir(fn)):  # [FIX P1] sorted, as in PIP_Execution.py
        if fm.fnmatch(ifile, f'{fheader}{ftype}'):
            frames.append(imageio.v3.imread(os.path.join(fn, ifile)))
    return frames


def grid_seeds(N, H, W, gs, S):
    """Initial points of a block: 16x16 grid exactly as PIP_Execution.run_model (or FlowVelo features with PIP_SEEDS)."""
    B = 1
    N_ = np.sqrt(N).round().astype(np.int32)
    grid_y, grid_x = utils.basic.meshgrid2d(B, N_, N_, stack=False, norm=False, device=device)
    grid_y = 8 + grid_y.reshape(B, -1) / float(N_ - 1) * (H - 16)
    grid_x = 8 + grid_x.reshape(B, -1) / float(N_ - 1) * (W - 16)
    xy0 = torch.stack([grid_x, grid_y], dim=-1)  # 1, N, 2
    if os.environ.get('PIP_SEEDS'):
        import glob as _g

        f0 = int(os.environ['PIP_FIRST_FRAME']) + (gs - 1) * S
        cands = sorted(
            (int(q.rsplit('_', 1)[1][:4]), q)
            for q in _g.glob(os.path.join(os.environ['PIP_SEEDS'], 'FD_every_*.txt'))
        )
        fd = [q for fr_, q in cands if fr_ <= f0][-1]
        pts = np.loadtxt(fd, delimiter='\t', skiprows=1)[:, 1:3].astype(np.float32)
        sx, sy = W / float(os.environ['PIP_NATIVE_W']), H / float(os.environ['PIP_NATIVE_H'])
        rs = np.random.default_rng(gs)
        pick = rs.choice(len(pts), N, replace=len(pts) < N)
        xy0 = torch.tensor(
            np.c_[pts[pick, 0] * sx, pts[pick, 1] * sy], dtype=torch.float32, device=device
        ).unsqueeze(0)
        print(
            'SEEDS from',
            os.path.basename(fd),
            'for block starting frame',
            f0,
            ':',
            len(pts),
            'features ->',
            N,
            flush=True,
        )
    return xy0


def run_block_reinit(model, rgbs, N, iters, gs, k, win):
    """rgbs: 1,S,3,H,W of one block.  Returns 1,S,N,2 chained trajectories.
    Every k frames the model is called afresh on frames [t, t+win) with the points at their current positions
    (feat_init=None -> features sampled at frame t), and frames t+1..t+k of its answer are kept."""
    rgbs = rgbs.to(device).float()
    _, S, C, H, W = rgbs.shape
    pos = grid_seeds(N, H, W, gs, S)  # 1, N, 2
    traj = torch.zeros(1, S, N, 2, dtype=torch.float32, device=device)
    traj[:, 0] = pos
    ncalls = 0
    t0 = time.time()
    for t in range(0, S - 1, k):
        n_keep = min(k, S - 1 - t)
        w = max(win, n_keep + 1)
        seq = rgbs[:, t : t + w]
        if seq.shape[1] < w:  # pad by repeating the last frame
            seq = torch.cat([seq, seq[:, -1:].repeat(1, w - seq.shape[1], 1, 1, 1)], 1)
        trajs_e0 = pos.unsqueeze(1).repeat(1, w, 1, 1)
        preds, _, _, _ = model(trajs_e0, seq, iters=iters, feat_init=None, beautify=True)
        p = preds[-1]  # 1, w, N, 2
        traj[:, t + 1 : t + 1 + n_keep] = p[:, 1 : 1 + n_keep]
        pos = p[:, n_keep].clone()
        ncalls += 1
    print(
        'Block %d: %d model calls, k=%d, win=%d, %.1f s' % (gs, ncalls, k, win, time.time() - t0),
        flush=True,
    )
    return traj


def main(
    filename=scene_config.IMAGES_DIR,
    outputname="PIP_Run_" + scene_config.SCENE + os.environ.get("PIP_RUN_SUFFIX", ""),
    S=48,
    N=scene_config.N,
    timestride=1,
    iters=16,
    max_iters=0,
    out_dir='./Outputs',
    init_dir=CKPT_DIR,
):
    print(
        "Model's name:",
        outputname,
        '| reinit k =',
        K_REINIT,
        'win =',
        WIN,
        'img =',
        IMG,
        'ckpt =',
        init_dir,
    )
    rgbs = read_images(filename, "????", ".png")
    rgbs = np.stack(rgbs, axis=0)[:, :, :, 0:3].copy()[::timestride]
    S_here, H, W, C = rgbs.shape
    NSq = round(math.sqrt(N))
    image_size = (256, 256) if IMG == 256 else (H, W)  # 512 -> native size (Overview 512x1024)
    print('Input data format:', rgbs.shape, 'working size', image_size)

    model_name = "%s_%d_%d_%s_p%d" % (
        outputname,
        S,
        N,
        datetime.datetime.now().strftime('%d_%m_%Y_%H_%M'),
        os.getpid(),
    )
    output_dir = os.path.join(out_dir, model_name)
    os.makedirs(os.path.join(output_dir, 'frames'), exist_ok=True)
    print('Summary Name:', model_name)

    model = Pips().to(device)
    ckpt_path = next(
        os.path.join(init_dir, f) for f in sorted(os.listdir(init_dir)) if f.endswith('.pth')
    )
    checkpoint = torch.load(ckpt_path, map_location='cpu', weights_only=False)
    model.load_state_dict(checkpoint['model_state_dict'], strict=False)
    print('Loaded checkpoint:', ckpt_path)
    model.eval()

    global_step = 0
    idx = list(range(0, max(S_here - S, 1), S))
    max_iters = int(os.environ.get('PIP_MAX_BLOCKS', max_iters))  # test aid: limit blocks
    if max_iters:
        idx = idx[:max_iters]
    print('Range values:', idx, 'Steps to compute:', len(idx))
    full = torch.empty([0, S, NSq * NSq, 2], dtype=torch.float32, device=device)
    for si in idx:
        global_step += 1
        rgb_seq = (
            torch.from_numpy(rgbs[si : si + S]).permute(0, 3, 1, 2).to(torch.float32).to(device)
        )
        rgb_seq = F.interpolate(rgb_seq, image_size, mode='bilinear').unsqueeze(0)
        with torch.no_grad():
            trajs_e = run_block_reinit(model, rgb_seq, N, iters, global_step, K_REINIT, WIN)
        full = torch.cat((full, trajs_e), 0)
        with open(output_dir + '/frames/Out_Format.txt', 'w') as fh:
            fh.write('%s %s %s %s %s %s' % (full.shape + image_size))
    d, o = full.shape[:2]
    for f in range(d):
        B_dir = output_dir + '/frames/B' + str(f)
        os.mkdir(B_dir)
        for j in range(o):
            np.savetxt(
                B_dir + '/trajs_tensor_B' + str(f) + '_F' + str(j) + '.txt',
                full[f, j].cpu(),
                fmt='%.5f',
                delimiter=',',
            )
    with open(os.path.join(output_dir, 'REINIT_CONFIG.txt'), 'w') as fh:
        fh.write('k=%d win=%d img=%d ckpt=%s N=%d S=%d\n' % (K_REINIT, WIN, IMG, ckpt_path, N, S))
    print('DONE', output_dir, flush=True)


if __name__ == '__main__':
    main()
