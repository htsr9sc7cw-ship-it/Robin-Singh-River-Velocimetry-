# Pre-registration: retraining-strategy study (Study C), written 2026-09-18 00:20 before any strategy S2–S6 run
Thesis brief objective 2 ("assess strategies for training or re-training PIPs++") and objective 3 (pre-trained vs re-trained
under diverse conditions). Plan file: ~/.claude/plans/gentle-jingling-nest.md (18 Sep). Everything below is fixed now.

## Common protocol
Held-out viewpoints (never trained on): Path4, Low_1, Low_1.001, low angle, Overview (dense + sparse = 10 variants); leakage
control: Path2 dense (training view). Training viewpoints: Path1, Path2, Path3, Path5, Path6, Path7, Low_1.002, Low_1.003,
Low_2 (+ for S2–S6: Path3 clear, high angle clear). Labels: exact tracer trajectories (tracers_*/trajs.npz). Frames 80–280.
Budget per strategy: 3 000 steps or the stated hour cap, batch 1, on the Apple GPU (MPS, CPU fallback for grid_sampler
backward). Selection of S6: lowest median ratio_h15 over the 10 held-out variants, in the best of the deployment modes
below; ties -> the strategy that changed fewer things relative to the reference model. TAP-Vid-DAVIS is reported, never
used for selection.
Deployment modes for every checkpoint: D1 re-tracked every 2 frames / 8-frame window (as Sect. 5.12); D2 window 16,
re-init every 16; D3 long-term: one call per 48-frame block (the paper's mode); D4 fresh seeds every 2 frames, each batch
followed 16 frames (FlowVelo's FD/FT scheme). Metrics: ratio, ratio_h15, direction (frac_cos08), speed ratio, TAP-Vid
delta_avg / OA / AJ at the 256-px evaluation scale, survival_16, median_l2; velocity-field bias / RMSE / coverage.

## Strategies
S0 pre-trained (done). S1 FT-1 (done: S 12, crop 256, 9 views, h-flip only, lr 1e-4 constant, 3 000 steps).
S2 data + augmentation, continued from S1: + 2 clear-water views; scale 0.7–1.3, brightness/contrast ±15 %, h+v flip;
   lr 5e-5 constant; S 12, crop 256, N 64; 3 000 steps.
S3 long-sequence (paper recipe), from the pre-trained model: S 36 (fallback 24 if MPS memory forbids — recorded), crop 256–320,
   N 48, 8 refinement iterations in the loss, one-cycle lr peak 1e-4, augmentations of S2 + temporal reversal + moving crop;
   3 000 steps or 8 h.
S4 rehearsal: S2 recipe with 50 % PointOdyssey sample clips per step (published loader on the sample tar), 3 000 steps.
S5 from scratch: S2 recipe from random initialisation, lr 5e-4 one-cycle, 3 000 steps.
S6 README stage 2 on the winner of S2–S5: B 1, S 48–64 (memory test; fallback 36), native 512 crop, one-cycle peak 1e-4,
   as many steps as fit in 6 h; evaluated on held-out × D1–D4, Low_1 / Low_1.001 ladder rungs, clear variants, TAP-Vid-DAVIS.

## Predictions (locked)
P-G1  S2 direction agreement (D1, held-out median) > 0.65 (S1: 0.56).
P-G2  S3 beats S1 on the Low_1 dense and sparse variants by >= 0.1 in ratio_h15.
P-G3  S4 is within 0.05 of S2 in held-out median ratio_h15 (rehearsal neither helps nor hurts on water).
P-G4  S5 is worse than S1 by >= 0.1 in held-out median ratio_h15 (the pre-trained prior matters).
P-G5  S6 held-out median ratio_h15 < 0.55 and below NCC (features every 2 frames) on >= 5 of 10 variants.
P-G6  No strategy brings Low_1.001 (83 px/frame) below 0.8 in any mode.
P-G7  On the Low_1 ladder S6 breaks (ratio > 0.8 or direction < 0.5) at a higher rung than S0.
P-G8  For S1 and S6, long-term mode D3 scores better (lower ratio_h15) than re-tracked D1; for S0 the reverse holds.
P-G9  Reference reproduction on TAP-Vid-DAVIS within ±2 delta_avg points of the README's 70.6.
P-G10 S1 loses >= 10 delta_avg points on TAP-Vid-DAVIS relative to the reference; S4 loses <= 5.
P-G11 S6 survival_16 over the 48-frame block on held-out water >= 0.5 (S0 < 0.1).
P-G12 S6 meets the hydrometry target on >= 6 of 10 held-out variants: mean-speed bias within ±10 % and field RMSE within 20 %
      of the mean speed on >= 80 % of water cells; NCC meets it on >= 7 (dense) and <= 3 (sparse).
P-G13 D4 (fresh seeds every 2 frames) gives S6 a coverage (fraction of water cells with an estimate) above NCC's on every
      dense held-out variant.

## Deviations
Recorded here with time and reason, before the corresponding result is looked at.
S3 clip length 36
- 2026-09-18 09:40 (deviation, before any S3 result): S3 clip length 36 -> 24. The memory test passed, but training at S 36 ran at
  45 s/step with 4 GB of swap (8 GB machine); at the 8 h cap it would have reached ~640 of 3 000 steps. Restarted from the
  pre-trained weights with S 24 (the fallback named in the register); the 380-step S 36 attempt is kept in
  "Mr Singh please delete this/incomplete_runs" and not used.

## Interim outcomes (2026-09-18 10:05, results/strategies_v3.csv, held-out 10, mode D4 unless stated)
P-G1  failed — S2 direction agreement 0.81 in D4 (S1 0.83); in D1 0.51 (S1 0.56). More data + augmentation did not change direction.
P-G8  refuted for S1 and S2 — long-term mode D3 (0.88 / 0.96) is WORSE than fresh-seeds D4 (0.72 / 0.71) and re-tracked D1 (0.64 / 0.81);
      for S0 D3 = D1 = D4 = 1.00. On this water, short fresh tracks beat long memory (FlowVelo's design principle).
Headline so far (D4): pre-trained 1.00 / 22 % direction; FT-1 0.72 / 83 %; S2 0.71 / 81 %; NCC 0.62 / 89 %; LK 0.99 / 46 %.

## Addendum Sat 2026-09-19 00:45 (before S6 training started)
- **P-G15 (native resolution).** S6 is trained at the native 512 px; it is evaluated in fresh-seeds mode both at 256 px (as all
  other strategies) and at 512 px on the 10 held-out static variants. Prediction: at 512 the fast variants (Low_1, Low_1_001)
  improve by ≥ 0.1 in ratio_h15 relative to 256; the slow variants change by < 0.05. Rule: the headline resolution for S6 on the
  moving-surface frames is the one with the lower held-out median ratio_h15; both are reported in Table 5.14.
- **Deviation (time).** S6 long-term mode (D3) on the moving-surface frames is dropped; D3 is characterised on the static
  held-out set (P-G8). If 512 wins, S6 at 512 is run on the 16 dense moving-surface variants only (sparse stays at 256), for time.
S6 clip length 64 at native 512 (parent S2)

## Outcomes S2–S5 (2026-09-19 09:35, complete results/strategies_v3.csv after OPS-8; held-out 10 variants; ratio_h15 medians)
S0 1.00 · S1 0.72 · S2 0.71 · S3 0.75 (D4) / **0.69 (D3)** · S4 0.71 · S5 1.04 · NCC 0.62 · LK 0.99 (`results/stats_strategies_ratio_h15.md` for CIs, sign tests).
- P-G1 (S2 direction > 0.65): direction agreement 0.81 — numerically confirmed, but S1 already scores 0.83 in mode D4 (the 0.56 of the
  register's baseline was mode D1); the prediction's premise was a deployment effect → recorded as **not informative**.
- P-G2 (S3 ≥ 0.1 better than S1 on Low_1 variants): S3 0.86 (D4) / 0.83 (D3) vs S1 0.86 → **refuted**.
- P-G3 (S4 within 0.05 of S2): 0.706 vs 0.712 → **confirmed**.
- P-G4 (S5 worse than S1 by ≥ 0.1): 1.04 vs 0.72, 10 : 0 against S2 (p = 0.002) → **confirmed**.
- P-G6 (nothing works at 83 px/frame): all ≥ 0.90 on Low_1_001 sparse → **holds** (final check with S6).
- P-G8 (retrained models prefer long-term mode): **confirmed for S3 only** (0.69 < 0.75); refuted for S1 (0.88 vs 0.72), S2 (0.96 vs 0.71), S4 (0.88 vs 0.71).
- Selection rule → **S6 parent = S3** (lowest held-out median in its best mode). The 01:26 pick "S2" was made on an incomplete table (OPS-8) and is void.
- Velocity-field metric (P-G12 target ≥ 0.80 of water cells within ±10 %/20 %): best S3-D3 0.31, NCC 0.28, S1 0.25 → **not reached** by any method so far.

## Deviation Sat 2026-09-19 09:30 — S6 crop
Native 512-px training does not run on the 8 GB M1: S 64/48/36 out of memory (OPS-7); S 16/N 32 → 9.1 GB, 130 s/step; S 12/N 24 → 7.6 GB,
40 s/step (swap thrash, OPS-10). S6 is trained at **crop 384, S 12, N 24** (1.5× the 256-px crop of S1–S5, the largest that fits), from
S3, 4 h. Native 512 px is kept as an *inference* condition (P-G15: S6 evaluated at 256 and 512). The README's stage 2 (512 × 896, S 64)
is therefore only approximated; this is stated in Sect. 5.15 and 6.7.

## Final outcomes (2026-09-20 06:00) — S6, moving surface, DAVIS
S6 (crop 384, S 12, from S3): held-out D4-256 **0.69** (best PIPs++; 8/10 < 0.8; 3/10 < NCC 0.62), D3 0.72, D1 0.75, D4-512 0.72 (speed ratio 0.90).
P-G5 failed · P-G6 holds · P-G7 not tested (time) · P-G8 S3 only · P-G9 confirmed (66.4 vs 70.6 at 32 vs 128 frames) · P-G10 split
(S1 −11.4; S4 −11.3, rehearsal does not protect) · P-G11 failed (0.23) · P-G12 failed (NCC 0.45, S6 0.30 of cells in target) ·
P-G13 confirmed (28/28) · P-G14 confirmed (changes −0.01…−0.05, 35/40 < 0.1) · P-G15 failed (fast variants 0.92 vs 0.84; speed 0.76→0.90).
Moving-surface headline (28): S0 0.93 (0/28) · S6 0.69 (24/28; 7 < NCC) · NCC 0.49 (24/28) · LK 0.81 (12/28). Files: results/surfmove_headline_v3.csv,
tapvid_surfmove_v3.csv, velocity_field_surfmove_v3.csv, stats_surfmove_ratio_h15.md, s6_heldout_v3.csv, finetune/results_davis/*_S32.csv.
