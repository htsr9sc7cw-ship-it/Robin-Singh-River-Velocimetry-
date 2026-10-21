# Pre-registration — dataset v2, both trackers (locked 2026-09-12, before any batch run)

Data: 16 viewpoints x 2 seeding densities (sparse 0.0006, dense 0.0025 tracers per water px),
frames 80-280, tracers composited from the scene's own particle-projected flow (FIXLOG S4).
One preliminary PIPs++ run exists (v2_low_angle_sparse: RMSE 17.574 px/frame, dU +16.30) and
is excluded from the predictions below, which concern the other 31 variants and all PTV runs.

Scoring: XY_Validation/PIP_Evaluation_gt.py with PIP_FIX_SIGN=1, PIP_N=256, for both trackers
(PTV via ptv/ptv_to_piprun.py). Endpoint error in px/frame at the 256-px working resolution.

## Predictions (falsifiable; each with the number that would refute it)
P1  PIPs++ (untrained) behaves as a near-stationary tracker on every variant: its RMSE lies
    within 0.8-1.2 x the stay-still baseline on >= 28 of 31 variants. Refuted if it beats the
    baseline by > 20 % on >= 4 variants.
P2  PTV tuned_lk recovers the mean flow DIRECTION within 15 deg (circular) on every SPARSE
    variant whose median displacement is < 25 px/frame (the slow viewpoints: Overview, the
    high/low-angle cameras, Path1/2/6/7 as far as their speeds allow). Refuted by > 15 deg on
    any of them.
P3  PTV's directional error is larger on DENSE than on SPARSE for every viewpoint (association
    ambiguity grows with tracer density at fixed displacement). Refuted if dense <= sparse on
    >= 4 viewpoints.
P4  PTV fails (median endpoint error > 0.8 x median displacement, i.e. no better than stay-
    still) on variants with median displacement > 40 px/frame (fast low cameras), because the
    search window and the 1 px backward tolerance cannot bridge it. Refuted if it succeeds on
    >= 2 of them.
P5  Eltner's filter cascade (paper values 30/120/30 deg, 65 %) retains >= 30 % of PTV tracks
    on sparse slow variants and < 5 % of PIPs++ tracks on every variant. Refuted by the reverse
    on >= 3 variants.
P6  Where PTV succeeds (P2 cases), its median endpoint error is below PIPs++'s on the same
    variant; its coverage (32x32 cells with >= 1 final track) is below PIPs++'s everywhere.
P7  The gui_defaults control (her GUI v3 values) yields < 10 final tracks on >= 24 of 32
    variants.
P8  Speed ratio measured/true for PTV lies in 0.9-1.1 where it succeeds; PIPs++'s is < 0.3
    on every variant (it does not move with the water).
P9  Neither tracker's result depends on the material: clear vs muddy variants of the same
    viewpoint differ by < 10 % in RMSE for PIPs++ and < 20 % for PTV.

## Hypothesis thresholds (for chapter 2.6; same as above): H1 = P2+P4, H2 = P1, H3 = P6,
H4 = P5, H5 = P8.

## Stop conditions
- Consistency acceptance (accept_consistency.py) fails on any rendered scene -> that scene is
  regenerated before scoring, not scored.
- A perfect-tracker control through the evaluator does not score < 0.05 px on v2 -> stop.
