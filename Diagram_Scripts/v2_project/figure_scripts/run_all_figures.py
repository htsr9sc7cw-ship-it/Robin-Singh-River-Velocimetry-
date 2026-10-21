"""Runs every fig_*.py of this folder one after the other and prints OK / FAILED per figure.
Run:  python run_all_figures.py     (the worked-example scripts and fig_5_17 need the pips2 interpreter and are skipped here
unless PIPS2_PYTHON is set)."""

import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def pips2_python():
    """interpreter of the pips2 environment: PIPS2_PYTHON, else asked from conda, else None"""
    if os.environ.get("PIPS2_PYTHON"):
        return os.environ["PIPS2_PYTHON"]
    try:
        r = subprocess.run(
            ["conda", "run", "-n", "pips2", "python", "-c", "import sys;print(sys.executable)"],
            capture_output=True,
            text=True,
            shell=(os.name == "nt"),
        )
        return r.stdout.strip().splitlines()[-1] if r.returncode == 0 and r.stdout.strip() else None
    except OSError:
        return None


NEEDS_PIPS2 = ("fig_5_09", "fig_5_10", "fig_5_12", "fig_5_17")
for f in sorted(glob.glob(os.path.join(HERE, "fig_[1-9]_*.py"))):
    name = os.path.basename(f)
    py = sys.executable
    if name.startswith(NEEDS_PIPS2):
        py = pips2_python()
        if not py:
            print("SKIPPED (needs pips2) ", name)
            continue
    r = subprocess.run([py, "-W", "ignore", f], cwd=HERE, capture_output=True, text=True)
    if (
        r.returncode
        and name.startswith(NEEDS_PIPS2)
        and (
            "No such file" in r.stderr or "out of range" in r.stderr or "empty sequence" in r.stderr
        )
    ):
        print("SKIPPED (stored tracker runs of the thesis are not in this kit) ", name)
        continue
    print(
        "OK     " if r.returncode == 0 else "FAILED ",
        name,
        "" if r.returncode == 0 else r.stderr.strip().splitlines()[-1:],
    )
