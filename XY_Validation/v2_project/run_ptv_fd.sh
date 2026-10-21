#!/bin/bash
# FlowVelo at matched re-detection cadence (REINIT-1): modes tuned_ncc_fd<k> / tuned_lk_fd<k>.  Usage:
#   bash run_ptv_fd.sh "<scenes>" "<modes>"      e.g. "v2_Path4_dense v2_Low_1_dense" "tuned_ncc_fd1 tuned_ncc_fd2 tuned_lk_fd1 tuned_lk_fd2"
# Skip-if-done (Tracking_FT_*.txt exists in out_ptv/<scene>/<mode>/).  Scoring is done by the driver with --ptv-block-len 48.
cd "$(dirname "$0")"; X="$(dirname "$PWD")"
export XYV_DATA="$PWD/Vectors_and_Images" PTV_PARAMS="$PWD/ptv_params_v2.csv" PTV_OUT="$PWD/out_ptv"
SCENES="$1"; MODES="$2"
for m in $MODES; do for s in $SCENES; do
  ls out_ptv/$s/$m/Tracking_FT_*.txt >/dev/null 2>&1 && { echo "done  $s $m"; continue; }
  echo "PTV $s $m start $(date)"
  ( cd "$X/ptv" && /opt/anaconda3/envs/flowvelo/bin/python -W ignore run_flowvelo_ptv.py --mode $m --scene "$s" > "$PTV_OUT.fd.$s.$m.log" 2>&1 ); echo "PTV $s $m exit $? $(date)"
done; done; echo "PTV_FD_BATCH_DONE $(date)"
