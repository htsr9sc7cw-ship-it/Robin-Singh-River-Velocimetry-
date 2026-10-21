# Pre-registration: fine-tuned PIPs++ on the Elbersdorf renders (Study B)
Written 2026-09-17 before any training. The supervisor (2026-09-16) also asked whether PIPs++ can be trained so that it tracks
properly; the thesis' main axis stays "untrained", this is the second axis.

## Data
Labels: rerender/out/v2/<view>/tracers_<density>/trajs.npz — the exact 2-D trajectories of every composited tracer
(frames 80-280, valid/visible flags), i.e. the same tracers the trackers see. No other supervision.
Training views (dense + sparse): Path1, Path2, Path3, Path5, Path6, Path7, Low_1_002, Low_1_003, Low_2.
Held-out views, never seen in training: Path4, Low_1, Low_1_001, low_angle, Overview (10 variants) — the views the
thesis reports in detail — plus the speed-ladder rungs of Low_1 / Low_1_001.
Clips: S = 12 consecutive frames, random 256x256 crop at native scale (no resize: tracers are 1.5-3.5 px), N = 64
points valid+visible in the first two frames, horizontal flip as the only augmentation (reverses flow direction,
keeps tracer appearance). Initialisation as in pips2 train.py (random / ground-truth mix / zero-velocity).

## Training
Start from the reference checkpoint model-000200000.pth; AdamW, lr 1e-4 (5x lower than from-scratch), weight decay
1e-6, 6 refinement iterations in the loss (pips2 default), batch 1, gradient clipping 1.0, sequence loss of pips2
unchanged. Budget: max_iters 3000 or 8 h, whichever first (measured before training: ~6 s/it at S=8, 256 crop with the MPS
CPU fallback for grid_sampler backward; S=24/384 would be ~50 s/it = 42 h, not feasible); checkpoints every 500 iterations (all kept).
Device: Apple MPS (PYTORCH_ENABLE_MPS_FALLBACK=1 for the sampler backward).

## Evaluation
Every checkpoint through the unchanged pipeline: PIP_Execution_reinit.py with PIP_CKPT_DIR, the best Study-A setting
(k, resolution) from results/REINIT_WINNER.txt, same evaluator, same compare_v2.metrics. Rows PIPs++_ft<iter>_<winner>.
Held-out variants only in the headline table; one training view (Path2 dense) is scored once and labelled
"training view" as a leakage control, never mixed into the held-out table.

## Predictions (locked)
P-F1  Fine-tuned ratio on held-out Path4 dense < 0.5 (untrained best Study-A value expected > 0.8).
P-F2  Direction agreement (frac_cos08) on held-out dense variants > 0.8.
P-F3  On the Low_1 / Low_1_001 ladder the fine-tuned model breaks at a higher speed than the untrained one.
P-F4  On sparse held-out variants the fine-tuned model stays worse than NCC (ratio higher).
P-F5  The training-view control scores better than the held-out views (otherwise the split is not doing anything).

## Deviations
Recorded here with date and reason before results are looked at.
- 2026-09-17 00:30 (before training): clip S 24 -> 12 and crop 384 -> 256 for compute (see Training); the evaluation window is 8 frames, so 12-frame clips cover it.

## Outcomes (2026-09-17 16:35, results/finetune_v3.csv; every-2-frames cadence per the REINIT-2 deviation; ratio_h15 = equal 15-frame horizon, see FIXLOG E-1)
P-F1  confirmed on the equal horizon (Path4 dense ratio_h15 0.50; per-step ratio 0.85 — see E-1), i.e. borderline.
P-F2  failed — direction agreement on held-out dense variants 0.56-0.76 (median 0.70 dense), below 0.8.
P-F3  not testable as planned: the ladder rungs were not evaluated (compute); on the base rungs the fine-tuned model works on
      Low_1 (48 px/frame: 0.63) where the untrained one is at 1.00, and neither works at 83 px/frame — consistent with the prediction.
P-F4  split — on the 5 sparse held-out variants the fine-tuned model is worse than NCC on 3 (low angle 0.53 vs 0.38, Overview 0.79 vs 0.59, Low_1.001 1.01 vs 0.83) and better on 2 (Path4 0.44 vs 0.66, Low_1 0.61 vs 1.13); ratio_h15.
P-F5  confirmed — training view Path2 dense 0.71 vs held-out median 0.88 (per-step ratio).
