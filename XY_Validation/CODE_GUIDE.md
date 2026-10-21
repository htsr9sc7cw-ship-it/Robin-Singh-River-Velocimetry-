# Code guide

One entry per script: what it does, which thesis section, table or figure it belongs to, its inputs and outputs, the command that runs it and the environment it needs. The entries are generated from the script headers by `make_code_guide.py`, so they equal the code. The commands behind every table are in `REPRODUCE.md`.

## Quick start

```bash
cd thesis_kit
python run.py setup      # once per computer
python run.py list       # names of all runnable scripts
python run.py demo       # one scene, numbers compared with the thesis (6 to 8 minutes)
python run.py <name>     # any single script
```

## Requirements

- **Operating system and hardware:** developed and tested on macOS with an Apple M-series GPU (8 GB unified memory); without a GPU the scripts run on the CPU, more slowly.

- **Python environments** (files in `environment/`): `pips2.yml` for PIPs++ and the evaluation (PyTorch, OpenEXR), `flowvelo.yml` for FlowVeloTool, `base.txt` for tables, statistics and figures (numpy, pandas, matplotlib).


`base.txt` (key packages, full list in the file):
```
numpy
pandas
matplotlib
pillow
scipy
```


`pips2.yml` (key packages, full list in the file):
```
  - python=3.8
      - torch==2.4.1
      - torchvision==0.19.1
      - numpy==1.24.4
      - scipy==1.10.1
      - matplotlib==3.7.3
      - pillow==10.4.0
      - opencv-python==4.8.0.76
      - imageio==2.35.1
      - OpenEXR>=3.2
      - tensorboardX==2.6.2.2
```


`flowvelo.yml` (key packages, full list in the file):
```
  - python=3.8
      - numpy==1.23.5
      - pandas==1.5.3
      - scipy==1.10.1
      - matplotlib==3.7.3
      - pillow==10.0.1
      - opencv-python==4.8.0.76
      - imageio==2.31.6
      - OpenEXR>=3.2
```

- **Blender 5.2** (`bpy`, `mathutils`): only for the scripts in `rerender/` (re-rendering). Not needed to reproduce the tables and figures from the stored results.

- **Third-party code** (not modified except for the changes listed in Appendix A.3): PIPs++ (`nets`, `utils`, `datasets`, `saverloader.py`), FlowVeloTool, DeepMind `tapvid_metrics.py` and `tapnet_viz.py`.

- **Paths in shell scripts:** 3 of the shell scripts (the long run_*.sh drivers of the study) contain the absolute path of the project drive in their first line (cd "/Volumes/..."). They document exactly how the study was run; to run them elsewhere, change that first line to the folder of this package (the Python scripts and run.py find each other relative to their own location and need no change).

- **Data not in the package** (too large): the other scenes of the final dataset, the Blender fluid caches (about 40 GB) and the TAP-Vid-DAVIS benchmark (2.5 GB, DeepMind). Scripts that need them say so when started.


## Scripts by group


### Data: fluid simulation, rendering, ground truth, tracers

**`rerender/accept_consistency.py`**  
- *Purpose:* Data-consistency acceptance for dataset v2 (tracker-independent):
- *Thesis section:* see README.md
- *Inputs:* see README.md
- *Outputs:* see README.md
- *Command:* `/opt/anaconda3/envs/pips2/bin/python accept_consistency.py <out>`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`rerender/bake_and_render.py`**  
- *Purpose:* R3/R4/R6: bake the fluid cache and render frames + Vector pass from Basefile_a_TRACERS.blend.
- *Thesis section:* 4.2, 4.3
- *Inputs:* Blender file with the fluid scene, camera name, frame range
- *Outputs:* fluid cache, rendered frames, motion-vector pass
- *Command:* `cd rerender && python bake_and_render.py`
- *Environment:* Blender 5.2 (bpy), or base Python for the helpers

**`rerender/flow_trials.py`**  
- *Purpose:* S1: low-resolution trial bakes to find a setting that sustains a current after the domain fills.
- *Thesis section:* see README.md
- *Inputs:* see README.md
- *Outputs:* see README.md
- *Command:* `cd rerender && python flow_trials.py`
- *Environment:* Blender 5.2 (bpy), or base Python for the helpers

