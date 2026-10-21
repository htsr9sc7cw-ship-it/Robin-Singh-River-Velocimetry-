#!/bin/bash
# Study B driver: fine-tune, then score every checkpoint on the held-out variants with the Study-A winner setting.
# Resumable: training resumes from the last checkpoint; evaluations skip finished ones.
cd "$(dirname "$0")"; P="$(dirname "$PWD")/v2_project"; export PYTORCH_ENABLE_MPS_FALLBACK=1
HELD="v2_Path4_dense v2_Path4_sparse v2_Low_1_dense v2_Low_1_sparse v2_Low_1_001_dense v2_Low_1_001_sparse v2_low_angle_dense v2_low_angle_sparse v2_Overview_dense v2_Overview_sparse"
CTRL="v2_Path2_dense"
echo "=== finetune start $(date) ==="
if ! grep -q TRAIN_DONE train_v3.out 2>/dev/null; then
  /opt/anaconda3/envs/pips2/bin/python train_v3.py --max-iters 3000 --max-hours 8 --S 12 --crop 256 --resume >> train_v3.out 2>&1
fi
echo "training finished $(date)"
WIN=$(cat "$P/results/REINIT_WINNER.txt" 2>/dev/null || echo r1_512); K=$(echo $WIN | sed 's/r\([0-9]*\)_.*/\1/'); IMG=${WIN##*_}
# evaluation budget (~15 min per variant at 512): final checkpoint on all held-out variants + the control;
# intermediate checkpoints (every 1000 it.) on Path4 dense + Low_1 dense only (learning curve)
LAST=$(ls ckpt/model-*.pth | sort | tail -1); SUFS=""
for ck in $(ls ckpt/model-*.pth | sort); do
  it=$(basename $ck .pth | sed 's/model-0*//'); d=ckpt_$it; mkdir -p $d; ln -sf "$PWD/$ck" $d/model.pth
  if [ "$ck" = "$LAST" ]; then SC="$HELD $CTRL"; elif [ $((it % 1000)) -eq 0 ]; then SC="v2_Path4_dense v2_Low_1_dense"; else continue; fi
  bash "$P/run_pips_reinit.sh" "$SC" "$K:$IMG" "$PWD/$d" "ft$it" >> eval_ft.log 2>&1; SUFS="$SUFS ft${it}_$WIN"
done
( cd "$P" && /opt/anaconda3/bin/python compare_v2.py --scenes $HELD $CTRL --modes tuned_ncc tuned_lk gui_defaults \
    --pips-suffixes $WIN $SUFS --out finetune_v3.csv > "$PWD/compare_finetune.log" 2>&1 )
echo "=== finetune end $(date) ==="
