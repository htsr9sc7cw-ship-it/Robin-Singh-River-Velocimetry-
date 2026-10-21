#!/bin/bash
# OPS-13: chain scoring steps that failed in after_S6 (PTV evaluation step was missing; --out prefix bug). CPU only, sequential.
cd "$(dirname "$0")"; exec >> finish_surfmove.log 2>&1; echo "=== finish_surfmove start $(date) ==="
SM=$(ls Vectors_and_Images | grep surfmove | tr '\n' ' ')
nice -n 5 /opt/anaconda3/bin/python compare_v2.py --ptv-eval --scenes $SM --modes tuned_ncc_fd2 tuned_lk_fd2 --ptv-block-len 48 --workers 3 --out surfmove_headline_v3.csv; echo "ptv-eval exit $? $(date)"
nice -n 5 /opt/anaconda3/bin/python compare_v2.py --scenes $SM --modes tuned_ncc_fd2 tuned_lk_fd2 --pips-suffixes b2_256 S6_b2_256 --ptv-block-len 48 --workers 3 --out surfmove_headline_v3.csv; echo "score exit $? $(date)"
nice -n 5 /opt/anaconda3/envs/pips2/bin/python -W ignore tapvid_eval.py --scenes $SM --methods PIPs++_b2_256 PIPs++_S6_b2_256 PTV_tuned_ncc_fd2 PTV_tuned_lk_fd2 --out tapvid_surfmove_v3.csv; echo "tapvid exit $? $(date)"
nice -n 5 /opt/anaconda3/envs/pips2/bin/python -W ignore velocity_field_eval.py --scenes $SM --methods PIPs++_b2_256 PIPs++_S6_b2_256 PTV_tuned_ncc_fd2 PTV_tuned_lk_fd2 --out results/velocity_field_surfmove_v3.csv; echo "velocity exit $? $(date)"
/opt/anaconda3/bin/python results_stats.py --csv results/surfmove_headline_v3.csv --metric ratio_h15 --exclude v2_Path3_clear_surfmove_dense v2_Path3_clear_surfmove_sparse v2_high_angle_clear_surfmove_dense v2_high_angle_clear_surfmove_sparse --out results/stats_surfmove_ratio_h15.md
touch results/STAGE_SURFMOVE_SCORED; echo "=== finish_surfmove end $(date) ==="
# S6 videos for the 16 dense moving-water viewpoints (h264 + gif written by the script)
for s in $(echo $SM | tr ' ' '\n' | grep dense); do [ -f "results/videos_tapnet/${s}_S6_b2_256_side_by_side.mp4" ] && continue; PIP_TAP_SUFFIX=S6_b2_256 PIP_TAP_MAXPTS=250 PIP_TAP_MAXPTV=1500 nice -n 10 /opt/anaconda3/envs/pips2/bin/python -W ignore make_tapnet_video.py "$s"; echo "video $s S6 exit $? $(date)"; done
touch results/STAGE_VIDEOS_S6_DONE; echo "=== videos end $(date) ==="
