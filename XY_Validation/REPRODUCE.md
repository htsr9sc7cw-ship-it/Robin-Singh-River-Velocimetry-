# REPRODUCE.md — exact commands behind every table of the thesis (root: `XY_Validation/`; interpreters: `pips2` env for PIPs++, `flowvelo` env for FlowVelo, base `/opt/anaconda3/bin/python` for scoring)

## 0 Data
- Renders + exact ground truth: `rerender/` (Blender FLIP scene, `bake_and_render.py` (run with Blender 5.2: `blender -b -P bake_and_render.py`); moving surface: `run_surfmove_all.sh`) → `rerender/out/v2/<view>/{images_tracers_*,vector,tracers_*}`; scene links in `v2_project/Vectors_and_Images/v2_<view>_{dense,sparse}` and `v2_<view>_surfmove_{dense,sparse}` (absolute links, FIXLOG OPS-12).
- Ground-truth known-answer control (must PASS before any table): `cd v2_project && python known_answer_eval.py v2_Path4_dense v2_Overview_dense v2_Path4_surfmove_dense`.

## 1 Pre-trained PIPs++ (Sects. 5.2–5.12)
- Inherited seeding, 48-frame blocks: `bash v2_project/run_pips_v2.sh` (drivers `PIP_Execution.py`, `PIP_Evaluation_gt.py`; PIP_FIX_SIGN=1 PIP_FIX_TRANSPOSE=1).
- Re-initialised every k frames: `bash run_pips_reinit.sh "<scenes>" "2:256"` (k=48 reproduces the inherited run, diff 0.0).
- Fresh seeds every 2 frames (D4): `bash run_pips_batch.sh "<scenes>" "2:256"`; native scale `"2:512"`.
- FlowVelo at matched cadence: `bash run_ptv_fd.sh "<scenes>" "tuned_ncc_fd2 tuned_lk_fd2"` (params `ptv_params_v2.csv` from `ptv/derive_ptv_params.py`).
- Scoring: `python compare_v2.py --ptv-eval --scenes … --modes tuned_ncc_fd2 tuned_lk_fd2 --ptv-block-len 48 --out <name>.csv` then the same without `--ptv-eval` and with `--pips-suffixes r2_256 b2_256 …` → `results/<name>.csv` (Tables 5.10–5.13: `three_way_v3_k2.csv`, `three_way_v3_reinit.csv`, `finetune_v3.csv`).

## 2 Retraining strategies (Sect. 5.14; register `finetune/PREREGISTRATION_strategies.md`)
- `cd finetune && bash run_strategies.sh` (S2–S5 train + evaluate; recipes in the script lines 31–43); S6: `bash run_S6.sh` (from `ckpt_S3_final`, crop 384, S 12, N 24).
- Held-out scoring: `compare_v2.py --scenes $HELD … --pips-suffixes S2_r2_256 S2_r48_256 S2_b2_256 S3_… S4_… S5_… --out strategies_v3.csv`; S6: `--pips-suffixes S6_r2_256 S6_r48_256 S6_b2_256 S6_b2_512 --out s6_heldout_v3.csv`.
- Selection rule (lowest held-out median ratio_h15 in the best mode; ties S2<S4<S3<S5) → `results/STRATEGY_WINNER.txt` (S3). Statistics: `python results_stats.py --csv results/strategies_v3.csv --metric ratio_h15 --exclude v2_Path2_dense --out results/stats_strategies_ratio_h15.md`.

## 3 Headline on moving water (Sect. 5.16)
- `bash finetune/after_S6.sh` (S0 + S6 D4 on 32 surfmove variants; FlowVelo fd2) and `bash v2_project/finish_surfmove.sh` (scoring): outputs `results/surfmove_headline_v3.csv`, `tapvid_surfmove_v3.csv` (`tapvid_eval.py`), `velocity_field_surfmove_v3.csv` (`velocity_field_eval.py`), `stats_surfmove_ratio_h15.md`; tables T5_16/T5_17 built by the snippets recorded in STATE.md (20 Sep 05:xx).

## 4 TAP-Vid-DAVIS (Sect. 5.17)
- Data: `finetune/tapvid_davis/tapvid_davis/tapvid_davis.pkl` (DeepMind). `bash finetune/run_davis.sh` → `finetune/results_davis/<ckpt>_S32.csv` (`test_on_tap_mps.py --S 32`, identical for all checkpoints).

## 5 Figures and videos
- `python make_results_reinit.py` (Tables 5.7–5.13, figs H–J); Figure 5.15: snippet in STATE.md; videos: `PIP_TAP_SUFFIX=S6_b2_256 PIP_TAP_MAXPTS=150 python make_tapnet_video.py <scene>` → `results/videos_tapnet/{h264,gif}` (DeepMind `plot_tracks_tails`, vendored `tapnet_viz.py`).

## 6 Registers, logs, weights
- Registers: `v2_project/PREREGISTRATION_v2*.md`, `finetune/PREREGISTRATION_finetune.md`, `finetune/PREREGISTRATION_strategies.md` (+ outcomes). Logs: `FIXLOG.md` (every fault with time and cost), `CHANGE_REGISTER.md`, `STATE.md`, `thesis/APPENDIX_B_modifications.md`.
- Weights: `finetune/ckpt_3000/model.pth` (S1), `finetune/ckpt_S{2,3,4,5}_final/model.pth`, `finetune/ckpt_S6/model-003000.pth` (final). Reference: `reference_model/model-000200000.pth` (audited, Sect. 5.17).