**`rerender/gt_from_particles.py`**  
- *Purpose:* Ground truth for dataset v2: project the simulation's own particles through the render camera
- *Thesis section:* see README.md
- *Inputs:* see README.md
- *Outputs:* see README.md
- *Command:* `cd rerender && python gt_from_particles.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`rerender/make_ts_variant.py`**  
- *Purpose:* Speed ladder (PREREGISTRATION_v2_sweep.md, Sweep 2): save a copy of Basefile_a_TRACERS.blend with
- *Thesis section:* see README.md
- *Inputs:* see README.md
- *Outputs:* see README.md
- *Command:* `cd rerender && python make_ts_variant.py`
- *Environment:* Blender 5.2 (bpy), or base Python for the helpers

**`rerender/match_cameras.py`**  
- *Purpose:* R5: which camera produced which of the 15 original scenes?  Not recorded anywhere, so it is
- *Thesis section:* 4.3
- *Inputs:* rendered candidate cameras, original scene frames
- *Outputs:* camera_to_scene.csv and SIFT evidence
- *Command:* `/opt/anaconda3/envs/pips2/bin/python match_cameras.py render`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`rerender/moving_surface_control.py`**  
- *Purpose:* Moving-surface control (AUD21-1 item 3): the surface-only render of dataset v3 is pixel-static; only the composited
- *Thesis section:* see README.md
- *Inputs:* see README.md
- *Outputs:* see README.md
- *Command:* `/opt/anaconda3/envs/pips2/bin/python moving_surface_control.py out/v2/v2_Path4 out/v2/v2_Path4_surfmove`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`rerender/rasterise_gt.py`**  
- *Purpose:* Step 2 of the dataset ground truth (v3.2 rule, FIXLOG V2-1 fix b' + AUD21-4): from the projected particles of
- *Thesis section:* 4.4
- *Inputs:* projected FLIP particles of one viewpoint
- *Outputs:* per-pixel backward ground-truth field (EXR)
- *Command:* `/opt/anaconda3/envs/pips2/bin/python rasterise_gt.py out/v2/<scene>`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`rerender/rerender_clear.sh`**  
- *Purpose:* [FIXLOG R-1] re-render the two clear-water viewpoints with the clear material, then v3.2 GT + tracers.
- *Command:* `cd rerender && bash rerender_clear.sh`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`rerender/run_surfmove_all.sh`**  
- *Purpose:* Moving-surface versions of ALL viewpoints (Robin, 18 Sep: the GIFs must look like flowing water): the surface texture is
- *Command:* `cd rerender && bash run_surfmove_all.sh`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`rerender/speed_ladder.sh`**  
- *Purpose:* Speed ladder (PREREGISTRATION_v2_sweep.md Sweep 2). Per rung: bake -> calibrate -> render 2 cameras
- *Command:* `cd rerender && bash speed_ladder.sh`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`rerender/synth_tracers.py`**  
- *Purpose:* Composite sparse, persistent foam-like tracers onto surface-only renders, advected through the
- *Thesis section:* see README.md
- *Inputs:* see README.md
- *Outputs:* see README.md
- *Command:* `/opt/anaconda3/envs/pips2/bin/python synth_tracers.py <out> [--density 0.0025] [--seed 0]`
- *Environment:* pips2 environment (PyTorch, OpenEXR)


### PTV: parameters, driver, filter cascade, Lucas-Kanade sweep

**`ptv/corrected_cascade.py`**  
- *Purpose:* Corrected filter pass (thesis 4.2.4 F2, AUD21-11 B-1): re-run Eltner's steadiness and angle-range criteria on every
- *Command:* `/opt/anaconda3/bin/python corrected_cascade.py <v2_project dir>`
- *Environment:* flowvelo environment

**`ptv/derive_ptv_params.py`**  
- *Purpose:* Derive per-scene FlowVeloTool parameters FROM THE DATA and write them to ptv_params.csv.
- *Command:* `/opt/anaconda3/envs/pips2/bin/python derive_ptv_params.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`ptv/ptv_to_piprun.py`**  
- *Purpose:* Convert a FlowVelo run into the PIP_Run_* folder layout so that the SAME evaluator
- *Command:* `/opt/anaconda3/bin/python ptv_to_piprun.py --run ../out/ptv/<scene>/tuned_lk --project <project root>`
- *Environment:* flowvelo environment

**`ptv/run_flowvelo_ptv.py`**  
- *Purpose:* Run Anette Eltner's FlowVeloTool (unmodified, latest_version) on the Blender Elbersdorf
- *Command:* `/opt/anaconda3/envs/flowvelo/bin/python run_flowvelo_ptv.py --mode tuned_lk --scene all`
- *Environment:* flowvelo environment

