"""Run Anette Eltner's FlowVeloTool (unmodified, latest_version) on the Blender Elbersdorf
scenes in her "Stay in image space" mode, headless.

    /opt/anaconda3/envs/flowvelo/bin/python run_flowvelo_ptv.py --mode tuned_lk --scene all
    /opt/anaconda3/envs/flowvelo/bin/python run_flowvelo_ptv.py --mode tuned_lk --scene path3 --test

What this file is
-----------------
A line-by-line reproduction of GUI_FeatureDetectionTracking_v3.EstimateVelocity() with
stayImgSpace=True, the tkinter widgets replaced by a parameter dict.  The call sequence is
hers: searchMask -> FeatureDetectionPTV -> FeatureTracking -> writeOutput -> FilterTracks,
and the outputs are her files (Tracking_FT_*.txt, TracksFiltered_px.txt, logfileImgSpace.txt).
Her own precedent for running without the GUI is riverReach/FeatureDetectionTracking_riverReach.py
(Eltner et al. 2021, ESPL), which this driver is modelled on.

Her source is imported from ./flowvelo_src, a byte-for-byte copy of
FlowVeloTool-master/python3_version/latest_version (SHA-256 verified, see SHA256_VERIFIED.txt).
NOTHING in that folder is modified.

Modes
-----
  gui_defaults : her GUI v3 default values, all scenes (control run: what happens untuned)
  tuned_lk     : per-scene parameters from ptv_params.csv, Lucas-Kanade with initial estimates
  tuned_ncc    : per-scene parameters, normalised cross-correlation + sub-pixel (her paper's method)

Deviations from her GUI path, each deliberate and documented
------------------------------------------------------------
[D1] Feature detection is called through detectF.featureDetection(..., improve_img=True) for the
     tuned modes, because ptv.FeatureDetectionPTV hard-codes improve_img=False as its last
     argument, so the GUI can never switch histogram equalisation on.  The ten lines of ID
     bookkeeping after detection are copied from FeatureDetectionPTV verbatim.  gui_defaults
     uses FeatureDetectionPTV itself (improve_img off), exactly as the GUI would.
[D2] The images folder handed to her code is a PNG-only folder of symlinks, because her
     read_imgs_folder has `if '.jpg' or '.png' in f` (always true) and the scene folders contain
     a Thumbs.db.  FIXLOG F4.
[D3] savePlotData is False for full runs (her draw_tracks runs 8x per scene at dpi 600 with a
     Python loop per arrow); True for --figures scenes so her own plots exist for the thesis.
[D4] Her FeatureTracking always writes a temppFT*.jpg per frame pair (not gated by any flag);
     it is left to do so, into the output folder.
"""
import os, re
import sys
import csv
import time
import glob
import argparse

import numpy as np
import pandas as pd
import cv2
import matplotlib
matplotlib.use('Agg')

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'flowvelo_src')
sys.path.insert(0, SRC)
import photogrammetry_functions as photogrF   # noqa: E402  (hers)
import input_output_functions as ioF          # noqa: E402  (hers)
import featureDetect_functions as detectF     # noqa: E402  (hers)
import PTV_functions as ptv                   # noqa: E402  (hers)

ROOT = os.path.dirname(os.path.dirname(HERE))                        # THESIS ORIGINAL
DATA = os.environ.get('XYV_DATA') or os.path.join(ROOT, 'Vectors_and_Images')      # XYV_DATA -> dataset v2
OUT = os.environ.get('PTV_OUT') or os.path.join(os.path.dirname(HERE), 'out', 'ptv')
IOR_FILE = os.path.join(HERE, 'interiorGeometry_blender.txt')
PARAMS_CSV = os.environ.get('PTV_PARAMS') or os.path.join(HERE, 'ptv_params.csv')
FRAMES_ROOT = os.path.join(HERE, 'frames_pngonly')
MASK_ROOT = os.path.join(HERE, 'masks')

