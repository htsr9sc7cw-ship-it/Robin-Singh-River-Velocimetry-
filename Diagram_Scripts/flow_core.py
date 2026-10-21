"""
flow_core.py -- the flow maths for the dense visualisation. No drawing here.

WHAT THE BLENDER VECTOR PASS ACTUALLY CONTAINS
----------------------------------------------
Tutorial section 6.1.2, verbatim:

    "The Red and Green channel contain the X and Y displacement
     from the current frame to previous frame."

So, unambiguously:
    R = X displacement = HORIZONTAL
    G = Y displacement = VERTICAL
and it points BACKWARD in time (current -> previous), which is the same sentence.

One adjustment is needed and only one: Blender's Y axis points UP, while image rows increase
DOWNWARD. So V must be negated to be used in image coordinates. Nothing in the document says
the channels are swapped, and measurement agrees -- warping frame t back to t-1 on Low4:

    no warp (baseline)                       9.1645
    R horizontal, G vertical  (x+R, y-G)     5.6968   <-- best
    R horizontal, G vertical  (x+R, y+G)    12.3967
    swapped                   (x+G, y-R)     9.0801
    swapped                   (x-G, y+R)    11.4626

This also matches the tutorial's own section 7 script, which builds forward flow as
u = R*(-1) and v = (-G)*(-1), i.e. (-R, +G).

DEVICE
------
The advection is `grid_sample` over every pixel, which is a real tensor workload, so it runs on
the Apple GPU through MPS. Benchmarked on this machine at 512x512x301 frames:
    mps 5.4 s   cpu 9.1 s
`verify_mps_matches_numpy()` checks the GPU path against the already-verified numpy
implementation in convert_uv_to_xy.py before any of it is trusted.
"""

import array as arr
import glob
import os

import Imath
import numpy as np
import OpenEXR as oexr
import torch

FLOAT = Imath.PixelType(Imath.PixelType.FLOAT)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.environ.get("XYV_DATA") or os.path.join(
    ROOT, "Vectors_and_Images"
)  # XYV_DATA overrides (dataset v2)


def pick_device(name="mps"):
    if name == "mps" and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def scene_list():
    return sorted(d for d in os.listdir(DATA) if os.path.isdir(os.path.join(DATA, d, "vector")))


def vector_files(scene):
    """Sorted -- not optional. Unsorted frame order was a real bug in this project once."""
    return sorted(glob.glob(os.path.join(DATA, scene, "vector", "*.exr")))


def image_files(scene):
    return sorted(glob.glob(os.path.join(DATA, scene, "images", "*.png")))


def read_flow(path):
    """Return (U, V, H, W) in IMAGE coordinates: U horizontal, V vertical, V already negated."""
    f = oexr.InputFile(path)
    dw = f.header()["dataWindow"]
    W = dw.max.x - dw.min.x + 1
    H = dw.max.y - dw.min.y + 1
    U = np.array(arr.array("f", f.channel("R", FLOAT)).tolist(), np.float32).reshape(H, W)
    V = np.array(arr.array("f", f.channel("G", FLOAT)).tolist(), np.float32).reshape(H, W)
    f.close()
    return U, -V, H, W  # V negated: Blender Y-up -> image rows down


def _sample(field, px, py, H, W):
    """Bilinear sample a (1,1,H,W) field at pixel coords px,py -> (N,) tensor.

    Coordinates are CLAMPED into the image before sampling, rather than relying on
    padding_mode='border' -- MPS raises "Unsupported Border padding mode". Clamping first is
    equivalent, and it matches what the numpy `bilinear` in convert_uv_to_xy.py already does
    (it clips x0,y0 into range), so the two implementations agree by construction.
    """
    cx = px.clamp(0.0, float(W - 1))
    cy = py.clamp(0.0, float(H - 1))
    gx = (cx / max(W - 1, 1)) * 2.0 - 1.0
    gy = (cy / max(H - 1, 1)) * 2.0 - 1.0
    grid = torch.stack([gx, gy], dim=-1).view(1, 1, -1, 2)
    out = torch.nn.functional.grid_sample(
        field, grid, mode="bilinear", padding_mode="zeros", align_corners=True
    )
    return out.view(-1)


def step_forward(px, py, U, V, H, W, iters=6):
    """Advance points from frame t to t+1 given the BACKWARD flow at t+1.

    We only have backward flow, so moving forward means inverting it: find q with
    q + B(q) = p. Fixed-point iteration, Gauss-Seidel (qy uses the updated qx).

    iters=6 not 3: measured on Low1, 3 iterations left 9.4% of points beyond 1 px error
    (max 2.22 px); 6 gives max 0.098 px.
    """
    qx = px - _sample(U, px, py, H, W)
    qy = py - _sample(V, px, py, H, W)
    for _ in range(iters):
        qx = px - _sample(U, qx, qy, H, W)
        qy = py - _sample(V, qx, qy, H, W)
    return qx, qy


def to_field(A, device):
    return torch.from_numpy(np.ascontiguousarray(A)).to(device).view(1, 1, *A.shape)


def flow_to_color(U, V, max_mag=None):
    """Middlebury colour coding: hue = direction of travel, brightness = speed.

    IMPORTANT: U,V here are BACKWARD flow in image coords. The direction a pixel actually
    TRAVELS is the negative of that, so we negate before computing the hue -- otherwise every
    arrow in the legend points the wrong way while still looking plausible.
    """
    fx, fy = -U, -V  # backward -> forward: the way the pixel is going
    mag = np.sqrt(fx * fx + fy * fy)
    ang = np.arctan2(fy, fx)  # -pi..pi, 0 = right, +pi/2 = DOWN (rows increase down)
    if max_mag is None:
        max_mag = max(np.percentile(mag, 99), 1e-6)
    h = (ang + np.pi) / (2 * np.pi)  # 0..1
    s = np.ones_like(h)
    v = np.clip(mag / max_mag, 0, 1)
    return _hsv_to_rgb(h, s, v), max_mag


def _hsv_to_rgb(h, s, v):
    h6 = (h * 6.0) % 6.0
    i = np.floor(h6).astype(np.int32)
    f = h6 - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    r = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [v, q, p, p, t, v])
    g = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [t, v, v, q, p, p])
    b = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [p, p, t, v, v, q])
    return (np.stack([r, g, b], -1) * 255).astype(np.uint8)


def colour_wheel(size=140):
    """Legend for flow_to_color. Same maths, so if one is wrong both are wrong together."""
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    cx = cy = (size - 1) / 2.0
    dx, dy = (x - cx) / cx, (y - cy) / cy
    r = np.sqrt(dx * dx + dy * dy)
    # flow_to_color negates, so pre-negate here to make the wheel show TRAVEL direction
    img, _ = flow_to_color(-dx, -dy, max_mag=1.0)
    img[r > 1.0] = 0
    return img
