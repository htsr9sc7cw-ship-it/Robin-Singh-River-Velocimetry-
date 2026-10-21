#!/bin/bash
# PIPs++ (untrained, sorted frames) + evaluation with PIP_FIX_SIGN=1 for every linked v2 scene not yet run.
cd "/Volumes/Drive Von Robin/THESIS ORIGINAL  /XY_Validation/v2_project"
export PIP_PROJECT="$PWD" PIP_N=256 PIP_FIX_SIGN=1 PIP_FIX_TRANSPOSE=1 PIP_MP=0 PIP_NO_PLOTS=1   # [FIXLOG C4]; scoring only (figures: make_results.py / make_fig_example.py)
for s in Vectors_and_Images/*/; do s=$(basename "$s")
  ls -d Outputs/PIP_Run_${s}_48_256_*/frames/B0 >/dev/null 2>&1 && continue
  echo "PIPS $s start $(date)"; PIP_SCENE="$s" /opt/anaconda3/envs/pips2/bin/python PIP_Execution.py > "Outputs/log_exec_$s.txt" 2>&1; echo "PIPS $s exec exit $?"
  PIP_SCENE="$s" /opt/anaconda3/envs/pips2/bin/python PIP_Evaluation_gt.py > "Outputs/log_eval_$s.txt" 2>&1; echo "PIPS $s eval exit $? $(grep -E 'RMSE' Outputs/log_eval_$s.txt | head -1)"
done; echo PIPS_ALL_DONE
