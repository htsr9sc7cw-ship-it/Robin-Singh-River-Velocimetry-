"""PIP_Execution.py

Thesis section: see README.md
Inputs: see README.md
Outputs: see README.md


"""

# 1. IMPORTING LIBRARIES
# List of packages to be imported, in order to execute the PIPs model.

import time, os, datetime, torch, math, imageio, cv2
import utils.improc, saverloader

import numpy as np
import scene_config

device = scene_config.DEVICE  # 'mps' (Apple GPU) if available, else 'cpu'
import torch.nn.functional as F
import torchvision.io as tio
import fnmatch as fm

from nets.pips2 import Pips
from tensorboardX import SummaryWriter
from PIL import Image

# published PIPs++ checkpoint: ./reference_model if present, else the folder next to the project folder
REFERENCE_MODEL = './reference_model' if os.path.isdir('./reference_model') else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'reference_model')

# 2. DEFINING FUNCIONS
# Special functions to perform specific tasks in our code.

# 2.1 READ FRAMES FROM A VIDEO
# When a video file is specified, this reads the frames and stores/return a list with them.


def read_video(fn):  # Variables: file name (fn).
    vidcap = cv2.VideoCapture(
        fn
    )  # Capturing video frames with OpenCV. That is a CPU based function.
    frames = []  # Defining frame as an empty list.
    while vidcap.isOpened():  # While the cv2.VideoCapture is doing his job...
        ret, frame = (
            vidcap.read()
        )  # The cv2.VideoCapture.read combines 2 functions, the .grab() to capture images, and .ret() to return Boolean information about if no valid image was retrieved.
        if ret == False:  # If no valid frame was been retrieved, than...
            break  # End loop.
        frames.append(frame)  # Else, append the frame on the list.
    vidcap.release()  # End the reading function.
    return frames  # Return the list of frames.


# 2.2 READ FRAMES FROM A IMAGE DATASET
# When a folder with a sequence of images is specified, this reads the images on a specific format and extension, and stores/return a list with them.


def read_images(
    fn, fheader, ftype
):  # Variables: folder name (fn), name format of images (fheader), images extension (ftype).
    frames = []  # Defining frame as an empty list.
    for ifile in sorted(
        os.listdir(fn)
    ):  # [FIX P1] SORTED: os.listdir order is arbitrary on APFS; every v1 run used shuffled frames (Outputs/Audit/AUDIT_F1_DEFINITIVE.txt)
        if fm.fnmatch(
            ifile, f'{fheader}{ftype}'
        ):  # If the name of image matches with specified format and extension...
            iframe = os.path.join(fn, ifile)  # Define iframe as the full path of the file.
            # img = Image.open(iframe)
            # frames.append(img.rotate(270))
            frames.append(imageio.v3.imread(iframe))  # Append the path on the list of frames.
    return frames  # Return the list of frames.


# 2.3 PIP'S PROCESSING FUNCTION
# We can divide this function in three parts:
#   01: Grid creation: calculate the coordinates of the particle's grid, and define as initial point.
#   02: Inference runtime: based on given checkpoint, run the neural networks to predict wherw the particles are moving on image.
#   03: Visualization: create frames for visual particle tracking.


