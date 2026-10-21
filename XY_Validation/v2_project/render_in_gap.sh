#!/bin/bash
# Renders DeepMind-visualiser (tapnet plot_tracks_tails) videos in a GPU gap: waits for a stage marker, pauses (SIGSTOP)
# any running train_v3.py so that matplotlib never runs beside training (swap 8 GB on 18 Sep 10:13), renders, resumes it.
# usage: bash render_in_gap.sh <marker-file> <suffix> <scenes...>
X="/Volumes/Drive Von Robin/THESIS ORIGINAL  /XY_Validation/v2_project"; M="$1"; SUF="$2"; shift 2
LOG="$X/results/videos_tapnet/render_$(date +%d%H%M).log"; mkdir -p "$X/results/videos_tapnet"
while [ ! -f "$M" ]; do sleep 120; done
sleep 30; PIDS=$(pgrep -f train_v3.py); [ -n "$PIDS" ] && kill -STOP $PIDS && echo "$(date) paused train $PIDS" >> "$LOG"
cd "$X"; for s in "$@"; do
  PIP_TAP_SUFFIX="$SUF" PIP_TAP_MAXPTS=400 nice -n 10 /opt/anaconda3/envs/pips2/bin/python -W ignore make_tapnet_video.py "$s" >> "$LOG" 2>&1
  echo "$(date) $s exit $? swap $(sysctl -n vm.swapusage | sed -E 's/.*used = ([0-9.]+M).*/\1/')" >> "$LOG"
done
[ -n "$PIDS" ] && kill -CONT $PIDS && echo "$(date) resumed train" >> "$LOG"; echo "=== render end ===" >> "$LOG"
