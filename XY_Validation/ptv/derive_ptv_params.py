"""Derive per-scene FlowVeloTool parameters FROM THE DATA and write them to ptv_params.csv.

Run with the pips2 interpreter (needs flow_core / OpenEXR):
    /opt/anaconda3/envs/pips2/bin/python derive_ptv_params.py

Why this exists as a separate script: the parameter values are a thesis result in themselves
(Eltner 2020, Sect. 3.5: "the decision about how to set the parameters ... remains challenging").
Keeping the derivation apart from the tracker driver means an auditor can check the numbers
without touching the run, and the run cannot quietly change them.

Every column carries its ORIGIN in the header comment below, as required by audit element #5.

Parameter origins:
  paper   = Eltner, Sardemann & Grundmann (2020), HESS 24, Sect. 2.4.3-2.4.4
  gui     = GUI_FeatureDetectionTracking_v3.py default values
  derived = computed here from the rendered frames and the ground-truth flow, formula given

Flow sign: flow_core.read_flow returns BACKWARD flow in image coordinates (V already negated).
The direction a particle TRAVELS is -(U, V).  Verified in flow_core.flow_to_color and in
verify_xy_convention.py (0.00e+00 error, wrong-sign control 3.5-229.6 px).
"""
import os
import sys
import csv

import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # XY_Validation/  -> flow_core
import flow_core as fc                                # noqa: E402

OUT = os.environ.get('PTV_PARAMS') or os.path.join(HERE, 'ptv_params.csv')
BLIND = os.environ.get('PTV_BLIND') == '1'          # speed prior from the images (phase correlation), not from the GT

# ---- fixed choices, with origin ---------------------------------------------------------
STEADINESS_DEG = 30      # paper 2.4.4 ("30 deg in this study")
RANGE_DEG = 120          # paper 2.4.4 ("here 120 deg")
MAINFLOW_BUFFER_DEG = 30 # paper 2.4.4 ("buffer threshold (here 30 deg)")
MIN_COUNT_PCT = 65       # paper 2.4.4 ("here 65 %")
MIN_DIST_PX = 0.1        # paper 2.4.4 ("0.1 and 10 pixels")
FD_EVERY_FRAC = 0.75     # paper: FD every 15, track 20 -> 0.75
NEIGHBOR_RADIUS = 30     # gui
MAX_NEIGHBORS = 5        # gui
MAX_FEATURES = 3000      # script default (maxFtNbr_FD = 3000)
TRACK_EVERY_NTH = 1      # derived: fast scenes cannot afford skipping frames
BRIGHT_PERCENTILE = 60   # derived: keeps the brighter 40 % of each frame's own histogram
TARGET_FEATURES = 500    # derived: sensitivity swept until GFTT returns at least this many

SAMPLE_FRAMES = 10       # frames used for the flow statistics (spread over the clip)


def flow_stats(scene):
    """Mean forward flow vector and speed percentiles over SAMPLE_FRAMES frames, water only."""
    files = fc.vector_files(scene)
    idx = np.linspace(0, len(files) - 1, SAMPLE_FRAMES).astype(int)
    fx, fy, mags = [], [], []
    for i in idx:
        U, V, H, W = fc.read_flow(files[i])
        m = np.hypot(U, V)
        water = m > 1e-4
        fx.append(-U[water]); fy.append(-V[water]); mags.append(m[water])   # forward = -(U,V)
    fx = np.concatenate(fx); fy = np.concatenate(fy); mags = np.concatenate(mags)
    return (float(fx.mean()), float(fy.mean()), float(mags.mean()),
            float(np.percentile(mags, 95)), float(mags.max()), H, W)


def flow_stats_blind(scene):
    """[AUD21-1 item 2] speed prior WITHOUT the ground truth, the way a practitioner would get it: a coarse first pass —
    up to 200 GFTT features on the equalised frame, 15-px templates matched by normalised cross-correlation in a +-120 px
    search window in the next frame, 10 frame pairs spread over the clip; shifts with NCC > 0.8 kept. Whole-image phase
    correlation was tried first and returned ~0.2 px on every scene because the (static) surface render dominates the
    image — itself a finding, recorded in FIXLOG. Percentiles come from the kept shifts."""
    files = fc.image_files(scene)
    idx = np.linspace(0, len(files) - 2, SAMPLE_FRAMES).astype(int)
    T, R = 15, 120; h = T // 2
    sh = []
    for i in idx:
        a = cv2.equalizeHist(cv2.imread(files[i], 0)); b = cv2.equalizeHist(cv2.imread(files[i + 1], 0)); H, W = a.shape
        g = cv2.goodFeaturesToTrack(a, 200, 0.01, 10)
        if g is None: continue
        for (x, y) in g.reshape(-1, 2):
            x, y = int(x), int(y)
            if x - h < 0 or y - h < 0 or x + h + 1 > W or y + h + 1 > H: continue
            tpl = a[y - h:y + h + 1, x - h:x + h + 1]
            x0, x1 = max(0, x - R - h), min(W, x + R + h + 1); y0, y1 = max(0, y - R - h), min(H, y + R + h + 1)
            res = cv2.matchTemplate(b[y0:y1, x0:x1], tpl, cv2.TM_CCOEFF_NORMED)
            _, mv, _, ml = cv2.minMaxLoc(res)
            if mv > 0.8: sh.append((ml[0] + x0 + h - x, ml[1] + y0 + h - y))
    sh = np.array(sh, float) if sh else np.zeros((1, 2))
    m = np.hypot(sh[:, 0], sh[:, 1])
    return float(np.median(sh[:, 0])), float(np.median(sh[:, 1])), float(np.median(m)), float(np.percentile(m, 95)), float(m.max()), H, W