# Her GUI v3 defaults, transcribed from GUI_FeatureDetectionTracking_v3.py __init__ (.set(...))
GUI_DEFAULTS = dict(
    maxFtNbr_FD=1000, minimumThreshBrightness=70, neighborSearchRadius_FD=30,
    maximumNeighbors_FD=5, sensitiveFD=0.02, improve_img=False,
    template_width=7, template_height=7, search_area_x_CC=24, search_area_y_CC=24,
    shiftSearchFromCenter_x=0, shiftSearchFromCenter_y=8, subpixel=False, performLSM=False,
    FD_everyIthFrame=10, FT_forNthNberFrames=20, TrackEveryNthFrame=2,
    minTrackedFeatures_pct=66, minDistance_px=2, maxDistance_px=50,
    threshAngleSteadiness=25, threshAngleRange=90, binNbrMainflowdirection=0,
    MainFlowAngleBuffer=10, lk=True, initialLK=False,
)
# constants she hard-codes in EstimateVelocity
THRESH_LSM = 0.001
LSM_BUFFER = 3


def scene_list():
    return sorted(d for d in os.listdir(DATA) if os.path.isdir(os.path.join(DATA, d, 'vector')))


def prepare_inputs(scene):
    """PNG-only frames folder (symlinks) and an all-white AoI mask. Idempotent."""
    fdir = os.path.join(FRAMES_ROOT, scene) + '/'
    os.makedirs(fdir, exist_ok=True)
    src = sorted(glob.glob(os.path.join(DATA, scene, 'images', '*.png')))
    for p in src:
        dst = os.path.join(fdir, os.path.basename(p))
        if not os.path.lexists(dst):
            os.symlink(p, dst)
    os.makedirs(MASK_ROOT, exist_ok=True)
    h, w = cv2.imread(src[0], 0).shape                                # Overview is 1024x512 (audit D5 #9)
    mask = os.path.join(MASK_ROOT, 'full_frame_%dx%d.png' % (w, h))
    if not os.path.exists(mask):
        cv2.imwrite(mask, np.full((h, w), 255, np.uint8))
    ior = os.path.join(HERE, 'interiorGeometry_blender_%dx%d.txt' % (w, h))
    if not os.path.exists(ior):                                       # square pixels: sensor scaled with the frame
        open(ior, 'w').write('1 blender_pinhole 50.0 0 0 0 0 0 0 0 0 0 0 %.3f %.3f %d %d' % (36.0, 36.0 * h / w, w, h))
    return fdir, mask, src, ior


def load_params(mode, scene):
    # [REINIT-1, PREREGISTRATION_v2_reinit.md] mode suffix _fd<k> (e.g. tuned_ncc_fd1) = same parameters, but a fresh
    # feature batch every k frames instead of 0.75*FT (matched re-detection cadence for the re-initialised PIPs++ runs)
    fd_override = None
    m = re.match(r'^(.*)_fd(\d+)$', mode)
    if m:
        mode, fd_override = m.group(1), int(m.group(2))
    p = _load_params_base(mode, scene)
    if fd_override is not None:
        p['FD_everyIthFrame'] = fd_override
    return p


def _load_params_base(mode, scene):
    if mode == 'gui_defaults':
        return dict(GUI_DEFAULTS)
    df = pd.read_csv(PARAMS_CSV)
    r = df[df.scene == scene].iloc[0]
    p = dict(
        maxFtNbr_FD=int(r.maxFtNbr_FD), minimumThreshBrightness=float(r.minimumThreshBrightness),
        neighborSearchRadius_FD=int(r.neighborSearchRadius_FD), maximumNeighbors_FD=int(r.maximumNeighbors_FD),
        sensitiveFD=float(r.sensitiveFD), improve_img=bool(r.improve_img),
        template_width=int(r.template_width), template_height=int(r.template_height),
        search_area_x_CC=int(r.search_area_x_CC), search_area_y_CC=int(r.search_area_y_CC),
        shiftSearchFromCenter_x=int(r.shiftSearchFromCenter_x), shiftSearchFromCenter_y=int(r.shiftSearchFromCenter_y),
        performLSM=False,
        FD_everyIthFrame=int(r.FD_everyIthFrame), FT_forNthNberFrames=int(r.FT_forNthNberFrames),
        TrackEveryNthFrame=int(r.TrackEveryNthFrame),
        minTrackedFeatures_pct=float(r.minTrackedFeatures_pct),
        minDistance_px=float(r.minDistance_px), maxDistance_px=float(r.maxDistance_px),
        threshAngleSteadiness=float(r.threshAngleSteadiness), threshAngleRange=float(r.threshAngleRange),
        binNbrMainflowdirection=int(r.binNbrMainflowdirection), MainFlowAngleBuffer=float(r.MainFlowAngleBuffer),
    )
    # [F7] no ground-truth-derived shift in any mode: a failed LK returns the seed and passes her
    # backward check with zero error (47.9 % of sub-steps were exactly the seed on Path3)
    p.update(shiftSearchFromCenter_x=0, shiftSearchFromCenter_y=0)
    if mode == 'tuned_lk':
        p.update(lk=True, initialLK=False, subpixel=False)
    elif mode == 'tuned_ncc':
        p.update(lk=False, initialLK=False, subpixel=True)
    else:
        raise ValueError(mode)
    return p


