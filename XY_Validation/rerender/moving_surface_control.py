"""moving_surface_control.py

Thesis section: see README.md
Inputs: see README.md
Outputs: see README.md

Moving-surface control (AUD21-1 item 3): the surface-only render of dataset v3 is pixel-static; only the composited
tracers move. This control makes the surface texture move WITH the ground truth: every frame f > f0 is the first frame
resampled through the composed backward maps, I'_f(q) = I_f0(q + D_f(q)) with D_{f+1}(q) = D_f(q + B_{f+1}(q)) + B_{f+1}(q)
(one resampling per frame, no blur accumulation); where q + D_f leaves the image the original frame f is used (inflow).
    /opt/anaconda3/envs/pips2/bin/python moving_surface_control.py out/v2/v2_Path4 out/v2/v2_Path4_surfmove
Creates <dst>/{images (warped), vector, forward, gt_particles (symlinks)}; then run synth_tracers.py on <dst>.
"""

import os, sys, glob, numpy as np, cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import flow_core as fc

src, dst = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
os.makedirs(os.path.join(dst, 'images'), exist_ok=True)
for sub in ('vector', 'forward', 'gt_particles'):
    if not os.path.lexists(os.path.join(dst, sub)):
        os.symlink(os.path.join(src, sub), os.path.join(dst, sub))
imgs = sorted(glob.glob(os.path.join(src, 'images', '*.png')))
fnum = lambda p: int(os.path.basename(p)[:4])


def bil(F, x, y):
    H, W = F.shape[:2]
    x = np.clip(x, 0, W - 1.001)
    y = np.clip(y, 0, H - 1.001)
    x0 = np.floor(x).astype(int)
    y0 = np.floor(y).astype(int)
    fx = (x - x0)[..., None]
    fy = (y - y0)[..., None]
    return (
        F[y0, x0] * (1 - fx) * (1 - fy)
        + F[y0, x0 + 1] * fx * (1 - fy)
        + F[y0 + 1, x0] * (1 - fx) * fy
        + F[y0 + 1, x0 + 1] * fx * fy
    )


I0 = cv2.imread(imgs[0]).astype(np.float32)
H, W = I0.shape[:2]
qy, qx = np.mgrid[0:H, 0:W].astype(np.float32)
Dx = np.zeros((H, W), np.float32)
Dy = np.zeros((H, W), np.float32)
cv2.imwrite(os.path.join(dst, 'images', os.path.basename(imgs[0])), I0.astype(np.uint8))
for p in imgs[1:]:
    f = fnum(p)
    U, V, _, _ = fc.read_flow(
        os.path.join(src, 'vector', 'Vector%04d.exr' % f)
    )  # backward flow at f
    Dx = bil(Dx[..., None], qx + U, qy + V)[..., 0] + U
    Dy = bil(Dy[..., None], qx + U, qy + V)[..., 0] + V
    sx, sy = qx + Dx, qy + Dy
    inside = (sx >= 0) & (sx <= W - 1) & (sy >= 0) & (sy <= H - 1) & (np.hypot(U, V) > 1e-4)
    warped = bil(I0, sx, sy)
    orig = cv2.imread(p).astype(np.float32)
    out = np.where(inside[..., None], warped, orig)
    cv2.imwrite(
        os.path.join(dst, 'images', os.path.basename(p)), np.clip(out, 0, 255).astype(np.uint8)
    )
    if f % 50 == 0:
        print('SURFMOVE frame', f, 'inside %.2f' % inside.mean(), flush=True)
print('DONE surfmove', dst)
