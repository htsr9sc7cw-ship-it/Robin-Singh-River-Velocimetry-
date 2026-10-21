"""PIP_Evaluation_gt.py

Thesis section: 3.5
Inputs: tracker run folder in the PIPs++ layout, ground-truth field
Outputs: per-step tables Trajs_F*.txt and evaluation summary


"""

# 1. IMPORTING LIBRARIES

import numpy as np
import imageio as iio
import OpenEXR as oexr
import array as arr

import matplotlib  # [MAC] Use a non-GUI backend so the 288 frame renders run fast and headless.

matplotlib.use('Agg')

from fnmatch import fnmatch
from matplotlib import animation
from matplotlib import pyplot as plot
from matplotlib.gridspec import GridSpec
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.ticker import FixedLocator
from matrepr import mprint
from multiprocessing import Process, Pool
from os import listdir, mkdir, path, environ, makedirs
from psutil import cpu_count
from re import findall
from scipy.ndimage import zoom
from scipy.interpolate import griddata
from scipy.spatial import cKDTree
from time import time

from os import (
    environ,
)  # [PERF] needed before section 2.1 so MP/worker count can come from the environment.

ST = time()  # Initial time of the code.

# 2. SETTING UP GLOBAL VARIABLES

# 2.1 EXECUTION

MP, C = int(environ.get('PIP_MP', '0')), int(environ.get('PIP_WORKERS', '1'))
_FIX_SIGN = (
    environ.get('PIP_FIX_SIGN', '0') == '1'
)  # [FIX E1] see difference loop                                                                                # MULTIPROCESSING: If you want to use multiprocessing, MP = 1, else, MP = 0. C is related to number of processes to be created (C max = 0 = CPU physical cores).  [MAC: disabled — single process is simpler/safer for the rendering step]
K, S = (
    16,
    16,
)  # DOWNSAMPLING VECTOR'S BACKGROUND: Size of avgpool kernel and stride, to be apllied on too big images. Optional.
B = 1  # DIVISOR: Restrict RAM usage during gif/video creation, dividing the number of images to be processed per B. Optional.
CPU = cpu_count(logical=False)  # Return the number of physical CPU cores on the machine.
P_Data, Backg = (
    'heat',
    'rgbs',
)  # [MAC: background = real river frames (rgbs) instead of 'pips' mp4, which needs ffmpeg/NVIDIA]

if C < 1:  # If setted number of cores is < 1, than use all cores.
    C = CPU
elif (
    1 > C >= CPU
):  # If setted number of cores is on range of cpu cores (except 1), than use C cores.
    pass
elif C > CPU:  # If setted number of cores is > CPU cores, than use all cores.
    C = CPU

# 2.2 PATHS

import sys as _sys  # [HARNESS] this copy lives in XY_Validation/, so the project root must be on

_sys.path.insert(
    0,
    environ.get(
        'PIP_PROJECT'
    )  # sys.path before scene_config (which lives at the root) can be imported.
    or path.dirname(path.dirname(path.abspath(__file__))),
)
import scene_config  # Shared SCENE selector.

PROJECT = environ.get('PIP_PROJECT') or path.dirname(
    path.abspath(__file__)
)  # Project root (overridable: this copy lives in XY_Validation/).
BLENDER = (
    scene_config.SCENE_DIR
)  # Folder with blender's data for the SELECTED scene (has vector/ and images/).

# Auto-detect the most recent COMPLETED PIPs run FOR THE SELECTED SCENE (so multiple scenes
# do not collide). A run is "completed" only if its frames/B0 folder exists.
_tag = 'PIP_Run_%s_48_%d_' % (
    scene_config.SCENE,
    scene_config.N,
)  # match scene AND particle count N
_runs = sorted(
    [
        d
        for d in listdir(path.join(PROJECT, 'Outputs'))
        if d.startswith(_tag) and path.isdir(path.join(PROJECT, 'Outputs', d, 'frames', 'B0'))
    ],
    key=lambda d: path.getmtime(path.join(PROJECT, 'Outputs', d)),
)
if not _runs and not environ.get('PIP_RUN_DIR'):
    raise FileNotFoundError(
        'No COMPLETED run found for scene "%s". Run PIP_Execution.py for this scene first.'
        % scene_config.SCENE
    )
PIP = (
    path.join(PROJECT, 'Outputs', _runs[-1]) if _runs else None
)  # Folder with PIP's output (newest completed run for this scene).
if environ.get(
    'PIP_RUN_DIR'
):  # [2026-09-13] explicit run (parallel scoring: 'newest' is ambiguous)
    PIP = environ['PIP_RUN_DIR']
print('Scene       :', scene_config.SCENE)
print('Using PIPs output:', PIP)
_flags = {
    k: environ.get(k, '<unset>')
    for k in (
        'PIP_FIX_SIGN',
        'PIP_FIX_TRANSPOSE',
        'PIP_GT_MODE',
        'PIP_MP',
        'PIP_SCENE',
        'PIP_N',
        'PIP_NO_PLOTS',
    )
}
print('Evaluator flags:', _flags)  # [AUD10-7 element 3] flag state recorded

Out = environ.get('PIP_EVAL_OUT') or path.join(
    PROJECT, 'Outputs', 'PIP_Eval' + str(path.split(PIP)[1])[7:]  # Folder to dump the output files.
)
# [HARNESS] The original used `if exists(Out): pass else: mkdir(...subdirs)`, so once Out
# itself existed the SUBFOLDERS were never created. That was harmless when Out was only ever
# made by this same block, but breaks as soon as Out is pre-created (as PIP_EVAL_OUT does).
# makedirs(..., exist_ok=True) on each directory is correct either way.
for _d in (
    '',
    '/Images',
    '/Animation',
    '/Tables',
    '/Animation/' + P_Data + '_' + Backg,
    '/Images/' + P_Data + '_' + Backg,
):
    makedirs(Out + _d, exist_ok=True)
with open(Out + '/FLAGS.txt', 'w') as _f:
    _f.write(repr(_flags) + '\n')  # [AUD10-7 element 3]

# 3. FUNCTIONS