def detect_with_equalisation(dir_imgs, img_list, frameCount, p, searchMask, savePlotData,
                             directoryOutput, first_loop, feature_ID_max):
    """[D1] Same as ptv.FeatureDetectionPTV but with improve_img=True. Body copied from hers."""
    featuresToTrack = detectF.featureDetection(dir_imgs, img_list[frameCount], searchMask,
                                               p['minimumThreshBrightness'], p['neighborSearchRadius_FD'],
                                               p['maximumNeighbors_FD'], p['maxFtNbr_FD'], p['sensitiveFD'],
                                               savePlotData, directoryOutput, True)
    feature_ID = np.array(range(featuresToTrack.shape[0]))
    if first_loop:
        feature_ID_max = featuresToTrack.shape[0] + 1
        first_loop = False
    else:
        feature_ID = feature_ID_max + feature_ID
        feature_ID_max = feature_ID_max + featuresToTrack.shape[0] + 1
    featuresToTrack_id = np.hstack((feature_ID.reshape(-1, 1), featuresToTrack[:, 1].reshape(-1, 1)))
    featuresToTrack = np.hstack((featuresToTrack_id, featuresToTrack[:, 0].reshape(-1, 1)))
    print('nbr features detected: ' + str(featuresToTrack.shape[0]) + '\n')
    with open(os.path.join(directoryOutput, 'FD_every_' + str(p['FD_everyIthFrame']) + '_' +
                           img_list[frameCount][:-4]) + '.txt', 'w') as fh:
        w = csv.writer(fh, delimiter='\t'); w.writerow(['id', 'x', 'y']); w.writerows(featuresToTrack)
    return featuresToTrack, first_loop, feature_ID_max