def image_stats(scene):
    """Brightness percentile and GFTT feature count on the mid-clip frame, with and without
    histogram equalisation (her improve_img option)."""
    files = fc.image_files(scene)
    img = cv2.imread(files[len(files) // 2], 0)
    p60 = float(np.percentile(img, BRIGHT_PERCENTILE))
    eq = cv2.equalizeHist(img)

    def count(im, q):
        g = cv2.goodFeaturesToTrack(im, MAX_FEATURES, q, 10)
        return 0 if g is None else len(g)

    n_default = count(img, 0.002)
    # sweep sensitivity down until enough features on the EQUALISED frame (what the run uses)
    sens = None
    for q in (0.02, 0.01, 0.005, 0.002, 0.001, 0.0005, 0.0002, 0.0001):
        n = count(eq, q)
        if n >= TARGET_FEATURES:
            sens = q
            break
    if sens is None:
        sens = 0.0001
        n = count(eq, sens)
    return float(img.mean()), p60, n_default, sens, n


def main():
    rows = []
    for scene in fc.scene_list():
        mx, my, mean_sp, p95, mx_sp, H, W = flow_stats_blind(scene) if BLIND else flow_stats(scene)
        grey, p60, n_def, sens, n_eq = image_stats(scene)

        # tracking length: a particle should survive the whole track inside the frame
        ft = int(np.clip(round(min(H, W) / max(mean_sp, 1e-3)), 3, 20))
        fd = max(1, int(round(ft * FD_EVERY_FRAC)))
        # NCC: search area is the TOTAL window width in her code -> must cover 2*p95 plus template
        template = int(np.clip(round(mean_sp / 2) * 2 + 1, 7, 31))       # odd, 7..31
        search = int(2 * np.ceil(p95) + template + 2)
        if search % 2 == 0:
            search += 1
        max_dist = float(np.ceil(1.5 * p95))
        min_count = int(ft * (MIN_COUNT_PCT / 100) / TRACK_EVERY_NTH)

        rows.append(dict(
            scene=scene,
            # --- measured ---
            flow_mean_x_px=round(mx, 3), flow_mean_y_px=round(my, 3),
            speed_mean_px=round(mean_sp, 2), speed_p95_px=round(p95, 2), speed_max_px=round(mx_sp, 2),
            grey_mean=round(grey, 1), gftt_at_default=n_def, gftt_at_chosen_eq=n_eq,
            # --- her parameters, derived ---
            minimumThreshBrightness=round(p60, 1),          # derived: p60 of the frame
            sensitiveFD=sens,                               # derived: sweep to >= 500 features
            improve_img=True,                               # derived: her function option, not reachable from the GUI (F8); switched on
            maxFtNbr_FD=MAX_FEATURES,                       # script
            neighborSearchRadius_FD=NEIGHBOR_RADIUS,        # gui
            maximumNeighbors_FD=MAX_NEIGHBORS,              # gui
            template_width=template, template_height=template,   # derived: ~mean speed, odd, 7..31
            search_area_x_CC=search, search_area_y_CC=search,     # derived: 2*p95 + template
            shiftSearchFromCenter_x=int(round(mx * TRACK_EVERY_NTH)),   # derived: mean forward flow
            shiftSearchFromCenter_y=int(round(my * TRACK_EVERY_NTH)),
            FD_everyIthFrame=fd, FT_forNthNberFrames=ft, TrackEveryNthFrame=TRACK_EVERY_NTH,   # derived: FT = frames to cross the frame (3..20), FD = 0.75*FT (paper ratio 15/20)
            minTrackedFeatures_pct=MIN_COUNT_PCT, minimumTrackedFeatures=min_count,   # paper: 65 %; count = int(FT*0.65/TrackEveryNth), her GUI formula
            minDistance_px=MIN_DIST_PX, maxDistance_px=max_dist,    # derived: 1.5*p95
            threshAngleSteadiness=STEADINESS_DEG, threshAngleRange=RANGE_DEG,
            binNbrMainflowdirection=0,                      # gui (0 = use median direction; tutorial: 'should be 0')
            MainFlowAngleBuffer=MAINFLOW_BUFFER_DEG,        # paper
        ))
        r = rows[-1]
        print('%-50s speed %5.1f/%6.1f  bright p60 %5.1f  sens %.4f (%4d feats)  tmpl %2d  search %3d  shift (%+d,%+d)  FT %2d FD %2d  maxd %5.1f'
              % (scene[15:], r['speed_mean_px'], r['speed_p95_px'], r['minimumThreshBrightness'],
                 r['sensitiveFD'], r['gftt_at_chosen_eq'], template, search,
                 r['shiftSearchFromCenter_x'], r['shiftSearchFromCenter_y'], ft, fd, max_dist))

    with open(OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print('\nwrote', OUT)


if __name__ == '__main__':
    main()