**`ptv/run_lk_sweep.py`**  
- *Purpose:* Sweep 1 of PREREGISTRATION_v2_sweep.md: LK pyramid depth x template size, her source untouched.
- *Command:* `cd ptv && python run_lk_sweep.py`
- *Environment:* flowvelo environment


### Evaluation: PIPs++ drivers, scoring, statistics, tables

**`v2_project/PIP_Evaluation_gt.py`**  
- *Purpose:* (see header of the script)
- *Thesis section:* 3.5
- *Inputs:* tracker run folder in the PIPs++ layout, ground-truth field
- *Outputs:* per-step tables Trajs_F*.txt and evaluation summary
- *Command:* `cd v2_project && python PIP_Evaluation_gt.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/PIP_Execution.py`**  
- *Purpose:* (see header of the script)
- *Thesis section:* see README.md
- *Inputs:* see README.md
- *Outputs:* see README.md
- *Command:* `cd v2_project && python PIP_Execution.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/PIP_Execution_batch.py`**  
- *Purpose:* PIP_Execution_batch.py — deployment mode D4 (PREREGISTRATION_strategies.md): FlowVelo's scheme applied to PIPs++.
- *Thesis section:* 3.5 (mode D4)
- *Inputs:* frames of a variant, PIPs++ checkpoint
- *Outputs:* PIPs++ run folder with tracks and dropout mask
- *Command:* `cd v2_project && python PIP_Execution_batch.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/PIP_Execution_reinit.py`**  
- *Purpose:* PIP_Execution_reinit.py — PIPs++ with RE-INITIALISED tracking (Study A, PREREGISTRATION_v2_reinit.md).
- *Thesis section:* see README.md
- *Inputs:* see README.md
- *Outputs:* see README.md
- *Command:* `cd v2_project && python PIP_Execution_reinit.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/compare_v2.py`**  
- *Purpose:* Three-way comparison on dataset v2, both trackers through the SAME evaluator.
- *Thesis section:* 3.5
- *Inputs:* evaluation folders of all trackers
- *Outputs:* result CSV with ratio, direction, speed, coverage and TAP-Vid metrics
- *Command:* `/opt/anaconda3/envs/pips2/bin/python compare_v2.py [--ptv-eval]`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/field_consistency.py`**  
- *Purpose:* Whole-field consistency (AUD21-5 A-2): ALL tracer steps of a variant (not only whole-block, in-frame tracers as in
- *Thesis section:* 3.5, 5.1
- *Inputs:* tracer trajectories and ground-truth EXR of a variant
- *Outputs:* one line per variant in results/FIELD_CONSISTENCY.txt
- *Command:* `cd v2_project && python field_consistency.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/finish_surfmove.sh`**  
- *Purpose:* OPS-13: chain scoring steps that failed in after_S6 (PTV evaluation step was missing; --out prefix bug). CPU only, sequential.
- *Command:* `cd v2_project && bash finish_surfmove.sh`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/known_answer_eval.py`**  
- *Purpose:* Known-answer test THROUGH the evaluator (FIXLOG C4 process gap): the exact tracer trajectories
- *Thesis section:* 3.5, 5.1
- *Inputs:* tracers/trajs.npz of a variant, ground-truth field
- *Outputs:* known-answer verdict (PASS, PASS_FLOOR, FAIL) per variant
- *Command:* `/opt/anaconda3/bin/python known_answer_eval.py v2_Path4_dense v2_Overview_dense`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/make_results.py`**  
- *Purpose:* Results tables and figures from results/three_way_v2.csv (corrected scoring, FIXLOG C1-C3).
- *Thesis section:* see README.md
- *Inputs:* see README.md
- *Outputs:* see README.md
- *Command:* `/opt/anaconda3/bin/python make_results.py          (base interpreter: pandas + matplotlib)`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/make_results_reinit.py`**  
- *Purpose:* Tables and figures for REINIT-1 (re-initialised PIPs++, matched-cadence FlowVelo) and Study B (fine-tuned).
- *Thesis section:* 5
- *Inputs:* result CSV files
- *Outputs:* result tables and figures
- *Command:* `/opt/anaconda3/bin/python make_results_reinit.py`
- *Environment:* flowvelo environment

