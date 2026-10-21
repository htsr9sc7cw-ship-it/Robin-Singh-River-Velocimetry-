#!/bin/bash
# Re-initialised PIPs++ (REINIT-1, PREREGISTRATION_v2_reinit.md).  Usage:
#   bash run_pips_reinit.sh "<scenes space-separated>" "<configs space-separated>"   configs = k:img, e.g. "1:512 2:512 48:512 1:256 2:256"
# One run + one evaluation per scene x config; skip-if-done (Outputs/PIP_Eval_<scene>_r<k>_<img>/Tables exists), so re-running resumes.
cd "$(dirname "$0")"; export PIP_PROJECT="$PWD" PIP_N=256 PIP_FIX_SIGN=1 PIP_FIX_TRANSPOSE=1 PIP_MP=0 PIP_NO_PLOTS=1 PIP_WIN=${PIP_WIN:-8}
SCENES="$1"; CONFIGS="$2"; CKPT="$3"; PFX="$4"     # optional: checkpoint folder + suffix prefix (Study B: ckpt dir, ft1500)
[ -n "$CKPT" ] && export PIP_CKPT_DIR="$CKPT"
for cfg in $CONFIGS; do k=${cfg%%:*}; img=${cfg##*:}; suf="${PFX:+${PFX}_}r${k}_${img}"
  for s in $SCENES; do
    [ -d "Outputs/PIP_Eval_${s}_${suf}/Tables" ] && { echo "done  $s $suf"; continue; }
    echo "REINIT $s $suf start $(date)"
    PIP_SCENE=$s PIP_REINIT_K=$k PIP_IMG=$img PIP_RUN_SUFFIX="_${suf}" /opt/anaconda3/envs/pips2/bin/python PIP_Execution_reinit.py > "Outputs/log_exec_${s}_${suf}.txt" 2>&1 || { echo "EXEC FAILED $s $suf"; continue; }
    run=$(grep '^DONE ' "Outputs/log_exec_${s}_${suf}.txt" | tail -1 | sed 's/^DONE .\///')
    [ -f "$run/frames/Out_Format.txt" ] || { echo "NO OUTPUT $s $suf"; continue; }
    PIP_SCENE=$s PIP_RUN_DIR="$PWD/$run" PIP_EVAL_OUT="$PWD/Outputs/PIP_Eval_${s}_${suf}" /opt/anaconda3/envs/pips2/bin/python -W ignore PIP_Evaluation_gt.py > "Outputs/log_eval_${s}_${suf}.txt" 2>&1 || { echo "EVAL FAILED $s $suf"; continue; }
    echo "$PWD/$run" > "Outputs/PIP_Eval_${s}_${suf}/SOURCE_RUN.txt"
    echo "REINIT $s $suf $(grep 'RMSE (endpoint' "Outputs/log_eval_${s}_${suf}.txt") $(date)"
  done
done; echo "REINIT_BATCH_DONE $(date)"
