#!/bin/bash
# OPS-14: S6 three-panel videos rendered ALONE (renders beside DAVIS were OOM-killed, exit 137, swap 9.9 GB). Waits until run_davis.sh
# has finished (or 05:00), then renders the 16 dense moving-water viewpoints sequentially; skip-if-done.
cd "$(dirname "$0")"; exec >> render_videos_S6.log 2>&1; echo "=== render start $(date) ==="
while pgrep -f "bash run_davis.sh" >/dev/null && [ "$(date +%H)" -lt 5 ]; do sleep 120; done
pgrep -f "bash run_davis.sh" >/dev/null && { pkill -f "bash run_davis.sh"; pkill -f test_on_tap_mps.py; echo "davis stopped at $(date) for the videos"; sleep 10; }
for s in $(ls Vectors_and_Images | grep surfmove_dense); do [ -f "results/videos_tapnet/h264/${s}_S6_b2_256_side_by_side.mp4" ] && continue
  PIP_TAP_SUFFIX=S6_b2_256 PIP_TAP_MAXPTS=150 PIP_TAP_MAXPTV=1000 nice -n 5 /opt/anaconda3/envs/pips2/bin/python -W ignore make_tapnet_video.py "$s"; echo "video $s S6 exit $? swap $(sysctl -n vm.swapusage | sed -E 's/.*used = ([0-9.]+M).*/\1/') $(date)"; done
touch results/STAGE_VIDEOS_S6_DONE; echo "=== render end $(date) ==="