**`v2_project/make_tapnet_video.py`**  
- *Purpose:* Videos rendered with DeepMind's own tapnet visualiser (tapnet_viz.plot_tracks_tails / paint_point_track, vendored):
- *Thesis section:* see README.md
- *Inputs:* see README.md
- *Outputs:* see README.md
- *Command:* `cd v2_project && python make_tapnet_video.py`
- *Environment:* flowvelo environment

**`v2_project/render_in_gap.sh`**  
- *Purpose:* Renders DeepMind-visualiser (tapnet plot_tracks_tails) videos in a GPU gap: waits for a stage marker, pauses (SIGSTOP)
- *Command:* `cd v2_project && bash render_in_gap.sh`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/render_videos_S6.sh`**  
- *Purpose:* has finished (or 05:00), then renders the 16 dense moving-water viewpoints sequentially; skip-if-done.
- *Command:* `cd v2_project && bash render_videos_S6.sh`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/results_stats.py`**  
- *Purpose:* Statistics for the headline tables (plan: recommendation 1). Variants are the unit.  For a results CSV with columns
- *Thesis section:* 3.5
- *Inputs:* result CSV
- *Outputs:* medians with bootstrap intervals and paired sign tests
- *Command:* `cd v2_project && python results_stats.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/run_on_drive.sh`**  
- *Purpose:* Drive-safe runner: bash run_on_drive.sh <script> [args]  — relaunches the (resumable) script whenever the external drive
- *Command:* `cd v2_project && bash run_on_drive.sh`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/run_pips_batch.sh`**  
- *Purpose:* D4 batch mode runner: bash run_pips_batch.sh "<scenes>" "<every>:<img>" [ckpt-dir] [prefix]   -> suffix <prefix>_b<every>_<img>
- *Command:* `cd v2_project && bash run_pips_batch.sh`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/run_pips_reinit.sh`**  
- *Purpose:* Re-initialised PIPs++ (REINIT-1, PREREGISTRATION_v2_reinit.md).  Usage:
- *Command:* `bash run_pips_reinit.sh "<scenes space-separated>" "<configs space-separated>"   configs = k:img, e.g. "1:512 2:512 48:512 1:256 2:256"`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/run_pips_v2.sh`**  
- *Purpose:* PIPs++ (untrained, sorted frames) + evaluation with PIP_FIX_SIGN=1 for every linked v2 scene not yet run.
- *Command:* `cd v2_project && bash run_pips_v2.sh`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/run_ptv_fd.sh`**  
- *Purpose:* FlowVelo at matched re-detection cadence (REINIT-1): modes tuned_ncc_fd<k> / tuned_lk_fd<k>.  Usage:
- *Command:* `bash run_ptv_fd.sh "<scenes>" "<modes>"      e.g. "v2_Path4_dense v2_Low_1_dense" "tuned_ncc_fd1 tuned_ncc_fd2 tuned_lk_fd1 tuned_lk_fd2"`
- *Environment:* flowvelo environment

**`v2_project/run_reinit_all.sh`**  
- *Purpose:* REINIT-1 unattended driver (PREREGISTRATION_v2_reinit.md).  Start / resume with exactly:
- *Command:* `cd v2_project && bash run_reinit_all.sh`
- *Environment:* flowvelo environment

