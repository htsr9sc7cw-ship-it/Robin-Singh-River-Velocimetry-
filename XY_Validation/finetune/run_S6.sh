#!/bin/bash
# S6 rerun after the 512-px OOM (FIXLOG OPS-7): README stage 2 adapted to the 8 GB M1 — the largest clip that fits at native 512 px is
# S 12 N 24 after S 16/N 32 used 9.1 GB and thrashed at 130 s/step (OPS-10); probe Sat 08:55: S24/512 OOM, S16/512 fits, S12/512 fits, S24/384 fits). Same 4 h budget as S2–S5. Parent: S3 (rule applied to the complete S2–S5 table at 09:35; the 01:26 pick "S2" was made on a stale table, FIXLOG OPS-8).
cd "$(dirname "$0")"; X="$(dirname "$PWD")"; P="$X/v2_project"; PY=/opt/anaconda3/envs/pips2/bin/python; export PYTORCH_ENABLE_MPS_FALLBACK=1
HELD="v2_Path4_dense v2_Path4_sparse v2_Low_1_dense v2_Low_1_sparse v2_Low_1_001_dense v2_Low_1_001_sparse v2_low_angle_dense v2_low_angle_sparse v2_Overview_dense v2_Overview_sparse v2_Path2_dense"
exec >> run_S6.log 2>&1; echo "=== S6 start $(date) ==="
true
echo "TRAIN S6 start $(date)"; caffeinate -i $PY train_v3.py --ckpt "$PWD/ckpt_S6" --resume --debug-png "$PWD/ckpt_S6/debug_clip.png" --init "$PWD/ckpt_S3_final/model.pth" --lr 1e-4 --onecycle --S 12 --crop 384 --N 24 --iters 6 --persist --augs photometric,vflip,reverse --extra Path3_clear,high_angle_clear --max-iters 3000 --max-hours 4 >> train_S6.out 2>&1; echo "TRAIN S6 exit $? $(date)"
last=$(ls ckpt_S6/model-*.pth | sort | tail -1); [ -n "$last" ] || { echo "no checkpoint"; echo "=== S6 end $(date) ==="; exit 1; }
rm -rf ckpt_S6_final; mkdir -p ckpt_S6_final; ln -s "$PWD/$last" ckpt_S6_final/model.pth; [ -f ckpt_S6_final/model.pth ] || { echo "bad link"; exit 1; }
for m in "2:256:8" "48:256:8"; do k=${m%%:*}; rest=${m#*:}; img=${rest%%:*}; win=${rest#*:}; PIP_WIN=$win bash "$P/run_pips_reinit.sh" "$HELD" "$k:$img" "$PWD/ckpt_S6_final" "S6" >> eval_S6.log 2>&1; done
bash "$P/run_pips_batch.sh" "$HELD" "2:256" "$PWD/ckpt_S6_final" "S6" >> eval_S6.log 2>&1
echo "EVAL S6 done $(date)"; touch "$P/results/STAGE_S6_DONE"; echo "=== S6 end $(date) ==="
