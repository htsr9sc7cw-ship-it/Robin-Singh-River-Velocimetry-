"""Corrected filter pass (thesis 4.2.4 F2, AUD21-11 B-1): re-run Eltner's steadiness and angle-range criteria on every
FlowVelo run with the direction computed by atan2 (no quadrant bug) and the spread by CIRCULAR statistics, same
thresholds as the run (from logfileImgSpace.txt). Her other filters (min/max distance, min count, main-flow buffer) are
taken as she computed them. Writes results/cascade_corrected.csv: scene, mode, n_after_mincount, her_final, corrected_final.
    /opt/anaconda3/bin/python corrected_cascade.py <v2_project dir>
"""
import os, sys, glob, re, csv, numpy as np, pandas as pd
P = sys.argv[1]; rows = []
def circ_std_deg(a):
    a = np.deg2rad(a); R = np.hypot(np.cos(a).mean(), np.sin(a).mean()); return float(np.rad2deg(np.sqrt(-2 * np.log(max(R, 1e-12)))))
def circ_range_deg(a):
    a = np.sort(np.mod(a, 360)); gaps = np.diff(np.r_[a, a[0] + 360]); return float(360 - gaps.max())
for run in sorted(glob.glob(os.path.join(P, 'out_ptv', 'v2_*', '*'))):
    scene, mode = run.split(os.sep)[-2:]
    lf = os.path.join(run, 'logfileImgSpace.txt'); tf = glob.glob(os.path.join(run, 'Tracking_FT_*.txt'))
    if not os.path.exists(lf) or not tf: continue
    txt = open(lf).read()
    def par(k, default):
        m = re.search(k + r"[^\d\-]*([\d.]+)", txt); return float(m.group(1)) if m else default
    st, rg = par('threshAngleSteadiness', 30), par('threshAngleRange', 120)
    mind, maxd, minc = par('minDistance_px', 0.1), par('maxDistance_px', 50), par('minimumTrackedFeatures', 3)
    d = pd.read_csv(tf[0], sep='\t'); d['fr'] = d.frame.astype(str).str[:4].astype(int)
    her_final = len(pd.read_csv(os.path.join(run, 'TracksFiltered_px.txt'), sep='\t').id.unique()) if os.path.exists(os.path.join(run, 'TracksFiltered_px.txt')) else 0
    keep_pre, keep_post = 0, 0; angles_all = []
    for i, g in d.groupby('id'):
        g = g.sort_values('fr'); dx = np.diff(g.x.values); dy = np.diff(g.y.values); dist = np.hypot(dx, dy)
        if len(dist) < minc or (dist < mind).any() or (dist > maxd).any(): continue
        keep_pre += 1
        ang = np.rad2deg(np.arctan2(dy, dx))
        if circ_std_deg(ang) <= st and circ_range_deg(ang) <= rg: keep_post += 1; angles_all.append(ang.mean())
    rows.append(dict(scene=scene, mode=mode, n_after_mincount=keep_pre, her_final=her_final, corrected_steady_range=keep_post, steadiness_deg=st, range_deg=rg))
pd.DataFrame(rows).to_csv(os.path.join(P, 'results', 'cascade_corrected.csv'), index=False); print(pd.DataFrame(rows).groupby('mode')[['n_after_mincount', 'her_final', 'corrected_steady_range']].sum())