**`v2_project/saverloader.py`**  
- *Purpose:* (see header of the script)
- *Command:* `cd v2_project && python saverloader.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/scene_config.py`**  
- *Purpose:* Shared configuration for PIP_Execution.py, PIP_Evaluation.py and make_visuals.py.
- *Thesis section:* see README.md
- *Inputs:* see README.md
- *Outputs:* see README.md
- *Command:* `cd v2_project && python scene_config.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/tapnet_viz.py`**  
- *Purpose:* Visualization utility functions.
- *Command:* `cd v2_project && python tapnet_viz.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/tapnet_viz_utils_upstream.py`**  
- *Purpose:* Visualization utility functions.
- *Command:* `cd v2_project && python tapnet_viz_utils_upstream.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/tapvid_eval.py`**  
- *Purpose:* TAP-Vid / PIPs++-repo metrics for every evaluation folder (plan 18 Sep; PREREGISTRATION_strategies.md).
- *Thesis section:* see README.md
- *Inputs:* see README.md
- *Outputs:* see README.md
- *Command:* `/opt/anaconda3/envs/pips2/bin/python tapvid_eval.py --scenes ... --methods PIPs++ PIPs++_S2_r2_256 PTV_tuned_ncc_fd2 ... --out tapvid_v3.csv`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/tapvid_metrics.py`**  
- *Purpose:* compute_tapvid_metrics, vendored unchanged from google-deepmind/tapnet (tapnet/tapvid/evaluation_datasets.py,
- *Command:* `cd v2_project && python tapvid_metrics.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/velocity_field_eval.py`**  
- *Purpose:* Surface-velocity-field accuracy in hydrometry terms (plan: T5.15, pre-registration P-G12).
- *Thesis section:* 3.5, 5.7
- *Inputs:* evaluation tables of a tracker
- *Outputs:* bias, field RMSE and coverage per variant
- *Command:* `cd v2_project && python velocity_field_eval.py`
- *Environment:* base Python (numpy, pandas, matplotlib)


### Retraining: strategies, TAP-Vid-DAVIS test

**`finetune/after_S6.sh`**  
- *Purpose:* Saturday automation (plan: decision Fri 09:50 + P-G14, TAP-Vid-DAVIS audit/forgetting, videos for all 16 viewpoints).
- *Command:* `cd finetune && bash after_S6.sh`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`finetune/mem_probe.py`**  
- *Purpose:* (see header of the script)
- *Thesis section:* see README.md
- *Inputs:* see README.md
- *Outputs:* see README.md
- *Command:* `cd finetune && python mem_probe.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`finetune/run_S6.sh`**  
- *Purpose:* S6 rerun after the 512-px OOM (FIXLOG OPS-7): README stage 2 adapted to the 8 GB M1 — the largest clip that fits at native 512 px is
- *Command:* `cd finetune && bash run_S6.sh`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`finetune/run_davis.sh`**  
- *Purpose:* TAP-Vid-DAVIS at the window that fits the 8 GB M1 (S 32; the repo's S 128 and S 64 run out of MPS memory, probe 19 Sep 23:00).
- *Command:* `cd finetune && bash run_davis.sh`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`finetune/run_finetune.sh`**  
- *Purpose:* Study B driver: fine-tune, then score every checkpoint on the held-out variants with the Study-A winner setting.
- *Command:* `cd finetune && bash run_finetune.sh`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`finetune/run_strategies.sh`**  
- *Purpose:* Study C driver (PREREGISTRATION_strategies.md, 18 Sep): S2 -> S3 -> S4 -> S5 -> pick -> S6, each: train (resumable) ->
- *Command:* `cd finetune && bash run_strategies.sh`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`finetune/saverloader.py`**  
- *Purpose:* (see header of the script)
- *Command:* `cd finetune && python saverloader.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`finetune/test_on_tap_mps.py`**  
- *Purpose:* test_on_tap_mps.py — the PIPs++ repository's TAP-Vid-DAVIS test (test_on_tap.py) with a device and checkpoint argument;
- *Thesis section:* 3.5, 5.8
- *Inputs:* TAP-Vid-DAVIS pickle, checkpoint
- *Outputs:* delta_avg, survival and median error per checkpoint
- *Command:* `cd finetune && python test_on_tap_mps.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`finetune/train_v3.py`**  
- *Purpose:* train_v3.py — fine-tune PIPs++ on the Elbersdorf renders (Study B, PREREGISTRATION_finetune.md).
- *Thesis section:* 3.4, 5.6
- *Inputs:* tracer trajectories and frames of the training viewpoints, checkpoint
- *Outputs:* checkpoints and training log
- *Command:* `/opt/anaconda3/envs/pips2/bin/python train_v3.py --max-iters 3000 --max-hours 8`
- *Environment:* pips2 environment (PyTorch, OpenEXR)


### Diagrams: one script per picture

**`v2_project/figure_scripts/check_figures.py`**  
- *Purpose:* Checks every figure script: (1) does it run, (2) does the picture look professional, (3) are the numbers in the
- *Command:* `python check_figures.py            all figures, short report, exit code 1 if anything FAILS`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/figure_scripts/fig_1_01_route_map.py`**  
- *Purpose:* Figure 1.1  Route map of the study.
- *Picture:* figT_route_map.png (computes from result files)
- *Command:* `cd v2_project/figure_scripts && python fig_1_01_route_map.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_3_01_methodology.py`**  
- *Purpose:* Figure 3.1  Methodology at a glance.
- *Picture:* figV_methodology.png (schematic)
- *Command:* `cd v2_project/figure_scripts && python fig_3_01_methodology.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_3_02_retraining_tree.py`**  
- *Purpose:* Figure 3.2  Retraining strategies as a tree.
- *Picture:* figP_strategy_tree.png (computes from result files)
- *Command:* `cd v2_project/figure_scripts && python fig_3_02_retraining_tree.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_3_03_deployment_modes.py`**  
- *Purpose:* Figure 3.3  Deployment modes: the same 48 frames, four ways of driving a tracker (D3, D1, D4, FlowVelo).
- *Picture:* figQ_deployment_modes.png (schematic)
- *Command:* `cd v2_project/figure_scripts && python fig_3_03_deployment_modes.py`
- *Environment:* flowvelo environment

**`v2_project/figure_scripts/fig_3_04_how_trackers_search.py`**  
- *Purpose:* Figure 3.4  How the three trackers find the next position: NCC, LK and PIPs++ in three plain rows.
- *Picture:* figR_mechanisms.png (schematic)
- *Command:* `cd v2_project/figure_scripts && python fig_3_04_how_trackers_search.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_3_05_example_frames.py`**  
- *Purpose:* Figure (example frames) of the final dataset.
- *Picture:* see script (schematic)
- *Command:* `cd v2_project/figure_scripts && python fig_3_05_example_frames.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_3_06_reach_layout.py`**  
- *Purpose:* Figure (reach layout) of the simulated reach and the camera positions.
- *Picture:* see script (computes from result files)
- *Command:* `cd v2_project/figure_scripts && python fig_3_06_reach_layout.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_3_07_ptv_pipeline.py`**  
- *Purpose:* Figure 4.3  Processing steps of the PTV implementation (schematic).
- *Picture:* figZ_ptv_pipeline.png (schematic)
- *Command:* `cd v2_project/figure_scripts && python fig_3_07_ptv_pipeline.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_3_08_ratio_concept.py`**  
- *Purpose:* Figure 4.4  Concept of the ratio for one step (schematic; the numbers are those of the illustration in Sect. 4.5).
- *Picture:* see script (schematic)
- *Command:* `cd v2_project/figure_scripts && python fig_3_08_ratio_concept.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_5_01_rmse_ratio_vs_speed.py`**  
- *Purpose:* Figure 5.1  Error ratio against flow speed (28 muddy variants, four methods).
- *Picture:* figA_rmse_ratio_vs_speed.png (schematic)
- *Command:* `cd v2_project/figure_scripts && python fig_5_01_rmse_ratio_vs_speed.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_5_02_position_accuracy_by_speed.py`**  
- *Purpose:* Figure 5.2  Position accuracy by speed group: fraction of sub-steps within an error threshold.
- *Picture:* figB_delta_accuracy_by_speed.png (schematic)
- *Command:* `cd v2_project/figure_scripts && python fig_5_02_position_accuracy_by_speed.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_5_03_direction_and_speed.py`**  
- *Purpose:* Figure 5.3  Direction agreement and speed ratio against flow speed.
- *Picture:* figC_direction_and_speed_ratio.png (schematic)
- *Command:* `cd v2_project/figure_scripts && python fig_5_03_direction_and_speed.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_5_04_sparse_vs_dense.py`**  
- *Purpose:* Figure 5.4  Sparse against dense tracers: Error ratio per camera view and method.
- *Picture:* figE_sparse_vs_dense.png (schematic)
- *Command:* `cd v2_project/figure_scripts && python fig_5_04_sparse_vs_dense.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_5_05_filter_cascade.py`**  
- *Purpose:* Figure 5.5  FlowVelo filter cascade: tracks remaining after each filter stage, by mode.
- *Picture:* figD_filter_cascade.png (schematic)
- *Command:* `cd v2_project/figure_scripts && python fig_5_05_filter_cascade.py`
- *Environment:* flowvelo environment

**`v2_project/figure_scripts/fig_5_06_speed_ladder.py`**  
- *Purpose:* Figure 5.6  Speed ladder: Error ratio as the same simulation is replayed at 1/4, 1/2 and full speed.
- *Picture:* figG_speed_ladder.png (computes from result files)
- *Command:* `cd v2_project/figure_scripts && python fig_5_06_speed_ladder.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_5_07_reinit_pilot.py`**  
- *Purpose:* Figure 5.7  Re-initialisation pilot: Error ratio of every setting on the four pilot variants.
- *Picture:* figH_reinit_pilot.png (computes from result files)
- *Command:* `cd v2_project/figure_scripts && python fig_5_07_reinit_pilot.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_5_08_retracking_every_2_frames.py`**  
- *Purpose:* Figure 5.8  Re-tracking every 2 frames: all 28 variants, Error ratio against flow speed.
- *Picture:* figI_reinit_full_vs_speed.png (computes from result files)
- *Command:* `cd v2_project/figure_scripts && python fig_5_08_retracking_every_2_frames.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_5_09_worked_example_pretrained.py`**  
- *Purpose:* Figure 5.9  Worked example, pre-trained model: Path4 dense, pre-trained PIPs++ re-tracked every 2 frames.
- *Picture:* see script (schematic)
- *Command:* `cd v2_project/figure_scripts && python fig_5_09_worked_example_pretrained.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/figure_scripts/fig_5_10_worked_example_first_frame.py`**  
- *Purpose:* Figure 5.10  Worked example, first frame: Path4 dense, ground truth, PTV NCC, PTV LK and pre-trained PIPs++.
- *Picture:* see script (schematic)
- *Command:* `cd v2_project/figure_scripts && python fig_5_10_worked_example_first_frame.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/figure_scripts/fig_5_11_finetune_heldout.py`**  
- *Purpose:* Figure 5.11  Fine-tuned PIPs++ on the held-out camera views: Error ratio over the 15-frame horizon per variant.
- *Picture:* figJ_finetune_heldout.png (computes from result files)
- *Command:* `cd v2_project/figure_scripts && python fig_5_11_finetune_heldout.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_5_12_worked_examples_finetuned.py`**  
- *Purpose:* Figure 5.12  Worked examples, fine-tuned model: Path4 dense (left) and Low 1 dense (right), FT-1 re-tracked every 2 frames.
- *Picture:* see script (schematic)
- *Command:* `cd v2_project/figure_scripts && python fig_5_12_worked_examples_finetuned.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/figure_scripts/fig_5_13_strategies_heldout.py`**  
- *Purpose:* Figure 5.13  Retraining strategies on the ten held-out variants: median ratio with 95 % bootstrap interval.
- *Picture:* figK_strategies_heldout.png (computes from result files)
- *Command:* `cd v2_project/figure_scripts && python fig_5_13_strategies_heldout.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_5_14_training_curves.py`**  
- *Purpose:* Figure 5.14  Training error of all runs: position error per training clip, smoothed, logarithmic axis.
- *Picture:* figR1_training_curves.png (computes from result files)
- *Command:* `cd v2_project/figure_scripts && python fig_5_14_training_curves.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_5_15_headline_moving_water.py`**  
- *Purpose:* Figure 5.15  Headline comparison on moving water: ratio (15-frame horizon), speed ratio and coverage.
- *Picture:* figL_surfmove_headline.png (computes from result files)
- *Command:* `cd v2_project/figure_scripts && python fig_5_15_headline_moving_water.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_5_16_heatmap_all_variants.py`**  
- *Purpose:* Figure 5.16  Heat map of all variants: Error ratio (15-frame horizon) of every method on every moving-water variant,
- *Picture:* figM_heatmap_surfmove.png (computes from result files)
- *Command:* `cd v2_project/figure_scripts && python fig_5_16_heatmap_all_variants.py`
- *Environment:* flowvelo environment

**`v2_project/figure_scripts/fig_5_17_velocity_field_maps.py`**  
- *Purpose:* Figure 5.17  Surface-velocity field on Path4 dense (moving water, 32-px cells): ground truth, S6 and NCC.
- *Picture:* see script (computes from result files)
- *Command:* `cd v2_project/figure_scripts && python fig_5_17_velocity_field_maps.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/figure_scripts/fig_5_18_davis_retention.py`**  
- *Purpose:* Figure 5.18  TAP-Vid-DAVIS after retraining: delta_avg of the reference weights and of each strategy
- *Picture:* figR4_davis.png (computes from result files)
- *Command:* `cd v2_project/figure_scripts && python fig_5_18_davis_retention.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_5_19_results_at_a_glance.py`**  
- *Purpose:* Figure 5.19  Results at a glance.
- *Picture:* figU_results_at_glance.png (computes from result files)
- *Command:* `cd v2_project/figure_scripts && python fig_5_19_results_at_a_glance.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_6_01_accuracy_vs_coverage.py`**  
- *Purpose:* Figure 6.1  Accuracy against coverage, one point per moving-water variant.
- *Picture:* figS_accuracy_vs_coverage.png (computes from result files)
- *Command:* `cd v2_project/figure_scripts && python fig_6_01_accuracy_vs_coverage.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/fig_common.py`**  
- *Purpose:* Shared helpers for the figure scripts: paths, saving, the result tables and the method styles.
- *Picture:* see script (computes from result files)
- *Command:* `cd v2_project/figure_scripts && python fig_common.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/figure_scripts/run_all_figures.py`**  
- *Purpose:* Runs every fig_*.py of this folder one after the other and prints OK / FAILED per figure.
- *Command:* `cd v2_project/figure_scripts && python run_all_figures.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`v2_project/figure_scripts/tud_style.py`**  
- *Purpose:* Shared figure style of the thesis, after the corporate design of TU Dresden.
- *Command:* `cd v2_project/figure_scripts && python tud_style.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`v2_project/figure_scripts/worked_example.py`**  
- *Purpose:* Helper of the three worked-example figures (5.9, 5.10, 5.12): one frame, the true displacement and the tracks of
- *Command:* `cd v2_project/figure_scripts && python worked_example.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)