def run_model(model, rgbs, S_max, N, iters, gs):
    print('Actual Step: ' + str(gs))
    rgbs = rgbs.to(
        device
    ).float()  # Tensor.cuda creates a copy of object on cuda GPU memory. If the tensor is already on GPU, just return the object. Tensor format: float32 (torch.Tensor.float). Tensor: B, S, C, H, W

    B, S, C, H, W = (
        rgbs.shape
    )  # B(ase dimension = 1), S(equence frames length), C(hannels of the image), H(eight), W(idth).
    assert B == 1  # Ensuring that B = 1.

    N_ = (
        np.sqrt(N).round().astype(np.int32)
    )  # Rounding the N(umber of points to track) square root, with format int32.
    grid_y, grid_x = utils.basic.meshgrid2d(
        B, N_, N_, stack=False, norm=False, device=device
    )  # Creating a 2D mesh of tensors, with size N_ x N_.
    grid_y = 8 + grid_y.reshape(B, -1) / float(N_ - 1) * (
        H - 16
    )  # Adjusting the Y grid coordinates to match the center of spatial stride pixels on image.
    grid_x = 8 + grid_x.reshape(B, -1) / float(N_ - 1) * (
        W - 16
    )  # Adjusting the X grid coordinates to match the center of spatial stride pixels on image.
    xy0 = torch.stack(
        [grid_x, grid_y], dim=-1
    )  # Stacking grids. Format of initial tensor: B, N_*N_, 2.
    # [AUD21-1 item 1] feature-seeded variant: PIP_SEEDS=<dir of FlowVelo FD_every_*.txt> -> seeds = the GFTT features FlowVelo
    # detected at the nearest detection frame <= the block's first frame (native px -> working px); sampled to N (with
    # replacement only if fewer than N were detected). Grid seeding is the default and unchanged.
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
    _, S, C, H, W = rgbs.shape

    trajs_e = xy0.unsqueeze(1).repeat(1, S, 1, 1)  # Setting up the initial velocities as 0.

    iter_start_time = time.time()  # Time on begin of inference.

    preds, preds_anim, _, _ = model(
        trajs_e, rgbs, iters=iters, feat_init=None, beautify=True
    )  # Calling the inference function.
    trajs_e = preds[
        -1
    ]  # The estimatives for trajectory on actual step, is the last prediction iteration returned by PIPs.

    iter_time = (
        time.time() - iter_start_time
    )  # Counting the process run time: Actual time - Initial time.
    print('Inference time: %.2f seconds (%.1f fps)' % (iter_time, S / iter_time))

    return trajs_e  # Returning the estimatives for trajectories.


# 3. MAIN FUNCTION