def import_from_pip(mode):

    P_For = np.zeros((7))  # Create an new np.array to store PIP's output information.
    P_For = np.loadtxt(PIP + '/frames/Out_Format.txt').astype(
        np.int16
    )  # Loading PIPs output format file.
    P_For = np.insert(
        P_For, 6, (np.multiply(P_For[0], P_For[1]))
    )  # Calculate the number of PIPs frames.

    if mode == 'format':
        return P_For
    elif mode == 'full':
        pass
    else:
        raise ValueError('Incorrect argument for import_from_pip function.')

    a, b, c, d, h, w, e = P_For[
        [0, 1, 2, 3, 4, 5, 6]
    ]  # Get shape informetion about PIP's output data.
    # a = Number of folders.
    # b = Number of frames per folder.
    # c = Number of particles per frame.
    # d and e = PIP's image dimensions (HxW).
    # g = Total of frames.
    P_Vec = np.zeros((e, c, 6))  # Null np.array to storage PIPs positions outputs.

    f = 0
    for i in range(a):  # For all frames blocks...
        PIP_F1 = sorted(
            listdir(PIP + '/frames/B' + str(i)), key=ex_num
        )  # List and store all file paths on the i-block folder, ordered by name.
        for j in range(b):  # For all frames...
            PIP_F2 = path.join(
                PIP + '/frames/B' + str(i), PIP_F1[j]
            )  # Store the file path of j-frame.
            P_Vec[f, :, :] = read_txt(
                PIP_F2, c, w, h
            )  # [FIXLOG C5] signature is (file, c, w, h)                                      # Read the frame file and return the particle's output coordinate data.
            if (
                j == 0
            ):  # If we read the first frame, the displacement in relation of previous frame is zero.
                for k in range(c):
                    P_Vec[f, k, (3, 4, 5)] = (0, 0, 0)
            else:
                for k in range(c):  # For each particle in this frame...
                    P_Vec[f, k, 3] = (
                        P_Vec[f, k, 1] - P_Vec[(f - 1), k, 1]
                    )  # Calculate the displacement variation between this frame and the prior (u and v components).
                    P_Vec[f, k, 4] = P_Vec[f, k, 2] - P_Vec[(f - 1), k, 2]
                    P_Vec[f, k, 5] = np.sqrt(
                        np.square(P_Vec[f, k, (3)]) + np.square(P_Vec[f, k, (4)])
                    )  # Calculating the travelled distance of particle number c.
            f += 1

    return P_Vec, P_For


def read_txt(file, c, w, h):  # Read PIPs '.txt' output files.

    xy = np.zeros((c, 6))  # Creating a empty np.array to store outputs.
    xy[:, 0] = np.arange(
        c
    )  # On zero postion of data axis, enumerate particles, from 0 to c-number of particles.
    xy[:, (1, 2)] = np.loadtxt(
        file, delimiter=','
    )  # Load on 1st and 2nd positions of data axis, the x and y particle position stored on PIP's output txt.
    xy[:, 1] = np.clip(
        xy[:, 1], 0, w - 1
    )  # Limit the value of particles x to be in range (0, W-size of the image).
    xy[:, 2] = np.clip(
        xy[:, 2], 0, h - 1
    )  # Limit the value of particles y to be in range (0, H-size of the image).

    return np.array(xy)


def import_from_blender(mode):

    if mode == 'exr':

        B_Img = []

        # [GT SWITCH] PIP_GT_MODE=uv (default) reads the original displacement EXRs.
        # PIP_GT_MODE=xy reads our converted POSITION EXRs and recovers the displacement
        # with the exact inverse  U = X - x ,  V = -(Y - y).
        # The subtraction is done in FLAT ROW-MAJOR (H,W) order -- the order write_dense
        # used -- and only then reshaped exactly as this script always did. That keeps the
        # correspondence exact even for the non-square scene, where this script's
        # reshape(W, -1) is not the true (H,W) layout.
        _gt_mode = environ.get('PIP_GT_MODE', 'uv')
        _gt_dir = environ.get('PIP_GT_DIR', BLENDER + '/vector')
        for f in sorted(
            listdir(_gt_dir)
        ):  # For all files in the GT directory (sorted so frames align with images)...
            if not f.endswith('.exr'):  # Skip non-exr files (e.g. .DS_Store).
                continue
            file = oexr.InputFile(path.join(_gt_dir, f))  # Open the f-'.exr' file.
            dw = file.header()['dataWindow']  # Get the data window information on file header.
            sz = (
                dw.max.x - dw.min.x + 1,
                dw.max.y - dw.min.y + 1,
            )  # Based on dw data, calculate image dimensions.
            (R, G) = [
                arr.array('f', file.channel(Chan)).tolist() for Chan in ("R", "G")
            ]  # Get the information stored on R and G image bands and store.
            # [FIX b1] sz is (W,H) but the EXR channel buffer is flat ROW-MAJOR (H,W). The original
            # allocated (W,H) and reshaped into it. On a square image that still yields a correctly
            # laid-out array (only the later [x][y] sampling is transposed), but on the 1024x512
            # Overview scene it is a genuine reflow: element [i][j] becomes flat[i*512+j] while the
            # true pixel is flat[r*1024+c]. The array is scrambled BEFORE the resize, so the zoom
            # factors and the w/W, h/H magnitude rescale are then applied inverted as well.
            # Measured on Overview: RMSE 3.187 -> 5.928 (+86%), capture 19.15% -> 10.23%.
            frame = (
                np.zeros((sz[1], sz[0], 2))
                if environ.get('PIP_FIX_TRANSPOSE') == '1'
                else np.zeros((sz[0], sz[1], 2))
            )  # (H,W,2) when fixed; original (W,H,2) otherwise.
            _R = np.array(R, dtype=np.float64)  # Flat, row-major (H,W).
            _G = np.array(G, dtype=np.float64)
            if _gt_mode == 'xy':
                _W, _H = sz[0], sz[1]
                _yy, _xx = np.mgrid[0:_H, 0:_W]
                _R = _R - _xx.ravel().astype(np.float64)  # U = X - x
                _G = -(_G - _yy.ravel().astype(np.float64))  # V = -(Y - y)
            frame[:, :, 0] = _R.reshape(
                frame.shape[0], -1
            )  # Copy R-band information to first data axis slot.
            frame[:, :, 1] = _G.reshape(
                frame.shape[0], -1
            )  # Copy G-band information to second data axis slot.
            B_Img.append(frame)  # Append frame to the frame list.
            file.close  # Close the '.exr' file.

        B_Img = np.array(B_Img)  # Convert the list of np.arrays to an np.array of np.arrays.
        return B_Img
    elif mode == 'iio-1':

        B_Rgbs = []

        for file in sorted(
            listdir(BLENDER + '/images')
        ):  # For all files in Blender's images directory (sorted so they align with frames)...
            if fnmatch(file, '????.png'):
                iframe = path.join(BLENDER + '/images', file)
                img = iio.v3.imread(iframe)
                B_Rgbs.append(img[:, :, 0:3])  # Keep only RGB (drop alpha if present).

        B_Rgbs = np.stack(B_Rgbs, axis=0)
        return B_Rgbs
    elif mode == 'iio-2':

        B_Dept = []

        for file in sorted(
            listdir(BLENDER + '/depths')
        ):  # For all files in Blender's depths directory...
            if fnmatch(file, '????.png'):
                iframe = path.join(BLENDER + '/depths', file)
                B_Dept.append(iio.v3.imread(iframe))

        B_Dept = np.stack(B_Dept, axis=0)
        return B_Dept