### Thesis build and checks

**`thesis/table_3_2.py`**  
- *Purpose:* (see header of the script)
- *Thesis section:* see README.md
- *Inputs:* see README.md
- *Outputs:* see README.md
- *Command:* `cd thesis && python table_3_2.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)


### Entry points and helpers

**`convert_uv_to_xy.py`**  
- *Purpose:* convert_uv_to_xy.py — converts every Elbersdorf scene's Blender vector EXRs (U,V displacement)
- *Thesis section:* see README.md
- *Inputs:* see README.md
- *Outputs:* see README.md
- *Command:* `cd . && python convert_uv_to_xy.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`demo.py`**  
- *Purpose:* demo.py: the whole study on one scene, start to finish, with real runs (no stored results are used).
- *Command:* `python run.py demo            about 8 min on a laptop GPU (Apple M-series), longer on a CPU`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`flow_core.py`**  
- *Purpose:* flow_core.py -- the flow maths for the dense visualisation. No drawing here.
- *Thesis section:* see README.md
- *Inputs:* see README.md
- *Outputs:* see README.md
- *Command:* `cd . && python flow_core.py`
- *Environment:* base Python (numpy, pandas, matplotlib)

**`link_external.sh`**  
- *Purpose:* Link the data and the two third-party code bases that the scripts need into this folder.
- *Command:* `cd . && bash link_external.sh`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`lk_sweep_demo.py`**  
- *Purpose:* lk_sweep_demo.py: Lucas-Kanade pyramid depth 2 to 5 on the demo scene, scored, next to the thesis values (Sect. 5.3, Fig. 5.6 text).
- *Command:* `python run.py lk_sweep          (about 4 min)`
- *Environment:* flowvelo environment

