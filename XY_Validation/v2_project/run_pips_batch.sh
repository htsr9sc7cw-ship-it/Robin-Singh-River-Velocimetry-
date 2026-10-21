#!/bin/bash
# D4 batch mode runner: bash run_pips_batch.sh "<scenes>" "<every>:<img>" [ckpt-dir] [prefix]   -> suffix <prefix>_b<every>_<img>
cd "$(dirname "$0")"; export PIP_PROJECT="$PWD" PIP_N=${PIP_N:-64} PIP_FIX_SIGN=1 PIP_FIX_TRANSPOSE=1 PIP_MP=0 PIP_NO_PLOTS=1 PIP_BATCH_LEN=${PIP_BATCH_LEN:-16}
SCENES="$1"; cfg="$2"; CKPT="$3"; PFX="$4"; e=${cfg%%:*}; img=${cfg##*:}; suf="${PFX:+${PFX}_}b${e}_${img}"; [ -n "$CKPT" ] && export PIP_CKPT_DIR="$CKPT"
for s in $SCENES; do
  [ -d "Outputs/PIP_Eval_${s}_${suf}/Tables" ] && { echo "done  $s $suf"; continue; }
  echo "BATCH $s $suf start $(date)"
  PIP_SCENE=$s PIP_BATCH_EVERY=$e PIP_IMG=$img PIP_RUN_SUFFIX="_${suf}" /opt/anaconda3/envs/pips2/bin/python PIP_Execution_batch.py > "Outputs/log_exec_${s}_${suf}.txt" 2>&1 || { echo "EXEC FAILED $s $suf"; continue; }
  run=$(grep '^DONE ' "Outputs/log_exec_${s}_${suf}.txt" | tail -1 | sed 's/^DONE .\///'); [ -f "$run/frames/Out_Format.txt" ] || { echo "NO OUTPUT $s $suf"; continue; }
  c=$(awk '{print $3}' "$run/frames/Out_Format.txt")
  PIP_SCENE=$s PIP_N=$c PIP_RUN_DIR="$PWD/$run" PIP_EVAL_OUT="$PWD/Outputs/PIP_Eval_${s}_${suf}" /opt/anaconda3/envs/pips2/bin/python -W ignore PIP_Evaluation_gt.py > "Outputs/log_eval_${s}_${suf}.txt" 2>&1 || { echo "EVAL FAILED $s $suf"; continue; }
  echo "$PWD/$run" > "Outputs/PIP_Eval_${s}_${suf}/SOURCE_RUN.txt"; echo "BATCH $s $suf $(grep 'RMSE (endpoint' "Outputs/log_eval_${s}_${suf}.txt") $(date)"
done; echo "BATCH_DONE $(date)"
