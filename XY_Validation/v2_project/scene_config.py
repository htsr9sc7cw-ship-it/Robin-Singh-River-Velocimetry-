"""scene_config.py

Thesis section: see README.md
Inputs: see README.md
Outputs: see README.md

Shared configuration for PIP_Execution.py, PIP_Evaluation.py and make_visuals.py.

CHANGE ONLY THE 'SCENE' LINE BELOW to pick which dataset to run.
Then run PIP_Execution.py, then PIP_Evaluation.py, then make_visuals.py.

Available scenes are the folder names inside Vectors_and_Images/.
"""

import os
import torch

# Folder that holds all the scene datasets (each with images/ and vector/).
DATA_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Vectors_and_Images')

# >>> CHANGE THIS LINE to pick a scene <<<
# (run_all_scenes.py overrides this via the PIP_SCENE environment variable.)
SCENE = os.environ.get('PIP_SCENE', 'Elbersdorf_3ms_muddy0.4_day_perspective_Low1')

# >>> NUMBER OF TRACKED PARTICLES (must be a perfect square: grid is sqrt(N) x sqrt(N)) <<<
# (n_sweep.py overrides this via the PIP_N environment variable.)
N = int(os.environ.get('PIP_N', '256'))

# Device: use Apple GPU (mps) if available, else CPU. Much faster on Apple Silicon.
if torch.backends.mps.is_available():
    DEVICE = 'mps'
else:
    DEVICE = 'cpu'

# Convenience paths derived from SCENE.
SCENE_DIR = os.path.join(DATA_ROOT, SCENE)  # contains images/ and vector/
IMAGES_DIR = os.path.join(SCENE_DIR, 'images')
VECTOR_DIR = os.path.join(SCENE_DIR, 'vector')


def list_scenes():
    """Return all scene folder names that have both images/ and vector/."""
    out = []
    for d in sorted(os.listdir(DATA_ROOT)):
        p = os.path.join(DATA_ROOT, d)
        if os.path.isdir(os.path.join(p, 'images')) and os.path.isdir(os.path.join(p, 'vector')):
            out.append(d)
    return out