**`make_code_guide.py`**  
- *Purpose:* and a check that every file named in REPRODUCE.md and in the guide exists
- *Thesis section:* Appendix A.2
- *Inputs:* the headers of all scripts of this package, REPRODUCE.md, ../environment/*, run.py
- *Outputs:* CODE_GUIDE.md (one entry per script: purpose, thesis section, inputs, outputs, command, environment)
- *Command:* `python make_code_guide.py            # writes CODE_GUIDE.md next to this file`
- *Environment:* flowvelo environment
- *Requires:* Python 3.9 or later, standard library only.

**`rasterise_demo.py`**  
- *Purpose:* rasterise_demo.py: exact ground truth from the simulated particles, rebuilt and compared with the ground truth of the thesis (Sect. 4.4).
- *Command:* `python run.py rasterise_gt        (about 6 min)`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`rebuild_xy_seeds.py`**  
- *Purpose:* rebuild_xy_seeds.py -- rebuild the X,Y seed tracks in the real PointOdyssey format.
- *Thesis section:* see README.md
- *Inputs:* see README.md
- *Outputs:* see README.md
- *Command:* `cd . && python rebuild_xy_seeds.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`run.py`**  
- *Purpose:* ONE command for every script of the thesis (Mac, Windows, Linux):
- *Command:* `python run.py setup             once per computer: creates the two conda environments and installs the base packages`
- *Environment:* pips2 environment (PyTorch, OpenEXR)

**`verify_xy_convention.py`**  
- *Purpose:* verify_xy_convention.py -- prove every converted X,Y file matches the confirmed U,V convention.
- *Thesis section:* see README.md
- *Inputs:* see README.md
- *Outputs:* see README.md
- *Command:* `cd . && python verify_xy_convention.py`
- *Environment:* pips2 environment (PyTorch, OpenEXR)


## Commands behind every table and figure of the thesis

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

