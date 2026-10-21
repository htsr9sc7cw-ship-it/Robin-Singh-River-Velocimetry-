#!/bin/bash
# Saturday automation (plan: decision Fri 09:50 + P-G14, TAP-Vid-DAVIS audit/forgetting, videos for all 16 viewpoints).
# Waits for STAGE_S6_DONE, then runs unattended, one GPU job at a time, resumable (every step skips if its output exists).
# Launch: cd v2_project && env -i HOME=$HOME PATH=$PATH nohup bash run_on_drive.sh finetune/after_S6.sh & disown   (log: finetune/after_S6.log)
cd "$(dirname "$0")"; X="$(dirname "$PWD")"; P="$X/v2_project"; PY=/opt/anaconda3/envs/pips2/bin/python; PYB=/opt/anaconda3/bin/python
exec >> after_S6.log 2>&1; echo "=== after_S6 start $(date) ==="
while [ ! -f "$P/results/STAGE_S6_DONE" ] || pgrep -f "train_v3.py|PIP_Execution" >/dev/null; do sleep 300; done
HELDV="v2_Path4_dense v2_Path4_sparse v2_Low_1_dense v2_Low_1_sparse v2_Low_1_001_dense v2_Low_1_001_sparse v2_low_angle_dense v2_low_angle_sparse v2_Overview_dense v2_Overview_sparse"
SM=$(ls "$P/Vectors_and_Images" | grep surfmove | tr '\n' ' ')                               # 32 = 16 viewpoints x {dense, sparse}
SMH=$(echo $SM | tr ' ' '\n' | grep -v clear | tr '\n' ' ')                                    # 28 muddy variants = headline set
S6="$PWD/ckpt_S6_final"; [ -f "$S6/model.pth" ] || { echo "no S6 model"; exit 1; }
# 1 known-answer control on moving-surface variants (GT-advected tracks through the same pipeline) - must PASS before any table is read
( cd "$P" && $PYB known_answer_eval.py v2_Path4_surfmove_dense v2_Overview_surfmove_dense v2_Low_1_surfmove_sparse > results/known_answer_surfmove.log 2>&1 ); grep -c PASS "$P/results/known_answer_surfmove.log"; echo "known-answer $(date)"
# 2 FlowVelo (CPU) in the background, one process, params derived by the same rule as every other scene
( cd "$P" && export XYV_DATA="$P/Vectors_and_Images" PTV_PARAMS="$P/ptv_params_v2.csv" PTV_OUT="$P/out_ptv"; ( cd ../ptv && $PY -W ignore derive_ptv_params.py > "$PTV_OUT.derive_surfmove.log" 2>&1 ); nice -n 5 bash run_ptv_fd.sh "$SM" "tuned_ncc_fd2 tuned_lk_fd2" > ptv_surfmove.log 2>&1 ) &
# 2b P-G15 (registered Sat 00:45): S6 at NATIVE resolution (PIP_IMG 512, fresh seeds every 2 frames) on the 10 held-out static variants;
#    rule: the headline resolution for S6 is the one with the lower held-out median ratio_h15 (256 vs 512); both are reported.
bash "$P/run_pips_batch.sh" "$HELDV" "2:512" "$S6" "S6"; echo "S6 D4 512 held-out done $(date)"
( cd "$P" && $PYB compare_v2.py --scenes $HELDV --modes tuned_ncc_fd2 --pips-suffixes S6_b2_256 S6_r48_256 S6_b2_512 --ptv-block-len 48 --out results/s6_resolution_v3.csv > results/s6_resolution_v3.log 2>&1 )
BEST=$($PYB -c "import pandas as pd; d=pd.read_csv('$P/results/s6_resolution_v3.csv'); d=d[d.scene!='v2_Path2_dense']; m=d[d.method.str.startswith('PIPs++_S6')].groupby('method').ratio_h15.median(); print(m.idxmin()[7:])")
RES=256; case "$BEST" in *512*) RES=512;; esac; echo "S6 best held-out mode: $BEST (resolution $RES) $(date)"; echo "$BEST" > "$P/results/S6_BEST_MODE.txt"; echo "$RES" > "$P/results/S6_RESOLUTION.txt"
# 3 PIPs++ (GPU, sequential): S0 fresh seeds every 2 frames (256); S6 fresh seeds at 256 on all 32; if 512 won, S6 at 512 on the 16 dense variants
#    (deviation Sat 00:45: S6 long-term mode D3 on the moving-surface frames dropped for time; D3 is characterised on the static held-out set)
bash "$P/run_pips_batch.sh" "$SM" "2:256" "" "" ; echo "S0 D4 surfmove done $(date)"; touch "$P/results/STAGE_SM_S0_DONE"
bash "$P/run_pips_batch.sh" "$SM" "2:256" "$S6" "S6"; echo "S6 D4 surfmove done $(date)"
[ "$BEST" = S6_r48_256 ] && { bash "$P/run_pips_reinit.sh" "$SM" "48:256" "$S6" "S6"; echo "S6 D3 surfmove done $(date)"; }   # long-term mode only if it is S6's best mode on held-out (S3, its parent, prefers it: 0.685 vs 0.748)
[ "$RES" = 512 ] && { bash "$P/run_pips_batch.sh" "$(echo $SM | tr ' ' '\n' | grep dense | tr '\n' ' ')" "2:512" "$S6" "S6"; echo "S6 D4 512 surfmove dense done $(date)"; }
wait; echo "FlowVelo surfmove done $(date)"
# 4 scoring: compare_v2 (+ ratio_h15), TAP-Vid metrics, velocity field, stats
( cd "$P" && $PYB compare_v2.py --scenes $SM --modes tuned_ncc_fd2 tuned_lk_fd2 --pips-suffixes b2_256 S6_b2_256 S6_r48_256 S6_b2_512 --ptv-block-len 48 --out results/surfmove_headline_v3.csv > results/surfmove_headline_v3.log 2>&1
  $PY -W ignore tapvid_eval.py --scenes $SM --methods PIPs++_b2_256 PIPs++_S6_b2_256 PIPs++_S6_r48_256 PIPs++_S6_b2_512 PTV_tuned_ncc_fd2 PTV_tuned_lk_fd2 --out results/tapvid_surfmove_v3.csv > results/tapvid_surfmove_v3.log 2>&1
  $PY -W ignore velocity_field_eval.py --scenes $SM --methods PIPs++_b2_256 PIPs++_S6_b2_256 PIPs++_S6_r48_256 PIPs++_S6_b2_512 PTV_tuned_ncc_fd2 PTV_tuned_lk_fd2 --out results/velocity_field_surfmove_v3.csv > results/velocity_field_surfmove_v3.log 2>&1
  $PY -W ignore velocity_field_eval.py --scenes $HELDV --methods PIPs++_b2_256 PIPs++_ft3000_b2_256 PIPs++_S6_b2_256 PTV_tuned_ncc_fd2 PTV_tuned_lk_fd2 --out results/velocity_field_heldout_v3.csv > results/velocity_field_heldout_v3.log 2>&1
  for m in ratio_h15; do $PYB results_stats.py --csv results/surfmove_headline_v3.csv --metric $m --methods PIPs++_b2_256 PIPs++_S6_b2_256 PIPs++_S6_r48_256 PIPs++_S6_b2_512 PTV_tuned_ncc_fd2 PTV_tuned_lk_fd2 --out results/stats_surfmove_$m.md; done )
