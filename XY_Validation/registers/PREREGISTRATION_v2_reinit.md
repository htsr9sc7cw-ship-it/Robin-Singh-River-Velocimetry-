# Pre-registration: re-initialised PIPs++ and matched-cadence PTV (Study A / A')
Written 2026-09-16 before any run. Trigger: the supervisor's feedback at the 2026-09-16 meeting — the GIFs show PIPs++ seeding its
points once per 48-frame block and never re-seeding; he asked for tracking re-initialised every frame or every 2 frames.

## What is run
PIPs++ (untrained reference checkpoint model-000200000.pth, iters 16, N 256 grid, blocks of 48 frames from frame 80 as
before) with `PIP_Execution_reinit.py`: inside every block the tracker is re-initialised at its own tracked positions
every k frames (features re-sampled at the current frame, model window PIP_WIN = 8 frames), steps chained.
Factors: k in {1, 2} (supervisor), working resolution r in {256 (as all runs so far), 512 native};
control: k = 48 at 512 (no re-init, only the resolution changes). Suffixes _r1_256 _r2_256 _r1_512 _r2_512 _r48_512.
Sanity: _r48_256 must reproduce the existing grid run (max |dx| < 1e-3 px) — the chaining code is a no-op at k = 48.

FlowVelo at the same re-detection cadence: `FD_everyIthFrame` 1 and 2 (today 0.75*FT = 4..15) for tuned_ncc and tuned_lk,
all other parameters as in ptv_params.csv; modes tuned_ncc_fd1, tuned_ncc_fd2, tuned_lk_fd1, tuned_lk_fd2.
Adapter `ptv_to_piprun.py --block-len 48` so blocks and the per-track horizon (15) match the PIPs++ rows.

Pilot variants: v2_Path4_dense, v2_Path4_sparse, v2_Low_1_dense, v2_Low_1_sparse (the LK-sweep four).
Then the best PIPs++ setting (lowest median ratio over the four; ties -> fewer model calls) on all 28 muddy variants,
with the PTV mode of the same cadence.

Scoring: unchanged contract (compare_v2.metrics: native px, k = 0 of each block excluded, border steps excluded,
dropout mask, |truth| > 1e-3). ratio = RMSE / stay-still RMSE; broken = ratio > 0.8 or frac_cos08 < 0.5 (sweep rule).

## Predictions (locked)
P-R1  Re-initialising at 256 px changes the PIPs++ ratio by < 0.1 on every pilot variant (tracers are 0.75-1.75 px at 256).
P-R2  512 native improves the PIPs++ ratio by >= 0.2 on Path4 dense for every k.
P-R3  At 512: ratio(k=1) <= ratio(k=2) <= ratio(k=48).
P-R4  No untrained PIPs++ setting reaches NCC's ratio (0.30) on Path4 dense.
P-R5  NCC at fd1/fd2 changes NCC's ratio by < 0.05 on each pilot variant (more tracks, same per-step error).
P-R6  LK at fd1/fd2 stays broken (ratio > 0.8) on every pilot variant.

## Deviations
Recorded below with date and reason before results are looked at.

## Outcomes (pilot scored 2026-09-17 03:17, results/pips_reinit_pilot.csv; numbers = RMSE ratio)
P-R1  confirmed — re-init at 256 changes the ratio by 0.06 on Path4 (0.970 -> 0.913 dense, 0.997 -> 0.943 sparse) and < 0.01 on Low_1; all < 0.1.
P-R2  failed — 512 native does not improve Path4 dense at any k (k=1 0.976, k=2 0.984, k=48 0.997 vs 0.970 at 256); 256 is better than 512.
P-R3  failed (strictly) — at 512 the order k=1 <= k=2 <= k=48 holds on Path4 (0.976, 0.984, 0.997) and Path4 sparse (0.976, 0.986, 0.999)
      but not on Low_1 (1.003, 1.004, 1.000; differences within 0.004).
P-R4  confirmed — best untrained setting 0.913 (r1_256, Path4 dense) vs NCC 0.253.
P-R5  failed on the fast view — NCC fd1/fd2 changes the ratio by < 0.01 on Path4 (0.253 -> 0.258 / 0.257; 0.702 -> 0.698 / 0.719)
      but by -0.13 / -0.10 on Low_1 dense (1.074 -> 0.946 / 0.970) and -0.09 / -0.06 on Low_1 sparse (1.202 -> 1.117 / 1.139);
      scored sub-steps rise 5-10x (Path4 dense 2 887 -> 28 804). On Low_1 sparse the fd1 median speed ratio collapses to 0.06
      (0.71 at the published cadence): the extra batches add mostly near-stationary false matches there.
P-R6  confirmed — LK fd1/fd2 0.895-1.001 on every pilot variant.
Winner by the locked rule: r1_256 (median ratio over the four 0.968; r2_256 0.985, r1_512 0.987, r2_512 0.993, r48_512 0.999).
Direction agreement of the winner 0.49 on Path4 (0.30 before), speed ratio 0.14 (0.05 before): re-initialisation makes the
untrained network move with the water, but at one seventh of its speed.

## Deviation (2026-09-17 12:00, before any all-28 every-2-frames result exists)
The author fixes the headline comparison at re-tracking EVERY 2 FRAMES for both trackers (PIPs++ re-initialised every 2
frames at 256 px; FlowVelo features every 2 frames), on all 28 muddy variants and for the fine-tuned checkpoints, instead of
the pilot winner (every frame). Reason: a single, symmetric cadence for the whole study, chosen by the author with the
supervisor's request in mind. The every-frame results (all 28, untrained; 3 held-out fine-tuned rows) are kept and reported
as supplementary rows; the once-per-48 rows remain as the inherited baseline.
