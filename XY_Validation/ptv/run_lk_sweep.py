"""Sweep 1 of PREREGISTRATION_v2_sweep.md: LK pyramid depth x template size, her source untouched.

    PTV_OUT=<v2_project>/out_ptv_sweep XYV_DATA=<v2_project>/Vectors_and_Images PTV_PARAMS=<csv> \
    /opt/anaconda3/envs/flowvelo/bin/python run_lk_sweep.py --scene v2_Path4_dense

`maxLevel` is hard-coded (=2) inside featureTracking_functions.performFeatureTrackingLK; it is
overridden here by wrapping cv2.calcOpticalFlowPyrLK as seen from HER module only, so every other
line of her code runs as published. Template size goes through the normal parameter path.
Output: out_ptv_sweep/<scene>/lk_L<maxLevel>_T<template>/ (same files as a tuned_lk run).
"""
import os, sys, argparse, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import run_flowvelo_ptv as drv                      # the headless driver (D1)
import featureTracking_functions as trackF          # hers, on drv's sys.path
import cv2

ap = argparse.ArgumentParser(); ap.add_argument('--scene', required=True)
ap.add_argument('--levels', nargs='*', type=int, default=[2, 3, 4, 5]); ap.add_argument('--templates', nargs='*', default=['tuned', '31', '51'])
a = ap.parse_args()

_orig_lk = cv2.calcOpticalFlowPyrLK
_orig_load = drv.load_params

def load_params(mode, scene):
    """mode = 'lk_L<level>_T<template|tuned>': tuned_lk parameters with the template overridden."""
    m = re.fullmatch(r'lk_L(\d+)_T(\w+)', mode)
    p = _orig_load('tuned_lk', scene)
    if m.group(2) != 'tuned':
        p['template_width'] = p['template_height'] = int(m.group(2))
    p['lk_maxLevel'] = int(m.group(1))                       # recorded in her logfile via the params dump
    return p
drv.load_params = load_params                                 # run_scene resolves the name through its module globals

for L in a.levels:
    def patched(*args, _L=L, **kw):
        kw['maxLevel'] = _L
        return _orig_lk(*args, **kw)
    trackF.cv2.calcOpticalFlowPyrLK = patched
    for T in a.templates:
        tag = 'lk_L%d_T%s' % (L, T)
        row = drv.run_scene(a.scene, tag, False, False)
        print('SWEEP', a.scene, tag, {k: row.get(k) for k in ('n_final', 'seconds', 'error') if k in row}, flush=True)
