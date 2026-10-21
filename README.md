# Evaluation of AI-Based Particle Tracking for Surface Water Velocity Estimation: code

Code of the Master thesis *Evaluation of AI-Based Particle Tracking Method for Surface Water Velocity Estimation* (Robin Singh, TU Dresden, 2026; supervisors Prof. Dr. Anette Eltner and Dr. Pedro Zamboni).

The thesis evaluates the learned point tracker PIPs++ (pre-trained and retrained) against particle tracking velocimetry (PTV, FlowVeloTool) on a synthetic river data set with known ground truth. This repository contains every script written for the study: ground-truth construction, tracer synthesis, tracker drivers, scoring, statistics, result tables and the scripts of all diagrams.

* `CODE_GUIDE.md`: one entry per script (purpose, thesis section, inputs, outputs, command, environment) and the requirements.
* `XY_Validation/REPRODUCE.md`: the exact command behind every table of the thesis.
* `environment/`: package lists (`base.txt`, `pips2.yml`, `flowvelo.yml`).
* `run.py`: `python run.py list` shows all runnable scripts, `python run.py demo` reproduces the numbers of one scene.

## Repository layout

| Folder | Content |
|---|---|
| `XY_Validation/` | The study: `rerender/` (ground truth, tracers), `ptv/` (PTV drivers and parameters), `v2_project/` (PIPs++ drivers, scoring, statistics, tables, figure scripts), `finetune/` (retraining), `registers/` (pre-registered predictions) |
| `Diagram_Scripts/` | One script per diagram of the thesis, a one-command runner and the result tables they read |
| `thesis_tools/` | Scripts that recompute and check the numbers of the thesis |
| `thesis_build/` | Scripts that assemble, format and check the thesis document |
| `digital_appendix_tools/` | Scripts that assemble and verify the digital appendix and the code package |
| `environment/` | Package lists for the Python environments |
| `run.py` | Entry point: `python run.py list`, `python run.py demo` |

## What is not in this repository
Large files and third-party code are not included (see `THIRD_PARTY.md`): model weights, rendered data of the final data set, the Blender fluid caches and the TAP-Vid-DAVIS benchmark. They are delivered separately (data carrier handed in with the thesis).

## Set-up
1. Install the environments of `environment/` (Python 3.8 with PyTorch for PIPs++, see `CODE_GUIDE.md`).
2. Clone the original PIPs++ code (https://github.com/aharley/pips2, commit 8b5bd9e) and copy `nets/`, `utils/`, `datasets/` and `saverloader.py` next to `run.py`.
3. Clone FlowVeloTool (https://github.com/AnetteEltner/FlowVeloTool, commit 7f40008) into `XY_Validation/ptv/flowvelo_src/`.
4. Put the pre-trained checkpoint into `reference_model/` and the data of the scene from the data carrier into the folders named in `CODE_GUIDE.md`.
5. `python run.py demo`.

Tested on macOS with an Apple M-series GPU (8 GB). Several long shell drivers contain the absolute path of the original project drive in their first line; change it to the local folder (see `CODE_GUIDE.md`).
