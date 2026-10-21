#!/bin/bash
# TAP-Vid-DAVIS at the window that fits the 8 GB M1 (S 32; the repo's S 128 and S 64 run out of MPS memory, probe 19 Sep 23:00).
# Same S for every checkpoint, so the comparison between checkpoints (forgetting, P-G10) is exact; the reference value of the README
# (d_avg 70.6 at S 128) is compared with the same weights at S 32 (P-G9 becomes: reproduce the README within the window effect).
cd "$(dirname "$0")"; exec >> run_davis.log 2>&1; echo "=== davis start $(date) ==="; X="$(dirname "$PWD")"
while [ ! -f "$X/v2_project/results/STAGE_SURFMOVE_SCORED" ]; do sleep 120; done
for c in "reference:$X/../reference_model/model-000200000.pth" "S6:$PWD/ckpt_S6_final/model.pth" "S1:$PWD/ckpt_3000/model.pth" "S4:$PWD/ckpt_S4_final/model.pth" "S3:$PWD/ckpt_S3_final/model.pth" "S2:$PWD/ckpt_S2_final/model.pth" "S5:$PWD/ckpt_S5_final/model.pth"; do
  id=${c%%:*}; ck=${c#*:}; [ -f "$ck" ] || { echo "skip $id"; continue; }; [ -f "results_davis/${id}_S32.csv" ] && continue
  echo "DAVIS $id start $(date)"; PYTORCH_ENABLE_MPS_FALLBACK=1 /opt/anaconda3/envs/pips2/bin/python -W ignore test_on_tap_mps.py --ckpt "$ck" --out "results_davis/${id}_S32.csv" --S 32 > "results_davis/${id}_S32.log" 2>&1; echo "DAVIS $id exit $? $(date)"; grep "MEAN" "results_davis/${id}_S32.log"
  [ "$(date +%H)" -ge 7 ] && [ "$(date +%d)" = 20 ] && { echo "stop: Sunday 07:00 reached"; break; }
done; echo "=== davis end $(date) ==="
