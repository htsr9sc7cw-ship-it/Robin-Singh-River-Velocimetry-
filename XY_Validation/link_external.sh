#!/bin/bash
# Link the data and the two third-party code bases that the scripts need into this folder.
# Usage:  bash link_external.sh /path/to/XY_Validation      (the project folder that holds the data)
# Nothing is copied or modified in the project; only symbolic links are made here.
set -e
P="${1:?usage: bash link_external.sh /path/to/XY_Validation}"
cd "$(dirname "$0")"
PIPS2="$(dirname "$P")/pips2-master Original from PIPs++ GitHub"      # https://github.com/aharley/pips2
# renders, ground truth, tracers (dataset v3): the scene folders of the project contain absolute links that break when the
# drive is mounted under another name, so every link is re-pointed to the project folder given above
python3 - "$P" <<'PY'
import os, sys
P = sys.argv[1]; src = os.path.join(P, 'v2_project', 'Vectors_and_Images'); dst = 'v2_project/Vectors_and_Images'
for scene in sorted(os.listdir(src)):
    d = os.path.join(src, scene)
    if not os.path.isdir(d): continue
    os.makedirs(os.path.join(dst, scene), exist_ok=True)
    for name in os.listdir(d):
        t = os.path.realpath(os.path.join(d, name)) if os.path.exists(os.path.join(d, name)) else os.readlink(os.path.join(d, name)) if os.path.islink(os.path.join(d, name)) else os.path.join(d, name)
        if not os.path.exists(t) and 'XY_Validation/' in t: t = os.path.join(P, t.split('XY_Validation/', 1)[1])
        link = os.path.join(dst, scene, name)
        if os.path.lexists(link): os.remove(link)
        os.symlink(t, link)
PY
ln -sfn "$P/ptv/flowvelo_src"            ptv/flowvelo_src                  # FlowVeloTool, unmodified (https://github.com/AnetteEltner/FlowVeloTool)
ln -sfn "$P/rerender/out"                rerender/out                      # re-rendered scenes
ln -sfn "$(dirname "$P")/reference_model" reference_model                  # published PIPs++ checkpoint
# PIPs++ network and helpers: the working copy of the project (nets/pips2.py with the training-only device change) lies next to XY_Validation
for m in nets utils saverloader.py; do for d in v2_project finetune; do ln -sfn "$(dirname "$P")/$m" "$d/$m"; done; done
[ -e "$PIPS2/datasets" ] && ln -sfn "$PIPS2/datasets" finetune/datasets    # PointOdyssey loader of the PIPs++ repository (used by test_on_tap_mps.py, rehearsal)
mkdir -p v2_project/results/figures v2_project/Outputs
ln -sfn "$P/v2_project/results/figures/gallery" v2_project/results/figures/gallery
echo "linked. Interpreters: pips2 env for PIPs++ scripts, flowvelo env for FlowVelo, base Python for scoring (see README.md)"
