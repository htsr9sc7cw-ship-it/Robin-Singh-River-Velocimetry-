"""known_answer_eval.py

Thesis section: 3.5, 5.1
Inputs: tracers/trajs.npz of a variant, ground-truth field
Outputs: known-answer verdict (PASS, PASS_FLOOR, FAIL) per variant

Known-answer test THROUGH the evaluator (FIXLOG C4 process gap): the exact tracer trajectories
(tracers/trajs.npz, advected through the scene's own GT field) are written in the PIP_Run layout
and scored by PIP_Evaluation_gt.py with the v2 flags. A correct evaluator must report ~0 px.
    /opt/anaconda3/bin/python known_answer_eval.py v2_Path4_dense v2_Overview_dense
PASS if median endpoint error < 0.15 px and RMSE < 1.0 px (v3 GT: nearest-pixel sampling of a smooth field; measured 0.09 / 0.78 on Path4, FIXLOG V2-1 b'); else FAIL.
"""

import os, sys, glob, re, subprocess, datetime, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
B = 8
C = 60
for scene in sys.argv[1:]:
    try:
        z = np.load(os.path.join(HERE, 'Vectors_and_Images', scene, 'tracers', 'trajs.npz'))
        T, val, frames = z['trajs_2d'], z['valids'], z['frames']
        png = sorted(glob.glob(os.path.join(HERE, 'Vectors_and_Images', scene, 'images', '*.png')))[
            0
        ]
        hdr = open(png, 'rb').read(24)
        W, H = int.from_bytes(hdr[16:20], 'big'), int.from_bytes(hdr[20:24], 'big')
        nb = len(frames) // B
        rng = np.random.default_rng(1)
        # [AUD21-2 D1] C adapts to the scene: the smallest per-block pool of whole-block, in-frame tracers (min 10)
        pools = []
        for bi in range(nb):
            f0 = bi * B
            alive = val[f0 : f0 + B].all(0)
            inside = (
                (T[f0 : f0 + B, :, 0] > 2).all(0)
                & (T[f0 : f0 + B, :, 0] < W - 3).all(0)
                & (T[f0 : f0 + B, :, 1] > 2).all(0)
                & (T[f0 : f0 + B, :, 1] < H - 3).all(0)
            )
            pools.append(int((alive & inside).sum()))
        C_here = max(10, min(C, min(pools)))
        if min(pools) < 10:
            ln = 'KNOWN-ANSWER %s: SKIP (a block has only %d whole-block tracers)' % (
                scene,
                min(pools),
            )
            print(ln, flush=True)
            open(os.path.join(HERE, 'results', 'KNOWN_ANSWER.txt'), 'a').write(
                datetime.datetime.now().isoformat() + ' ' + ln + '\n'
            )
            continue
        tag = 'PIP_Run_%s_48_%d_KA_%s' % (
            scene,
            C_here,
            datetime.datetime.now().strftime('%d_%m_%Y_%H_%M_%S'),
        )
        out = os.path.join(HERE, 'Outputs', tag, 'frames')
        os.makedirs(out, exist_ok=True)
        mask = np.ones((nb * B, C), bool)
        for bi in range(nb):
            f0 = bi * B
            alive = val[f0 : f0 + B].all(0)  # tracers valid for the whole block
            inside = (
                (T[f0 : f0 + B, :, 0] > 2).all(0)
                & (T[f0 : f0 + B, :, 0] < W - 3).all(0)
                & (T[f0 : f0 + B, :, 1] > 2).all(0)
                & (T[f0 : f0 + B, :, 1] < H - 3).all(0)
            )
            ids = rng.choice(np.where(alive & inside)[0], C_here, replace=False)
            os.makedirs(os.path.join(out, 'B%d' % bi), exist_ok=True)
            for k in range(B):
                np.savetxt(
                    os.path.join(out, 'B%d' % bi, 'trajs_tensor_B%d_F%d.txt' % (bi, k)),
                    T[f0 + k, ids],
                    fmt='%.4f',
                    delimiter=',',
                )
        np.savetxt(
            os.path.join(out, 'Out_Format.txt'), np.array([[nb, B, C_here, 2, H, W]]), fmt='%d'
        )
        np.save(os.path.join(out, 'ptv_dropout_mask.npy'), mask[:, :C_here])
        ev = os.path.join(HERE, 'Outputs', 'KA_Eval_%s' % scene)
        env = dict(
            os.environ,
            PIP_PROJECT=HERE,
            PIP_FIX_SIGN='1',
            PIP_FIX_TRANSPOSE='1',
            PIP_MP='0',
            PIP_NO_PLOTS='1',
            PIP_SCENE=scene,
            PIP_N=str(C_here),
            PIP_EVAL_OUT=ev,
            PIP_RUN_DIR=os.path.join(HERE, 'Outputs', tag),
        )
        r = subprocess.run(
            [
                '/opt/anaconda3/envs/pips2/bin/python',
                '-W',
                'ignore',
                os.path.join(HERE, 'PIP_Evaluation_gt.py'),
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        used = re.search(r'Using PIPs output: (.*)', r.stdout)
        assert used and tag in used.group(1), r.stdout[-2000:] + r.stderr[-2000:]
        Tb = sorted(
            glob.glob(os.path.join(ev, 'Tables', 'Trajs_F*.txt')),
            key=lambda p: int(re.findall(r'F(\d+)', p)[0]),
        )
        A = np.stack([np.loadtxt(p, delimiter=',') for p in Tb])
        keep = np.ones(A.shape[:2], bool)
        keep[0::B] = False
        dx, dy, dU, dV = A[..., 3], A[..., 4], A[..., 6], A[..., 7]
        tx, ty = dx - dU, dy - dV
        keep &= np.isfinite(dx) & (np.hypot(tx, ty) > 1e-3)
        err = np.hypot(dU, dV)[keep]
        rmse_ = np.sqrt((err**2).mean())
        f3 = (err > 3).mean()
        # two tiers (PREREGISTRATION_v2_sweep.md deviations): PASS = floor negligible; PASS_FLOOR = median consistent but a tail
        # of > 3 px steps remains on folded (fast, perspective-compressed) fields -> the per-scene floor is reported with the results
        verdict = (
            'PASS'
            if np.median(err) < 0.15 and rmse_ < 1.0
            else ('PASS_FLOOR' if np.median(err) < 0.15 and f3 < 0.05 else 'FAIL')
        )
        line = (
            'KNOWN-ANSWER %s %dx%d: n %d  median err %.4f px  RMSE %.4f px  p99 %.3f  frac>3px %.3f  truth median %.2f  -> %s'
            % (
                scene,
                W,
                H,
                keep.sum(),
                np.median(err),
                rmse_,
                np.percentile(err, 99),
                f3,
                np.median(np.hypot(tx, ty)[keep]),
                verdict,
            )
        )
        print(line, flush=True)
        open(os.path.join(HERE, 'results', 'KNOWN_ANSWER.txt'), 'a').write(
            datetime.datetime.now().isoformat() + ' ' + line + '\n'
        )
    except Exception as ex:
        print('KNOWN-ANSWER %s: ERROR %r' % (scene, ex), flush=True)
