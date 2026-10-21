#!/bin/bash
# Study C driver (PREREGISTRATION_strategies.md, 18 Sep): S2 -> S3 -> S4 -> S5 -> pick -> S6, each: train (resumable) ->
# evaluate held-out in deployment modes -> marker. Skip-if-done everywhere. Started through v2_project/run_on_drive.sh.
cd "$(dirname "$0")"; P="$(dirname "$PWD")/v2_project"; export PYTORCH_ENABLE_MPS_FALLBACK=1
PY=/opt/anaconda3/envs/pips2/bin/python; POD="$(dirname "$(dirname "$PWD")")/PointOdyssey_Reference/sample"
HELD="v2_Path4_dense v2_Path4_sparse v2_Low_1_dense v2_Low_1_sparse v2_Low_1_001_dense v2_Low_1_001_sparse v2_low_angle_dense v2_low_angle_sparse v2_Overview_dense v2_Overview_sparse v2_Path2_dense"
AUGS="scale,photometric,vflip"; AUGS3="scale,photometric,vflip,reverse,movingcrop"
echo "=== strategies start $(date) ==="
# wait for the deployment-axis job (GPU) to finish
while ! grep -q "deploy axis end" run_deploy_axis.log 2>/dev/null; do sleep 60; done

train() { # id, ckpt-dir, args...
  local id=$1 dir=$2; shift 2
  grep -q TRAIN_DONE "train_$id.out" 2>/dev/null && { echo "train $id done"; return; }
  echo "TRAIN $id start $(date)"; $PY train_v3.py --ckpt "$PWD/$dir" --resume --debug-png "$PWD/$dir/debug_clip.png" "$@" >> "train_$id.out" 2>&1; echo "TRAIN $id exit $? $(date)"
}
evalck() { # id, ckpt-dir, modes(space list of k:img[:win])
  local id=$1 dir=$2 modes=$3; local last=$(ls "$dir"/model-*.pth | sort | tail -1); mkdir -p "${dir}_final"; ln -sf "$PWD/$last" "${dir}_final/model.pth"
  for m in $modes; do k=${m%%:*}; rest=${m#*:}; img=${rest%%:*}; win=${rest#*:}; [ "$win" = "$img" ] && win=8
    PIP_WIN=$win bash "$P/run_pips_reinit.sh" "$HELD" "$k:$img" "$PWD/${dir}_final" "$id" >> "eval_$id.log" 2>&1; done
  bash "$P/run_pips_batch.sh" "$HELD" "2:256" "$PWD/${dir}_final" "$id" >> "eval_$id.log" 2>&1                 # D4: fresh seeds every 2 frames
  echo "EVAL $id done $(date)"
}
# gallery for the viewpoints still missing (CPU, ~10 min), then D4 for the baselines: pre-trained (S0) and FT-1 (S1)
( cd "$P" && /opt/anaconda3/envs/pips2/bin/python make_gallery.py >> gallery.log 2>&1 )

bash "$P/run_pips_batch.sh" "$HELD" "2:256" "" "" >> eval_S0.log 2>&1
bash "$P/run_pips_batch.sh" "$HELD" "2:256" "$PWD/ckpt_3000" "ft3000" >> eval_S1.log 2>&1
touch "$P/results/STAGE_D4BASE_DONE"
# S2: data + augmentation, continued from S1
train S2 ckpt_S2 --init ckpt/model-003000.pth --lr 5e-5 --S 12 --crop 256 --N 64 --iters 6 --augs $AUGS --extra Path3_clear,high_angle_clear --max-iters 3000 --max-hours 4
evalck S2 ckpt_S2 "2:256 48:256"; touch "$P/results/STAGE_S2_DONE"
# S3: long-sequence, paper recipe, from the pre-trained model. S 36 passed the memory test but ran at 45 s/step (4 GB swap) on
# 18 Sep 06:14-09:35 -> stopped at step 380 and restarted with S 24 (register deviation, 09:40).
S3S=24
train S3 ckpt_S3 --init ../../reference_model/model-000200000.pth --lr 1e-4 --onecycle --S $S3S --crop 256 --N 48 --iters 8 --persist --augs $AUGS3 --extra Path3_clear,high_angle_clear --max-iters 3000 --max-hours 8
evalck S3 ckpt_S3 "2:256 48:256"; touch "$P/results/STAGE_S3_DONE"
# S4: rehearsal with PointOdyssey
train S4 ckpt_S4 --init ckpt/model-003000.pth --lr 5e-5 --S 12 --crop 256 --N 64 --iters 6 --augs $AUGS --extra Path3_clear,high_angle_clear --mix-pod "$POD" --mix-frac 0.5 --max-iters 3000 --max-hours 4
evalck S4 ckpt_S4 "2:256 48:256"; touch "$P/results/STAGE_S4_DONE"
# S5: from scratch
train S5 ckpt_S5 --init none --lr 5e-4 --onecycle --S 12 --crop 256 --N 64 --iters 6 --augs $AUGS --extra Path3_clear,high_angle_clear --max-iters 3000 --max-hours 4
evalck S5 ckpt_S5 "2:256 48:256"; touch "$P/results/STAGE_S5_DONE"
# score S2-S5 and pick S6's parent by the register rule (lowest held-out median ratio_h15 over modes; ties -> fewer changes: S2 < S4 < S3 < S5)
( cd "$P" && /opt/anaconda3/bin/python compare_v2.py --scenes $HELD --modes tuned_ncc_fd2 tuned_lk_fd2 --pips-suffixes r2_256 b2_256 ft3000_r2_256 ft3000_r48_256 ft3000_r16_256 ft3000_b2_256 r16_256 S2_r2_256 S2_r48_256 S2_b2_256 S3_r2_256 S3_r48_256 S3_b2_256 S4_r2_256 S4_r48_256 S4_b2_256 S5_r2_256 S5_r48_256 S5_b2_256 --out strategies_v3.csv > compare_strategies.log 2>&1 )
WIN=$(/opt/anaconda3/bin/python - <<'PYEOF'
import pandas as pd
d = pd.read_csv('../v2_project/results/strategies_v3.csv'); d = d[d.scene != 'v2_Path2_dense']
best = {}
for s in ['S2', 'S3', 'S4', 'S5']:
    g = d[d.method.str.startswith('PIPs++_' + s + '_')]
    if len(g): best[s] = g.groupby('method').ratio_h15.median().min()
order = ['S2', 'S4', 'S3', 'S5']; w = min(best, key=lambda s: (round(best[s], 3), order.index(s)))
open('../v2_project/results/STRATEGY_WINNER.txt', 'w').write(w + '\n'); print(w)
PYEOF
)
echo "S6 parent: $WIN $(date)"
# S6: README stage 2 - high-resolution long clips from the winner; memory test S 64 -> 48 -> 36
S6S=64; for s in 64 48 36; do $PY - <<PYEOF && { S6S=$s; break; }
import torch, sys; sys.path.insert(0, '../..'); from nets.pips2 import Pips
m = Pips(stride=8).to('mps'); x = torch.zeros(1, $s, 3, 512, 512, device='mps'); t = torch.zeros(1, $s, 32, 2, device='mps')
try:
    p, _, _, l = m(t, x, iters=6, trajs_g=t, vis_g=torch.ones(1, $s, 32, device='mps'), valids=torch.ones(1, $s, 32, device='mps'), is_train=True); l.backward(); print('S$s at 512 fits')
except Exception as e: print('S$s fails', e); sys.exit(1)
PYEOF
done
echo "S6 clip length $S6S at native 512 (parent $WIN)" >> PREREGISTRATION_strategies.md
train S6 ckpt_S6 --init "$PWD/ckpt_${WIN}_final/model.pth" --lr 1e-4 --onecycle --S $S6S --crop 512 --N 32 --iters 6 --persist --augs photometric,vflip,reverse --extra Path3_clear,high_angle_clear --max-iters 3000 --max-hours 6
evalck S6 ckpt_S6 "2:256 48:256 16:256:16"; touch "$P/results/STAGE_S6_DONE"
echo "=== strategies end $(date) ==="
