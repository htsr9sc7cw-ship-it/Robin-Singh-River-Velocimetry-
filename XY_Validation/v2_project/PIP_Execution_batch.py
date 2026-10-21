"""PIP_Execution_batch.py

Thesis section: 3.5 (mode D4)
Inputs: frames of a variant, PIPs++ checkpoint
Outputs: PIPs++ run folder with tracks and dropout mask

PIP_Execution_batch.py — deployment mode D4 (PREREGISTRATION_strategies.md): FlowVelo's scheme applied to PIPs++.
Inside every 48-frame block a FRESH grid batch is seeded every PIP_BATCH_EVERY frames (default 2) and followed for
PIP_BATCH_LEN frames (default 16, one model call per batch); batches are stacked as extra particles of the block, with
frames/ptv_dropout_mask.npy marking each particle alive from its birth frame to its last frame (frozen at the birth position
before, at the last position after) — the layout ptv_to_piprun.py --block-len produces for FlowVelo, so the evaluator and
compare_v2.metrics score it identically. Env: PIP_SCENE, PIP_N (points per batch, default 64), PIP_IMG, PIP_CKPT_DIR,
PIP_RUN_SUFFIX (e.g. _S6_b2_256), PIP_BATCH_EVERY, PIP_BATCH_LEN, PIP_MAX_BLOCKS.
"""

import os, sys, time, datetime, math, torch, numpy as np
import torch.nn.functional as F

sys.argv = sys.argv[:1]
import PIP_Execution_reinit as R
from nets.pips2 import Pips

device = R.device
EVERY = int(os.environ.get('PIP_BATCH_EVERY', '2'))
BLEN = int(os.environ.get('PIP_BATCH_LEN', '16'))


def main(S=48, iters=16, out_dir='./Outputs'):
    scene = R.scene_config.SCENE
    n_per = int(os.environ.get('PIP_N', '64'))
    IMG = R.IMG
    init_dir = R.CKPT_DIR
    rgbs = np.stack(R.read_images(R.scene_config.IMAGES_DIR, "????", ".png"), 0)[
        :, :, :, 0:3
    ].copy()
    S_here, H, W, _ = rgbs.shape
    image_size = (256, 256) if IMG == 256 else (H, W)
    births = list(range(0, S - 1, EVERY))
    c = n_per * len(births)
    name = "PIP_Run_%s%s_%d_%d_%s_p%d" % (
        scene,
        os.environ.get("PIP_RUN_SUFFIX", ""),
        S,
        c,
        datetime.datetime.now().strftime('%d_%m_%Y_%H_%M'),
        os.getpid(),
    )
    out = os.path.join(out_dir, name, 'frames')
    os.makedirs(out, exist_ok=True)
    print(
        "Batch mode:",
        name,
        '| every',
        EVERY,
        'len',
        BLEN,
        'points/batch',
        n_per,
        'img',
        IMG,
        'ckpt',
        init_dir,
        flush=True,
    )
    model = Pips().to(device)
    ck = torch.load(
        next(os.path.join(init_dir, f) for f in sorted(os.listdir(init_dir)) if f.endswith('.pth')),
        map_location='cpu',
        weights_only=False,
    )
    model.load_state_dict(ck['model_state_dict'], strict=False)
    model.eval()
    idx = list(range(0, max(S_here - S, 1), S))
    mb = int(os.environ.get('PIP_MAX_BLOCKS', 0))
    idx = idx[:mb] if mb else idx
    full = np.zeros((len(idx), S, c, 2), np.float32)
    mask = np.zeros((len(idx), S, c), bool)
    for bi, si in enumerate(idx):
        t0 = time.time()
        seq = torch.from_numpy(rgbs[si : si + S]).permute(0, 3, 1, 2).to(torch.float32).to(device)
        seq = F.interpolate(seq, image_size, mode='bilinear').unsqueeze(0)
        _, _, _, h, w = seq.shape
        with torch.no_grad():
            for j, bf in enumerate(births):
                L = min(BLEN, S - bf)
                win = seq[:, bf : bf + L]
                if L < 2:
                    continue
                pos = R.grid_seeds(
                    n_per, h, w, bi * 100 + j, S
                )  # 1,n,2 (deterministic grid; seeds env honoured)
                preds, _, _, _ = model(
                    pos.unsqueeze(1).repeat(1, L, 1, 1),
                    win,
                    iters=iters,
                    feat_init=None,
                    beautify=True,
                )
                p = preds[-1][0].cpu().numpy()  # L,n,2
                cols = slice(j * n_per, (j + 1) * n_per)
                full[bi, :bf, cols] = p[0]
                full[bi, bf : bf + L, cols] = p
                full[bi, bf + L :, cols] = p[-1]
                mask[bi, bf : bf + L, cols] = True
        print('Block %d: %d batches, %.1f s' % (bi + 1, len(births), time.time() - t0), flush=True)
    for bi in range(len(idx)):
        d = os.path.join(out, 'B%d' % bi)
        os.makedirs(d, exist_ok=True)
        for k in range(S):
            np.savetxt(
                os.path.join(d, 'trajs_tensor_B%d_F%d.txt' % (bi, k)),
                full[bi, k],
                fmt='%.5f',
                delimiter=',',
            )
    np.save(os.path.join(out, 'ptv_dropout_mask.npy'), mask.reshape(-1, c))
    np.save(os.path.join(out, 'ptv_interpolated_mask.npy'), np.zeros((len(idx) * S, c), bool))
    open(os.path.join(out, 'Out_Format.txt'), 'w').write(
        '%d %d %d 2 %d %d' % (len(idx), S, c, image_size[0], image_size[1])
    )
    open(os.path.join(out_dir, name, 'REINIT_CONFIG.txt'), 'w').write(
        'batch every=%d len=%d n_per=%d img=%d ckpt=%s\n' % (EVERY, BLEN, n_per, IMG, init_dir)
    )
    print('DONE', os.path.join(out_dir, name), flush=True)


if __name__ == '__main__':
    main()
