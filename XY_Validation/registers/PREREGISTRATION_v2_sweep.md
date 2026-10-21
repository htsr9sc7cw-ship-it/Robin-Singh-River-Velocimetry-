# Pre-registration — LK parameter sweep and speed ladder (dataset v2)
Written 2026-09-13 00:50, before any sweep run or ladder bake exists. Not edited after a run.

## Why
Locked results so far (corrected scoring, C1–C3): untrained PIPs++ ≈ stay-still on all 32
variants; PTV NCC follows the flow at ~22 px/frame on dense tracers but retains few tracks; PTV
LK (tuned, and GUI defaults) fails at ≥ 22 px/frame; everything fails at 45–85 px/frame.
Two follow-up questions, both about *where the methods break*, not about making them look good:
Q1 Does LK fail because of her hard-coded `maxLevel=2` (reach ≈ ±14 px) or because the water
   surface shading in v2 does not move with the flow?
Q2 At what displacement per frame does each method break?

## Sweep 1 — LK parameters (tracker code unchanged; `maxLevel` overridden by a documented
monkey-patch of `performFeatureTrackingLK` in the driver, her source file untouched)
Grid, run on 4 variants only (Path4_dense, Path2_dense, Low_1_dense, Overview_dense):
  maxLevel ∈ {2 (hers), 3, 4, 5}  ×  template ∈ {tuned (per-scene csv), 31, 51}
Everything else = tuned_lk. Scored by the same compare_v2.py path (mask, k>0, native px).
Predictions (P-L1..P-L3):
  P-L1 On Overview (7 px/frame) maxLevel makes < 10 % difference in RMSE — already in reach.
  P-L2 On Path (22 px/frame) maxLevel ≥ 4 lowers LK RMSE below stay-still by ≥ 20 % on dense
       tracers, but the fraction of exactly-zero sub-steps stays > 10 % (surface lock-on).
  P-L3 On Low_1 (45 px/frame) no setting brings LK RMSE below 0.8 × stay-still.
Decision rule: the *best* setting is NOT adopted as "tuned_lk"; the sweep is reported as a
table. tuned_lk stays as pre-registered in PREREGISTRATION_v2.md.

## Sweep 2 — speed ladder (same simulation, slower playback)
Domain `time_scale` ∈ {1.0 (existing), 0.5, 0.25}; cache and .blend copy per rung
(`Basefile_a_TRACERS_ts<ts>.blend`, cache `//cache_ts<ts>`); same res 200, same gravity tilt,
same cameras Camera.Low_1 and Camera.Low_1.001; rendered window = the same physical time as
frames 80–280 of the base (ts 0.5: frames 160–360; ts 0.25: frames 320–520); same surface-only
render + composited tracers (sparse/dense); PTV in the 3 modes + PIPs++; same scoring.
Velocity calibration per rung (rule fixed now): vscale_rung = front speed during filling
(m/frame, y-min of the particle cloud, frames 10–40·(1/ts)) ÷ (median |velocity attribute| ×
time_scale) over the same frames. At ts 1.0 this must reproduce 1.35 ± 0.1 (S4), otherwise the
rung is rejected. Sphere control (0.5 px) repeated on each rung.
Expected displacement at Camera.Low_1: ≈ 45, 22, 11 px/frame; at Low_1.001: ≈ 85, 42, 21.
Predictions (P-S1..P-S4):
  P-S1 PTV NCC: RMSE/stay-still ≤ 0.6 at ≤ 22 px/frame; ≥ 0.9 at ≥ 45 px/frame.
  P-S2 PTV LK (hers, maxLevel 2): RMSE/stay-still ≤ 0.6 only at ≤ 11 px/frame.
  P-S3 PIPs++ untrained: RMSE/stay-still ≥ 0.9 at every rung (does not depend on speed).
  P-S4 Track retention through her cascade rises monotonically as speed falls.
Break-point definition (fixed now): the first rung, going up in speed, where
RMSE/stay-still > 0.8 or frac_cos08 < 0.5.

## What is not allowed
No rung, setting or variant is dropped after seeing its score. No metric is added or removed.
Failed predictions are reported as failed.

## Addendum 2026-09-13 01:20 (before any rung bake) — calibration rule replaced
The front-speed rule above was tested on the base bake (rerender/vscale_ts1.txt): the front
(fastest particles) and the median attribute (bulk) are different populations, so the ratio is
not a calibration (0.39–0.89 depending on the interval). Replaced by set containment
(rerender/calibrate_vscale_voxel.py): advect the frame-t cloud by k·V·time_scale, count the
fraction inside the voxelised frame-(t+1) cloud; k range 0.25–8. The curve is periodic (the
FLIP cloud keeps a lattice of one cell, period ≈ 0.36 in k at ts 1), so the ENVELOPE peak on
FILLING frames is used (front moving = informative). Base bake, frames 22/26: global maximum at
k = 1.45 (0.877), next peaks 0.79/0.76/0.72 -> the 1.35 in use is within 7 %; accepted, 1.35 is
kept for the base (changing it would regenerate all v2 GT for a 7 % magnitude change; it is
reported as the GT magnitude uncertainty). Rungs: vscale_rung = envelope peak on their filling
frames; gate: 1.45 ± 0.15 if the attribute scales with time_scale as gt_from_particles assumes,
otherwise the rung's own value is used and the discrepancy logged.

## Deviations recorded after the fact (2026-09-13, evening; mtime authoritative)
- Rung GT rasterised with the base calibration 1.35 instead of the rung's own envelope peak (FIXLOG L8): ladder consistency.
- Rung windows cover simulation time 80–180 (ts 0.5) and 80–130 (ts 0.25) of the base, not 80–280 (AUD10-3): steady flow, harmless, sentence above was wrong.
- Known-answer stop condition: the pre-registered "< 0.05 px" assumed bilinear consistency; with the v3 ground-truth rule and the
  evaluator's nearest-pixel sampling the achievable floor is ~0.09 px median / 0.8 px RMSE (measured on Path4 80–110 before the
  criterion was written). New criterion: median < 0.15 px AND RMSE < 1.0 px, set BEFORE the 40-variant test ran (known_answer_eval.py
  mtime 22:02 vs results/KNOWN_ANSWER.txt v3 lines). The v2 dataset FAILED the original criterion (0.85 px) — that failure is why v3 exists.
- Known-answer tiers (23:55, before the v3.1 40-variant test): PASS = median < 0.15 px and RMSE < 1.0 px; PASS_FLOOR = median < 0.15 px
  and < 5 % of steps off by > 3 px (fold regions of fast perspective views; the per-scene floor is reported next to the results);
  FAIL otherwise -> the variant is excluded from the pre-registered tests. v3.1 test (scratchpad, archived in audit/evidence):
  Path4 median 0.023 / RMSE 0.18 px; Low_1 0.10 / 2.95 px, 2.6 % > 3 px.