def call_resize(images, h, w, order):

    Fr, H, W, _ = images.shape

    if MP == 1 and C != 1:  # If the user agreed with multiprocessing use...

        cpu_dist = np.linspace(
            0, Fr, C + 1
        )  # Calculate an equal number of images to run in C-number of cores.
        func_args = []  # Empty list to store functions arguments.
        for i in range(1, cpu_dist.shape[0]):  # For all image groups...
            func_args.append(
                (
                    images[
                        int(cpu_dist[i - 1]) : int(cpu_dist[i])
                    ],  # Append to a list an sequence of function args to be executed.
                    h / H,
                    w / W,
                    order,
                )
            )

        with Pool(
            processes=C
        ) as pool:  # Creating a process pool, with C-number of process for a C-number of cores.
            results = pool.starmap(scipy_resize, func_args)  # Store results in a list.
            pool.close()  # Close the pool.
            pool.join()  # Wait for all process in the pool to finish.
    elif (
        MP == 0 or (MP == 1 and C == 1) or order == 0
    ):  # If the user not agree with multiprocessing use...

        results = [
            scipy_resize(images, h / H, w / W, order)
        ]  # Apply the zoom on all Ble_Img images and store the result on the list. [MAC fix: pass required 'order' arg]

    results_np = [np.array(i) for i in results]  # Create a list of np.arrays with resized images.
    images_2 = np.concatenate(results_np)  # Create a np.array of np.arrays with resized images.
    images, results, results_np = None, None, None

    return images_2


def scipy_resize(Images, VF, HF, order):  # Resize images using spline interpolation.

    R_Images = []  # Creating a empty list to store images.

    for i in range(
        Images.shape[0]
    ):  # For all blender images that are comparable with PIPs frames...
        R_Images.append(
            zoom(
                Images[i],  # Apply the scipy.zoom function on i-image (Spline interpolation).
                (
                    VF,
                    HF,
                    1,
                ),  # Zoom factor to be applied on image axes (Vertical Factor, Horizontal Factor, Without zoom on data axis).
                order=order,  # Order of spline interpolation (from 0 to 5).
                mode='grid-constant',  # How the image borders will be filled (fill with 0 values).
                grid_mode=True,
            )
        )  # How zoom will be applied in pixel level (pixel center = false, pixel borders = true).

    # R_Images = np.array(R_Images)
    return R_Images


def read_blender_vectors(B_Img, Limit, Reset, use_xy: bool = False, xy=None):

    Fc, H, W, _ = B_Img.shape  # Getting the number of images to process (frame count, Fc).

    if use_xy:

        _, Pc, _ = xy.shape

        if Limit == 0:  # If you want to read all frames from blender folder...

            B_data = np.zeros((Fc, Pc, 3))  # Creating a null vector to store outputs.

            for i in range(Fc):  # For all frames in Ble_Vec...
                if (Fc / Reset) == int:  # If Fc is a multiple of Res...
                    for j in range(Pc):  # For all partciles in Fc frame....
                        B_data[i, j, (0, 1, 2)] = (0, 0, 0)  # Blender data is zero.
                else:
                    for j in range(Pc):
                        # [FIX b2] B_Img is [frame][row=y][col=x]; the original indexed [x][y],
                        # i.e. transposed. Measured: 97-100% of samples read a DIFFERENT pixel,
                        # mean discrepancy 16.8-20.1 px/frame. Also `np.flip` on a 0-d scalar is a
                        # no-op, so the vertical flip it implies never happened -- removed rather
                        # than left in place implying behaviour it never had.
                        x = np.floor(xy[i, j, 1]).astype(
                            np.int32
                        )  # x coordinate of i-frame, j-particle.
                        y = np.floor(xy[i, j, 2]).astype(
                            np.int32
                        )  # y coordinate of i-frame, j-particle.
                        if environ.get('PIP_FIX_TRANSPOSE') == '1':
                            U = np.array(B_Img[i, y, x, 0]).astype(
                                np.float32
                            )  # [row=y][col=x] -- correct.
                            V = np.array(B_Img[i, y, x, 1]).astype(np.float32)
                        else:
                            U = np.array(B_Img[i, x, y, 0]).astype(
                                np.float32
                            )  # original (transposed) behaviour.
                            V = np.array(B_Img[i, x, y, 1]).astype(np.float32)
                        UV = np.sqrt(
                            np.square(U) + np.square(V)
                        )  # Calculating the vectors intensity.
                        B_data[i, j, (0, 1, 2)] = (U, V, UV)  # Storing data.

            return B_data
        elif Limit <= Fc and Limit > 0:  # In case of the limit is user-determined...

            B_data = np.zeros((Limit, Pc, 3))

            for i in range(Limit):  # For all 'Lim' number of frames in Ble_Vec...
                if (Limit / Reset) == int:
                    for j in range(Pc):
                        B_data[i, j, (0, 1, 2)] = (0, 0, 0)
                else:
                    for j in range(Pc):
                        # [FIX b2 - second site] identical defect in the Limit>0 branch.
                        x = np.floor(xy[i, j, 1]).astype(np.int32)
                        y = np.floor(xy[i, j, 2]).astype(np.int32)
                        if environ.get('PIP_FIX_TRANSPOSE') == '1':
                            U = np.array(B_Img[i, y, x, 0]).astype(
                                np.float32
                            )  # [row=y][col=x] -- correct.
                            V = np.array(B_Img[i, y, x, 1]).astype(np.float32)
                        else:
                            U = np.array(B_Img[i, x, y, 0]).astype(
                                np.float32
                            )  # original (transposed) behaviour.
                            V = np.array(B_Img[i, x, y, 1]).astype(np.float32)
                        UV = np.sqrt(np.square(U) + np.square(V))
                        B_data[i, j, (0, 1, 2)] = (U, V, UV)

            return B_data
        else:

            raise ValueError(
                'An incorrect limit value (%s) was entered on read_blender_vectors function.'
                % Limit
            )
    else:

        if Limit == 0:

            B_data = np.zeros((Fc, H, W, 3))

            for i in range(Fc):
                U = np.array(B_Img[i, :, :, 0]).astype(
                    np.float32
                )  # Return the U component of the blender's i-vector image to all pixels.
                V = np.array(B_Img[i, :, :, 1]).astype(
                    np.float32
                )  # Return the V component of the blender's i-vector image to all pixels.
                UV = np.sqrt(np.square(U) + np.square(V))  # Calculating the vectors intensity.
                B_data[i, :, :, (0, 1, 2)] = (U, V, UV)

            return B_data
        elif Limit <= Fc and Limit > 0:

            B_data = np.zeros((Fc, H, W, 3))

            for i in range(Limit):
                U = np.array(B_Img[i, :, :, 0]).astype(np.float32)
                V = np.array(B_Img[i, :, :, 1]).astype(np.float32)
                UV = np.sqrt(np.square(U) + np.square(V))
                B_data[i, :, :, (0, 1, 2)] = (U, V, UV)

            return B_data
        else:

            raise ValueError(
                'An incorrect limit value (Lim) was entered on read_blender_vectors_full function.'
            )