touch "$P/results/STAGE_SURFMOVE_DONE"; echo "scoring done $(date)"
# 5 videos with DeepMind's visualiser (tapnet plot_tracks_tails): all 16 viewpoints, dense moving-surface frames, S6 and S0 vs NCC
( cd "$P" && for s in $(echo $SM | tr ' ' '\n' | grep dense); do for suf in $BEST b2_256; do
    [ -f "results/videos_tapnet/${s}_${suf}_side_by_side.mp4" ] && continue
    PIP_TAP_SUFFIX=$suf PIP_TAP_MAXPTS=400 PIP_TAP_MAXPTV=1500 nice -n 10 $PY -W ignore make_tapnet_video.py "$s" >> results/videos_tapnet/render_surfmove.log 2>&1; echo "video $s $suf exit $?"; done; done )
touch "$P/results/STAGE_VIDEOS_DONE"; echo "videos done $(date)"
# 6 TAP-Vid-DAVIS: reference reproduction (weights/code audit, P-G9) and forgetting per checkpoint (P-G10)
mkdir -p results_davis; for c in "reference:$X/../reference_model/model-000200000.pth" "S6:$S6/model.pth" "S1:$PWD/ckpt_3000/model.pth" "S4:$PWD/ckpt_S4_final/model.pth" "S3:$PWD/ckpt_S3_final/model.pth" "S2:$PWD/ckpt_S2_final/model.pth" "S5:$PWD/ckpt_S5_final/model.pth"; do   # order = priority (P-G9, P-G10 need reference, S1, S4, S6); the rest if time
  id=${c%%:*}; ck=${c#*:}; [ -f "$ck" ] || { echo "DAVIS skip $id (no ckpt)"; continue; }; [ -f "results_davis/$id.csv" ] && continue
  echo "DAVIS $id start $(date)"; PYTORCH_ENABLE_MPS_FALLBACK=1 $PY -W ignore test_on_tap_mps.py --ckpt "$ck" --out "results_davis/$id.csv" > "results_davis/$id.log" 2>&1; echo "DAVIS $id exit $? $(date)"; done
touch "$P/results/STAGE_DAVIS_DONE"
# 7 spare: repo-style full-sequence tracking (S = 128 windows) on the held-out set, if track_fullseq.py exists
[ -f track_fullseq.py ] && for c in ":" "S6:$S6"; do id=${c%%:*}; PIP_CKPT_DIR=${c#*:} $PY -W ignore track_fullseq.py --scenes $HELDV --tag "${id:-S0}" >> fullseq.log 2>&1; done
echo "=== after_S6 end $(date) ==="
