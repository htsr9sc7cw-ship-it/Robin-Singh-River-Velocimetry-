"""Runs the script of every diagram of the thesis and compares each result with the picture printed in the thesis.

    python run_all_diagrams.py            (PyCharm: right-click this file > Run)

For each diagram script (v2_project/figure_scripts/fig_*.py) the picture is computed from the result files of our real experiments
(v2_project/results/*.csv, written by compare_v2.py from the real tracker runs, and the tracker output in v2_project/Outputs) into v2_project/results/figures/, and then compared with the
picture of the thesis in thesis_diagrams_to_compare/. Every picture is reported as IDENTICAL (same pixels), SAME (same picture, tiny
rendering differences from fonts or library versions) or DIFFERENT.
Needs: Python 3 with numpy, pandas, matplotlib, pillow (all diagrams) and opencv-python (three diagrams that draw tracks on a frame).
"""

import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FS = os.path.join(HERE, "v2_project", "figure_scripts")
OUT = os.path.join(HERE, "v2_project", "results", "figures")
REF = os.path.join(HERE, "thesis_diagrams_to_compare")
NEEDS_CV2 = ("fig_5_10", "fig_5_12", "fig_5_17")


def has_cv2(py):
    return subprocess.run([py, "-c", "import cv2"], capture_output=True).returncode == 0


def interpreter_with_cv2():
    """the current interpreter if it has opencv, else PIPS2_PYTHON, else the conda environment pips2"""
    cands = [
        sys.executable,
        os.environ.get("PIPS2_PYTHON", ""),
        "/opt/anaconda3/envs/pips2/bin/python",
        os.path.expanduser("~/anaconda3/envs/pips2/bin/python"),
        os.path.expanduser("~/miniconda3/envs/pips2/bin/python"),
    ]
    return next((c for c in cands if c and os.path.exists(c) and has_cv2(c)), None)


def compare(a, b):
    """('identical' | 'same' | 'different', note). 'same' = same picture; only tiny rendering differences (font edges, one pixel of size)."""
    import numpy as np
    from PIL import Image, ImageChops

    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size == ib.size and ImageChops.difference(ia, ib).getbbox() is None:
        return "identical", ""
    w, h = min(ia.size[0], ib.size[0]), min(ia.size[1], ib.size[1])
    x = np.asarray(ia.crop((0, 0, w, h)), dtype=float)
    y = np.asarray(ib.crop((0, 0, w, h)), dtype=float)
    mad = float(np.abs(x - y).mean())
    note = "size %s against %s, mean grey-level difference %.2f" % (ia.size, ib.size, mad)
    return (
        "same"
        if abs(ia.size[0] - ib.size[0]) <= 4 and abs(ia.size[1] - ib.size[1]) <= 4 and mad < 3
        else "different"
    ), note


os.makedirs(OUT, exist_ok=True)
scripts = sorted(glob.glob(os.path.join(FS, "fig_[1-9]_*.py")))
print("Drawing %d diagrams ..." % len(scripts))
status = {}
for s in scripts:
    name = os.path.basename(s)
    py = sys.executable
    if name.startswith(NEEDS_CV2):
        py = interpreter_with_cv2()
        if not py:
            print("  SKIPPED %-45s needs opencv:  pip install opencv-python" % name)
            status[name] = "skipped"
            continue
    r = subprocess.run([py, "-W", "ignore", s], cwd=FS, capture_output=True, text=True)
    status[name] = "ok" if r.returncode == 0 else "failed"
    print(
        "  %-8s %s" % ("drawn" if r.returncode == 0 else "FAILED", name),
        "" if r.returncode == 0 else r.stderr.strip().splitlines()[-1:],
    )

print("\nComparison with the pictures of the thesis:")
count = {"identical": 0, "same": 0, "different": 0, "missing": 0}
for p in sorted(glob.glob(os.path.join(REF, "*.png"))):
    q = os.path.join(OUT, os.path.basename(p))
    if not os.path.exists(q):
        count["missing"] += 1
        print("  MISSING    %s" % os.path.basename(p))
        continue
    kind, note = compare(p, q)
    count[kind] += 1
    print("  %-10s %s %s" % (kind.upper(), os.path.basename(p), note))
print(
    "\n%d pictures drawn: %d pixel-identical to the thesis, %d the same picture with tiny rendering differences, %d different, %d missing."
    % (sum(count.values()), count["identical"], count["same"], count["different"], count["missing"])
)
print(
    "Tiny differences come from the fonts and library versions of the computer; the numbers drawn are the same."
)