def call_plotter(
    P_Vec, Frame_Stat
):  # [Multiprocessing] Check what we need to plot and call the functions to do that.
    if (
        environ.get('PIP_NO_PLOTS') == '1'
    ):  # [PERF, 2026-09-13] scoring-only runs: Tables are written by main(); the 20 MB of frames + GIF per evaluation are skipped
        print('PIP_NO_PLOTS=1: plotting skipped')
        return

    P_For = import_from_pip('format')  # Get information about the format of PIP's output.
    Fc, Pt, _ = P_Vec.shape  # Defining the number of frames and particles per frame.
    h, w = P_For[[4, 5]]  # Defining the size of image that PIP's used on analysis.

    if Backg == 'rgbs':  # Import the background images (defined by user).
        B_Imgs = import_from_blender('iio-1')
    elif Backg == 'depth':
        B_Imgs = import_from_blender('iio-2')
    elif Backg == 'vector':
        B_Imgs = import_from_blender('exr')
    elif Backg == 'pips':
        video = PIP + '/videos/Run_Full.mp4'
        B_Imgs = iio.v3.imread(video, plugin="pyav")

    if MP == 1 and C != 1:  # If the user agreed with multiprocessing use...

        pplot_d = (
            np.linspace(0, Fc, C + 1).astype(np.int32).tolist()
        )  # [PERF FIX] C+1 points = C chunks (was C points = C-1 chunks, leaving one worker idle). int32 so >32767 frames are safe.                           # Calculate the number of images that will be distributed to the cores to render. Put this in a list.
        pplot_a = []  # Create a empty list to store the future processes arguments.
        for i in range(len(pplot_d)):  # For each group of images to be processed by an core:
            if i == (len(pplot_d) - 1):
                break
            else:
                m = pplot_d[i]  # Begin work on image number m.
                n = pplot_d[i + 1]  # Render until reach image n.
                pplot_a.append(
                    (P_Vec, B_Imgs, Frame_Stat, m, n, h, w)
                )  # Write the necessary arguments, based on what kind of image combination defined.

        # [PERF FIX] was hardcoded Pool(processes=16). macOS uses spawn, so EVERY worker gets a
        # pickled copy of B_Imgs (301x512x512x3 = 237 MB). 16 workers = 3.8 GB on an 8 GB machine,
        # which swaps and runs SLOWER than single-process -- almost certainly why MP was disabled.
        # Bounded by C instead (6 workers = 1.4 GB).
        with Pool(processes=C) as pool:  # One process per configured worker.
            frames = pool.starmap(pip_plotting, pplot_a)  # Distribute tasks.
            pool.close()  # Close processes when their finish the job.
            pool.join()  # Gather results.
    elif MP == 0 or (MP == 1 and C == 1):  # If the user not agreed with multiprocessing use...

        frames = pip_plotting(
            P_Vec, B_Imgs, Frame_Stat, 0, P_Vec.shape[0], h, w
        )  # Write the necessary arguments, based on what kind of image combination defined.

    ts_plotting(Frame_Stat)
    animations(P_Vec.shape[0])
    return


def average_pooling(input_array):  # Visually downsampling images to facilitate visualization.

    H_in, W_in = input_array.shape  # Getting input data dimensions.
    H_pool, W_pool = (H_in - K) // S + 1, (
        W_in - K
    ) // S + 1  # Calculating the new dimensions to downsampled image.
    H_out, W_out = H_pool * K, W_pool * K  # Calculating

    pool_array = np.zeros(
        (H_pool, W_pool)
    )  # Creating a empty array to store the downsampled image.
    up_array = np.zeros((H_out, W_out))  # Creating other empty array to store the output image.

    for i in range(H_pool):  # 2D average pooling.
        for j in range(W_pool):
            start_i = i * S
            start_j = j * S
            end_i = start_i + K
            end_j = start_j + K
            pool_array[i, j] = np.mean(
                input_array[start_i:end_i, start_j:end_j]
            )  # Pool method: mean values.

    up_array = zoom(
        pool_array, K, order=0, mode='grid-constant', grid_mode=True
    )  # Upsampling pooled image without interpolations.

    return up_array, pool_array