def main(
    # Define all parameters for run the model:
    filename=scene_config.IMAGES_DIR,  # Path to the input data (images of the selected SCENE).
    outputname="PIP_Run_"
    + scene_config.SCENE
    + os.environ.get(
        "PIP_RUN_SUFFIX", ""
    ),  # The name of output file (includes the scene name; suffix e.g. _fseed for the feature-seeded variant).
    S=48,  # Determine the number of frames that will be analyzed in a given step.
    N=scene_config.N,  # Determine the number of particles that will be tracked (set in scene_config.py / PIP_N env var).
    stride=8,  # Spatial stride of the model (pixels).
    timestride=1,  # Temporal stride of the model (frames).
    iters=16,  # Number of inference steps.
    image_size=(
        256,
        256,
    ),  # You can select any image size, the model will resize the input data to match that format.
    max_iters=0,  # The number of inference steps. If you want to run all the video, define this as 0.
    shuffle=False,  # Dataset shuffling.
    log_freq=1,  # How frequently the output image summary will be wrote?
    out_dir='./Outputs',  # Folder to store the outputs.
    init_dir=REFERENCE_MODEL,  # Folder with model's checkpoint.
    device_ids=[0],  # IDs of computation devices.
):

    # Pre-processing the dataset, matching PIPs format.

    # exp_name = 'Testes'                                    # Export suffix.
    print("Model's name:", outputname)
    # torch.cuda.empty_cache() — not needed on CPU
    rgbs = read_images(filename, "????", ".png")  # Reading frames from a sequence of images.
    # rgbs = read_video(filename)                            # Reading frames from a video.
    rgbs = np.stack(rgbs, axis=0)  # S(equence),H(eight),W(idth),3(bands).
    # rgbs = rgbs[:,:,:,::-1].copy()                         # Copies the original arrays on BGR space, in a reverse way, leading to RGB space.
    rgbs = rgbs[
        :, :, :, 0:3
    ].copy()  # Copies the original arrays on RGB space, excluding the 4th image channel (alpha?).
    rgbs = rgbs[
        ::timestride
    ]  # Slices the array from begin to the end, on a step equal to timestride.
    S_here, H, W, C = rgbs.shape  # S_here: actual sequence length
    NSq = round(math.sqrt(N))  # Rounded square root of number of tracking points (N).
    print('Input data format:', rgbs.shape)

    # Configuring how the model will write the output files, togheter with the tensorboardX Summary Writer.

    model_name = "%s_%d_%d" % (
        outputname,
        S,
        N,
    )  # , exp_name)                     # %s: string format (name and exp_name), %d: integer format (S and N).
    model_date = datetime.datetime.now().strftime(
        '%d_%m_%Y_%H_%M'
    )  # Copy the actual time in H:M:S format.
    model_name = model_name + '_' + model_date  # Concatenate names.
    output_dir = os.path.join(
        out_dir, model_name
    )  # The output place will be a folder with name 'model_name', inside the 'out_dir' folder.
    os.makedirs(os.path.join(output_dir, 'frames'), exist_ok=True)
    print('Summary Name:', model_name)

    # Initialize the PIPs NN last checkpoint from file (if exists), and lock the parameters to use on inference.

    model = Pips().to(
        device
    )  # Initiate the PIPs model, and move all parameters related to cuda's device.
    parameters = list(
        model.parameters()
    )  # The model's parameters list. These are tensors, in which values will be learned/upgraded during neural network training.
    if init_dir:  # If init_dir is not false, aka, user specified a path to...
        ckpt_path = next(
            os.path.join(init_dir, f) for f in os.listdir(init_dir) if f.endswith('.pth')
        )
        checkpoint = torch.load(ckpt_path, map_location='cpu', weights_only=False)
        model.load_state_dict(checkpoint['model_state_dict'], strict=False)
        print('Loaded checkpoint:', ckpt_path)
    model.eval()  # Put the model on evaluation mode, aka, disabling the gradients computaion (neural processing).

    # Setting up some variables that will be usefull during the inference loop.

    global_step = 0  # Setting the step marker to be on zero point.
    idx = list(
        range(0, max(S_here - S, 1), S)
    )  # Range will return a sequence of integer values, starting from start (first arg, inclusive), until stop (second arg, exclusive), on a step defined by the third arg. List will construct a series of range values.
    print('Range values:', idx)
    if max_iters:  # If max_iters was defined, than...
        idx = idx[:max_iters]  # Slice idx list by the maximum number of interations.
    print('Steps to compute:', len(idx))

    full_trajs_tensor = torch.empty(
        [0, S, NSq * NSq, 2], dtype=torch.float32, device=device
    )  # Creating a empty tensor, with the same dimensions of the output trajectories tensors, to stack them.

    # Inefernce loop.

    for si in idx:
        global_step += 1  # Add 1 on steps counter
        iter_start_time = (
            time.time()
        )  # Return the current time in seconds, since some epoch. If the epoch is not given, consider 01-01-1970, 0:00.

        rgb_seq = rgbs[
            si : si + S
        ]  # Actual sequence of images, starting on frame si, until the frame si+S (sequence length).
        rgb_seq = (
            torch.from_numpy(rgb_seq).permute(0, 3, 1, 2).to(torch.float32).to(device)
        )  # torch.from_numpy will create a tensor from the refered numpy array. torch.permute will change the positions of tensor elements: S,H,W,3 -> S,3,H,W. torch.Tensor.to will return the tensor in that specific data format.
        rgb_seq = F.interpolate(rgb_seq, image_size, mode='bilinear').unsqueeze(
            0
        )  # torch.nn.functional.interpolate will down/up sample the input image (rgbs), to size defined on image_size, with bilinear technique. torch.unsqueeze will add a unitary dimension on tensor, at position 0: S,3,H,W -> 1,S,3,H,W

        with torch.no_grad():  # Disabling the gradient computations. Inference time!
            trajs_e = run_model(
                model,
                rgb_seq,
                S_max=S,
                N=N,
                iters=iters,
                gs=global_step,
            )  # Estimatives for trajectories: calling the run function.

        iter_time = (
            time.time() - iter_start_time
        )  # The time spent on this iter is equal the actual time - initial time.

        full_trajs_tensor = torch.cat((full_trajs_tensor, trajs_e), 0)
        d, o, _, _ = full_trajs_tensor.shape

        with open(output_dir + '/frames/Out_Format.txt', 'w') as file:
            file.write('%s %s %s %s %s %s' % (full_trajs_tensor.shape + image_size))

    for f in range(0, d):
        B_dir = output_dir + '/frames/B' + str(f)
        os.mkdir(B_dir)
        for j in range(0, o):
            np.savetxt(
                B_dir + '/trajs_tensor_B' + str(f) + '_F' + str(j) + '.txt',
                full_trajs_tensor[f, j].cpu(),
                fmt='%.5f',
                delimiter=',',
            )

    # torch.save(full_trajs_tensor, (output_dir + '/trajs_tensor.pt'))
    torch.cuda.empty_cache()  # Cleaning the video memory cache.


if __name__ == '__main__':
    main()
