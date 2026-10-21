#!/bin/bash
# REINIT-1 unattended driver (PREREGISTRATION_v2_reinit.md).  Start / resume with exactly:
#   cd "<v2_project>" && nohup caffeinate -i bash run_reinit_all.sh >> reinit_all.log 2>&1 &
# Every stage skips what is already done, so re-running the same command after a crash or sleep simply continues.
# Status: pgrep -f run_reinit_all ; tail reinit_all.log
cd "$(dirname "$0")"; PY=/opt/anaconda3/bin/python; R=results
PILOT="v2_Path4_dense v2_Path4_sparse v2_Low_1_dense v2_Low_1_sparse"
PILOT_CFG="48:512 1:512 2:512 1:256 2:256"
FD_MODES="tuned_ncc_fd1 tuned_ncc_fd2 tuned_lk_fd1 tuned_lk_fd2"
ALL28=$(ls Vectors_and_Images | grep '^v2_' | grep -v 'ts0_\|_clear\|surfmove' | tr '\n' ' ')
echo "=== driver start $(date) ==="

# Stage 1: pilot — PIPs++ (GPU) and FlowVelo fd modes (CPU) side by side
bash run_pips_reinit.sh "$PILOT" "$PILOT_CFG" > reinit_pilot_pips.log 2>&1 &
p1=$!
bash run_ptv_fd.sh "$PILOT" "$FD_MODES" > reinit_pilot_ptv.log 2>&1 &
p2=$!
wait $p1 $p2; echo "stage1 pilot runs finished $(date)"

# Stage 2: score the pilot (fd modes in 48-frame blocks; reference rows from the existing evaluations)
if [ ! -f $R/pips_reinit_pilot.csv ]; then
  $PY compare_v2.py --ptv-eval --workers 4 --ptv-block-len 48 --scenes $PILOT --modes $FD_MODES --method-suffix "" \
      --pips-suffixes r48_512 r1_512 r2_512 r1_256 r2_256 --out pips_reinit_pilot_fd.csv > compare_reinit_pilot.log 2>&1
  $PY compare_v2.py --scenes $PILOT --modes tuned_ncc tuned_lk gui_defaults --pips-suffixes r48_512 r1_512 r2_512 r1_256 r2_256 \
      --out pips_reinit_pilot.csv >> compare_reinit_pilot.log 2>&1
  $PY - <<'PYEOF'
import pandas as pd
a = pd.read_csv('results/pips_reinit_pilot.csv'); b = pd.read_csv('results/pips_reinit_pilot_fd.csv')
b = b[b.method.str.startswith('PTV_')]
d = pd.concat([a, b]).drop_duplicates(['scene', 'method']); d['ratio'] = d.rmse / d.rmse_stay
d.to_csv('results/pips_reinit_pilot.csv', index=False)
print(d.pivot(index='scene', columns='method', values='ratio').round(3).to_string())
PYEOF
  echo "stage2 pilot scored $(date)"
fi

# Stage 3: winner by the pre-registered rule (lowest median ratio over the four; ties -> fewer model calls = larger k)
if [ ! -f $R/REINIT_WINNER.txt ]; then
  $PY - <<'PYEOF'
import pandas as pd, re
d = pd.read_csv('results/pips_reinit_pilot.csv'); d = d[d.method.str.startswith('PIPs++_r')]
m = (d.rmse / d.rmse_stay).groupby(d.method).median().reset_index(); m.columns = ['method', 'ratio']
m['k'] = m.method.str.extract(r'_r(\d+)_').astype(int); m = m.sort_values(['ratio', 'k'], ascending=[True, False])
w = m.iloc[0]; suf = w.method.replace('PIPs++_', '')
open('results/REINIT_WINNER.txt', 'w').write('%s\n' % suf)
print(m.to_string(index=False)); print('WINNER', suf)
PYEOF
fi
WIN=$(cat $R/REINIT_WINNER.txt); K=$(echo $WIN | sed 's/r\([0-9]*\)_.*/\1/'); IMG=${WIN##*_}
echo "winner $WIN (k=$K img=$IMG) $(date)"

# Stage 4: winner on all 28 muddy variants + FlowVelo at the same cadence (k=48 -> the existing FD runs already match)
bash run_pips_reinit.sh "$ALL28" "$K:$IMG" > reinit_full_pips.log 2>&1 &
p1=$!
if [ "$K" = "1" ] || [ "$K" = "2" ]; then bash run_ptv_fd.sh "$ALL28" "tuned_ncc_fd$K tuned_lk_fd$K" > reinit_full_ptv.log 2>&1 & p2=$!; else p2=""; fi
wait $p1 $p2; echo "stage4 full runs finished $(date)"

# Stage 5: score everything into one CSV
if [ ! -f $R/three_way_v3_reinit.csv ]; then
  if [ "$K" = "1" ] || [ "$K" = "2" ]; then
    $PY compare_v2.py --ptv-eval --workers 4 --ptv-block-len 48 --scenes $ALL28 --modes tuned_ncc_fd$K tuned_lk_fd$K \
        --no-pips --out three_way_v3_reinit_fd.csv > compare_reinit_full.log 2>&1
  fi
  $PY compare_v2.py --scenes $ALL28 --modes tuned_ncc tuned_lk gui_defaults --pips-suffixes $WIN r48_512 r1_512 r2_512 r1_256 r2_256 \
      --out three_way_v3_reinit.csv >> compare_reinit_full.log 2>&1
  $PY - <<'PYEOF'
import pandas as pd, os
a = pd.read_csv('results/three_way_v3_reinit.csv')
if os.path.exists('results/three_way_v3_reinit_fd.csv'):
    b = pd.read_csv('results/three_way_v3_reinit_fd.csv'); a = pd.concat([a, b[b.method.str.startswith('PTV_')]])
a = a.drop_duplicates(['scene', 'method']); a['ratio'] = a.rmse / a.rmse_stay
a.to_csv('results/three_way_v3_reinit.csv', index=False)
print(a.groupby('method').ratio.median().round(3).to_string())
PYEOF
  echo "stage5 scored $(date)"
fi

# Stage 6: tables / figures / GIF (scripts added while the runs were going; skipped if absent)
[ -f make_results_reinit.py ] && $PY make_results_reinit.py > make_results_reinit.log 2>&1 && echo "stage6 results $(date)"

# Stage 7: Study B fine-tuning (if prepared)
[ -f ../finetune/run_finetune.sh ] && bash ../finetune/run_finetune.sh >> ../finetune/run_finetune.log 2>&1 && echo "stage7 finetune $(date)"
echo "=== driver end $(date) ==="