def animations(Q):  # Generate animated images outputs.

    Ani_Out = Out + '/Animation'
    Img_Out = Out + '/Images/' + P_Data + '_' + Backg

    if B != 1:
        blocks = np.linspace(0, Q, B).astype(
            np.int16
        )  # Dividing input data to equally sized blocks of data.

        for i in range(0, blocks.shape[0]):  # For all processing blocks, do...

            Frames = []  # Image buffer.

            for f in range(blocks[i], blocks[i + 1] - 1):  # For all image files on block range...
                In_F = iio.v3.imread(
                    Img_Out + '/Render_F' + str(f) + ".png"
                )  # Reading the images to be processed.
                # In_F = zoom(In_F, 3, order = 3)                                            # Uniformly modify the size of the output image. Order = 3 address to use bicubic interpolation. Optional.
                Frames.append(In_F)  # Bufferng images.

        iio.v2.mimsave(Ani_Out + str(i) + ".gif", Frames, duration=0.05)  # GIF generator.
        # iio.v2.mimsave(Ani_Out + str(i) + ".mp4", Frames, fps = 20, **codec)               # Video generator. Optional.
        Frames.clear()
    else:
        # [PERF FIX] The original buffered every decoded frame into a list before writing:
        #     Frames.append(In_F) x288, then mimsave(Frames)
        # At ~1200x800x4 per frame that is roughly 1 GB resident, on a machine with 8 GB that is
        # also running up to 6 render workers. Streaming each frame straight to the writer keeps
        # only one frame in memory and produces a byte-equivalent GIF.
        with iio.v2.get_writer(
            Ani_Out + "Full.gif", duration=0.05
        ) as _w:  # [MAC] GIF generator (no ffmpeg/NVIDIA needed).
            for f in range(0, Q - 1):  # For all image files on input folder...
                _w.append_data(
                    iio.v3.imread(Img_Out + '/Render_F' + str(f) + ".png")
                )  # Read and write one frame at a time.
        print('Saved animation:', Ani_Out + 'Full.gif')
        # (no Frames.clear() here any more -- the streaming writer never builds a list)


def uv_plotting(Vc, Q1, Q2, P):  # Plot U,V visualizations for Blender's vector images.

    _, H, W, _ = (
        Vc.shape
    )  # Getting the input data image dimensions.                                                                                 # Getting the image's dimensions data.

    if K <= 1 or K == None or K <= 0:  # Checking if K is a valid kernel
        dis = 1
    else:
        dis = K / 2

    x = (
        np.linspace(0, H, int(H / K), endpoint=False) + dis
    )  # Creating a vector of equally spaced value in range of image x length.
    y = (
        np.linspace(0, W, int(W / K), endpoint=False) + dis
    )  # Creating a vector of equally spaced value in range of image y length.
    X, Y = np.meshgrid(x, y)  # Creating a vector of image coordinates.

    for p in range(Q1, Q2):

        U1, U2 = average_pooling(
            np.flip(Vc[p, :, :, 0], 0).astype(np.float32)
        )  # Loading the U and V data, and reducing the resolution. U1/V1 is related a upsampled version of average pooled data (U2/V2). Upsampled to original size.
        V1, V2 = average_pooling(np.flip(Vc[p, :, :, 1], 0).astype(np.float32))
        UV = np.sqrt(
            np.square(U1) + np.square(V1)
        )  # Calculating the vectors intensity (U1/V1 - for each point/pixel, background image purpose).
        U2[U2 == 0] = 1e-9  # If a value of U/V are 0, replace for a value not null.
        V2[V2 == 0] = 1e-9
        U2 = -U2 / np.sqrt(
            np.square(U2) + np.square(V2)
        )  # Normalizing the vectors intensity (U2/V2 - for each point, arrows demonstration purpose).
        V2 = V2 / np.sqrt(np.square(U2) + np.square(V2))

        fig, ax = plot.subplots()  # Opening Matplotlib to generate figures.

        # Generating the arrows grid:

        quiver = ax.quiver(
            X,
            Y,  # X and Y coordinates of arrows center.
            U2,
            V2,  # U and V length components of arrows.
            color=(1, 1, 1, 0.2),  # Color of arrows.
            angles='uv',  # How to determine the angle of the arrows.
            pivot='mid',  # Location of pivot point (coordinate's point in relation to arrow point of rotation).
            scale=0.1,  # Size scale of arrows (size = size x 1/scale)
            scale_units='xy',
        )  # Length unit of arrow size.

        # Generating the background image:

        cax = ax.imshow(
            UV,  # Array of values to be gridded (pixel values).
            cmap='cividis',  # Colormap type.
            vmin=0,  # Minimum value to be displayed.
            vmax=300,  # Maximum value to be displayed.
            origin='lower',
        )  # Origin of (0,0).

        # Setting up some additional parameters for plot:

        # Plot configuration
        plot.xlim(0, W)  # Range values for X-axis.
        plot.ylim(0, H)  # Range values for Y-axis.

        # Axis configuration
        ax.set_aspect(1)  # Aspect ratio of axes (1 = square).
        ax.spines[['bottom', 'top', 'right', 'left']].set_color(
            'white'
        )  # Changing the borders colors to white.
        ax.tick_params(axis='both', colors='white')  # Changing the X and Y axes colors to white.

        # Adding a colorbar object
        cbar = plot.colorbar(cax)
        cbar.set_label(
            'Optical Flow (Pixels/Frames)', color='white'
        )  # Setting the name of colorbar and the display color.
        cbar.set_ticks(np.linspace(0, 300, 5))  # Setting the range of colorbar values.
        cbar.outline.set_color('white')  # Color of the colorbar borders.
        cbar.ax.tick_params(
            labelcolor='white', colors='white'
        )  # Changing the colorbar X and Y axes and labels colors to white.

        plot.savefig(
            Bl_Out + str(p) + ".png",  # Name of output filename.
            transparent=True,  # Appying a transparent background.
            dpi=400,
        )  # Output resolution (400dpi = 2560x1920)

        plot.close()


