# FlowVelo PTV versus untrained PIPs++ on rendered river scenes — summary of results
Dataset v3 (own re-render of the Elbersdorf reach, 14 muddy + 2 clear viewpoints × {sparse, dense} foam-like tracers, frames 80–280,
ground truth verified per variant by a known-answer test: 34 PASS / 7 PASS_FLOOR / 0 FAIL). All numbers in native px/frame.
"ratio" = RMSE of the tracked displacement ÷ RMSE of a tracker that reports no motion (1.0 = no skill). Every value comes from
three_way_v2.csv / speed_ladder_v2.csv / lk_sweep_v2.csv / blind_ptv_v2.csv / surfmove_control_v2.csv (independently recomputed, AUD21-6).

## 1. Overall comparison (medians over the 28 muddy-water variants)
| method | ratio | direction right (cos>0.8) | speed measured/true | variants with ratio < 0.8 |
|---|---|---|---|---|
| PIPs++ untrained, grid seeds | 0.99 | 28 % | 0.04 | 0 / 28 |
| PIPs++ untrained, seeded on FlowVelo's features | 0.99 | 28 % | 0.04 | 0 / 28 |
| **FlowVelo NCC, tuned** | **0.62** | **94 %** | **1.00** | **23 / 28** |
| FlowVelo LK, tuned (her maxLevel 2) | 0.97 | 62 % | 0.09 | 2 / 28 |
| FlowVelo LK, GUI defaults | 1.02 | 27 % | 0.15 | 0 / 28 |

## 2. Effect of tracer density: FlowVelo NCC ratio 0.73 (sparse) → 0.30 (dense); no effect on PIPs++ or the GUI defaults.

## 3. Lucas–Kanade pyramid depth (RMSE ratio; the published code fixes maxLevel = 2)
| view (px/frame) | L2 (published) | L3 | L4 |
|---|---|---|---|
| Overview (14) | 0.50 | 0.20 | 0.20 |
| Path2 (24) | 0.80 | 0.34 | 0.27 |
| Path4 (23) | 0.92 | 0.21 | 0.13 |
| Low_1 (48) | 1.00 | 1.00 | 1.00 |

## 4. Speed ladder: RMSE ratio versus flow speed (same simulation at playback 1, 0.5 and 0.25; dense tracers)
| px/frame | 8 | 21–22 | 46–48 | 83 |
|---|---|---|---|---|
| NCC (Low_1 / Low_1.001) | 0.47 / – | 0.50 / 0.24 | 1.07 / 0.36 | – / 0.63 |
| LK maxLevel 2 | 0.59 / – | 0.87 / 0.64 | 1.00 / 1.01 | – / 1.00 |
| GUI defaults | 0.98 / – | 1.02 / 1.01 | 1.00 / 1.01 | – / 1.00 |
| PIPs++ | 0.93 / – | 0.99 / 0.90 | 1.00 / 1.00 | – / 1.00 |
Break points (pre-registered rule): NCC 22–47 px/frame on the compressed view, none up to 83 on the other; LK ≈ 21; defaults < 8; PIPs++ none.

## 5. Control experiments
- Clear vs muddy water (Path3): NCC 0.30 vs 0.30, PIPs++ 0.99 vs 0.97 — no material effect.
- Moving surface texture (surface warped with the flow): PIPs++ 0.94 vs 0.97, LK 0.86 vs 0.92 — the static surface is not why PIPs++ fails.
- Blind-tuned PTV (speed prior from the images, not the ground truth): NCC 0.80 dense / 1.38 sparse — the oracle prior matters on sparse seeding.

## 6. The published filter cascade at these displacements
Retains 0–2 % of tracks (min-count criterion removes 93–99 %; steadiness removes another 42–58 %, of which 20–29 points come from a
quadrant bug in the direction computation — corrected pass: NCC 627 → 809 final tracks).

## 7. Pre-registered predictions: 16 locked before the runs; 8 confirmed, 7 failed (5 because the tools did better than predicted), 1 split.

Figures: figA (ratio vs speed), figB (δ-accuracy per speed group), figC (direction + speed ratio), figD (cascade), figE (sparse vs dense),
figF (worked example Path4: GT / NCC / PIPs++), figG (ladder); GIFs: gif_example_{Path4,Low_1_001,Overview}_dense.
