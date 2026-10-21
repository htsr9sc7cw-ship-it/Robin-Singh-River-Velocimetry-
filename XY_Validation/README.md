# Code of the thesis "Evaluation of AI-Based Particle Tracking Method for Surface Water Velocity Estimation"

Author: Robin Singh. This package holds every script that the thesis refers to (Appendix A.2), cleaned and in the folder
layout of the project (`XY_Validation/`). The scripts find each other relative to their own location, so keep the layout.
The code is the code that produced the results. Cleaning means a uniform header (purpose, thesis section, inputs, outputs)
and formatting with `black`; `RUN_CHECK.txt` shows that the code of every file equals the original and which scripts were run.

## Contents

| Folder | Scripts |
|---|---|
| `rerender/` | Blender fluid bake and render, camera matching, ground-truth projection, tracers, moving-surface control, render shell scripts |
| `v2_project/` | PIPs++ drivers (`PIP_Execution*.py`), the shared evaluator (`PIP_Evaluation_gt.py`), comparison and metrics (`compare_v2.py`, `velocity_field_eval.py`, `results_stats.py`, `tapvid_*`), figures and tables |
| `ptv/` | FlowVelo parameters, driver, filter cascade, LK pyramid sweep, adapter to the PIPs++ layout |
| `finetune/` | retraining (`train_v3.py`), TAP-Vid-DAVIS test, memory probe, run scripts for the strategies |
| `registers/` | the pre-registrations written before the experiments |
| `REPRODUCE.md` | the exact command for every table and figure |

Third-party code is not included and was not modified, except for the small changes listed in Appendix A.3 of the thesis: the PIPs++ code (`nets`, `utils`, `datasets`, `saverloader.py`;
https://github.com/aharley/pips2, commit 8b5bd9e), FlowVeloTool (https://github.com/AnetteEltner/FlowVeloTool, commit 7f40008)
and Blender 5.2 (`bpy`, `mathutils`; only for the scripts in `rerender/`). DeepMind's `tapvid_metrics.py` and `tapnet_viz.py` are
included with their licence headers (changes listed in Appendix A.3).

## Set-up

1. Three Python environments are used: `pips2` (PyTorch, for PIPs++), `flowvelo` (NumPy < 1.24, OpenCV, for FlowVelo) and a base
   Python with NumPy, pandas, matplotlib for scoring and figures.
2. Link the data and the third-party code (only symbolic links are made, nothing is copied or changed):

```
bash link_external.sh /path/to/XY_Validation
```

## Running one script (examples)

```
cd v2_project
python known_answer_eval.py v2_Path4_dense                                  # known-answer control, expects PASS
XYV_DATA=$PWD/Vectors_and_Images python field_consistency.py v2_Path4_dense   # whole-field consistency (pips2 env)
python compare_v2.py --help                                                  # scoring of all trackers
python results_stats.py --csv results/strategies_v3.csv --metric ratio_h15 --out stats.md
python make_strategy_figures.py                                              # route map, methodology figure, results at a glance
cd ../finetune
python train_v3.py --help                                                    # retraining; options for S, crop, N, learning rate
```

Scripts that need Blender (`rerender/`) run inside Blender, for example
`Blender --background Basefile_a_TRACERS.blend --python bake_and_render.py -- render --camera Camera.Low_1 --frames 100 130`.
The data (renders, ground truth, tracer trajectories) and the fine-tuned weights are large and are delivered on the project drive.