def ts_plotting(tsdata):

    x = np.linspace(0, tsdata.shape[0], tsdata.shape[0])
    y = tsdata[:, (2)]

    fig, ax = plot.subplots()
    ax.plot(x, y, color="red")

    ax.set_xlabel("Frames")
    ax.set_ylabel("UV Deviation")

    plot.savefig(
        Out + '/Images/' + 'Timeseries.png',  # Name of output filename.
        transparent=False,  # Appying a transparent background.
        dpi=400,
    )  # Output resolution (400dpi = 2560x1920)

    plot.close()


def pip_plotting(P_Vec, Back, Frame_Stat, m, n, h, w):  # Plot base PIP's particles visualizations.

    Img_Out = (
        Out + '/Images/' + P_Data + '_' + Backg
    )  # Shortcut to folder where output frames will be dump.

    frames = (
        np.arange(m, n).astype(np.int16).tolist()
    )  # Create a list of frames that will be created (from m to n).

    x, y, cmax, cmin = [], [], [], []  # Create empty lists to store future data.

    # For frame timeseries of means:

    for i in range(Frame_Stat.shape[0]):  # For each frame...
        x.append(i)  # Get frame number.
        y.append(Frame_Stat[i, 2])  # Get the frame mean value.

    ts_x = np.linspace(
        0,
        P_Vec.shape[0],  # Calculate the value for 6 ticks in x direction, based on frame quantity.
        6,
        endpoint=True,
    ).astype(np.int16)
    ts_y = np.linspace(
        np.floor(np.min(y)),
        np.ceil(
            np.max(y)
        ),  # Calculate the value for 4 ticks in y direction, based on metrics values.
        2,
        endpoint=True,
    ).astype(np.int16)
    ts_y = np.append(ts_y, [0])

    # For PIP's visual analysis:

    for i in range(P_Vec.shape[0]):  # For each frame...
        cmax.append(np.max(P_Vec[i, :, 8]))  # Get the maximum value for PIP's particles.
        cmin.append(np.min(P_Vec[i, :, 8]))  # Get the minimum value for PIP's particles.

    cnorm = Normalize(
        vmin=np.min(cmin), vmax=np.max(cmax)
    )  # Normalize the min/max mean values from all frames.

    if P_Data == 'heat':

        x_min, x_max = 0, h - 1
        y_min, y_max = 0, w - 1

        gy, gx = np.mgrid[x_min:x_max, y_min:y_max]
        gxy = np.vstack([gx.ravel(), gy.ravel()]).T
        xy = np.zeros((P_Vec.shape[1], 2))

    # Render:

    for i in frames:  # For each frame in PIP's outputs...

        x2, y2 = [], []  # Create empty lists to store coordinates.

        for j in range(P_Vec.shape[1]):  # For each particle in this frame...
            x2.append(P_Vec[i, j, 1])  # Get x-coordinate.
            y2.append(P_Vec[i, j, 2])  # Get y-coordinate.

        y2 = np.flip(y2)  # Invert y axis.

        fig = plot.figure(
            layout="constrained"
        )  # Matplotlib figure object will be created with certain constraints.
        gs = GridSpec(
            5, 1, figure=fig
        )  # Subdivide figure space in a grid with 5 rows and 1 column.

        # Object 1:

        ax1 = fig.add_subplot(
            gs[0:4, 0]
        )  # Define axis 1 as a figure subplot, contained in rows range 0 to 4, column 0.

        if P_Data == 'part':

            cobj = ax1.scatter(
                x2,
                y2,  # Create a scatter plot object of x and y values (particles coordinates).
                s=4,
                c=P_Vec[i, :, 8],  # What value will define particles colors.
                cmap='inferno',  # Colormap to the values.
                norm=cnorm,  # Normalizated values of colormap (based on min/max values of c)
                marker='o',
            )  # Format of particles marker.

            ax1.imshow(
                Back[i],  # Add the background image (image object).
                interpolation='lanczos',  # Interpolate image to resample, filling all figure canvas (if necessary).
                extent=(-0.5, h - 0.5, -0.5, w - 0.5),
            )  # Limits to plot image (same as canvas, origin on bottom-left).

            cbar = fig.colorbar(
                cobj,  # Create a colorbar object to show color values.
                orientation='horizontal',  # Colorbar will be drawed on horizontal (below image).
                shrink=0.45,  # Reduce colorbar size to match with image size.
                aspect=30,  # Ratio of horizontal:vertical format (30:1).
                pad=0.02,  # Space between colorbar and image above.
                norm=TwoSlopeNorm(vmin=np.min(cmin), vcenter=0, vmax=np.max(cmax)),
                ticks=[np.min(cmin), 0, np.max(cmax)],
            )  # List of ticks to be displayed.
            cbar.ax.tick_params(labelsize=7)  # Set the fontsize of the axis labels.
            cbar.ax.set_title("Particle's UV deviation (Pix/Frame)").set_fontsize(
                'x-small'
            )  # Title and respective fontsize for colorbar.

        if P_Data == 'heat':

            abs_max = max(abs(np.min(cmin)), abs(np.max(cmax)))
            norm = TwoSlopeNorm(vmin=np.min(-abs_max), vcenter=0, vmax=np.max(abs_max))

            for j in range(P_Vec.shape[1]):
                xy[j, (0, 1)] = P_Vec[i, j, (1, 2)]

            z = P_Vec[i, :, 8]
            idw = idw_interpolation(xy, z, gxy)
            idw = idw.reshape(gx.shape)

            # itp = np.where(np.isnan(itp), itp_near, itp)

            cobj = ax1.imshow(
                idw,  # Add the background image (image object).
                extent=(
                    -0.5,
                    h - 0.5,
                    -5.5,
                    w - 0.5,
                ),  # Limits to plot image (same as canvas, origin on bottom-left).
                origin='upper',
                cmap='inferno',
                alpha=0.7,
                norm=cnorm,
            )

            ax1.scatter(
                x2,
                y2,
                s=1,
                color='k',
                marker='o',
            )

            cbar = fig.colorbar(
                cobj, orientation='horizontal', shrink=0.45, aspect=30, pad=0.02, norm=norm
            )
            cbar.set_ticks([-abs_max, 0, abs_max])
            cbar.locator = FixedLocator([-abs_max, 0, abs_max])
            cbar.update_ticks()
            cbar.ax.tick_params(labelsize=7)
            cbar.ax.set_title("Particle's UV deviation (Pix/Frame)").set_fontsize('x-small')

        # ax1.set_title("PIP's Particles Evaluation: UV Displacement (Scene Comparison)")    # Title of first subplot.
        ax1.title.set_fontsize('medium')  # Title's font size
        ax1.set_xlim(0, w)  # Restrict X-axis to W-size of PIP's image.
        ax1.set_ylim(0, h)  # Restrict Y-axis to H-size of PIP's image.
        # ax1.tick_params(left = False, bottom = False,                                      # Remove ticks and labels from axis.
        # labelleft = False, labelbottom = False)

        # Object 2:

        ax2 = fig.add_subplot(
            gs[4, 0]
        )  # Define axis 2 as a figure subplot, contained in row 4, column 0.

        ax2.plot(
            x,
            y,  # Create a simple plot object of x and y values.
            '-',  # This plot will be a line format.
            color='darkblue',  # Line color.
            lw=1,
        )  # Line width.

        ax2.axvline(
            x[i],  # Create a vertical line object.
            ymin=0,  # Minimal point of line: plot's floor.
            ymax=1,  # Maximal point of line: plot's ceil.
            c='k',  # Line color.
            lw=1,
        )  # Line width.

        ax2.axhline(
            0,  # Create a vertical line object.
            xmin=0,  # Minimal point of line: y axis (left).
            xmax=1,  # Maximal point of line: y axis (right).
            c='k',  # Line color.
            lw=1,
        )  # Line width.

        ax2.plot(
            x[i],
            y[i],  # Create a simple plot object of x and y values, from actual frame data.
            'o',  # This plot will be a circle dot.
            c='y',  # Point color.
            markeredgewidth=1,  # Point border width.
            markeredgecolor='k',  # Point border color.
            markersize=3,
        )  # Point size.

        ax2.set_xlim(0, P_Vec.shape[0])  # Define X-axis range limit.
        ax2.set_xlabel('Frames').set_fontsize('x-small')  # Title of X-axis and fontsize.
        ax2.set_xticks(ts_x)  # List of X-axis ticks to be displayed.
        ax2.set_ylim(np.floor(np.min(y)), np.ceil(np.max(y)))  # Define Y-axis range limit.
        ax2.set_ylabel('UV Deviation (Pix/Frame)').set_fontsize(
            'x-small'
        )  # Title of Y-axis and fontsize.
        ax2.set_yticks(ts_y)  # List of Y-axis ticks to be displayed.
        ax2.set_box_aspect(1 / 4)  # Aspect ratio of object 2: 1V/4H
        ax2.tick_params(labelsize=7)  # Axis labels fontsize.

        plot.savefig(
            Img_Out + '/Render_F' + str(i) + '.png',  # Name of output filename.
            transparent=False,  # Appying a transparent background.
            dpi=120,
        )  # [MAC] Lower DPI + fixed frame size (no bbox='tight') so all GIF frames match.

        plot.close()  # Close figure (free memory).

    return