def run_scene(scene, mode, test_run=False, save_plots=False):
    t0 = time.time()
    p = load_params(mode, scene)
    dir_imgs, AoI_file, src_frames, ior_file = prepare_inputs(scene)
    directoryOutput = os.path.join(OUT, scene, mode + ('_test' if test_run else '')) + '/'
    os.makedirs(directoryOutput, exist_ok=True)
    img_name = src_frames[len(src_frames) // 2]                     # for visualisation
    savePlotData = save_plots

    # ---- exactly her EstimateVelocity from here on ------------------------------------
    minTrackedFeatures = int(p['FT_forNthNberFrames'] * (p['minTrackedFeatures_pct'] / 100) / p['TrackEveryNthFrame'])
    interior_orient = photogrF.read_aicon_ior(ior_file)
    img_list = ioF.read_imgs_folder(dir_imgs)
    print('all input data read\n------------------------------------------')

    eor_mat = None
    searchMask = ptv.searchMask(np.nan, np.nan, AoI_file, [], None, interior_orient, eor_mat,
                                savePlotData, directoryOutput, img_list, True, img_name)

    frameCount = 0
    imagesForGif = []
    trackedFeaturesOutput_undist = []
    first_loop = True
    feature_ID_max = None
    FT = p['FT_forNthNberFrames']

    if test_run and len(img_list) > 20:
        lenLoop = 20
    elif len(img_list) > FT + 1:
        lenLoop = len(img_list) - FT - 1
    else:
        lenLoop = 1

    n_detect_calls = 0
    while frameCount <= lenLoop:
        if frameCount % p['FD_everyIthFrame'] == 0:
            if first_loop:
                feature_ID_max = None
            if p['improve_img']:
                featuresToTrack, first_loop, feature_ID_max = detect_with_equalisation(
                    dir_imgs, img_list, frameCount, p, searchMask, savePlotData, directoryOutput,
                    first_loop, feature_ID_max)
            else:
                featuresToTrack, first_loop, feature_ID_max = ptv.FeatureDetectionPTV(
                    dir_imgs, img_list, frameCount, p['minimumThreshBrightness'], p['neighborSearchRadius_FD'],
                    searchMask, p['maximumNeighbors_FD'], p['maxFtNbr_FD'], p['sensitiveFD'], savePlotData,
                    directoryOutput, p['FD_everyIthFrame'], first_loop, feature_ID_max)
            n_detect_calls += 1
            trackedFeaturesOutput_undist, imagesForGif = ptv.FeatureTracking(
                p['template_width'], p['template_height'], p['search_area_x_CC'], p['search_area_y_CC'],
                p['shiftSearchFromCenter_x'], p['shiftSearchFromCenter_y'],
                frameCount, FT, p['TrackEveryNthFrame'], dir_imgs, img_list, featuresToTrack, interior_orient,
                p['performLSM'], LSM_BUFFER, THRESH_LSM, p['subpixel'], trackedFeaturesOutput_undist,
                False, imagesForGif, directoryOutput, p['lk'], p['initialLK'])
        frameCount += 1

    ioF.writeOutput(trackedFeaturesOutput_undist, FT, p['FD_everyIthFrame'], directoryOutput)
    t_track = time.time() - t0

    cascade = None
    try:
        filteredFeatures, cascade = ptv.FilterTracks(
            trackedFeaturesOutput_undist, img_name, directoryOutput,
            p['minDistance_px'], p['maxDistance_px'], minTrackedFeatures,
            p['threshAngleSteadiness'], p['threshAngleRange'],
            p['binNbrMainflowdirection'], p['MainFlowAngleBuffer'], False)
        n_final = int(np.unique(filteredFeatures.id).shape[0]) if len(filteredFeatures) else 0
    except Exception as e:                       # her FilterTracks raises on empty input
        print('FilterTracks failed:', repr(e))
        n_final = 0
    t_total = time.time() - t0

    # her logfileImgSpace.txt (same keys as the GUI writes), plus timing and our provenance
    log_file_writer, logfile = ioF.logfile_writer(directoryOutput + 'logfileImgSpace.txt')
    log_file_writer.writerow([['test run: ', test_run], ['mode: ', mode], ['scene: ', scene]] +
                             [[k + ': ', v] for k, v in p.items()] +
                             [['minimumTrackedFeatures: ', minTrackedFeatures],
                              ['n_detect_calls: ', n_detect_calls],
                              ['n_rows_tracking_file: ', len(trackedFeaturesOutput_undist)],
                              ['filter cascade [raw,mindist,maxdist,mincount,steady_deg,steady,range_deg,range,flowdir_deg,flowdir]: ', cascade],
                              ['n_final_tracks: ', n_final],
                              ['seconds_tracking: ', round(t_track, 1)], ['seconds_total: ', round(t_total, 1)],
                              ['ior_file: ', ior_file], ['params_csv: ', PARAMS_CSV],
                              ['flowvelo_src_sha: ', 'see flowvelo_src/SHA256_VERIFIED.txt']])
    logfile.flush(); logfile.close()

    summary = dict(scene=scene, mode=mode, test_run=test_run, n_detect_calls=n_detect_calls,
                   n_rows=len(trackedFeaturesOutput_undist), n_final=n_final,
                   cascade=cascade, seconds_tracking=round(t_track, 1), seconds_total=round(t_total, 1))
    print('SUMMARY', summary)
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', required=True, help='gui_defaults | tuned_lk | tuned_ncc, optionally with _fd<k> (fresh features every k frames)')
    ap.add_argument('--scene', default='all', help="'all' or a substring of the scene name")
    ap.add_argument('--test', action='store_true', help='her test_run: first 20 frames only')
    ap.add_argument('--plots', action='store_true', help='her savePlotData (slow)')
    a = ap.parse_args()

    scenes = scene_list()
    if a.scene != 'all':
        exact = [s for s in scenes if s.lower() == a.scene.lower()]                   # [REINIT-1] exact name wins over substring
        scenes = exact or [s for s in scenes if a.scene.lower() in s.lower()]
    rows = []
    for s in scenes:
        try:
            rows.append(run_scene(s, a.mode, a.test, a.plots))
        except Exception as e:
            import traceback; traceback.print_exc()
            rows.append(dict(scene=s, mode=a.mode, test_run=a.test, error=repr(e)))
    os.makedirs(OUT, exist_ok=True)
    tag = a.mode + ('_test' if a.test else '')
    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'RUN_SUMMARY_%s.csv' % tag), index=False)
    print('\n' + pd.DataFrame(rows).to_string())


if __name__ == '__main__':
    main()