def idw_interpolation(xy, z, xy_grid, power=2):

    tree = cKDTree(xy)
    distances, indices = tree.query(xy_grid, k=5)

    weights = np.zeros_like(distances)

    zero_dist_mask = distances == 0

    weights[~zero_dist_mask] = 1 / (distances[~zero_dist_mask] ** power)
    weights /= weights.sum(axis=1)[:, np.newaxis]

    z_grid = np.zeros(len(xy_grid))
    z_grid[zero_dist_mask[:, 0]] = z[indices[zero_dist_mask[:, 0], 0]]
    z_grid[~zero_dist_mask[:, 0]] = np.sum(
        z[indices[~zero_dist_mask[:, 0]]] * weights[~zero_dist_mask[:, 0]], axis=1
    )

    return z_grid


def ex_num(file):  # Read the number characters in a file name.

    num = findall(r'\d+', file)  # Array-like var to store numbers finded on specified file.
    return int(num[1])


def main():  # Coordinate functions and preprocess input data.

    global C

    print('\nPIPs PARTICLES EVALUATION CODE')
    if MP == 1 and C != 1:
        print('Optimizations for multicore systems is enabled.')
    elif MP == 0 or (MP == 1 and C == 1):
        print('Optimizations for multicore systems is disabled.')

    # 4.1 PIPs DATA PREPROCESSING

    print('\n______')
    print('Importing PIPs data to be preprocessed...')
    print('Looking for files in path ' + PIP)

    t0 = time()
    P_Vec, P_For = import_from_pip('full')
    Fr, Pt, _ = P_Vec.shape  # Defining Fc as the Frame Counter, and Pt the Particle Counter.
    b, h, w = P_For[[1, 4, 5]]
    t1 = time() - t0

    print('\nPIPs output file preprocessing is complete (%.2f seg).' % t1)
    print('PIPs output file have %s frames, with %s particles each.' % (Fr, Pt))

    # 4.2 BLENDER DATA IMPORTING

    print('\n______')
    print('Importing blender information to be analysed...')
    print('Looking for files in path ' + BLENDER + '/vectors')

    t2 = time()
    B_Img = import_from_blender('exr')
    Q, H, W, _ = B_Img.shape  # Getting the number of images to process and their dimensions.
    t3 = time() - t2
    print('\nBlender images have sucefully imported (%.2f seg).' % t3)
    print('The Blender folder has returned %s images, with shape %sx%s.' % (Q, H, W))

    if (H, W) != (h, w):
        print(
            "Blender images have a different size in comparison with that PIP's have used. Proceding to resize them."
        )
        t4 = time()
        B_Img = call_resize(B_Img, h, w, 0)
        # [SCALE FIX] Blender vectors are measured in source-resolution pixels (e.g. 512).
        # PIPs runs at the resized resolution (e.g. 256), so the displacement *values*
        # must be scaled by the same factor as the image, otherwise the comparison is
        # off by ~2x. U scales with width, V scales with height.
        B_Img[:, :, :, 0] *= w / W
        B_Img[:, :, :, 1] *= h / H
        t5 = time() - t4
        print(
            'Images have been sucessfully resized, from %sx%s to %sx%s (%.2f seg).'
            % (H, W, h, w, t5)
        )
        print('Vector magnitudes rescaled by factor %.4f (x) / %.4f (y).' % (w / W, h / H))

    # 4.3 COMPUTING BLENDER'S UV DATA

    print('\n______')
    print('Comparing PIPs and Blender Data...')

    t6 = time()
    B_Vec = read_blender_vectors(
        B_Img,
        Fr,
        b,  # Retrieve speed vectors informations for all images in the Ble_Img_2 np.array.
        use_xy=True,  # Use PIPs particles coordinates as the locations for get speed vectors informations.
        xy=P_Vec[:, :, (0, 1, 2)],
    )  # Specifying where is the xy data.
    t7 = time() - t6
    print('\nBlender scenes was parsed (%.2f seg).' % (t7))

    # 4.4 CALCULATING DIFFERENCES

    t8 = time()

    P_Vec = np.pad(
        P_Vec, ((0, 0), (0, 0), (0, 3)), mode='constant', constant_values=0
    )  # Create an empty fields on P_Vec to store particles new information.
    Frame_Stat = np.zeros((Fr, 3))  # Create an empty np.array to store frames information.

    for i in range(Fr):  # For all frames (Blender and PIPs related)...
        dU_Sum, dV_Sum, dUV_Sum = 0, 0, 0  # Set the initial deviations sum var's as zero.
        for j in range(Pt):  # For all particles on actual frame...
            # [FIX E1] B_Vec holds the BACKWARD Vector pass (R, G); the tracker displacement is
            # FORWARD. With PIP_FIX_SIGN=1 the truth is converted to forward (-R, +G in image
            # rows-down after read) before differencing. Measured: a perfect tracker scored
            # RMSE 34.02 px through the old line and 0.014 px through this one (audit D5 #1).
            if _FIX_SIGN:
                dU = np.subtract(P_Vec[i, j, 3], -B_Vec[i, j, 0])
                dV = np.subtract(P_Vec[i, j, 4], B_Vec[i, j, 1])
            else:
                dU = np.subtract(P_Vec[i, j, 3], B_Vec[i, j, 0])
                dV = np.subtract(P_Vec[i, j, 4], B_Vec[i, j, 1])
            dUV = np.subtract(P_Vec[i, j, 5], B_Vec[i, j, 2])
            P_Vec[i, j, (6, 7, 8)] = (dU, dV, dUV)
            dU_Sum += (
                dU  # Add the particle U difference value to total U differences on this frame.
            )
            dV_Sum += (
                dV  # Add the particle V difference value to total V differences on this frame.
            )
            dUV_Sum += (
                dUV  # Add the particle UV difference value to total UV differences on this frame.
            )
        Frame_Stat[i, (0, 1, 2)] = (
            dU_Sum / Pt,
            dV_Sum / Pt,
            dUV_Sum / Pt,
        )  # Calculate the mean of differences and store it.
        np.savetxt(
            Out
            + '/Tables/Trajs_F'
            + str(i)
            + '.txt',  # Create and save a '.txt' file with particles information on the actual frame.
            P_Vec[i],
            fmt='%.3f',
            delimiter=',',
        )
    t9 = time() - t8

    print('Metrics are evaluated and saved on output folder (%.2f seg).' % (t9))

    # ---- HEADLINE SUMMARY (the numbers to show) -------------------------------------------
    # P_Vec[:,:,6,7,8] = per-particle deviation of PIPs vs Blender in U, V, and magnitude (pixels/frame).
    dU_all = P_Vec[:, :, 6].ravel()
    dV_all = P_Vec[:, :, 7].ravel()
    dUV_all = P_Vec[:, :, 8].ravel()
    rmse = np.sqrt(np.mean(dU_all**2 + dV_all**2))  # Endpoint RMSE (pixels/frame).
    print('\n================ EVALUATION SUMMARY (PIPs vs Blender) ================')
    print(' Frames compared          : %d' % Fr)
    print(' Particles per frame      : %d' % Pt)
    print(' Mean dU  (x-direction)   : %+.3f px/frame   (bias: PIPs minus truth)' % np.mean(dU_all))
    print(' Mean dV  (y-direction)   : %+.3f px/frame' % np.mean(dV_all))
    print(' Mean |deviation|         : %.3f px/frame' % np.mean(np.abs(dUV_all)))
    print(' RMSE (endpoint error)    : %.3f px/frame' % rmse)
    print(' Std of deviation         : %.3f px/frame' % np.std(dUV_all))
    summary_path = Out + '/Tables/SUMMARY.txt'
    with open(summary_path, 'w') as sf:
        sf.write('EVALUATION SUMMARY (PIPs vs Blender)\n')
        sf.write('Frames compared      : %d\n' % Fr)
        sf.write('Particles per frame  : %d\n' % Pt)
        sf.write('Mean dU (x)          : %+.3f px/frame\n' % np.mean(dU_all))
        sf.write('Mean dV (y)          : %+.3f px/frame\n' % np.mean(dV_all))
        sf.write('Mean |deviation|     : %.3f px/frame\n' % np.mean(np.abs(dUV_all)))
        sf.write('RMSE (endpoint)      : %.3f px/frame\n' % rmse)
        sf.write('Std of deviation     : %.3f px/frame\n' % np.std(dUV_all))
    print(' Saved summary file       : %s' % summary_path)
    print('======================================================================\n')
    # --------------------------------------------------------------------------------------

    # 4.5 GENERATING PARTICLES IMAGES

    print('______')
    print('Rendering images and animations...')

    t10 = time()
    print(P_Vec.shape)
    call_plotter(P_Vec, Frame_Stat)
    t11 = time() - t10
    print('\nCamera frames have been sucefully imported (%.2f seg).' % t11)


if __name__ == '__main__':
    main()
